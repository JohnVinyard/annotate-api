from http import client
from cli import DefaultArgumentParser
from client import Client
import argparse
import os
from csv import DictReader
from zounds.util import midi_to_note, midi_instrument


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
                'title': f'{row["compsition"]} {row["movement"]}'
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
            print(start_seconds, stop_seconds, note, instrument)
            yield {
                'start_seconds': start_seconds,
                'duration_seconds': duration_seconds,
                'tags': [
                    f'musical_note:{note}',
                    instrument,
                ]
            }


if __name__ == '__main__':

    parser = argparse.ArgumentParser(parents=[
        DefaultArgumentParser()
    ])
    args = parser.parse_args()
    annotate_client = Client(args.annotate_api_endpoint)

    with open('musicnet.md', 'r') as f:
        about_me = f.read()

    annotate_client.upsert_dataset(
        user_name='musicnet',
        email='john.vinyard+musicnet-dataset@gmail.com',
        password=args.password,
        about_me=about_me)

    metadata = get_metadata(args.metadata_path)
    for _id, data in metadata.items():
        audio_path = os.path.join(args.metadata_path, 'train_data')
        labels_path = os.path.join(args.metadata_path, 'test_data')
        # push audio data to s3
        # create a sound
        # create a full-length annotation with composer and ensemble tags
        # read the id-specific CSV
        pass
