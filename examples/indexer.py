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
        segments won't be returned from every search, so indexes should be
        capable of computing features on the fly and/or accepting just a sound
        id and time stamp, locating the correct feature, and performing the
        search
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

'''
Training:

- One thread will begin pulling annotations and placing them into our reservoir
- Another thread will begin pulling batches from the reservoir and training the
  model

'''


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
    while True:
        yield from mfcc_stream(client)


def infinite_feature_stream(client):
    for item in infinite_mfcc_stream(client):
        resp = requests.get(item['data_url'])
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

        _id = item['id']
        yield _id, arr


def fill_reservoir(client, reservoir):
    for _id, arr in infinite_feature_stream(client):
        logger.info(f'pushing {_id} into reservoir')
        reservoir.add(arr)


def train_model(client, n_iterations=10000, batch_size=256):
    reservoir = zounds.learn.Reservoir(10000, dtype=np.float32)
    t = threading.Thread(
        target=fill_reservoir, args=(client, reservoir), daemon=True)
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

    # TODO: Persist the model somewhere


if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[DefaultArgumentParser()])
    parser.add_argument(
        '--train',
        action='store_true')
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
        train_model(api_client)
