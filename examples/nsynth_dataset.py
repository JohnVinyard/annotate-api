import boto3
import json
import argparse
from zounds.util import midi_to_note
import os
from botocore.exceptions import ClientError
import soundfile
from client import Client
from cli import DefaultArgumentParser
from http import client


def get_metadata(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    processed = {}
    for key, meta in data.items():
        tags = meta['qualities_str']
        tags.append(meta['instrument_family_str'])
        tags.append(meta['instrument_source_str'])

        # TODO: Decide on how key value pairs in tags will be handled
        tags.append('pitch:' + midi_to_note(meta['pitch']))
        tags.append('velocity:' + str(meta['velocity']))
        processed[key] = tags
    return processed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[
        DefaultArgumentParser()
    ])
    args = parser.parse_args()

    annotate_client = Client(args.annotate_api_endpoint)

    with open('nsynth.md', 'r') as f:
        about_me = f.read()

    annotate_client.upsert_dataset(
        user_name='nsynth',
        email='john.vinyard+nsynth-dataset@gmail.com',
        password=args.password,
        about_me=about_me
    )
    metadata = get_metadata(os.path.join(args.metadata_path, 'examples.json'))

    s3 = boto3.client(
        service_name='s3',
        endpoint_url=args.s3_endpoint,
        region_name=args.s3_region,
        aws_access_key_id=args.aws_access_key_id,
        aws_secret_access_key=args.aws_secret_access_key)

    audio_path = os.path.join(args.metadata_path, 'audio')
    nsynth_bucket_name = 'NSynth'

    # ensure the s3 bucket exists
    try:
        s3.head_bucket(Bucket=nsynth_bucket_name)
    except ClientError:
        s3.create_bucket(
            ACL='public-read',
            Bucket=nsynth_bucket_name)

    for filename in os.listdir(audio_path):
        full_path = os.path.join(audio_path, filename)
        key, _ = os.path.splitext(filename)

        # push the audio data to s3
        with open(full_path, 'rb') as f:
            s3.put_object(
                Bucket=nsynth_bucket_name,
                Body=f,
                Key=key,
                ACL='public-read',
                ContentType='audio/wav')
            url = f'{args.s3_endpoint}/{nsynth_bucket_name}/{key}'
            print(f'Created s3 resource at {url}')

        duration_seconds = soundfile.info(full_path).duration
        status, sound_uri, sound_id = annotate_client.create_sound(
            audio_url=url,
            info_url='https://magenta.tensorflow.org/datasets/nsynth',
            license_type='https://creativecommons.org/licenses/by/4.0',
            title=key,
            duration_seconds=duration_seconds,
            # TODO: This should depend on which part of the
            # dataset we're reading, and it might be helpful if this property
            # is mutable
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
            print(f'Sound and annotation for {sound_id} created')
        elif status == client.CONFLICT:
            print('Sound and annotation already created')
        else:
            raise RuntimeError(f'Unexpected {resp.status_code} encountered')
