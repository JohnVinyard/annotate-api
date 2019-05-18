import numpy as np
import json
from io import BytesIO
import time
import argparse
from cli import DefaultArgumentParser
from client import Client
from s3client import ObjectStorageClient
from zounds.persistence import DimensionEncoder, DimensionDecoder
import zounds


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
        encoder = DimensionEncoder()
        metadata = {
            'type': str(self.arr.dtype),
            'shape': self.arr.shape,
            'dimensions': list(encoder.encode(self.arr.dimensions)),
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
    def __init__(self, get_resources_func, s3_client, page_size=3):
        super().__init__()
        self.get_resources_func = get_resources_func
        self.s3_client = s3_client
        self.page_size = page_size

    def _iter_resources(self):
        while True:
            time.sleep(1)
            # data = self.client.get_sounds(self.low_id, self.page_size)
            data = self.get_resources_func(self.low_id, self.page_size)
            for item in data['items']:
                yield item

    def _process_resource(self, resource):
        raise NotImplementedError()

    def _run(self):
        for resource in self._iter_resources():
            print(resource['id'])
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
        print('Exiting')
        pass


class SoundListener(BaseListener):
    def __init__(self, client, s3_client, page_size=3):
        self.client = client
        super().__init__(client.get_sounds, s3_client, page_size)

    def _process_sound(self, sound):
        raise NotImplementedError()

    def _process_resource(self, resource):
        return self._process_sound(resource)


class AnnotationListener(BaseListener):
    def __init__(self, client, bot_id, s3_client, page_size=3):
        f = lambda low_id, page_size: \
            client.get_annotations(bot_id, low_id, page_size)
        self.client = client
        super().__init__(f, s3_client, page_size)

    def _process_annotation(self, annotation):
        raise NotImplementedError()

    def _process_resource(self, resource):
        return self._process_annotation(resource)


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
