import argparse
import falcon
from gunicorn.app.base import BaseApplication
from cli import DefaultArgumentParser
from log import module_logger
from client import Client
import threading
from bot_helper import annotation_stream, BinaryData, sound_stream
import requests
from multiprocessing.connection import Listener, Client as TcpClient
import json
import numpy as np
import zounds
from scipy.spatial.distance import cdist
from spatial_network import EmbeddingNetwork
from io import BytesIO


logger = module_logger(__file__)

logger.info('loading network')
network, device = EmbeddingNetwork.load_network('weights3d_2a.dat')
logger.info('loaded network')

# def compute_embedding(annotation):
#     resp = requests.get(annotation['data_url'])
#     arr = BinaryData.unpack(resp.content)
#     _, arr = arr.sliding_window_with_leftovers(42, dopad=True)
#     dims = arr.dimensions
#
#     # assign a random point on the unit sphere
#     projection = np.random.normal(0, 1, (arr.shape[0], 3))
#
#     # ensure unit norm
#     norms = np.linalg.norm(projection, axis=-1, keepdims=True)
#     projection /= (norms + 1e-8)
#
#
#
#     # restore time dimension
#     projection = zounds.ArrayWithUnits(
#         projection, [dims[0], zounds.IdentityDimension()])
#     return projection


def compute_embedding(samples):
    samples = zounds.soundfile.resample(samples, zounds.SR22050())
    logger.info(samples)
    freq = samples.frequency * 8192
    windowed = samples.sliding_window(
        zounds.SampleRate(frequency=freq, duration=freq))
    dims = windowed.dimensions
    logger.info(windowed.shape)
    output = zounds.learn.apply_network(network, windowed, chunksize=8)
    output = zounds.ArrayWithUnits(
        output, [dims[0], zounds.IdentityDimension()])
    return output


class Index(threading.Thread):
    def __init__(self, client, feature_user_name, user_uri):
        super().__init__(daemon=True)
        self.user_uri = user_uri
        self.feature_user_name = feature_user_name
        self.client = client

        self.identifiers = []
        self.index = None
        self.offsets = {}

        self.time_dimension = self._fetch_time_dimension()

    def _fetch_time_dimension(self):
        uri, samples = next(self._stream_sounds())
        feature = compute_embedding(samples)
        return feature.dimensions[0]

    # def _stream_annotations(self):
    #     yield from annotation_stream(
    #         self.client, self.feature_user_name, wait_for_new=True)

    def _stream_sounds(self):
        for sound in sound_stream(self.client, wait_for_new=True):
            uri = f'/sounds/{sound["id"]}'
            resp = requests.get(sound['audio_url'])
            bio = BytesIO(resp.content)
            samples = zounds.AudioSamples.from_file(bio).mono
            yield uri, samples

    def run(self):
        for sound, samples in self._stream_sounds():
            embedding = compute_embedding(samples)

            freq = embedding.dimensions[0].frequency / zounds.Seconds(1)
            ids = [(sound, freq * i) for i in range(len(embedding))]

            self.offsets[sound] = len(self.identifiers)

            self.identifiers.extend(ids)

            if self.index is None:
                self.index = embedding
            else:
                self.index = np.concatenate([self.index, embedding])

            logger.info(self.index.shape)
            logger.info(len(self.identifiers))

        # for annotation in self._stream_annotations():
        #     sound = annotation['sound']
        #     embedding = compute_embedding(annotation)
        #     freq = embedding.dimensions[0].frequency / zounds.Seconds(1)
        #     ids = [(sound, freq * i) for i in range(len(embedding))]
        #
        #     self.offsets[sound] = len(self.identifiers)
        #
        #     self.identifiers.extend(ids)
        #
        #     if self.index is None:
        #         self.index = embedding
        #     else:
        #         self.index = np.concatenate([self.index, embedding])
        #
        #     logger.info(self.index.shape)
        #     logger.info(len(self.identifiers))

    def transform_index(self, index):
        point, pair = index
        sound_uri, start_seconds = pair
        duration = self.time_dimension.duration / zounds.Seconds(1)
        return {
            'created_by': self.user_uri,
            'sound': sound_uri,
            'start_seconds': start_seconds,
            'duration_seconds': duration,
            'end_seconds': start_seconds + duration,
            'point': list(point)
        }

    def search(self, embedding, nresults=100):
        embedding = np.array(embedding)
        logger.info(f'embedding {embedding.shape}')
        logger.info(f'index {self.index.shape}')
        dist = cdist(embedding[None, ...], self.index, metric='cosine')[0]
        logger.info(f'dist {dist.shape}')
        indices = np.argsort(dist)[:nresults]
        logger.info(f'indices {indices.shape}')
        ids = [
            (self.index[i].astype(np.float64), self.identifiers[i])
            for i in indices
        ]
        return list(map(self.transform_index, ids))


class IndexServer(Listener):
    def __init__(self, address, index):
        super().__init__(address)
        self.index = index
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        logger.info('Started index TCP server')

    def _perform_search(self, query):
        return self.index.search(query)

    def run(self):
        while True:
            connection = self.accept()
            raw_query = connection.recv_bytes().decode()
            query = json.loads(raw_query)
            results = self._perform_search(query)
            connection.send_bytes(json.dumps(results).encode())
            connection.close()


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

        point = [
            req.get_param_as_float('x'),
            req.get_param_as_float('y'),
            req.get_param_as_float('z')
        ]
        connection = TcpClient(self.index_server_address)
        connection.send_bytes(json.dumps(point).encode())
        raw_resp = connection.recv_bytes()
        results = json.loads(raw_resp.decode())

        resp.media = {
            'total_count': len(results),
            'items': results
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[DefaultArgumentParser()])
    parser.add_argument(
        '--bind',
        default='0.0.0.0:8080')
    parser.add_argument(
        '--index-server-port',
        default=8081,
        type=int)
    args = parser.parse_args()

    user_name = 'spatial_index'
    feature_user_name = 'spectrogram'

    api_client = Client(args.annotate_api_endpoint, logger=logger)
    user_uri = api_client.upsert_aggregator(
        user_name,
        'john.vinyard+spatial_index@gmail.com',
        args.password,
        'I create an index over 3D spatial embeddings',
        'https://example.com')

    # begin to build the index, and start up an index server that will host
    # the in-memory index and respond to requests from HTTP workers
    index_server_address = ('', args.index_server_port)
    index = Index(api_client, feature_user_name, user_uri)
    index.start()
    index_server = IndexServer(index_server_address, index)

    # serve the index over HTTP using a standalone gunicorn application
    api = falcon.API()
    api.add_route('/', IndexResource(index_server_address))
    logger.info(f'serving index on port {args.bind}')
    StandaloneApplication(api, args.bind).run()
