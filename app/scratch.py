from errors import PermissionsError, ImmutableError
from identifier import user_id_generator
from password import password_hasher
import datetime
from model import UserType


# TODO: validation, including multiple errors - CHECK
# TODO: event log/session - CHECK

#
# TODO: expression parsing
# TODO: two-way property name mapping


class BaseRepository(object):
    def __init__(self):
        super().__init__()

    def __getitem__(self, _id):
        raise NotImplemented()

    def __setitem__(self, _id, value):
        raise NotImplemented()

    def __delitem__(self, _id):
        raise NotImplemented()

    def query(self, predicate, page_size, page_number):
        raise NotImplemented()


class BaseEntity(object):
    def __new__(cls, _id=None, **kwargs):
        obj = super(BaseEntity, cls).__new__(cls)
        obj.__events = []
        object.__setattr__(obj, 'id', _id or user_id_generator())
        return obj

    def __init__(self):
        super().__init__()

    @property
    def immutable(self):
        return set()

    @classmethod
    def hydrate(cls, _id=None, **kwargs):
        obj = cls.__new__(cls, _id=_id, **kwargs)
        for k, v in kwargs.items():
            object.__setattr__(obj, k, v)
        return obj

    @property
    def events(self):
        return self.__events

    def _is_public(self, key):
        return not key.startswith('_')

    def _get_validator_for(self, key):
        return getattr(self, f'validate_{key}')

    def __setattr__(self, key, value):
        if self._is_public(key):
            try:
                old_value = getattr(self, key)
                if key in self.immutable and old_value is not None:
                    raise ImmutableError(key)
            except AttributeError:
                old_value = None
            self.__events.append(('set', key, old_value, value))
        super().__setattr__(key, value)

    def validate(self):
        for k, v in self.__dict__.items():
            if not self._is_public(k):
                continue

            try:
                validator = self._get_validator_for(k)
                value = getattr(self, k)
                try:
                    validator(value)
                except Exception as e:
                    yield k, e
            except AttributeError:
                # no validator was defined
                continue


class UserData(BaseEntity):
    def __init__(
            self,
            _id=None,
            user_name=None,
            email=None,
            user_type=None,
            about_me=None,
            date_created=None,
            deleted=None,
            password=None,
            **kwargs):
        super().__init__()

        self.password = password or password_hasher(password)
        self.date_created = date_created or datetime.datetime.utcnow()
        self.deleted = False if deleted is None else deleted

        self.user_type = user_type
        self.about_me = about_me
        self.email = email
        self.user_name = user_name

    @property
    def immutable(self):
        return {'email'}

    def validate_user_type(self, value):
        UserType(value)

    def validate_about_me(self, value):
        if self.user_type == UserType.HUMAN:
            return

        if not value:
            raise ValueError(
                'About me must be specified when '
                'user_type is dataset or featurebot')

    def validate_user_name(self, value):
        if not value:
            raise ValueError('user_name must be provided')

    def validate_email(self, value):
        if not value:
            raise ValueError('email must be provided')

    def __repr__(self):
        cls = self.__class__.__name__
        data = self.__dict__
        return f'{cls}({data})'


if __name__ == '__main__':
    '''
    Events should be added when
    - setting properties (ALWAYS)
    - constructing a user for the very first time (ALWAYS)
    - pulling a user back from the database and constructing it (NEVER)
    '''

    user = UserData(
        _id='',
        user_name='Hal',
        email='hal@eta.com',
        password='password',
        about_me='Something Something',
        user_type=UserType.DATASET
    )

    user = UserData.hydrate(
        _id='',
        user_name='Hal',
        email='hal@eta.com',
        password='password',
        about_me='Something Something',
        user_type=UserType.DATASET
    )


    user.about_me = ''
    # TODO: Password should be hashed when set. look into descriptors
    # https://docs.python.org/3.6/howto/descriptor.html
    user.password = 'blarg'
    print(user)

    print('Events ' + '*' * 100)
    for event in user.events:
        print(event)

    print('Errors ' + '*' * 100)
    for error in user.validate():
        print(error)
