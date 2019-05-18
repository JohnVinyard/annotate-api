import requests
import zounds
import numpy as np
from bot_helper import BinaryData, main, AnnotationListener
import os

SAMPLE_RATE = zounds.SR11025()
frequency_band = zounds.FrequencyBand(20, SAMPLE_RATE.nyquist)
CHROMA_SCALE = zounds.ChromaScale(frequency_band)


class ChromaListener(AnnotationListener):
    def __init__(self, client, s3_client, page_size=3):
        self.bot = client.get_user('fft')
        print('subscribed to user', self.bot)
        super().__init__(client, self.bot['id'], s3_client, page_size)

    def _process_annotation(self, annotation):
        # fetch the fft data
        resp = requests.get(annotation['data_url'])
        fft_feature = BinaryData.unpack(resp.content)

        # compute the chroma feature
        chroma = CHROMA_SCALE.apply(fft_feature, zounds.HanningWindowingFunc())
        chroma = zounds.ArrayWithUnits(chroma, [
            fft_feature.dimensions[0],
            zounds.IdentityDimension()
        ]).astype(np.float32)

        # pack the chroma data and create the resources
        binary_data = BinaryData(chroma)
        sound_id = os.path.split(annotation['sound'])[-1]

        # push output to s3
        data_url = self.s3_client.put_object(
            sound_id,
            binary_data.packed_file_like_object(),
            'application/octet-stream')
        print(f'pushed binary data to {data_url}')

        # create annotation
        self.client.create_annotations(sound_id, {
            'start_seconds': annotation['start_seconds'],
            'duration_seconds': annotation['duration_seconds'],
            'data_url': data_url
        })
        print('created annotation')

    # def _process_sound(self, sound):
    #     # fetch audio
    #     resp = requests.get(sound['audio_url'])
    #     raw_audio = BytesIO(resp.content)
    #
    #     # processing pipeline to compute spectrograms
    #     samples = zounds.AudioSamples.from_file(raw_audio).mono
    #     samples = samples.mono
    #     samples = zounds.soundfile.resample(samples, SAMPLE_RATE)
    #     windowing_sample_rate = zounds.SampleRate(
    #         frequency=(FILTER_BANK_KERNEL_SIZE // 2) * SAMPLE_RATE.frequency,
    #         duration=FILTER_BANK_KERNEL_SIZE * SAMPLE_RATE.frequency)
    #     windowed = samples.sliding_window(windowing_sample_rate)
    #     windowed = np.asarray(windowed)
    #     spec = np.dot(FILTER_BANK, windowed.T).T
    #     spec = np.abs(spec)
    #     spec = 20 * np.log10(spec + 1)
    #     spec = np.ascontiguousarray(spec).astype(np.float32)
    #     spec = zounds.ArrayWithUnits(spec, [
    #         zounds.TimeDimension(*windowing_sample_rate),
    #         zounds.FrequencyDimension(scale)
    #     ])
    #
    #     chroma_scale = zounds.ChromaScale(frequency_band)
    #     chroma = chroma_scale.apply(spec, zounds.HanningWindowingFunc())
    #     chroma = zounds.ArrayWithUnits(chroma, [
    #         zounds.TimeDimension(*windowing_sample_rate),
    #         zounds.IdentityDimension()
    #     ]).astype(np.float32)
    #
    #     print(chroma.shape, chroma.dimensions)
    #
    #     binary_data = BinaryData(chroma)
    #
    #     # push output to s3
    #     data_url = self.s3_client.put_object(
    #         sound['id'],
    #         binary_data.packed_file_like_object(),
    #         'application/octet-stream')
    #     print(f'pushed binary data to {data_url}')
    #
    #     # create annotation
    #     self.client.create_annotations(sound['id'], {
    #         'start_seconds': 0,
    #         'duration_seconds': sound['duration_seconds'],
    #         'data_url': data_url
    #     })
    #     print('created annotation')


if __name__ == '__main__':
    main(
        user_name='chroma',
        bucket_name='ChromaBot',
        email='john.vinyard+chroma@gmail.com',
        about_me='I compute chroma features!',
        info_url='https://en.wikipedia.org/wiki/Chroma_feature',
        listener_cls=ChromaListener)
