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
