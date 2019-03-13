import unittest2
import requests
import subprocess
from http import client
import time
import os
import uuid

path, fn = os.path.split(__file__)


class BaseTests(object):
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
        return cls.url('/users/{user_id}'.format(**locals()))

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

    def _user_create_data(
            self,
            user_name=None,
            password=None,
            user_type=None,
            email=None,
            about_me=None):
        return {
            'user_name': user_name or 'user',
            'password': password or 'password',
            'user_type': user_type or 'human',
            'email': email or 'hal@eta.com',
            'about_me': about_me or 'Up and coming tennis star'
        }

    def _get_auth(self, user_create_data):
        return user_create_data['user_name'], user_create_data['password']

    def create_user(self, user_type='human', user_name=None, email=None):

        create_data = self._user_create_data(
            user_name=user_name or uuid.uuid4().hex,
            password=uuid.uuid4().hex,
            user_type=user_type,
            email=email or '{}@example.com'.format(uuid.uuid4().hex),
            about_me=uuid.uuid4().hex
        )
        create_resp = requests.post(self.users_resource(), json=create_data)
        self.assertEqual(client.CREATED, create_resp.status_code)
        location = create_resp.headers['location']
        return create_data, location

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

    def test_can_view_most_data_about_self_when_listing_users(self):
        self.fail()

    def test_can_view_limited_data_about_other_user_when_listing_users(self):
        self.fail()

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
        # For now, the API will return forbidden when attempting to delete
        # any user that isn't the requesting user, rather than the arguably
        # more appropriate 404 Not Found error.
        self.assertEqual(client.FORBIDDEN, delete_resp.status_code)

    def test_unauthorized_when_deleting_user_without_creds(self):
        delete_resp = requests.delete(self.users_resource('1234'))
        self.assertEqual(client.UNAUTHORIZED, delete_resp.status_code)

    def test_unauthorized_when_fetching_single_user_without_creds(self):
        user1, user1_location = self.create_user()
        user_resp = requests.get(self.url(user1_location))
        self.assertEqual(client.UNAUTHORIZED, user_resp.status_code)

    def test_validation_error_for_bad_user_type(self):
        self.fail()

    def test_validation_error_for_bad_user_name(self):
        self.fail()

    def test_validation_error_for_bad_password(self):
        self.fail()

    def test_validation_error_for_bad_email(self):
        self.fail()

    def test_validation_error_has_information_about_multiple_problems(self):
        self.fail()

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

    def test_can_update_about_me_text(self):
        self.fail()

    def test_cannot_update_other_user(self):
        self.fail()

    def test_invalid_about_me_update_for_featurebot_fails(self):
        self.fail()

    def test_invalid_about_me_update_for_dataset_fails(self):
        self.fail()

    def test_can_update_password(self):
        self.fail()

    def test_not_found_for_non_existent_user(self):
        user1, user1_location = self.create_user()
        user_resp = requests.get(
            self.users_resource('1234'), auth=self._get_auth(user1))
        self.assertEqual(client.NOT_FOUND, user_resp.status_code)

    def test_unauthorized_when_fetching_non_existent_user_without_creds(self):
        user_resp = requests.get(self.users_resource('1234'))
        self.assertEqual(client.UNAUTHORIZED, user_resp.status_code)
