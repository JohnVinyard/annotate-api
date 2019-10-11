import requests
import zounds
from io import BytesIO
from bot_helper import BinaryData, main, SoundListener
import numpy as np
from log import module_logger

logger = module_logger(__file__)

SAMPLE_RATE = zounds.SR11025()
FILTER_BANK_KERNEL_SIZE = 512

windowing_sample_rate = zounds.SampleRate(
    frequency=(FILTER_BANK_KERNEL_SIZE // 2) * SAMPLE_RATE.frequency,
    duration=FILTER_BANK_KERNEL_SIZE * SAMPLE_RATE.frequency)


class FFTListener(SoundListener):
    def __init__(self, client, s3_client, page_size=3, logger=None):
        super().__init__(client, s3_client, page_size, logger)

    def _process_samples(self, samples):
        samples = samples.mono
        samples = zounds.soundfile.resample(samples, SAMPLE_RATE)

        spec = zounds.spectral.stft(samples, windowing_sample_rate)
        dims = spec.dimensions
        spec = np.abs(spec)
        spec = spec.astype(np.float32)
        spec = zounds.ArrayWithUnits(spec, dims)
        binary_data = BinaryData(spec)
        return binary_data

    def _process_sound(self, sound):
        # fetch audio
        resp = requests.get(sound['audio_url'])
        raw_audio = BytesIO(resp.content)

        # processing pipeline to compute spectrograms
        samples = zounds.AudioSamples.from_file(raw_audio)

        binary_data = self._process_samples(samples)

        # push output to s3
        data_url = self.s3_client.put_object(
            sound['id'],
            binary_data.packed_file_like_object(),
            'application/octet-stream')
        logger.info(f'pushed binary data to {data_url}')

        # create annotation
        self.client.create_annotations(sound['id'], {
            'start_seconds': 0,
            'duration_seconds': sound['duration_seconds'],
            'data_url': data_url
        })
        logger.info('created annotation')


if __name__ == '__main__':
    main(
        user_name='stft_bot',
        bucket_name='stft-bot',
        email='john.vinyard+stft_bot@gmail.com',
        about_me='stft_bot.md',
        info_url='https://en.wikipedia.org/wiki/Short-time_Fourier_transform',
        listener_cls=FFTListener,
        logger=logger)
