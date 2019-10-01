import argparse
from cli import DefaultArgumentParser
from log import module_logger
from client import Client
from bot_helper import annotation_stream, BinaryData, sound_stream
import requests
import zounds
from spatial_network import EmbeddingNetwork
from io import BytesIO

logger = module_logger(__file__)


def compute_embedding(samples, network):
    # TODO: resampling can fail for some odd sampling rates
    samples = zounds.soundfile.resample(samples, zounds.SR11025())
    freq = samples.frequency * 8192
    windowed = samples.sliding_window(
        zounds.SampleRate(frequency=freq, duration=freq))
    dims = windowed.dimensions
    output = zounds.learn.apply_network(network, windowed, chunksize=8)
    logger.info(output.shape)
    output = zounds.ArrayWithUnits(
        output, [dims[0], zounds.IdentityDimension()])
    return output


class Indexer(object):
    def __init__(
            self,
            client,
            user_uri,
            index_api_endpoint,
            network,
            index_access_key):
        super().__init__()
        self.index_access_key = index_access_key
        self.network = network
        self.index_api_endpoint = index_api_endpoint
        self.user_uri = user_uri
        self.client = client
        self.time_dimension = self._fetch_time_dimension()

    def _fetch_time_dimension(self):
        uri, samples = next(self._stream_sounds())
        feature = compute_embedding(samples, self.network)
        return feature.dimensions[0]

    def _stream_sounds(self):
        for sound in sound_stream(self.client, wait_for_new=True):
            sound_id = sound['id']
            resp = requests.get(sound['audio_url'])
            bio = BytesIO(resp.content)
            try:
                samples = zounds.AudioSamples.from_file(bio).mono
                yield sound_id, samples
            except ValueError:
                continue

    def _auth_headers(self):
        return {'Authorization': self.index_access_key}

    def run(self):
        resp = requests.delete(
            self.index_api_endpoint,
            headers=self._auth_headers())

        resp.raise_for_status()
        logger.info(
            f'Deleted all index data with status code {resp.status_code}')
        for sound_id, samples in self._stream_sounds():
            embedding = compute_embedding(samples, self.network)
            uri = f'{self.index_api_endpoint}/{sound_id}'
            resp = requests.put(
                uri, data=embedding.tostring(), headers=self._auth_headers())
            logger.info(f'{uri} {resp.status_code}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[DefaultArgumentParser()])
    parser.add_argument(
        '--index-endpoint',
        type=str,
        required=True)
    parser.add_argument(
        '--index-access-key',
        type=str,
        required=True)
    args = parser.parse_args()

    user_name = 'spatial_index'

    api_client = Client(args.annotate_api_endpoint, logger=logger)
    user_uri = api_client.upsert_aggregator(
        user_name,
        'john.vinyard+spatial_index@gmail.com',
        args.password,
        'I create an index over 3D spatial embeddings',
        'https://example.com')

    logger.info('loading network')
    network, device = EmbeddingNetwork.load_network('weights3d_2b.dat')
    logger.info('loaded network')

    # poll the annotate API endlessly for new sounds, compute their embeddings
    # and push them to the index API
    indexer = Indexer(
        api_client,
        user_uri,
        args.index_endpoint,
        network,
        args.index_access_key)
    indexer.run()
