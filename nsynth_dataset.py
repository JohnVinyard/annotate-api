import requests
import boto3
import json
import argparse
from zounds.util import midi_to_note
import os
from urllib.parse import urljoin
from http import client
from botocore.exceptions import ClientError
import soundfile


# TODO: this should include train and validation datasets too

# TODO: How do I tag train and validation, as opposed to tags relating directly
# to the sound content itself?




def create_user(password, hostname):
    user_data = {
        # TODO: Should users also have an info url property?
        'user_name': 'nsynth',
        'user_type': 'dataset',
        'email': 'john.vinyard+nsynth-dataset@gmail.com',
        'password': password,
        # TODO: This should be read from a markdown file in the dataset-specific
        # repository
        'about_me': '''NSynth is an audio dataset containing 305,979 musical notes, each with a unique pitch, timbre, and envelope. For 1,006 instruments from commercial sample libraries, we generated four second, monophonic 16kHz audio snippets, referred to as notes, by ranging over every pitch of a standard MIDI pian o (21-108) as well as five different velocities (25, 50, 75, 100, 127). The note was held for the first three seconds and allowed to decay for the final second.'''
    }
    auth = (user_data['user_name'], user_data['password'])

    resource = urljoin(hostname, '/users')
    resp = requests.post(resource, json=user_data)
    if resp.status_code == client.CREATED:
        print('Created NSynth user')
    elif resp.status_code == client.CONFLICT:
        print('NSynth user already exists')
        uri = urljoin(hostname, resp.headers['location'])
        update_data = {
            'password': password,
            'about_me': user_data['about_me']
        }
        resp = requests.patch(uri, json=update_data, auth=auth)
        resp.raise_for_status()
        print('Updated NSynth user')
    session = requests.Session()
    session.auth = auth
    return session


def get_metadata(json_path):
    # TODO: Decide on how key value pairs in tags will be handled
    # TODO: Add velocity to the tags
    with open(json_path, 'r') as f:
        data = json.load(f)

    processed = {}
    for key, meta in data.items():
        tags = meta['qualities_str']
        tags.append(meta['instrument_family_str'])
        tags.append(meta['instrument_source_str'])
        tags.append('pitch:' + midi_to_note(meta['pitch']))
        processed[key] = tags
    return processed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--password',
        required=True,
        help='NSynth user password')
    parser.add_argument(
        '--metadata-path',
        required=True,
        help='path to JSON metadata file, excluding the filename')
    parser.add_argument(
        '--annotate-api-endpoint',
        required=True,
        help='scheme, hostname and optional port for annotation API')
    parser.add_argument(
        '--s3-endpoint',
        required=True,
        help='scheme, hostname and optional port of s3 endpoint')
    parser.add_argument(
        '--s3-region',
        required=False,
        default=None)
    parser.add_argument(
        '--aws-access-key-id',
        required=False,
        default=None)
    parser.add_argument(
        '--aws-secret-access-key',
        required=False,
        default=None)

    args = parser.parse_args()

    session = create_user(args.password, args.annotate_api_endpoint)
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
            duration_seconds = soundfile.info(f).duration
            f.seek(0)
            s3.put_object(
                Bucket=nsynth_bucket_name,
                Body=f,
                Key=key,
                ACL='public-read',
                ContentType='audio/wav')
            url = f'{args.s3_endpoint}/{nsynth_bucket_name}/{key}'
            print(f'Created s3 resource at {url}')

        # create the sound resource
        resp = session.post(
            f'{args.annotate_api_endpoint}/sounds',
            json={
                'audio_url': url,
                'info_url': 'https://magenta.tensorflow.org/datasets/nsynth',
                'license_type': 'https://creativecommons.org/licenses/by/4.0',
                'title': key,
                'duration_seconds': duration_seconds
            })
        # Response should either be a 201 Created or a 409 Conflict, both of
        # which should include location information
        sound_uri = resp.headers['location']
        sound_id = os.path.split(sound_uri)[-1]

        if resp.status_code == client.CREATED:
            # If we've just created the sound resource, create the annotation
            # as well
            resp = session.post(
                f'{args.annotate_api_endpoint}/sounds/{sound_id}/annotations',
                json={
                    'annotations': [
                        {
                            'start_seconds': 0,
                            'duration_seconds': duration_seconds,
                            'tags': metadata[key]
                        }
                    ]
                }
            )
            print(f'Sound and annotation for {sound_id} created')
        elif resp.status_code == client.CONFLICT:
            print('Sound and annotation already created')
        else:
            raise RuntimeError(f'Unexpected {resp.status_code} encountered')
