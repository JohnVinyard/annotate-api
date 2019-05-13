import numpy as np
import json
import zounds
from io import BytesIO
import time
import argparse
from cli import DefaultArgumentParser
from client import Client
from s3client import ObjectStorageClient


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

    def packed_format(self):
        # adhering to the convention that the time dimension will be first

        time_dim = self.arr.dimensions[0]
        window_freq_seconds = \
            time_dim.frequency / zounds.Seconds(1)
        window_duration_seconds = \
            time_dim.duration / zounds.Seconds(1)

        metadata = {
            'type': str(self.arr.dtype),
            'shape': self.arr.shape,
            'dimensions': (
                {
                    'type': 'time',
                    'frequency_seconds': window_freq_seconds,
                    'duration_seconds': window_duration_seconds
                },
                {
                    'type': 'identity'
                },
            ),
            'max_value': float(self.arr.max()),
            'min_value': float(self.arr.min())
        }
        metadata_raw = json.dumps(metadata).encode()
        payload = \
            np.uint32(len(metadata_raw)).tostring() \
            + metadata_raw \
            + self.arr.tostring()
        return payload

    def packed_file_like_object(self):
        return BytesIO(self.packed_format())


class MetaListener(type):
    def __init__(cls, name, bases, attrs):
        super(MetaListener, cls).__init__(name, bases, attrs)
        cls.low_id = PersistentValue(f'{cls.__name__}.dat')


class Listener(object, metaclass=MetaListener):
    def __init__(self, client, s3_client, page_size=3):
        super().__init__()
        self.s3_client = s3_client
        self.client = client
        self.page_size = page_size

    def _iter_sounds(self):
        while True:
            time.sleep(1)
            data = self.client.get_sounds(self.low_id, self.page_size)
            for item in data['items']:
                yield item

    def _process_sound(self, sound):
        raise NotImplementedError()

    def _run(self):
        for sound in self._iter_sounds():
            print(sound['id'])
            self._process_sound(sound)
            self.low_id = sound['id']

    def run(self):
        try:
            self._run()
        except KeyboardInterrupt:
            return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('Exiting')
        pass


def main(
        user_name,
        bucket_name,
        email,
        about_me,
        info_url,
        listener_cls,
        page_size=3):
    parser = argparse.ArgumentParser(parents=[DefaultArgumentParser()])
    args = parser.parse_args()
    client = Client(args.annotate_api_endpoint)

    object_storage_client = ObjectStorageClient(
        endpoint=args.s3_endpoint,
        region=args.s3_region,
        access_key=args.aws_access_key_id,
        secret=args.aws_secret_access_key,
        bucket=bucket_name)
    object_storage_client.ensure_bucket_exists()

    # TODO: Some kind of structured information about transformation pipeline
    # in about me and/or info url
    client.upsert_featurebot(
        user_name,
        email,
        args.password,
        about_me,
        info_url)

    with listener_cls(client, object_storage_client, page_size).run():
        pass
