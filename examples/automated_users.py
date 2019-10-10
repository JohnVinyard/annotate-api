import subprocess
import threading
import argparse
import os


def output_reader(proc):
    for line in iter(proc.stdout.readline, b''):
        print(line.decode('utf-8'), end='')


class Process(subprocess.Popen):
    def __init__(
            self,
            filename,
            password,
            annotate_endpoint,
            s3_endpoint,
            **kwargs):

        self.s3_endpoint = s3_endpoint
        self.annotate_endpoint = annotate_endpoint
        self.password = password
        self.filename = filename

        cli_args = [
            'python', '-u', filename,
            '--password', password,
            '--annotate-api-endpoint', annotate_endpoint,
        ]

        if s3_endpoint:
            cli_args.extend(['--s3-endpoint', s3_endpoint])

        for item in kwargs.items():
            cli_args.extend(filter(lambda x: bool(x), item))

        super().__init__(
            cli_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd())
        self.thread = threading.Thread(
            target=output_reader, args=(self,), daemon=True)
        self.thread.start()


class ProcessCollection(object):
    def __init__(self, *processes):
        super().__init__()
        self.processes = {p.filename: p for p in processes}

    def wait(self):
        return {key: process.wait() for key, process in self.processes.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--annotate-api-endpoint',
        required=True,
        help='scheme, hostname and optional port for annotation API')
    parser.add_argument(
        '--s3-endpoint',
        default=None,
        help='scheme, hostname and optional port of s3 endpoint')
    args = parser.parse_args()

    password = 'password'

    def process(filename, **kwargs):
        return Process(
            filename,
            password,
            args.annotate_api_endpoint,
            args.s3_endpoint,
            **kwargs)

    processes = ProcessCollection(

        # datasets
        # process('phatdrumloops.py'),
        # process('internet_archive.py'),
        process('one_laptop_per_child.py'),
        # process(
        #     'musicnet_dataset.py',
        #     **{'--metadata-path': '/hdd/musicnet'}),
        # process(
        #     'nsynth_dataset.py',
        #     **{'--metadata-path': '/hdd/nsynth-valid.jsonwav/nsynth-valid'}),

        # bots
        process('chroma_bot.py'),
        process('stft_bot.py'),
        process('mfcc_bot.py'),
        # process('onset_bot.py'),
        process('spectrogram_bot.py'),
    )
    print(processes.wait())
