import os
import numpy as np
import json
from io import BytesIO
import time
import argparse

import requests
from cli import DefaultArgumentParser
from client import Client
from s3client import ObjectStorageClient
from zounds.persistence import DimensionEncoder, DimensionDecoder
import zounds
from mp3encoder import encode_mp3
from http import client
from pathlib import Path
import soundfile


def sound_stream(client, wait_for_new=False, page_size=100, low_id=None):
    def fetch(low):
        resp = client.get_sounds(low_id=low_id, page_size=page_size)
        items = resp['items']
        try:
            return items[-1]['id'], items
        except IndexError:
            return low, items

    low_id, items = fetch(low_id)
    while items or wait_for_new:
        yield from items
        low_id, items = fetch(low_id)


def annotation_stream(
        client, user_name, wait_for_new=False, page_size=100, low_id=None):
    bot = retry(client.get_user, 30)(user_name)

    def fetch(low):
        resp = client.get_annotations(
            bot['id'], low_id=low, page_size=page_size)
        items = resp['items']
        try:
            return items[-1]['id'], items
        except IndexError:
            return low, items

    low_id, items = fetch(low_id)
    while items or wait_for_new:
        yield from items
        low_id, items = fetch(low_id)


class PersistentValue(object):
    def __init__(self, path):
        self.path = path

    def __get__(self, instance, owner):
        try:
            with open(self.path, 'r') as f:
                return f.read()
        except IOError:
            return None

    def __set__(self, instance, value):
        with open(self.path, 'w') as f:
            f.write(value)


class BinaryData(object):
    def __init__(self, arr_with_units):
        super().__init__()
        self.arr = arr_with_units

    def metadata(self):
        encoder = DimensionEncoder()
        metadata = {
            'type': str(self.arr.dtype),
            'shape': self.arr.shape,
            'dimensions': list(encoder.encode(self.arr.dimensions)),
            'max_value': float(self.arr.max()),
            'min_value': float(self.arr.min())
        }
        return metadata

    def packed_format(self):
        metadata = self.metadata()
        metadata_raw = json.dumps(metadata).encode()
        payload = \
            np.uint32(len(metadata_raw)).tostring() \
            + metadata_raw \
            + self.arr.tostring()
        return payload

    def packed_file_like_object(self):
        return BytesIO(self.packed_format())

    @staticmethod
    def unpack(packed_array_with_units):
        x = packed_array_with_units
        json_length = np.fromstring(x[:4], dtype=np.uint32)[0]
        data = json.loads(x[4: json_length + 4])
        raw = np.fromstring(
            x[json_length + 4:],
            dtype=np.dtype(data['type'])).reshape(data['shape'])
        dim_decoder = DimensionDecoder()
        arr = zounds.ArrayWithUnits(
            raw, list(dim_decoder.decode(data['dimensions'])))
        return arr


class MetaListener(type):
    def __init__(cls, name, bases, attrs):
        super(MetaListener, cls).__init__(name, bases, attrs)
        cls.low_id = PersistentValue(f'{cls.__name__}.dat')


class BaseListener(object, metaclass=MetaListener):
    def __init__(self, get_resources_func, s3_client, page_size=3, logger=None):
        super().__init__()
        self.logger = logger
        self.get_resources_func = get_resources_func
        self.s3_client = s3_client
        self.page_size = page_size

    def _iter_resources(self):
        while True:
            time.sleep(1)
            data = self.get_resources_func(self.low_id, self.page_size)
            for item in data['items']:
                yield item

    def _process_resource(self, resource):
        raise NotImplementedError()

    def _run(self):
        for resource in self._iter_resources():
            self.logger.info(resource['id'])
            self._process_resource(resource)
            self.low_id = resource['id']

    def run(self):
        try:
            self._run()
        except KeyboardInterrupt:
            return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info('Exiting')
        pass


class SoundListener(BaseListener):
    def __init__(self, client, s3_client, page_size=3, logger=None):
        self.client = client
        super().__init__(client.get_sounds, s3_client, page_size, logger)

    def _process_sound(self, sound):
        raise NotImplementedError()

    def _process_resource(self, resource):
        return self._process_sound(resource)


def retry(func, timeout_seconds, delay=1.0):
    def x(*args, **kwargs):
        start = time.time()
        elapsed = time.time() - start
        while elapsed < timeout_seconds:
            try:
                return func(*args, **kwargs)
            except:
                time.sleep(delay)
            elapsed = time.time() - start

    return x


class AnnotationListener(BaseListener):
    def __init__(
            self,
            subscribed_to,
            client,
            s3_client,
            page_size=3,
            logger=None):
        self.subscribed_to = subscribed_to
        self.client = client
        self.bot = None
        super().__init__(None, s3_client, page_size, logger)

    def run(self):
        self.bot = retry(self.client.get_user, 30)(self.subscribed_to)
        self.logger.info(f'subscribed to user {self.bot}')

        def f(low_id, page_size):
            return self.client.get_annotations(
                self.bot['id'], low_id, page_size)

        self.get_resources_func = f
        return super().run()

    def _sound_id_from_uri(self, sound_uri):
        return os.path.split(sound_uri)[-1]

    def _process_annotation(self, annotation):
        raise NotImplementedError()

    def _process_resource(self, resource):
        return self._process_annotation(resource)


class BotDriver(object):
    def __init__(self, args, logger, bot):
        super().__init__()
        self.bot = bot
        self.annotate_client = Client(args.annotate_api_endpoint, logger=logger)
        self.object_storage_client = ObjectStorageClient(
            endpoint=args.s3_endpoint,
            region=args.s3_region,
            access_key=args.aws_access_key_id,
            secret=args.aws_secret_access_key,
            bucket=bot.bucket_name)
        self.object_storage_client.ensure_bucket_exists()
        self.args = args
        self.logger = logger

    def _about_me(self):
        try:
            with open(self.bot.about_me, 'r') as f:
                return f.read()
        except IOError:
            return self.bot.about_me

    def run(self):
        user_uri = self.annotate_client.upsert_dataset(
            user_name=self.bot.user_name,
            email=self.bot.email,
            password=self.args.password,
            about_me=self._about_me(),
            info_url=self.bot.info_url)
        self.logger.info(f'Added or updated user {user_uri}')

        for name, bio, metadata in self.bot.iter_sounds():
            try:
                encoded = encode_mp3(bio)
            except RuntimeError:
                self.logger.info(
                    f'Error decoding audio for {name}. Skipping.')
                continue
            path = Path(name)

            low_quality_id = \
                str(Path('low-quality') / path.with_suffix('.mp3'))
            low_quality_url = self.object_storage_client.put_object(
                low_quality_id, encoded, 'audio/mp3')
            self.logger.info(f'Pushed {low_quality_url} to s3')
            bio.seek(0)

            _id = str(path)
            url = self.object_storage_client.put_object(_id, bio, 'audio/wav')
            self.logger.info(f'Pushed audio data for {url} to s3')
            bio.seek(0)

            info = soundfile.info(bio)

            try:
                status, sound_uri, sound_id = self.annotate_client.create_sound(
                    audio_url=url,
                    low_quality_audio_url=low_quality_url,
                    info_url=self.bot.get_info_url(name, metadata),
                    license_type=self.bot.get_license_type(name, metadata),
                    title=str(path),
                    duration_seconds=info.duration)
            except requests.exceptions.HTTPError as e:
                self.logger.error(e.response.content)
                raise

            if status == client.CREATED:
                annotations = self.bot.get_annotations(name, metadata, bio)
                if annotations:
                    self.annotate_client.create_annotations(*annotations)
                    self.logger.info(f'Created annotations for {sound_uri}')
            elif status == client.CONFLICT:
                self.logger.warning(
                    f'Already created sound and annotation for {sound_uri}')
                # we've already created this sound and annotation
                pass
            else:
                raise RuntimeError(f'Unexpected {status} encountered')


def about_me_metadata(binary_data):
    dims = binary_data.arr.dimensions
    shape = list(binary_data.arr.shape)

    # The first time dimension should be displayed as variable since it depends
    # on the length of the audio input
    if isinstance(dims[0], zounds.TimeDimension):
        shape[0] = 'variable'

    metadata_dims = []
    for dim in dims:
        if isinstance(dim, zounds.TimeDimension):
            metadata_dims.append({
                'type': 'time',
                'sample_frequency_seconds': dim.frequency / zounds.Seconds(1),
                'sample_duration_seconds': dim.duration / zounds.Seconds(1)
            })
        elif isinstance(dim, zounds.FrequencyDimension):
            scale = dim.scale
            metadata_dims.append({
                'type': 'frequency',
                'start_hz': scale.start_hz,
                'stop_hz': scale.stop_hz,
                'n_bands': scale.n_bands,
                'scale_type': scale.__class__.__name__
            })
        else:
            metadata_dims.append({
                'type': 'identity'
            })

    return {
        'type': str(binary_data.arr.dtype),
        'shape': shape,
        'dimensions': metadata_dims
    }


def main(
        user_name,
        bucket_name,
        email,
        about_me,
        info_url,
        listener_cls,
        page_size=3,
        logger=None):
    parser = argparse.ArgumentParser(parents=[DefaultArgumentParser()])
    args = parser.parse_args()
    client = Client(args.annotate_api_endpoint, logger=logger)

    object_storage_client = ObjectStorageClient(
        endpoint=args.s3_endpoint,
        region=args.s3_region,
        access_key=args.aws_access_key_id,
        secret=args.aws_secret_access_key,
        bucket=bucket_name)

    listener = listener_cls(
        client, object_storage_client, page_size, logger=logger)

    # get metadata describing feature shape and dimensions
    try:
        metadata = listener.get_metadata()
    except AttributeError:
        # the listener does not provide metadata explicitly, but in the case
        # of listeners that accept audio samples directly, we can infer the
        # metadata
        samples = zounds.AudioSamples.silence(
            zounds.SR44100(), zounds.Seconds(10))
        binary_data = listener._process_samples(samples)
        metadata = about_me_metadata(binary_data)

    try:
        with open(about_me, 'r') as f:
            about_me = f.read()
    except IOError:
        pass

    about_me = about_me.format(metadata=json.dumps(metadata, indent=4))

    object_storage_client.ensure_bucket_exists()

    # TODO: Some kind of structured information about transformation pipeline
    # in about me and/or info url
    client.upsert_featurebot(
        user_name,
        email,
        args.password,
        about_me,
        info_url)

    with listener.run():
        pass
