import requests
import zounds
import numpy as np
from bot_helper import BinaryData, main, AnnotationListener
from scipy.fftpack import dct
from log import module_logger
from stft_bot import windowing_sample_rate

logger = module_logger(__file__)

N_FREQUENCY_BANDS = 200
SAMPLE_RATE = zounds.SR11025()
frequency_band = zounds.FrequencyBand(20, SAMPLE_RATE.nyquist)
scale = zounds.MelScale(frequency_band, N_FREQUENCY_BANDS)


class MFCCListener(AnnotationListener):
    def __init__(self, client, s3_client, page_size=3, logger=None):
        super().__init__(
            'stft_bot', client, s3_client, page_size, logger=logger)
        self.dtype = np.float32().dtype

    def get_metadata(self):
        return {
            'type': str(self.dtype),
            'shape': ('variable', 13),
            'dimensions': [
                {
                    'type': 'time',
                    'sample_frequency_seconds':
                        windowing_sample_rate.frequency / zounds.Seconds(1),
                    'sample_duration_seconds':
                        windowing_sample_rate.duration / zounds.Seconds(1)
                },
                {
                    'type': 'identity'
                }
            ]
        }

    def _process_annotation(self, annotation):
        # fetch the fft data
        resp = requests.get(annotation['data_url'])
        fft_feature = BinaryData.unpack(resp.content)

        # compute the chroma feature
        mel_spectrogram = scale.apply(
            fft_feature,
            zounds.HanningWindowingFunc())
        mel_spectrogram = zounds.ArrayWithUnits(mel_spectrogram, [
            fft_feature.dimensions[0],
            zounds.FrequencyDimension(scale)
        ])
        mel_spectrogram = 20 * np.log10(mel_spectrogram + 1)
        mfcc = np.abs(dct(mel_spectrogram, axis=1)[:, 1: 14])
        mfcc = zounds.ArrayWithUnits(mfcc, [
            fft_feature.dimensions[0],
            zounds.IdentityDimension()
        ]).astype(np.float32)

        # pack the chroma data and create the resources
        binary_data = BinaryData(mfcc)
        sound_id = self._sound_id_from_uri(annotation['sound'])

        # push output to s3
        data_url = self.s3_client.put_object(
            sound_id,
            binary_data.packed_file_like_object(),
            'application/octet-stream')
        logger.info(f'pushed binary data to {data_url}')

        # create annotation
        self.client.create_annotations(sound_id, {
            'start_seconds': annotation['start_seconds'],
            'duration_seconds': annotation['duration_seconds'],
            'data_url': data_url
        })
        logger.info('created annotation')


if __name__ == '__main__':
    main(
        user_name='mfcc_bot',
        bucket_name='mfcc-bot',
        email='john.vinyard+mfcc_bot@gmail.com',
        about_me='mfcc_bot.md',
        info_url='https://en.wikipedia.org/wiki/Mel-frequency_cepstrum',
        listener_cls=MFCCListener,
        logger=logger)
