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
    def tearDown(self):
        self.delete_all_data()

    def test_can_create_and_fetch_new_user(self):
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
