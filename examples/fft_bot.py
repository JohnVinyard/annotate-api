import requests
import zounds
from io import BytesIO
from bot_helper import BinaryData, main, Listener
import numpy as np

SAMPLE_RATE = zounds.SR11025()
FILTER_BANK_KERNEL_SIZE = 512


class FFTListener(Listener):
    def __init__(self, client, s3_client, page_size=3):
        super().__init__(client, s3_client, page_size)

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
        spec = zounds.spectral.stft(samples, windowing_sample_rate)
        dims = spec.dimensions
        spec = np.abs(spec)
        spec = spec.astype(np.float32)
        spec = zounds.ArrayWithUnits(spec, dims)
        binary_data = BinaryData(spec)

        # push output to s3
        data_url = self.s3_client.put_object(
            sound['id'],
            binary_data.packed_file_like_object(),
            'application/octet-stream')
        print(f'pushed binary data to {data_url}')

        # create annotation
        self.client.create_annotations(sound['id'], {
            'start_seconds': 0,
            'duration_seconds': sound['duration_seconds'],
            'data_url': data_url
        })
        print('created annotation')


if __name__ == '__main__':
    main(
        user_name='fft',
        bucket_name='FFTBot',
        email='john.vinyard+fft@gmail.com',
        about_me='I compute short-time FFTs!',
        info_url='https://en.wikipedia.org/wiki/Short-time_Fourier_transform',
        listener_cls=FFTListener)
