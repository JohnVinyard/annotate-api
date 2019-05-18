import requests
from urllib.parse import urljoin
from http import client
import os


class Client(object):
    def __init__(self, hostname, auth=None):
        super().__init__()
        self.hostname = hostname
        self.session = requests.Session()
        self.session.auth = auth

    @property
    def auth(self):
        return self.session.auth

    @auth.setter
    def auth(self, value):
        self.session.auth = value

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

        resource = urljoin(self.hostname, '/users')
        resp = requests.post(resource, json=user_data)
        if resp.status_code == client.CREATED:
            print(f'Created user {user_name}')
        elif resp.status_code == client.CONFLICT:
            print(f'user {user_name} already exists')
            uri = urljoin(self.hostname, resp.headers['location'])
            update_data = {
                'password': password,
                'about_me': user_data['about_me']
            }
            resp = requests.patch(uri, json=update_data, auth=auth)
            resp.raise_for_status()
            print(f'Updated user {user_name}')
        self.session.auth = auth

    def upsert_dataset(
            self, user_name, email, password, about_me, info_url=None):
        self._upsert_user(
            'dataset', user_name, email, password, about_me, info_url)

    def upsert_featurebot(
            self, user_name, email, password, about_me, info_url=None):
        self._upsert_user(
            'featurebot', user_name, email, password, about_me, info_url)

    def get_user(self, user_name):
        resource = urljoin(self.hostname, '/users')
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
            info_url,
            license_type,
            title,
            duration_seconds,
            tags=None):

        resp = self.session.post(
            f'{self.hostname}/sounds',
            json={
                'audio_url': audio_url,
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
        resp = self.session.post(
            f'{self.hostname}/sounds/{sound_id}/annotations',
            json={
                'annotations': annotations
            }
        )
        return resp.status_code

    def get_sounds(self, low_id=None, page_size=100):
        resp = self.session.get(
            f'{self.hostname}/sounds',
            params={'low_id': low_id, 'page_size': page_size}
        )
        resp.raise_for_status()
        return resp.json()

    def get_annotations(self, user, low_id=None, page_size=100):
        resp = self.session.get(
            f'{self.hostname}/users/{user}/annotations',
            params={'low_id': low_id, 'page_size': page_size}
        )
        resp.raise_for_status()
        return resp.json()
