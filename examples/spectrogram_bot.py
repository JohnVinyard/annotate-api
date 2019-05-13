import requests
import zounds
from io import BytesIO
import numpy as np
from bot_helper import BinaryData, main, Listener

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


class SpectrogramListener(Listener):
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
        windowed = samples.sliding_window(windowing_sample_rate)
        windowed = np.asarray(windowed)
        spec = np.dot(FILTER_BANK, windowed.T).T
        spec = np.abs(spec)
        spec = 20 * np.log10(spec + 1)
        spec = np.ascontiguousarray(spec).astype(np.float32)
        spec = zounds.ArrayWithUnits(spec, [
            zounds.TimeDimension(*windowing_sample_rate),
            zounds.IdentityDimension()
        ])
        print(spec.shape, spec.dimensions)

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
        user_name='spectrogram',
        bucket_name='SpectrogramBot',
        email='john.vinyard+spectrogram@gmail.com',
        about_me='I compute spectrograms!',
        info_url='https://en.wikipedia.org/wiki/Spectrogram',
        listener_cls=SpectrogramListener)
