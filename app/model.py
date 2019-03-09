import datetime
import uuid
import hashlib
from enum import Enum


class UserType(Enum):
    HUMAN = 'human'
    FEATUREBOT = 'featurebot'
    DATASET = 'dataset'


class User(object):
    def __init__(self, name, password, email, user_type, about_me):
        # TODO: Use bycrypt or some better hashing scheme
        self.about_me = about_me
        self.id = uuid.uuid4().hex
        self.password = hashlib.sha3_256(password.encode()).hexdigest()
        self.name = name
        self.email = email
        self.user_type = user_type
        self.date_created = datetime.datetime.utcnow()