"""
# TODO: Move these comments down into the __main__ method

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
import os
from multiprocessing.connection import Listener, Client as TcpClient
import json

logger = module_logger(__file__)

SHINGLE_SIZE = 10
WINDOW_SIZE = 42


def mfcc_stream(client, wait_for_new=False):
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
    while items or wait_for_new:
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

    # TODO: Consider a larger "shingle" size
    # sliding window
    _, arr = arr.sliding_window_with_leftovers(SHINGLE_SIZE, 1, dopad=True)
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
            if batch % 100 == 0:
                logger.info(f'Training on batch {batch} of {n_iterations}')
        except ValueError as e:
            logger.error(e)
            time.sleep(1)
            continue

    should_stop.append(True)
    return model


class Index(threading.Thread):
    def __init__(self, client, model, user_uri):
        super().__init__(daemon=True)
        self.user_uri = user_uri
        self.model = model
        self.client = client
        self.index = None
        self.time_slices = []
        self.current_offset = 0
        self.sound_offsets = {}
        self.window_size_frames = WINDOW_SIZE
        self.frequency = self._fetch_frequency()

    def __len__(self):
        return len(self.index)

    def _fetch_frequency(self):
        annotation = next(mfcc_stream(self.client))
        feature = compute_feature(annotation)
        _, windowed = feature.sliding_window_with_leftovers(42, dopad=True)
        return windowed.dimensions[0].frequency

    def run(self):
        for annotation in mfcc_stream(self.client, wait_for_new=True):
            feature = compute_feature(annotation)

            _, windowed = feature.sliding_window_with_leftovers(
                self.window_size_frames, dopad=True)

            time_dimension = windowed.dimensions[0]
            duration = time_dimension.duration

            original_shape = windowed.shape[:2]
            flattened_dim = windowed.shape[-2] * windowed.shape[-1]
            windowed = windowed.reshape((-1, flattened_dim))

            cluster_ids = self.model.predict(windowed)

            sparse = np.zeros(
                (len(cluster_ids), model.n_clusters), dtype=np.uint8)
            sparse[np.arange(len(cluster_ids)), cluster_ids] = 1
            sparse = sparse.reshape(original_shape + (-1,))

            pooled = sparse.max(axis=1)

            packed = np.packbits(pooled, axis=-1).view(np.uint64)
            if self.index is None:
                self.index = packed
            else:
                self.index = np.concatenate([self.index, packed])
            sound_id = annotation['sound']
            logger.info(
                f'building index for {sound_id} from process {os.getpid()}')
            self.time_slices.extend(
                (sound_id,
                 zounds.TimeSlice(start=i * self.frequency, duration=duration))
                for i in range(len(packed)))
            self.sound_offsets[sound_id] = self.current_offset
            self.current_offset += len(packed)

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

    def search(self, sound, seconds, nresults=10):
        logger.info(f'searching from process {os.getpid()}')
        code = self._get_code(sound, seconds)
        dist = zounds.nputil.packed_hamming_distance(code, self.index)
        indices = np.argsort(dist)[:nresults]
        return list(self._transform_indices(indices))


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
    def __init__(self, index_server_address):
        self.index_server_address = index_server_address

    def on_get(self, req, resp):
        resp.set_header('Access-Control-Allow-Origin', '*')

        sound = req.get_param('sound')
        seconds = req.get_param_as_float('seconds')
        nresults = req.get_param_as_int('nresults') or 10

        connection = TcpClient(self.index_server_address)
        query_data = {'sound': sound, 'seconds': seconds, 'nresults': nresults}
        connection.send_bytes(json.dumps(query_data).encode())
        raw_resp = connection.recv_bytes()
        results = json.loads(raw_resp.decode())

        resp.media = {
            'total_count': len(results),
            'items': results
        }


class IndexServer(Listener):
    def __init__(self, address, index):
        super().__init__(address)
        self.index = index
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        logger.info('Started index TCP server')

    def run(self):
        while True:
            connection = self.accept()
            raw_query = connection.recv_bytes().decode()
            query = json.loads(raw_query)
            results = self.index.search(**query)
            connection.send_bytes(json.dumps(results).encode())
            connection.close()


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
    parser.add_argument(
        '--index-server-port',
        default=8081,
        type=int)
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

    # begin to build the index, and start up an index server that will host
    # the in-memory index and respond to requests from HTTP workers
    index_server_address = ('', args.index_server_port)
    index = Index(api_client, model, user_uri)
    index.start()
    index_server = IndexServer(index_server_address, index)

    # serve the index over HTTP using a standalone gunicorn application
    api = falcon.API()
    api.add_route('/', IndexResource(index_server_address))
    logger.info(f'serving index on port {args.bind}')
    StandaloneApplication(api, args.bind).run()
