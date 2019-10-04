import shutil
import requests
import re
import os
from zipfile import ZipFile
from http import client
from pathlib import Path
from bot_helper import BotDriver
from io import BytesIO


def get_ids():
    pattern = re.compile('http://www\.archive\.org/details/(?P<_id>[^/"]+)')
    resp = requests.get('http://wiki.laptop.org/go/Free_sound_samples')
    return set(match.groupdict()['_id'] for match in pattern.finditer(resp.text))


def iter_ids(_ids):
    pattern = re.compile('.+\.zip')
    template = 'https://archive.org/download/{_id}{filename}'
    for _id in _ids:
        url = f'http://www.archive.org/details/{_id}'
        resp = requests.get(url, params={'output': 'json'})
        if resp.status_code != client.OK:
            continue
        files = resp.json()['files']
        filename = next(filter(lambda k: pattern.match(k), files.keys()))
        yield _id, template.format(**locals()), resp.json()


def download_file(url, local_path):
    r = requests.get(url, stream=True)
    with open(local_path, 'wb') as f:
        shutil.copyfileobj(r.raw, f)


def iter_sounds():
    _ids = get_ids()
    base_path = Path('/tmp')
    for _id, url, metadata in iter_ids(_ids):
        path = base_path.joinpath(_id)
        print(f'downloading {_id} {url}')
        download_file(url, path)
        with ZipFile(str(path)) as zf:
            for info in zf.infolist():
                if info.filename.startswith('__MACOSX'):
                    continue
                yield _id, info.filename, zf.open(info.filename), metadata
        print(f'removing{_id} {url}')
        os.remove(path)


class OLPCBot(object):
    def __init__(self):
        super().__init__()
        self.user_name = 'one_laptop_per_child'
        self.bucket_name = 'one-laptop-per-child'
        self.info_url = 'http://wiki.laptop.org/go/Free_sound_samples'
        self.about_me = 'one_laptop_per_child.md'
        self.email = 'john.vinyard+one-laptop-per-child@gmail.com'

    def iter_sounds(self):
        for _id, path, f, metadata in iter_sounds():
            yield path, BytesIO(f.read()), metadata

    def get_info_url(self, name, metadata):
        return f'https://archive.org/details/{name}'

    def get_license_type(self, name, metadata):
        return metadata['creativecommons']['license_url'].replace('\\', '')

    def get_annotations(self, name, metadata, bio):
        return []

#
# def save(base_path, _id, url):
#     full_path = os.path.join(base_path, _id) + '.zip'
#     print(f'saving {_id} to {full_path}')
#     download_file(url, full_path)
#     with zipfile.ZipFile(full_path) as zf:
#         zf.extractall(path=base_path)
#     os.remove(full_path)


if __name__ == '__main__':
    for _id, path, f in iter_sounds():
        print(_id, path, f)
