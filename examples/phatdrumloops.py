import argparse
from cli import DefaultArgumentParser
from client import Client
from s3client import ObjectStorageClient
import re
import requests
import urllib
from io import BytesIO
import soundfile
from http import client
from log import module_logger
from mp3encoder import encode_mp3
from pathlib import Path

logger = module_logger(__file__)


pattern = re.compile('href="(?P<uri>/audio/wav/[^\.]+\.wav)"')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(parents=[
        DefaultArgumentParser()
    ])
    args = parser.parse_args()
    annotate_client = Client(args.annotate_api_endpoint, logger=logger)

    bucket_name = 'phat-drum-loops'
    info_url = 'http://www.phatdrumloops.com/about.php'

    object_storage_client = ObjectStorageClient(
        endpoint=args.s3_endpoint,
        region=args.s3_region,
        access_key=args.aws_access_key_id,
        secret=args.aws_secret_access_key,
        bucket=bucket_name)
    object_storage_client.ensure_bucket_exists()

    with open('phatdrumloops.md', 'r') as f:
        about_me = f.read()

    annotate_client.upsert_dataset(
        user_name='phatdrumloops',
        email='john.vinyard+phatdrumloops-dataset@gmail.com',
        password=args.password,
        about_me=about_me,
        info_url=info_url)

    info_url = 'http://phatdrumloops.com/beats.php'
    resp = requests.get(info_url)

    for m in pattern.finditer(resp.text):
        path = Path(m.groupdict()['uri'])
        url = urllib.parse.urljoin('http://phatdrumloops.com', str(path))
        resp = requests.get(url, headers={'Range': 'bytes=0-'})
        bio = BytesIO(resp.content)

        try:
            encoded = encode_mp3(bio)
        except RuntimeError:
            logger.info(f'Error decoding audio for {url}. Skipping.')
            continue

        relative_path = path.relative_to('/')

        low_quality_id = \
            str(Path('low-quality') / relative_path.with_suffix('.mp3'))
        low_quality_url = object_storage_client.put_object(
            low_quality_id, encoded, 'audio/mp3')
        logger.info(f'Pushed {low_quality_url} to s3')
        bio.seek(0)

        _id = str(relative_path.with_suffix('.wav'))
        url = object_storage_client.put_object(_id, bio, 'audio/wav')
        logger.info(f'Pushed audio data for {url} to s3')
        bio.seek(0)

        info = soundfile.info(bio)
        status, sound_uri, sound_id = annotate_client.create_sound(
            audio_url=url,
            low_quality_audio_url=low_quality_url,
            info_url=info_url,
            license_type='https://creativecommons.org/licenses/by-nc-nd/4.0',
            title=_id,
            duration_seconds=info.duration)
        logger.info(f'Created sound resource {sound_uri}')
        if status == client.CREATED:
            annotate_client.create_annotations(
                sound_id,
                {
                    'start_seconds': 0,
                    'duration_seconds': info.duration,
                    'tags': ['drums']
                }
            )
            logger.info(f'Created annotation for {sound_uri}')
        elif status == client.CONFLICT:
            logger.warning(
                f'Already created sound and annotation for {sound_uri}')
            # we've already created this sound and annotation
            pass
        else:
            raise RuntimeError(f'Unexpected {status} encountered')
