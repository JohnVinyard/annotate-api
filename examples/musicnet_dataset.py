from http import client
from cli import DefaultArgumentParser
from client import Client
import argparse
import os
from csv import DictReader
from zounds.util import midi_to_note, midi_instrument


# TODO: How do I tag train and validation, as opposed to tags relating directly
# to the sound content itself?


def get_metadata(path):
    metadata = dict()
    metadata_file = os.path.join(path, 'musicnet_metadata.csv')
    with open(metadata_file, 'r') as f:
        reader = DictReader(f)
        for row in reader:
            composer = row['composer'].lower()
            ensemble = row['ensemble'].lower().replace(' ', '-')
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
            note = midi_to_note(int(row['note']))
            instrument = midi_instrument(int(row['instrument']))
            print(start_seconds, stop_seconds, note, instrument)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(parents=[
        DefaultArgumentParser()
    ])
    args = parser.parse_args()
    annotate_client = Client(args.annotate_api_endpoint)
    annotate_client.upsert_dataset(
        user_name='musicnet',
        email='john.vinyard+musicnet-dataset@gmail.com',
        password=args.password,
        about_me='''MusicNet is a collection of 330 freely-licensed classical music recordings, together with over 1 million annotated labels indicating the precise time of each note in every recording, the instrument that plays each note, and the note's position in the metrical structure of the composition. The labels are acquired from musical scores aligned to recordings by dynamic time warping. The labels are verified by trained musicians; we estimate a labeling error rate of 4%. We offer the MusicNet labels to the machine learning and music communities as a resource for training models and a common benchmark for comparing results'''
    )

    metadata = get_metadata(args.metadata_path)
    for _id, data in metadata.items():
        audio_path = os.path.join(args.metadata_path, 'train_data')
        labels_path = os.path.join(args.metadata_path, 'test_data')
        # push audio data to s3
        # create a sound
        # create a full-length annotation with composer and ensemble tags
        # read the id-specific CSV
        pass
