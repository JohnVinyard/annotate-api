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
    current_offset = 0
    offsets = []
    ids = []
    sound_offsets = {}

    for annotation in mfcc_stream(client):
        feature = compute_feature(annotation)

        # TODO: magic number 42
        _, windowed = feature.sliding_window_with_leftovers(42, dopad=True)

        # TODO: This is being set repeatedly because I don't have the times
        # factored out
        frequency = windowed.dimensions[0].frequency

        original_shape = windowed.shape[:2]
        flattened_dim = windowed.shape[-2] * windowed.shape[-1]
        windowed = windowed.reshape((-1, flattened_dim))

        cluster_ids = model.predict(windowed)

        sparse = np.zeros((len(cluster_ids), model.n_clusters), dtype=np.uint8)
        sparse[np.arange(len(cluster_ids)), cluster_ids] = 1
        sparse = sparse.reshape(original_shape + (-1,))

        pooled = sparse.max(axis=1)

        # TODO: This should be encapsulated in an index class
        packed = np.packbits(pooled, axis=-1).view(np.uint64)
        chunks.append(packed)
        offsets.append(current_offset)
        ids.append(annotation['sound'])
        sound_offsets[annotation['sound']] = current_offset
        current_offset += len(packed)

    index = np.concatenate(chunks)
    return index, offsets, ids, sound_offsets


if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[DefaultArgumentParser()])
    parser.add_argument(
        '--train',
        action='store_true')
    parser.add_argument(
        '--iterations',
        type=int,
        default=10000)
    args = parser.parse_args()

    api_client = Client(args.annotate_api_endpoint, logger=logger)
    # TODO: Should I introduce an indexer user type, since anonymous access
    # isn't allowed?
    api_client.upsert_user(
        'mfcc_index',
        'john.vinyard+mfcc_index@gmail.com',
        args.password,
        'I index MFCC features',
        'https://example.com')

    if args.train:
        model = train_model(api_client, n_iterations=args.iterations)

    index, offsets, ids, sound_offsets = build_index(api_client, model)
