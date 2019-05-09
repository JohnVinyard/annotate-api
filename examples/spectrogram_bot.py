from client import Client
from cli import DefaultArgumentParser
import argparse
import os
import time
import requests
import zounds
from io import BytesIO
import numpy as np
import json
from s3client import ObjectStorageClient

# TODO: Decide on convention for data storage (i.e., time dimension first or
# feature dimension first

# TODO: add stats to JSON metadata

# TODO: decide on storage format

'''
There are two "layers" of information I'll need.

The first is shape data and type data, e.g.

type=float32
shape=(100, 23)

This is the numpy array layer.

The next layer is the semantic information about each dimension.  For now, I'll
only support "time" and "identity" information, so
dimension_metadata=(
    {type: time, frequency_seconds: 1, duration_seconds: 1},
    {type: identity}
)

The storage format will be binary, and will follow the format

- uint32 representing the size in bytes of the json payload
- json payload
- raw bytes of the binary data


'''

# TODO: How will last known id be recorded?
'''
For now, we'll just store the last known id in a textfile on disk with the
same name as this file
'''


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


N_FREQUENCY_BANDS = 512
SAMPLE_RATE = zounds.SR11025()
frequency_band = zounds.FrequencyBand(20, SAMPLE_RATE.nyquist)
scale = zounds.MelScale(frequency_band, N_FREQUENCY_BANDS)
FILTER_BANK_KERNEL_SIZE = 512
FILTER_BANK = zounds.spectral.morlet_filter_bank(
    SAMPLE_RATE,
    FILTER_BANK_KERNEL_SIZE,
    scale,
    scaling_factor=np.linspace(0.1, 1.0, len(scale)),
    normalize=True)
FILTER_BANK *= zounds.AWeighting()
FILTER_BANK = np.array(FILTER_BANK)


class Listener(object):
    low_id = PersistentValue(f'{os.path.splitext(__file__)[0]}.dat')

    def __init__(self, client, s3_client, page_size=3):
        super().__init__()
        self.s3_client = s3_client
        self.client = client
        self.page_size = page_size

    def _iter_sounds(self):
        while True:
            time.sleep(1)
            data = client.get_sounds(self.low_id, self.page_size)
            for item in data['items']:
                yield item

    def _process_sound(self, sound):
        # fetch audio
        resp = requests.get(sound['audio_url'])
        raw_audio = BytesIO(resp.content)

        # processing pipeline to compute spectrograms
        samples = zounds.AudioSamples.from_file(raw_audio).mono
        samples = samples.mono
        samples = zounds.soundfile.resample(samples, SAMPLE_RATE)
        windowing_sample_rate = zounds.SampleRate(
            frequency=(FILTER_BANK_KERNEL_SIZE // 2) * SAMPLE_RATE.frequency,
            duration=FILTER_BANK_KERNEL_SIZE * SAMPLE_RATE.frequency)
        windowed = samples.sliding_window(windowing_sample_rate)
        windowed = np.asarray(windowed)
        spec = np.dot(FILTER_BANK, windowed.T).T
        spec = np.abs(spec)
        spec = 20 * np.log10(spec + 1)
        spec = np.ascontiguousarray(spec).astype(np.float32)
        print(spec.shape)

        # build output
        window_freq_seconds = \
            windowing_sample_rate.frequency / zounds.Seconds(1)
        window_duration_seconds = \
            windowing_sample_rate.duration / zounds.Seconds(1)

        metadata = {
            'type': str(spec.dtype),
            'shape': spec.shape,
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
            'max_value': float(spec.max()),
            'min_value': float(spec.min())
        }
        metadata_raw = json.dumps(metadata).encode()
        payload = \
            np.uint32(len(metadata_raw)).tostring() \
            + metadata_raw \
            + spec.tostring()

        # push output to s3
        data_url = self.s3_client.put_object(
            sound['id'],
            BytesIO(payload),
            'application/octet-stream')
        print(f'pushed binary data to {data_url}')

        # create annotation
        client.create_annotations(sound['id'], {
            'start_seconds': 0,
            'duration_seconds': sound['duration_seconds'],
            'data_url': data_url
        })
        print('created annotation')

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[DefaultArgumentParser()])
    args = parser.parse_args()
    client = Client(args.annotate_api_endpoint)
    bucket_name = 'SpectrogramBot'

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
        'spectrogram',
        'john.vinyard+spectrogram@gmail.com',
        args.password,
        'I compute spectrograms',
        'https://en.wikipedia.org/wiki/Spectrogram')
    print(__file__)
    with Listener(client, object_storage_client, page_size=3).run():
        pass
