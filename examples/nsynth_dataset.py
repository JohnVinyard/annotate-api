import json
import argparse
from zounds.util import midi_to_note
import os
import soundfile
from client import Client
from cli import DatasetArgumentParser
from http import client
from s3client import ObjectStorageClient
from log import module_logger

logger = module_logger(__file__)


def get_metadata(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    processed = {}
    for key, meta in data.items():
        tags = meta['qualities_str']
        tags.append(meta['instrument_family_str'])
        tags.append(meta['instrument_source_str'])
        tags.append('musical_note:' + midi_to_note(meta['pitch']))
        tags.append('midi_velocity:' + str(meta['velocity']))
        processed[key] = tags
    return processed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[
        DatasetArgumentParser()
    ])
    args = parser.parse_args()

    annotate_client = Client(args.annotate_api_endpoint, logger=logger)

    with open('nsynth.md', 'r') as f:
        about_me = f.read()

    annotate_client.upsert_dataset(
        user_name='nsynth',
        email='john.vinyard+nsynth-dataset@gmail.com',
        password=args.password,
        about_me=about_me
    )
    metadata = get_metadata(os.path.join(args.metadata_path, 'examples.json'))

    bucket_name = 'nsynth'

    object_storage_client = ObjectStorageClient(
        endpoint=args.s3_endpoint,
        region=args.s3_region,
        access_key=args.aws_access_key_id,
        secret=args.aws_secret_access_key,
        bucket=bucket_name)

    audio_path = os.path.join(args.metadata_path, 'audio')

    object_storage_client.ensure_bucket_exists()

    for filename in os.listdir(audio_path):
        full_path = os.path.join(audio_path, filename)
        key, _ = os.path.splitext(filename)

        # push the audio data to s3
        with open(full_path, 'rb') as f:
            url = object_storage_client.put_object(key, f, 'audio/wav')
            logger.info(f'Created s3 resource at {url}')

        duration_seconds = soundfile.info(full_path).duration
        status, sound_uri, sound_id = annotate_client.create_sound(
            audio_url=url,
            info_url='https://magenta.tensorflow.org/datasets/nsynth',
            license_type='https://creativecommons.org/licenses/by/4.0',
            title=key,
            duration_seconds=duration_seconds,
            # TODO: This should depend on which part of the
            # dataset we're reading, and it might be helpful if this property
            # is mutable, especially if/when there is overlap between train
            # and validation sets
            tags=['validation'])

        if status == client.CREATED:
            # If we've just created the sound resource, create the annotation
            # as well
            annotate_client.create_annotations(
                sound_id,
                {
                    'start_seconds': 0,
                    'duration_seconds': duration_seconds,
                    'tags': metadata[key]
                })
            logger.info(f'Sound and annotation for {sound_id} created')
        elif status == client.CONFLICT:
            logger.info('Sound and annotation already created')
        else:
            raise RuntimeError(f'Unexpected {resp.status_code} encountered')
