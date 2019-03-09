import unittest2
import requests
import subprocess
from http import client
import time
import os

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

    def test_can_create_and_fetch_new_user(self):
        create_data = self._user_create_data(user_name='HalIncandenza')
        print(create_data)
        create_resp = requests.post(self.users_resource(), json=create_data)
        self.assertEqual(client.CREATED, create_resp.status_code)
        uri = create_resp.headers['location']
        user_resp = requests.get(
            self.url(uri), auth=self._get_auth(create_data))
        self.assertEqual(client.OK, user_resp.status_code)
        print(user_resp.json())
        self.assertEqual(
            user_resp.json()['user_name'], create_data['user_name'])

    def test_unauthorized_when_attempting_to_list_users_without_creds(self):
        self.fail()

    def test_unauthorized_when_attempting_to_fetch_single_user_with_creds(self):
        self.fail()

    def test_validation_error_for_bad_user_type(self):
        self.fail()

    def test_validation_error_for_bad_user_name(self):
        self.fail()

    def test_validation_error_for_bad_password(self):
        self.fail()

    def test_validation_error_for_bad_email(self):
        self.fail()

    def test_can_list_users(self):
        self.fail()

    def test_must_authenticate_to_list_users(self):
        self.fail()

    def test_can_view_all_data_about_self(self):
        self.fail()

    def test_can_view_limited_data_about_other_user(self):
        self.fail()

    def test_can_delete_self(self):
        self.fail()

    def test_cannot_delete_other_user(self):
        self.fail()

    def test_usernames_must_be_unique(self):
        self.fail()

    def test_email_addresses_must_be_unique(self):
        self.fail()

    def test_can_update_about_me_text(self):
        self.fail()

    def test_invalid_about_me_update_for_featurebot_fails(self):
        self.fail()

    def test_can_update_password(self):
        self.fail()

    def test_not_found_for_non_existent_user(self):
        self.fail()

    def test_unauthorized_when_fetching_non_existent_user_without_creds(self):
        self.fail()
