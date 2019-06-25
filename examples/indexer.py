"""

Learning Phase
    - Stream MFCC features, maintaining a reservoir of N samples
    - Draw M samples at a time from the reservoir, at random
    - learn K-Means clusters for overlapping, unit-normed triplets of frames in
        a streaming fashion


Indexing Phase
    - stream MFCC features
    - get one-second, non-overlapping frames
    - compute K-means clusters for each MFCC triplet and pool into a single
        binary vector
    - Build a brute force, hamming distance index

Search Phase
    - serve the index over HTTP

Questions/Things to consider
    - In practice, the resources needed in the learning and indexing phases
        are likely to be very different.  Figure out a simple workflow for this
    - Unlike cochlea, where the index was baked in, codes for the fixed length
        segments won't be returned from other possible searches, so indexes
        should be capable of computing features on the fly and/or accepting
        just a sound id and time stamp, locating the correct feature, and
        performing the search
"""

import zounds
from log import module_logger
from client import Client
from cli import DefaultArgumentParser
from bot_helper import BinaryData, retry
import argparse
import requests
import numpy as np
import threading
import time
from sklearn.cluster import MiniBatchKMeans
from gunicorn.app.base import BaseApplication
import falcon
import base64

logger = module_logger(__file__)


def mfcc_stream(client):
    bot = retry(client.get_user, 30)('mfcc')

    low_id = None

    def fetch(low):
        resp = client.get_annotations(
            bot['id'], low_id=low, page_size=100)
        items = resp['items']
        try:
            return items[-1]['id'], items
        except IndexError:
            return low, items

    low_id, items = fetch(low_id)
    while items:
        yield from items
        low_id, items = fetch(low_id)


def infinite_mfcc_stream(client):
    """
    Loop over MFCC annotations endlessly
    """
    while True:
        yield from mfcc_stream(client)


def compute_feature(annotation):
    resp = requests.get(annotation['data_url'])
    arr = BinaryData.unpack(resp.content)

    # sliding window
    _, arr = arr.sliding_window_with_leftovers(3, 1, dopad=True)
    dims = arr.dimensions

    # unit norm
    orig_shape = arr.shape
    arr = arr.reshape((arr.shape[0], -1))
    norms = np.linalg.norm(arr, axis=-1, keepdims=True)
    arr /= (norms + 1e-8)
    arr = arr.reshape(orig_shape)
    arr = zounds.ArrayWithUnits(arr, dims)

    return arr


def infinite_feature_stream(client):
    for item in infinite_mfcc_stream(client):
        arr = compute_feature(item)
        _id = item['id']
        yield _id, arr


def fill_reservoir(client, reservoir, should_stop):
    for _id, arr in infinite_feature_stream(client):
        if should_stop:
            break
        logger.info(f'pushing {_id} into reservoir')
        reservoir.add(arr)


def train_model(client, n_iterations=10000, batch_size=256):
    reservoir = zounds.learn.Reservoir(10000, dtype=np.float32)
    should_stop = []
    t = threading.Thread(
        target=fill_reservoir,
        args=(client, reservoir, should_stop),
        daemon=True)
    t.start()

    model = MiniBatchKMeans(
        n_clusters=128,
        max_iter=n_iterations,
        batch_size=batch_size)

    batch = 0
    while batch < n_iterations:
        try:
            train_data = reservoir.get_batch(batch_size)
            model.partial_fit(train_data.reshape((train_data.shape[0], -1)))
            batch += 1
            logger.info(f'Training on batch {batch} of {n_iterations}')
        except ValueError as e:
            logger.error(e)
            time.sleep(1)
            continue

    should_stop.append(True)
    return model


def build_index(client, model):
    chunks = []
    time_slices = []
    current_offset = 0
    sound_offsets = {}

    for annotation in mfcc_stream(client):
        feature = compute_feature(annotation)

        # TODO: magic number 42
        _, windowed = feature.sliding_window_with_leftovers(42, dopad=True)

        # TODO: This is being set repeatedly because I don't have the times
        # factored out
        time_dimension = windowed.dimensions[0]
        frequency = time_dimension.frequency
        duration = time_dimension.duration

        original_shape = windowed.shape[:2]
        flattened_dim = windowed.shape[-2] * windowed.shape[-1]
        windowed = windowed.reshape((-1, flattened_dim))

        cluster_ids = model.predict(windowed)

        sparse = np.zeros((len(cluster_ids), model.n_clusters), dtype=np.uint8)
        sparse[np.arange(len(cluster_ids)), cluster_ids] = 1
        sparse = sparse.reshape(original_shape + (-1,))

        pooled = sparse.max(axis=1)

        # TODO: This should all be encapsulated in an index class
        packed = np.packbits(pooled, axis=-1).view(np.uint64)
        chunks.append(packed)
        sound_id = annotation['sound']
        logger.info(f'building index for {sound_id}')
        time_slices.extend(
            (sound_id, zounds.TimeSlice(start=i * frequency, duration=duration))
            for i in range(len(packed)))
        sound_offsets[sound_id] = current_offset
        current_offset += len(packed)

    index = np.concatenate(chunks)
    return frequency, index, time_slices, sound_offsets


class StandaloneApplication(BaseApplication):
    def __init__(self, app, bind):
        self.application = app
        self.bind = bind
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        self.cfg.set('bind', self.bind)

    def load(self):
        return self.application


class IndexResource(object):
    def __init__(self, frequency, index, time_slices, sound_offsets, user_uri):
        self.sound_offsets = sound_offsets
        self.user_uri = user_uri
        self.frequency = frequency
        self.index = index
        self.time_slices = time_slices

    def _get_code(self, sound, seconds):
        frequency = self.frequency / zounds.Seconds(1)
        offset = self.sound_offsets[sound]
        window_index = offset + int(seconds / frequency)
        return self.index[window_index]

    def _transform_indices(self, indices):
        for index in indices:
            sound_id, time_slice = self.time_slices[index]
            start = time_slice.start / zounds.Seconds(1)
            duration = time_slice.duration / zounds.Seconds(1)
            data = {
                'created_by': self.user_uri,
                'sound': sound_id,
                'start_seconds': start,
                'duration_seconds': duration,
                'end_seconds': start + duration
            }
            yield data

    def on_get(self, req, resp):
        """
        Queries will arrive in one of two forms:
            - a sound id and a point in time
            - a base-64 encoded packed code
        """
        sound = req.get_param('sound')
        seconds = req.get_param_as_float('seconds')
        nresults = req.get_param_as_int('nresults') or 10

        if sound and seconds is not None:
            # TODO: errors here should result in a reasonable HTTP error code
            code = self._get_code(sound, seconds)
        else:
            encoded = req.get_param('code')
            binary = base64.urlsafe_b64decode(encoded)
            code = np.fromstring(binary, dtype=np.uint64)

        dist = zounds.nputil.packed_hamming_distance(code, self.index)
        indices = np.argsort(dist)[:nresults]
        resp.media = {
            'total_count': len(indices),
            'items': list(self._transform_indices(indices))
        }
        resp.set_header('Access-Control-Allow-Origin', '*')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[DefaultArgumentParser()])
    parser.add_argument(
        '--train',
        action='store_true')
    parser.add_argument(
        '--iterations',
        type=int,
        default=10000)
    parser.add_argument(
        '--bind',
        default='0.0.0.0:8080')
    args = parser.parse_args()

    api_client = Client(args.annotate_api_endpoint, logger=logger)
    # TODO: Should I introduce an indexer user type, since anonymous access
    # isn't allowed?
    user_uri = api_client.upsert_user(
        'mfcc_index',
        'john.vinyard+mfcc_index@gmail.com',
        args.password,
        'I index MFCC features',
        'https://example.com')

    # train the model
    if args.train:
        model = train_model(api_client, n_iterations=args.iterations)

    # build the index
    # TODO: The index should be built in another thread, so that new sounds
    # are inserted as they arrive, forever
    frequency, index, time_slices, sound_offsets = \
        build_index(api_client, model)
    logger.info(f'built index of size {len(index)}')

    # serve the index over HTTP
    api = falcon.API()
    api.add_route('/', IndexResource(
        frequency, index, time_slices, sound_offsets, user_uri))
    logger.info(f'serving index on port {args.bind}')
    StandaloneApplication(api, args.bind).run()
