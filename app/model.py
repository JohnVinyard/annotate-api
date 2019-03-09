import datetime
from enum import Enum
from password import password_hasher
from identifier import user_id_generator


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
        self.date_created = date_created
        self.id = _id
        self.about_me = about_me
        self.user_type = user_type
        self.email = email
        self.user_name = user_name


class UserCreationData(object):
    def __init__(self, user_name, password, email, user_type, about_me):
        self.id = user_id_generator()
        self.password = password_hasher(password)
        self.date_created = datetime.datetime.utcnow()

        self.about_me = about_me
        self.user_name = user_name
        self.email = email
        self.user_type = user_type


class UserUpdateData(object):
    def __init__(self, password=None, about_me=None):
        self.about_me = about_me
        self.password = password
