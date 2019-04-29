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

    def upsert_dataset(self, user_name, email, password, about_me):
        user_data = {
            # TODO: Should users also have an info url property?
            'user_name': user_name,
            'user_type': 'dataset',
            'email': email,
            'password': password,
            # TODO: This should be read from a markdown file in the dataset-specific
            # repository
            'about_me': about_me
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
        # TODO: This is a temporary convenience for incremental refactoring.
        # Eventually the session should be treated as an internal and not
        # returned
        return auth

    def create_sound(
            self,
            audio_url,
            info_url,
            license_type,
            title,
            duration_seconds):

        resp = self.session.post(
            f'{self.hostname}/sounds',
            json={
                'audio_url': audio_url,
                'info_url': info_url,
                'license_type': license_type,
                'title': title,
                'duration_seconds': duration_seconds
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
