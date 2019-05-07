from http import client
from cli import DatasetArgumentParser
from client import Client
import argparse
import os
from csv import DictReader
from zounds.util import midi_to_note, midi_instrument
from s3client import ObjectStorageClient
import soundfile


def slugify(s):
    return s.lower().replace('(', '').replace(')', '').replace(' ', '-')


def get_metadata(path):
    metadata = dict()
    metadata_file = os.path.join(path, 'musicnet_metadata.csv')
    with open(metadata_file, 'r') as f:
        reader = DictReader(f)
        for row in reader:
            composer = slugify(row['composer'])
            ensemble = slugify(row['ensemble'])
            data = {
                'tags': [composer, ensemble],
                'title': f'{row["composition"]} {row["movement"]}'
            }
            metadata[row['id']] = data
    return metadata


def get_annotations(filename, samplerate):
    with open(filename, 'r') as f:
        reader = DictReader(f)
        for row in reader:
            start_seconds = int(row['start_time']) / samplerate
            stop_seconds = int(row['end_time']) / samplerate
            duration_seconds = stop_seconds - start_seconds
            note = midi_to_note(int(row['note']))
            instrument = slugify(midi_instrument(int(row['instrument'])))
            yield {
                'start_seconds': start_seconds,
                'duration_seconds': duration_seconds,
                'tags': [
                    f'musical_note:{note}',
                    instrument,
                ]
            }


def add_sounds(data_dir, labels_dir, metadata, tags):
    for audio_filename in os.listdir(data_dir):
        _id = os.path.splitext(audio_filename)[0]
        data = metadata[_id]
        audio_path = os.path.join(data_dir, audio_filename)
        labels_path = os.path.join(labels_dir, f'{_id}.csv')

        # push audio data to s3
        with open(audio_path, 'rb') as f:
            url = object_storage_client.put_object(_id, f, 'audio/wav')
            print(f'pushed {url} to s3')

        # create a sound
        info = soundfile.info(audio_path)
        status, sound_uri, sound_id = annotate_client.create_sound(
            audio_url=url,
            info_url=info_url,
            license_type='https://creativecommons.org/licenses/by/4.0',
            title=data['title'],
            duration_seconds=info.duration,
            tags=tags)

        if status == client.CREATED:
            # create a full-length annotation with composer and ensemble tags
            annotate_client.create_annotations(
                sound_id,
                {
                    'start_seconds': 0,
                    'duration_seconds': info.duration,
                    'tags': data['tags']
                })
            annotations = get_annotations(labels_path, info.samplerate)
            # create annotations for all notes
            annotate_client.create_annotations(sound_id, *annotations)
        elif status == client.CONFLICT:
            pass
        else:
            raise RuntimeError(f'Unexpected {status} encountered')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(parents=[
        DatasetArgumentParser()
    ])
    args = parser.parse_args()
    annotate_client = Client(args.annotate_api_endpoint)

    bucket_name = 'MusicNet'
    info_url = 'https://homes.cs.washington.edu/~thickstn/musicnet.html'

    object_storage_client = ObjectStorageClient(
        endpoint=args.s3_endpoint,
        region=args.s3_region,
        access_key=args.aws_access_key_id,
        secret=args.aws_secret_access_key,
        bucket=bucket_name)
    object_storage_client.ensure_bucket_exists()

    with open('musicnet.md', 'r') as f:
        about_me = f.read()

    annotate_client.upsert_dataset(
        user_name='musicnet',
        email='john.vinyard+musicnet-dataset@gmail.com',
        password=args.password,
        about_me=about_me,
        info_url=info_url)

    metadata = get_metadata(args.metadata_path)

    add_sounds(
        os.path.join(args.metadata_path, 'test_data'),
        os.path.join(args.metadata_path, 'test_labels'),
        metadata,
        ['test'])

    # add_sounds(
    #     os.path.join(args.metadata_path, 'train_data'),
    #     os.path.join(args.metadata_path, 'train_labels'),
    #     metadata,
    #     ['train'])
