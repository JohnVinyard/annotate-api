import datetime
import uuid
import hashlib
from enum import Enum


class UserType(Enum):
    HUMAN = 'human'
    FEATUREBOT = 'featurebot'
    DATASET = 'dataset'


class UserData(object):
    def __init__(
            self,
            _id,
            user_name,
            email,
            user_type,
            about_me,
            date_created,
            **kwargs):

        # TODO: Will need a JSON encoder that supports datetime
        # self.date_created = date_created
        self.id = _id
        self.about_me = about_me
        self.user_type = user_type
        self.email = email
        self.user_name = user_name


class UserCreationData(object):
    def __init__(self, user_name, password, email, user_type, about_me):
        # TODO: Use bycrypt or some better hashing scheme
        self.about_me = about_me
        self.id = uuid.uuid4().hex
        self.password = hashlib.sha3_256(password.encode()).hexdigest()
        self.user_name = user_name
        self.email = email
        self.user_type = user_type
        self.date_created = datetime.datetime.utcnow()


class UserUpdateData(object):
    def __init__(self, password=None, about_me=None):
        self.about_me = about_me
        self.password = password
