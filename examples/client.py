import json

import requests
from urllib.parse import urlparse, urlunparse
from http import client
import os


class Client(object):
    def __init__(self, hostname, auth=None, logger=None):
        super().__init__()

        self.parsed = urlparse(hostname)

        self.hostname = self.parsed.netloc
        self.base_path = self.parsed.path

        self.session = requests.Session()
        self.session.auth = auth
        self.logger = logger

    @property
    def auth(self):
        return self.session.auth

    @auth.setter
    def auth(self, value):
        self.session.auth = value

    def uri(self, path):
        parsed = self.parsed._replace(
            path=os.path.join(self.parsed.path, path))
        return urlunparse(parsed)

    def _upsert_user(
            self,
            user_type,
            user_name,
            email,
            password,
            about_me,
            info_url=None):

        user_data = {
            'user_name': user_name,
            'user_type': user_type,
            'email': email,
            'password': password,
            'about_me': about_me,
            'info_url': info_url
        }
        auth = (user_data['user_name'], user_data['password'])
        resource = self.uri('users')
        resp = requests.post(resource, json=user_data)
        location = resp.headers['location']
        if resp.status_code == client.CREATED:
            self.logger.info(f'Created user {user_name}')
        elif resp.status_code == client.CONFLICT:
            self.logger.info(f'user {user_name} already exists')
            # uri = urljoin(self.hostname, location)
            uri = self.uri(location[1:])
            update_data = {
                'password': password,
                'about_me': user_data['about_me']
            }
            resp = requests.patch(uri, json=update_data, auth=auth)
            resp.raise_for_status()
            self.logger.info(f'Updated user {user_name}')
        self.session.auth = auth
        return location

    def upsert_user(self, user_name, email, password, about_me, info_url):
        return self._upsert_user(
            'human', user_name, email, password, about_me, info_url)

    def upsert_dataset(
            self, user_name, email, password, about_me, info_url=None):
        return self._upsert_user(
            'dataset', user_name, email, password, about_me, info_url)

    def upsert_featurebot(
            self, user_name, email, password, about_me, info_url=None):
        return self._upsert_user(
            'featurebot', user_name, email, password, about_me, info_url)

    def upsert_aggregator(
            self, user_name, email, password, about_me, info_url=None):
        return self._upsert_user(
            'aggregator', user_name, email, password, about_me, info_url)

    def get_user(self, user_name):
        resource = self.uri('users')
        resp = self.session.get(
            resource,
            params={'page_size': 1, 'user_name': user_name})
        resp.raise_for_status()
        try:
            return resp.json()['items'][0]
        except IndexError:
            raise KeyError(f'No user with name {user_name}')

    def create_sound(
            self,
            audio_url,
            low_quality_audio_url,
            info_url,
            license_type,
            title,
            duration_seconds,
            tags=None):

        uri = self.uri('sounds')
        resp = self.session.post(
            uri,
            json={
                'audio_url': audio_url,
                'low_quality_audio_url': low_quality_audio_url,
                'info_url': info_url,
                'license_type': license_type,
                'title': title,
                'duration_seconds': duration_seconds,
                'tags': tags
            }
        )
        if resp.status_code in (client.CREATED, client.CONFLICT):
            # Response should either be a 201 Created or a 409 Conflict, both of
            # which should include location information
            sound_uri = resp.headers['location']
            sound_id = os.path.split(sound_uri)[-1]
            return resp.status_code, sound_uri, sound_id
        else:
            resp.raise_for_status()

    def create_annotations(self, sound_id, *annotations):
        uri = self.uri(f'sounds/{sound_id}/annotations')
        step = 500
        for i in range(0, len(annotations), step):
            resp = self.session.post(
                uri,
                json={
                    'annotations': annotations[i: i + step]
                }
            )
        return resp.status_code

    def get_sounds(self, low_id=None, page_size=100):
        uri = self.uri('sounds')
        resp = self.session.get(
            uri,
            params={'low_id': low_id, 'page_size': page_size}
        )
        resp.raise_for_status()
        return resp.json()

    def get_annotations(self, user, low_id=None, page_size=100):
        uri = self.uri(f'users/{user}/annotations')
        resp = self.session.get(
            uri,
            params={'low_id': low_id, 'page_size': page_size}
        )
        resp.raise_for_status()
        return resp.json()
