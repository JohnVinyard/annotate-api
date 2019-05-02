import unittest2
import requests
import subprocess
from http import client
import time
import os
import uuid

path, fn = os.path.split(__file__)


class BaseTests(object):
    def _user_create_data(
            self,
            user_name=None,
            password=None,
            user_type=None,
            email=None,
            about_me=None):
        return {
            'user_name': 'user' if user_name is None else user_name,
            'password': 'password' if password is None else password,
            'user_type': user_type or 'human',
            'email': 'hal@eta.com' if email is None else email,
            'about_me': about_me or 'Up and coming tennis star'
        }

    def _get_auth(self, user_create_data):
        return user_create_data['user_name'], user_create_data['password']

    def create_user(
            self,
            user_type='human',
            user_name=None,
            email=None,
            about_me=None):

        create_data = self._user_create_data(
            user_name=user_name or uuid.uuid4().hex,
            password=uuid.uuid4().hex,
            user_type=user_type,
            email=email or '{}@example.com'.format(uuid.uuid4().hex),
            about_me=about_me or uuid.uuid4().hex
        )
        create_resp = requests.post(self.users_resource(), json=create_data)
        self.assertEqual(client.CREATED, create_resp.status_code)
        location = create_resp.headers['location']
        return create_data, location

    def sound_data(
            self,
            info_url=None,
            audio_url=None,
            license_type=None,
            title=None,
            duration_seconds=None,
            tags=None):
        return dict(
            info_url=info_url or 'https://archive.org/details/Greatest_Speeches_of_the_20th_Century',
            audio_url=audio_url or 'https://archive.org/download/Greatest_Speeches_of_the_20th_Century/AbdicationAddress.ogg',
            license_type=license_type or 'https://creativecommons.org/licenses/by/4.0',
            title='Abdication Address - King Edward VIII' if title is None else title,
            duration_seconds=duration_seconds or (6 * 60) + 42,
            tags=tags
        )

    def annotation_data(self, tags=None, data_url=None, start_seconds=1):
        return dict(
            start_seconds=start_seconds,
            duration_seconds=1,
            tags=tags,
            data_url=data_url)

    def _create_sound_with_user(self, auth, tags=None):
        sound_id = uuid.uuid4().hex
        sound_data = self.sound_data(
            audio_url=f'https://example.com/{sound_id}', tags=tags)
        resp = requests.post(
            self.sounds_resource(), json=sound_data, auth=auth)
        return resp.headers['location'].split('/')[-1]

    def _create_sounds_with_user(self, auth, n_sounds, tags=None, delay=None):
        for _ in range(n_sounds):
            self._create_sound_with_user(auth, tags=tags)
            if delay:
                time.sleep(delay)

    @classmethod
    def startup_executable(cls):
        return os.path.join(path, 'start.sh')

    @classmethod
    def stop_executable(cls):
        return os.path.join(path, 'stop.sh')

    @classmethod
    def url(cls, path=''):
        return 'http://localhost{path}'.format(**locals())

    @classmethod
    def root_resource(cls):
        return cls.url()

    @classmethod
    def users_resource(cls, user_id=''):
        return cls.url(f'/users/{user_id}')

    @classmethod
    def sounds_resource(cls, sound_id=''):
        return cls.url(f'/sounds/{sound_id}')

    @classmethod
    def user_sounds_resource(cls, user_id=''):
        return cls.url(f'/users/{user_id}/sounds')

    @classmethod
    def user_annotations_resource(cls, user_id=''):
        return cls.url(f'/users/{user_id}/annotations')

    @classmethod
    def sound_annotations_resource(cls, sound_id=''):
        return cls.url(f'/sounds/{sound_id}/annotations')

    @classmethod
    def delete_all_data(cls):
        requests.delete(cls.root_resource())

    @classmethod
    def _health_check(cls):
        for i in range(90):
            time.sleep(1)
            print('try number {i}'.format(**locals()))
            try:
                resp = requests.get(cls.root_resource())
                resp.raise_for_status()
                break
            except (requests.HTTPError, requests.ConnectionError):
                pass

    @classmethod
    def setUpClass(cls):
        cls.process = subprocess.Popen([cls.startup_executable()], shell=True)
        cls._health_check()
        cls.delete_all_data()

    @classmethod
    def tearDownClass(cls):
        cls.delete_all_data()
        cls.process.terminate()
        cls.process = subprocess.Popen(
            [cls.stop_executable()], shell=True)


class SmokeTests(BaseTests, unittest2.TestCase):
    """
    Basic tests to ensure that the API is up and responding to requests
    """

    def tearDown(self):
        self.delete_all_data()

    def setUp(self):
        self.resp = requests.get(self.root_resource())

    def test_status_code_is_ok(self):
        self.assertEqual(self.resp.status_code, client.OK)

    def test_includes_sound_and_annotation_counts(self):
        data = self.resp.json()
        self.assertIn('totalSounds', data)
        self.assertIn('totalAnnotations', data)
        self.assertIn('totalUsers', data)


class UserTests(BaseTests, unittest2.TestCase):
    """
    Tests to ensure user CRUD operations, including validation
    """

    def tearDown(self):
        self.delete_all_data()

    def test_can_create_and_fetch_new_user(self):
        create_data = self._user_create_data(user_name='HalIncandenza')
        create_resp = requests.post(self.users_resource(), json=create_data)
        self.assertEqual(client.CREATED, create_resp.status_code)
        uri = create_resp.headers['location']
        _id = uri.split('/')[-1]
        user_resp = requests.get(
            self.url(uri), auth=self._get_auth(create_data))
        self.assertEqual(client.OK, user_resp.status_code)
        self.assertEqual(
            user_resp.json()['user_name'], create_data['user_name'])
        self.assertEqual(user_resp.json()['id'], _id)

    def test_can_head_user(self):
        user1, user1_location = self.create_user()
        user2, user2_location = self.create_user()
        resp = requests.head(
            self.url(user2_location), auth=self._get_auth(user1))
        self.assertEqual(client.NO_CONTENT, resp.status_code)

    def test_head_returns_not_found_for_non_existent_user(self):
        user1, user1_location = self.create_user()
        resp = requests.head(
            self.users_resource('1234'), auth=self._get_auth(user1))
        self.assertEqual(client.NOT_FOUND, resp.status_code)

    def test_unauthorized_when_attempting_to_list_users_without_creds(self):
        list_users_resp = requests.get(self.users_resource())
        self.assertEqual(list_users_resp.status_code, client.UNAUTHORIZED)

    def test_can_page_through_users(self):
        requesting_user, _ = self.create_user()

        for _ in range(95):
            self.create_user()

        resp = requests.get(
            self.users_resource(),
            params={'page_size': 10},
            auth=self._get_auth(requesting_user))

        self.assertEqual(client.OK, resp.status_code)
        resp_data = resp.json()
        self.assertEqual(10, len(resp_data['items']))
        self.assertEqual(96, resp_data['total_count'])

        items = [resp_data['items']]

        while 'next' in resp_data:
            current = requests.get(
                self.url(resp_data['next']),
                auth=self._get_auth(requesting_user))
            resp_data = current.json()
            items.append(resp_data['items'])

        self.assertEqual(10, len(items))
        self.assertEqual(6, len(items[-1]))
        self.assertEqual(96, sum(len(item) for item in items))

    def test_can_page_through_users_and_filter_by_user_type(self):
        requesting_user, _ = self.create_user()

        for _ in range(10):
            self.create_user(user_type='human')

        for _ in range(10):
            self.create_user(user_type='featurebot')

        resp = requests.get(
            self.users_resource(),
            params={'page_size': 3, 'user_type': 'featurebot'},
            auth=self._get_auth(requesting_user))

        self.assertEqual(client.OK, resp.status_code)
        resp_data = resp.json()
        self.assertEqual(3, len(resp_data['items']))
        self.assertEqual(10, resp_data['total_count'])

        items = [resp_data['items']]

        while 'next' in resp_data:
            current = requests.get(
                self.url(resp_data['next']),
                auth=self._get_auth(requesting_user))
            resp_data = current.json()
            items.append(resp_data['items'])

        self.assertEqual(4, len(items))
        self.assertEqual(1, len(items[-1]))
        self.assertEqual(10, sum(len(item) for item in items))

    def test_can_view_most_data_about_self_when_listing_users(self):
        user1, user1_location = self.create_user()
        user2, user2_location = self.create_user()
        requesting_user_auth = self._get_auth(user1)
        resp = requests.get(
            self.users_resource(),
            params={'page_size': 3},
            auth=requesting_user_auth)
        self.assertEqual(client.OK, resp.status_code)
        resp_data = resp.json()
        self.assertEqual(2, resp_data['total_count'])
        self.assertEqual(2, len(resp_data['items']))
        self.assertEqual(user1['email'], resp_data['items'][1]['email'])

    def test_can_view_limited_data_about_other_user_when_listing_users(self):
        user1, user1_location = self.create_user()
        user2, user2_location = self.create_user()
        requesting_user_auth = self._get_auth(user1)
        resp = requests.get(
            self.users_resource(),
            params={'page_size': 3},
            auth=requesting_user_auth)
        self.assertEqual(client.OK, resp.status_code)
        resp_data = resp.json()
        self.assertEqual(2, resp_data['total_count'])
        self.assertEqual(2, len(resp_data['items']))
        self.assertNotIn('email', resp_data['items'][0])

    def test_bad_request_when_filtering_by_invalid_user_type(self):
        requesting_user, _ = self.create_user()

        resp = requests.get(
            self.users_resource(),
            params={'page_size': 3, 'user_type': 'animal'},
            auth=self._get_auth(requesting_user))
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_bad_request_when_page_size_is_negative(self):
        requesting_user, _ = self.create_user()

        resp = requests.get(
            self.users_resource(),
            params={'page_size': -3, 'user_type': 'human'},
            auth=self._get_auth(requesting_user))
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_bad_request_when_page_size_is_too_large(self):
        requesting_user, _ = self.create_user()

        resp = requests.get(
            self.users_resource(),
            params={'page_size': 10000, 'user_type': 'human'},
            auth=self._get_auth(requesting_user))
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_can_view_most_data_about_self(self):
        user1, user1_location = self.create_user()
        resp = requests.get(
            self.url(user1_location), auth=self._get_auth(user1))
        self.assertIn('email', resp.json())
        self.assertNotIn('password', resp.json())

    def test_can_view_limited_data_about_other_user(self):
        user1, user1_location = self.create_user()
        user2, user2_location = self.create_user()
        resp = requests.get(
            self.url(user1_location), auth=self._get_auth(user2))
        self.assertNotIn('email', resp.json())
        self.assertNotIn('password', resp.json())

    def test_can_delete_self(self):
        user1, user1_location = self.create_user()
        user2, user2_location = self.create_user()

        auth = self._get_auth(user1)
        uri = self.url(user1_location)

        resp = requests.get(uri, auth=auth)
        self.assertEqual(user1['email'], resp.json()['email'])
        delete_resp = requests.delete(uri, auth=auth)
        self.assertEqual(client.OK, delete_resp.status_code)

        get_resp = requests.get(uri, auth=self._get_auth(user2))
        self.assertEqual(client.NOT_FOUND, get_resp.status_code)

    def test_cannot_delete_other_user(self):
        user1, user1_location = self.create_user()
        user2, user2_location = self.create_user()

        auth = self._get_auth(user1)
        uri = self.url(user1_location)

        resp = requests.get(uri, auth=auth)
        self.assertEqual(user1['email'], resp.json()['email'])
        delete_resp = requests.delete(uri, auth=self._get_auth(user2))
        self.assertEqual(client.FORBIDDEN, delete_resp.status_code)

    def test_not_found_when_deleting_non_existent_user(self):
        user1, user1_location = self.create_user()
        delete_resp = requests.delete(
            self.users_resource('1234'), auth=self._get_auth(user1))
        self.assertEqual(client.NOT_FOUND, delete_resp.status_code)

    def test_unauthorized_when_deleting_user_without_creds(self):
        delete_resp = requests.delete(self.users_resource('1234'))
        self.assertEqual(client.UNAUTHORIZED, delete_resp.status_code)

    def test_unauthorized_when_fetching_single_user_without_creds(self):
        user1, user1_location = self.create_user()
        user_resp = requests.get(self.url(user1_location))
        self.assertEqual(client.UNAUTHORIZED, user_resp.status_code)

    def test_validation_error_for_bad_user_type(self):
        user1_data = self._user_create_data(user_type='animal')
        resp = requests.post(self.users_resource(), json=user1_data)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)
        desc = resp.json()['description']
        self.assertEqual('user_type', desc[0][0])

    def test_validation_error_for_bad_user_name(self):
        user1_data = self._user_create_data(user_name='')
        resp = requests.post(self.users_resource(), json=user1_data)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)
        desc = resp.json()['description']
        self.assertEqual(1, len(desc))
        self.assertEqual('user_name', desc[0][0])

    def test_validation_error_for_bad_password(self):
        user1_data = self._user_create_data(password='')
        resp = requests.post(self.users_resource(), json=user1_data)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)
        desc = resp.json()['description']
        print(resp.json())
        self.assertEqual(1, len(desc))
        self.assertEqual('password', desc[0][0])

    def test_validation_error_for_bad_email(self):
        user1_data = self._user_create_data(email='')
        resp = requests.post(self.users_resource(), json=user1_data)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)
        desc = resp.json()['description']
        self.assertEqual(1, len(desc))
        self.assertEqual('email', desc[0][0])

    def test_validation_error_has_information_about_multiple_problems(self):
        user1_data = self._user_create_data(user_name='', email='')
        resp = requests.post(self.users_resource(), json=user1_data)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)
        desc = resp.json()['description']
        self.assertEqual(2, len(desc))
        fields = set(d[0] for d in desc)
        self.assertIn('user_name', fields)
        self.assertIn('email', fields)

    def test_usernames_must_be_unique(self):
        user1_data = self._user_create_data(
            user_name='user1', email='user1@example.com')
        resp = requests.post(self.users_resource(), json=user1_data)
        self.assertEqual(client.CREATED, resp.status_code)
        user2_data = self._user_create_data(
            user_name='user1', email='user2@example.com')
        resp2 = requests.post(self.users_resource(), json=user2_data)
        self.assertEqual(client.CONFLICT, resp2.status_code)

    def test_email_addresses_must_be_unique(self):
        user1_data = self._user_create_data(
            user_name='user1', email='user1@example.com')
        resp = requests.post(self.users_resource(), json=user1_data)
        self.assertEqual(client.CREATED, resp.status_code)
        user2_data = self._user_create_data(
            user_name='user2', email='user1@example.com')
        resp2 = requests.post(self.users_resource(), json=user2_data)
        self.assertEqual(client.CONFLICT, resp2.status_code)

    def test_location_header_is_included_when_conflict_is_encountered(self):
        user1_data = self._user_create_data(
            user_name='user1', email='user1@example.com')
        resp = requests.post(self.users_resource(), json=user1_data)
        self.assertEqual(client.CREATED, resp.status_code)
        expected_location = resp.headers['location']
        user2_data = self._user_create_data(
            user_name='user2', email='user1@example.com')
        resp2 = requests.post(self.users_resource(), json=user2_data)
        self.assertEqual(expected_location, resp2.headers['location'])

    def test_can_update_about_me_text(self):
        user1, user1_location = self.create_user(
            user_type='human', about_me='original')
        auth = self._get_auth(user1)
        resp = requests.patch(
            self.url(user1_location), json={'about_me': 'modified'}, auth=auth)
        self.assertEqual(client.OK, resp.status_code)
        resp = requests.get(
            self.url(user1_location), auth=auth)
        self.assertEqual('modified', resp.json()['about_me'])

    def test_cannot_update_other_user(self):
        user1, user1_location = self.create_user()
        user2, user2_location = self.create_user()
        auth = self._get_auth(user1)
        resp = requests.patch(
            self.url(user2_location), json={'about_me': 'modified'}, auth=auth)
        self.assertEqual(client.FORBIDDEN, resp.status_code)

    def test_invalid_about_me_update_for_featurebot_fails(self):
        user1, user1_location = self.create_user(
            user_type='dataset', about_me='original')
        auth = self._get_auth(user1)
        resp = requests.patch(
            self.url(user1_location), json={'about_me': ''}, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_invalid_about_me_update_for_dataset_fails(self):
        user1, user1_location = self.create_user(
            user_type='featurebot', about_me='original')
        auth = self._get_auth(user1)
        resp = requests.patch(
            self.url(user1_location), json={'about_me': ''}, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_can_update_password(self):
        user1, user1_location = self.create_user(
            user_type='human', about_me='original')
        auth = self._get_auth(user1)
        resp = requests.patch(
            self.url(user1_location), json={'password': 'modified'}, auth=auth)
        self.assertEqual(client.OK, resp.status_code)
        # using the original password
        resp = requests.get(
            self.url(user1_location), auth=auth)
        self.assertEqual(client.UNAUTHORIZED, resp.status_code)

        # using the new password
        new_auth = (user1['user_name'], 'modified')
        resp = requests.get(
            self.url(user1_location), auth=new_auth)
        self.assertEqual(client.OK, resp.status_code)
        self.assertEqual(user1['email'], resp.json()['email'])

    def test_cannot_update_username(self):
        user1, user1_location = self.create_user()
        auth = self._get_auth(user1)
        resp = requests.patch(
            self.url(user1_location), json={'user_name': 'modified'}, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_cannot_update_email(self):
        user1, user1_location = self.create_user()
        auth = self._get_auth(user1)
        resp = requests.patch(
            self.url(user1_location), json={'email': 'modified'}, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_not_found_for_non_existent_user(self):
        user1, user1_location = self.create_user()
        user_resp = requests.get(
            self.users_resource('1234'), auth=self._get_auth(user1))
        self.assertEqual(client.NOT_FOUND, user_resp.status_code)

    def test_unauthorized_when_fetching_non_existent_user_without_creds(self):
        user_resp = requests.get(self.users_resource('1234'))
        self.assertEqual(client.UNAUTHORIZED, user_resp.status_code)


class SoundTests(BaseTests, unittest2.TestCase):
    def tearDown(self):
        self.delete_all_data()

    def test_dataset_can_create_sound(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        sound_location = resp.headers['location']
        sound_resp = requests.get(self.url(sound_location), auth=auth)
        self.assertEqual(client.OK, sound_resp.status_code)
        self.assertEqual(sound_data['info_url'], sound_resp.json()['info_url'])

    def test_cannot_create_duplicate_sound(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CONFLICT, resp.status_code)

    def test_location_header_is_returned_when_creating_duplicate_sound(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        expected_location = resp.headers['location']
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CONFLICT, resp.status_code)
        self.assertEqual(expected_location, resp.headers['location'])

    def test_featurebot_cannot_create_sound(self):
        user1, user1_location = self.create_user(user_type='featurebot')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.FORBIDDEN, resp.status_code)

    def test_unauthorized_when_creating_sound_anonymously(self):
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data)
        self.assertEqual(client.UNAUTHORIZED, resp.status_code)

    def test_bad_request_for_bad_info_url(self):
        user1, user1_location = self.create_user()
        auth = self._get_auth(user1)
        sound_data = self.sound_data(info_url='blah')
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_bad_request_for_bad_audio_url(self):
        user1, user1_location = self.create_user()
        auth = self._get_auth(user1)
        sound_data = self.sound_data(audio_url='blah')
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_bad_request_for_bad_license_type(self):
        user1, user1_location = self.create_user()
        auth = self._get_auth(user1)
        sound_data = self.sound_data(license_type='blah')
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_bad_request_for_missing_title(self):
        user1, user1_location = self.create_user()
        auth = self._get_auth(user1)
        sound_data = self.sound_data(title='')
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_bad_request_for_missing_duration(self):
        user1, user1_location = self.create_user()
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        del sound_data['duration_seconds']
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_explicit_created_by_is_ignored(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        sound_data['created_by'] = '1234'
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        sound_location = resp.headers['location']
        sound_resp = requests.get(self.url(sound_location), auth=auth)
        self.assertEqual(client.OK, sound_resp.status_code)
        self.assertEqual(user1_location, sound_resp.json()['created_by'])

    def test_user_is_returned_as_uri(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        sound_location = resp.headers['location']
        sound_resp = requests.get(self.url(sound_location), auth=auth)
        self.assertEqual(client.OK, sound_resp.status_code)
        self.assertEqual(user1_location, sound_resp.json()['created_by'])

    def test_can_head_sound(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        sound_location = resp.headers['location']
        sound_resp = requests.head(self.url(sound_location), auth=auth)
        self.assertEqual(client.NO_CONTENT, sound_resp.status_code)

    def test_unauthorized_when_getting_sound_anonymously(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        sound_location = resp.headers['location']
        sound_resp = requests.head(self.url(sound_location))
        self.assertEqual(client.UNAUTHORIZED, sound_resp.status_code)

    def test_sounds_are_immutable(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        sound_location = resp.headers['location']
        sound_resp = requests.patch(
            self.url(sound_location),
            json={'info_url': 'https://example.com'},
            auth=auth)
        self.assertEqual(client.METHOD_NOT_ALLOWED, sound_resp.status_code)

    def test_cannot_delete_sound(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        sound_data = self.sound_data()
        resp = requests.post(self.sounds_resource(), json=sound_data, auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
        sound_location = resp.headers['location']
        sound_resp = requests.delete(self.url(sound_location), auth=auth)
        self.assertEqual(client.METHOD_NOT_ALLOWED, sound_resp.status_code)

    def test_can_list_sounds(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)

        self._create_sounds_with_user(auth, 93)
        resp = requests.get(
            self.sounds_resource(),
            params={'page_size': 10},
            auth=auth)

        self.assertEqual(client.OK, resp.status_code)
        resp_data = resp.json()
        self.assertEqual(10, len(resp_data['items']))
        self.assertEqual(93, resp_data['total_count'])

        items = [resp_data['items']]

        while 'next' in resp_data:
            current = requests.get(
                self.url(resp_data['next']),
                auth=auth)
            resp_data = current.json()
            items.append(resp_data['items'])

        self.assertEqual(10, len(items))
        self.assertEqual(3, len(items[-1]))
        self.assertEqual(93, sum(len(item) for item in items))

    def test_can_list_sounds_by_user_id(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)

        self._create_sounds_with_user(auth, 5)
        user2, user2_location = self.create_user(user_type='dataset')
        auth2 = self._get_auth(user2)
        user2_id = user1_location.split('/')[-1]

        self._create_sounds_with_user(auth2, 5)
        resp = requests.get(
            self.sounds_resource(),
            params={'page_size': 10, 'created_by': user2_id},
            auth=auth)

        items = resp.json()['items']
        self.assertEqual(5, len(items))
        user_uri = f'/users/{user2_id}'
        self.assertTrue(all([item['created_by'] == user_uri for item in items]))

    def test_can_stream_sounds_by_user_id(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)

        self._create_sounds_with_user(auth, 5)
        user2, user2_location = self.create_user(user_type='dataset')
        auth2 = self._get_auth(user2)
        user2_id = user1_location.split('/')[-1]

        self._create_sounds_with_user(auth2, 5)
        resp = requests.get(
            self.sounds_resource(),
            params={'page_size': 2, 'created_by': user2_id},
            auth=auth)
        items = resp.json()['items']
        self.assertEqual(2, len(items))
        user_uri = f'/users/{user2_id}'
        self.assertTrue(all([item['created_by'] == user_uri for item in items]))

        low_id = items[-1]['id']

        resp = requests.get(
            self.sounds_resource(),
            params={
                'page_size': 100,
                'created_by': user2_id,
                'low_id': low_id
            },
            auth=auth)
        items = resp.json()['items']
        self.assertEqual(3, len(items))
        user_uri = f'/users/{user2_id}'
        self.assertTrue(all([item['created_by'] == user_uri for item in items]))

    def test_supports_something_stream_like(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)

        self._create_sounds_with_user(auth, 10, delay=0.1)
        resp = requests.get(
            self.sounds_resource(),
            params={'page_size': 5},
            auth=auth)

        self.assertEqual(client.OK, resp.status_code)
        self.assertEqual(5, len(resp.json()['items']))
        self.assertEqual(10, resp.json()['total_count'])

        low_id = resp.json()['items'][-1]['id']

        resp = requests.get(
            self.sounds_resource(),
            params={
                'page_size': 10,
                'low_id': low_id
            },
            auth=auth)

        self.assertEqual(client.OK, resp.status_code)
        self.assertEqual(5, resp.json()['total_count'])
        self.assertEqual(5, len(resp.json()['items']))


class UserSoundTests(BaseTests, unittest2.TestCase):
    def test_not_found_for_nonexistent_user(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)
        self._create_sounds_with_user(auth, 5)
        resp = requests.get(
            self.user_sounds_resource('BAD_USER_ID'),
            params={'page_size': 10},
            auth=auth)
        self.assertEqual(client.NOT_FOUND, resp.status_code)

    def test_can_list_all_sounds_from_user(self):
        user1, user1_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user1)

        self._create_sounds_with_user(auth, 5)
        user2, user2_location = self.create_user(user_type='dataset')
        auth2 = self._get_auth(user2)
        user2_id = user2_location.split('/')[-1]

        self._create_sounds_with_user(auth2, 5)
        resp = requests.get(
            self.user_sounds_resource(user2_id),
            params={'page_size': 10},
            auth=auth)

        items = resp.json()['items']
        self.assertEqual(5, len(items))
        user_uri = f'/users/{user2_id}'
        self.assertTrue(all([item['created_by'] == user_uri for item in items]))

    def test_can_stream_user_sounds_using_low_id(self):
        user, user_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user)
        user_id = user_location.split('/')[-1]
        self._create_sounds_with_user(auth, 10)

        user2, user2_location = self.create_user(user_type='dataset')
        auth2 = self._get_auth(user2)
        self._create_sounds_with_user(auth2, 5)

        resp = requests.get(
            self.user_sounds_resource(user_id),
            params={'page_size': 3},
            auth=auth)
        items = resp.json()['items']
        low_id = items[-1]['id']

        resp = requests.get(
            self.user_sounds_resource(user_id),
            params={
                'page_size': 100,
                'low_id': low_id
            },
            auth=auth)
        user_uri = f'/users/{user_id}'
        items = resp.json()['items']
        self.assertEqual(7, len(items))
        self.assertTrue(all([item['created_by'] == user_uri for item in items]))

    def test_can_filter_by_sound_tags(self):
        user, user_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user)
        user_id = user_location.split('/')[-1]
        self._create_sounds_with_user(auth, 10, tags=['train'])
        self._create_sounds_with_user(auth, 11, tags=['validation'])

        resp = requests.get(
            self.user_sounds_resource(user_id),
            params={'page_size': 100, 'tags': 'train'},
            auth=auth)

        items = resp.json()['items']
        self.assertEqual(10, len(items))

        resp = requests.get(
            self.user_sounds_resource(user_id),
            params={'page_size': 100, 'tags': 'validation'},
            auth=auth)

        items = resp.json()['items']
        self.assertEqual(11, len(items))

    def test_sound_tag_filtering_is_implicit_and(self):
        user, user_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user)
        user_id = user_location.split('/')[-1]
        self._create_sounds_with_user(auth, 10, tags=['train'])
        self._create_sounds_with_user(auth, 11, tags=['validation'])
        self._create_sounds_with_user(auth, 5, tags=['train', 'validation'])

        resp = requests.get(
            self.user_sounds_resource(user_id),
            params={'page_size': 100, 'tags': 'train'},
            auth=auth)

        items = resp.json()['items']
        self.assertEqual(15, len(items))

        resp = requests.get(
            self.user_sounds_resource(user_id),
            params={'page_size': 100, 'tags': 'validation'},
            auth=auth)

        items = resp.json()['items']
        self.assertEqual(16, len(items))

        resp = requests.get(
            self.user_sounds_resource(user_id),
            params={'page_size': 100, 'tags': ['validation', 'train']},
            auth=auth)

        items = resp.json()['items']
        self.assertEqual(5, len(items))


class UserAnnotationTests(BaseTests, unittest2.TestCase):
    def test_not_found_for_nonexistent_user(self):
        user, user_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = [
            self.annotation_data(tags=[f'drums{i}']) for i in range(10)]
        requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': annotation_data},
            auth=auth)

        resp = requests.get(
            self.user_annotations_resource('BAD_USER_ID'), auth=auth)
        self.assertEqual(client.NOT_FOUND, resp.status_code)

    def test_can_list_all_annotations_for_user(self):
        user, user_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = [
            self.annotation_data(tags=[f'drums{i}']) for i in range(10)]
        requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': annotation_data},
            auth=auth)

        fb, fb_location = self.create_user(user_type='featurebot')
        fb_auth = self._get_auth(fb)
        fb_id = fb_location.split('/')[-1]
        annotation_data = [
            self.annotation_data(tags=[f'drums{i}']) for i in range(3)]
        requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': annotation_data},
            auth=fb_auth)

        user_uri = f'/users/{fb_id}'
        resp = requests.get(
            self.user_annotations_resource(fb_id),
            auth=auth)
        items = resp.json()['items']
        self.assertEqual(3, len(items))
        self.assertTrue(all([item['created_by'] == user_uri for item in items]))

    def test_can_stream_user_annotations_using_low_id(self):
        user, user_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = [
            self.annotation_data(tags=[f'drums{i}']) for i in range(10)]
        requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': annotation_data},
            auth=auth)

        fb, fb_location = self.create_user(user_type='featurebot')
        fb_auth = self._get_auth(fb)
        fb_id = fb_location.split('/')[-1]
        annotation_data = [
            self.annotation_data(tags=[f'drums{i}']) for i in range(40)]
        requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': annotation_data},
            auth=fb_auth)

        resp = requests.get(
            self.user_annotations_resource(fb_id),
            params={'page_size': 11},
            auth=auth)
        items = resp.json()['items']
        self.assertEqual(11, len(items))
        low_id = items[-1]['id']

        resp = requests.get(
            self.user_annotations_resource(fb_id),
            params={
                'page_size': 100,
                'low_id': low_id
            },
            auth=auth)
        user_uri = f'/users/{fb_id}'
        items = resp.json()['items']
        self.assertEqual(29, len(items))
        self.assertTrue(all([item['created_by'] == user_uri for item in items]))


class AnnotationTests(BaseTests, unittest2.TestCase):
    def tearDown(self):
        self.delete_all_data()

    def test_human_can_create_annotation(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = self.annotation_data(tags=['drums'])
        resp = requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': [annotation_data]},
            auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)

    def test_featurebot_can_create_annotation(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)

        fb, fb_location = self.create_user(user_type='featurebot')
        fb_auth = self._get_auth(fb)
        annotation_data = self.annotation_data(tags=['drums'])
        resp = requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': [annotation_data]},
            auth=fb_auth)
        self.assertEqual(client.CREATED, resp.status_code)

    def test_dataset_can_create_annotation(self):
        user, user_location = self.create_user(user_type='dataset')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = self.annotation_data(tags=['drums'])
        resp = requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': [annotation_data]},
            auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)

    def test_can_create_multiple_annotations_at_once(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = [
            self.annotation_data(tags=[f'drums{i}']) for i in range(10)]
        resp = requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': annotation_data},
            auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)

    def test_cannot_create_annotation_for_nonexistent_sound(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = self.annotation_data(tags=['drums'])
        resp = requests.post(
            self.sound_annotations_resource(sound_id + 'WRONG'),
            json={'annotations': [annotation_data]},
            auth=auth)
        self.assertEqual(client.NOT_FOUND, resp.status_code)

    def test_can_list_annotations_for_a_sound(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = [
            self.annotation_data(tags=[f'drums{i}']) for i in range(10)]
        requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': annotation_data},
            auth=auth)
        resp = requests.get(
            self.sound_annotations_resource(sound_id),
            auth=auth)
        self.assertEqual(10, len(resp.json()['items']))

    def test_not_found_when_listing_annotations_for_nonexistent_sound(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        resp = requests.get(
            self.sound_annotations_resource('WRONG'),
            auth=auth)
        self.assertEqual(client.NOT_FOUND, resp.status_code)

    def test_can_create_annotation_with_external_data_url(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = self.annotation_data(data_url='https://example.com')
        resp = requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': [annotation_data]},
            auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)

    def test_no_annotations_are_created_when_one_is_invalid(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)

        def data_url(i):
            return 'WRONG' if i == 0 else 'https://example.com'

        annotation_data = \
            [self.annotation_data(data_url=data_url(i)) for i in range(10)]
        resp = requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': annotation_data},
            auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_bad_request_when_creating_annotation_with_invalid_data_url(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = self.annotation_data(data_url='WRONG')
        resp = requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': [annotation_data]},
            auth=auth)
        self.assertEqual(client.BAD_REQUEST, resp.status_code)

    def test_can_create_annotation_with_start_seconds_of_zero(self):
        user, user_location = self.create_user(user_type='human')
        auth = self._get_auth(user)
        sound_id = self._create_sound_with_user(auth)
        annotation_data = self.annotation_data(
            data_url='https://example.com', start_seconds=0)
        resp = requests.post(
            self.sound_annotations_resource(sound_id),
            json={'annotations': [annotation_data]},
            auth=auth)
        self.assertEqual(client.CREATED, resp.status_code)
