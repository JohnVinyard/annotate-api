"""
This example bot will demonstrate two things:
    - annotations that include no tags and only represent a segmentation
    - a bot that does not use zounds to compute features
"""

import librosa
from bot_helper import main, SoundListener
from log import module_logger
import zounds
import requests
from io import BytesIO
import numpy as np

logger = module_logger(__file__)


class OnsetListener(SoundListener):
    def __init__(self, client, s3_client, page_size=3, logger=None):
        super().__init__(client, s3_client, page_size, logger)

    def get_metadata(self):
        return {}

    def _process_sound(self, sound):
        # fetch audio
        resp = requests.get(sound['audio_url'])
        raw_audio = BytesIO(resp.content)

        # Convert to mono
        samples = zounds.AudioSamples.from_file(raw_audio)
        samples = samples.mono

        onset_frame_indices = librosa.onset.onset_detect(
            samples,
            samples.samples_per_second,
            hop_length=samples.samplerate.suggested_hop,
            backtrack=True,
            units='samples')
        onset_frame_indices = np.concatenate([
            onset_frame_indices,
            np.array([len(samples)], dtype=onset_frame_indices.dtype)
        ])

        durations = np.diff(onset_frame_indices)
        onset_times = onset_frame_indices / samples.samples_per_second
        onset_durations = durations / samples.samples_per_second

        annotations = []
        for onset_time, duration in zip(onset_times[:-1], onset_durations):
            annotations.append({
                'start_seconds': onset_time,
                'duration_seconds': duration,
                'tags': ['onset']
            })
        logger.info(f'Created {len(annotations)} onsets for {sound["id"]}')

        if not annotations:
            return

        self.client.create_annotations(sound['id'], *annotations)


if __name__ == '__main__':
    main(
        user_name='onset_bot',
        bucket_name='onset-bot',
        email='john.vinyard+onset_bot@gmail.com',
        about_me='onset_bot.md',
        info_url='https://librosa.github.io/librosa/generated/librosa.onset.onset_detect.html',
        listener_cls=OnsetListener,
        logger=logger)

