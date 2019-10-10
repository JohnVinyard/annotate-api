import requests
import zounds
import numpy as np
from bot_helper import BinaryData, main, AnnotationListener
from log import module_logger
from stft_bot import windowing_sample_rate

logger = module_logger(__file__)

SAMPLE_RATE = zounds.SR11025()
frequency_band = zounds.FrequencyBand(20, SAMPLE_RATE.nyquist)
CHROMA_SCALE = zounds.ChromaScale(frequency_band)


class ChromaListener(AnnotationListener):
    def __init__(self, client, s3_client, page_size=3, logger=None):
        super().__init__(
            'stft_bot', client, s3_client, page_size, logger=logger)
        self.dtype = np.float32().dtype

    def get_metadata(self):
        return {
            'type': str(self.dtype),
            'shape': ('variable', CHROMA_SCALE.n_bands),
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
        chroma = CHROMA_SCALE.apply(fft_feature, zounds.HanningWindowingFunc())
        chroma = zounds.ArrayWithUnits(chroma, [
            fft_feature.dimensions[0],
            zounds.IdentityDimension()
        ]).astype(self.dtype)

        # pack the chroma data and create the resources
        binary_data = BinaryData(chroma)
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
        user_name='chroma_bot',
        bucket_name='chroma-bot',
        email='john.vinyard+chroma@gmail.com',
        about_me='chroma_bot.md',
        info_url='https://en.wikipedia.org/wiki/Chroma_feature',
        listener_cls=ChromaListener,
        logger=logger)
