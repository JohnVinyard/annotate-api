from errors import PermissionsError, ImmutableError
from identifier import user_id_generator
from password import password_hasher
import datetime
from model import UserType


class BaseRepository(object):
    def __init__(self):
        super().__init__()

    def __getitem__(self, _id):
        raise NotImplemented()

    def __setitem__(self, _id, value):
        raise NotImplemented()

    def __delitem__(self, _id):
        raise NotImplemented()

    def filter(self, predicate, page_size, page_number):
        raise NotImplemented()


# TODO: for data, two-way property name mapping
# TODO: materialized view of event log
# TODO: query syntax

# TODO: property visibility
# TODO: required fields and/or easier-to-implement validtors


class BaseDescriptor(object):
    def __init__(self, name=None, default_value=None, required=False):
        super().__init__()
        self.required = required
        self.default_value = default_value
        self.name = name

    def __get__(self, instance, owner):
        value = instance._data[self.name]
        return value

    def __set__(self, instance, value):
        instance._data[self.name] = value
        instance._events.append(('set', self.name, value))

    def validate(self, instance):
        if not self.required:
            return

        if not instance._data.get(self.name, None):
            raise ValueError(f'{self.name} is required')


class Transform(BaseDescriptor):
    def __init__(self, transform, **kwargs):
        self.transform = transform
        super().__init__(**kwargs)

    def __set__(self, instance, value):
        super().__set__(instance, self.transform(value))


class AboutMe(BaseDescriptor):
    def validate(self, instance):

        if instance.user_type == UserType.HUMAN:
            return

        if not instance.about_me:
            raise ValueError(
                'About me must be specified for datasets and featurebots')


class Immutable(BaseDescriptor):
    def __set__(self, instance, value):
        try:
            existing = instance._data[self.name]
            if existing is None:
                super().__set__(instance, value)
            else:
                raise ImmutableError(self.name)
        except KeyError:
            super().__set__(instance, value)


class MetaEntity(type):
    def __init__(cls, name, bases, attrs):
        cls._metafields = dict()
        for key, value in attrs.items():
            if isinstance(value, BaseDescriptor):
                value.name = key
                cls._metafields[key] = value
        super(MetaEntity, cls).__init__(name, bases, attrs)


class BaseEntity(object, metaclass=MetaEntity):
    def __init__(self, **kwargs):
        super().__init__()
        self._events = []
        self._data = {}
        for k, v in kwargs.items():
            self.__setattr__(k, v)

        for k, v in self._metafields.items():
            if v.default_value is not None and k not in self._data:
                try:
                    self._data[k] = v.default_value()
                except TypeError:
                    self._data[k] = v.default_value

    @classmethod
    def hydrate(cls, **kwargs):
        obj = cls.__new__(cls)
        obj._data = kwargs
        obj._events = []
        return obj

    @property
    def events(self):
        return tuple(self._events)

    def validate(self):
        for field in self._metafields.values():
            try:
                field.validate(self)
            except Exception as e:
                yield field.name, e

    def __repr__(self):
        return '{cls}({data})'.format(
            cls=self.__class__.__name__, data=self._data)


class Concrete(BaseEntity):
    id = BaseDescriptor(default_value=user_id_generator)
    date_created = BaseDescriptor(
        default_value=lambda: datetime.datetime.utcnow())
    deleted = BaseDescriptor(default_value=False)

    name = BaseDescriptor(required=True)
    password = Transform(password_hasher)
    user_type = Transform(UserType)
    email = Immutable()
    about_me = AboutMe()

if __name__ == '__main__':
    '''
    Events should be added when
    - setting properties (ALWAYS)
    - constructing a user for the very first time (ALWAYS)
    - pulling a user back from the database and constructing it (NEVER)
    '''

    print('New ' + '*' * 100)
    c = Concrete(
        name='John',
        password='password',
        email='hal@eta.com',
        user_type='human',
        about_me='I got problems')
    print(c)
    print('EVENTS', c.events)

    print('DB ' + '*' * 100)
    c = Concrete.hydrate(**c._data)
    print(c)
    print('EVENTS', c.events)
    c.user_type = UserType.FEATUREBOT
    c.about_me = ''
    c.name = None

    print('ERRORS ' + '*' * 100)
    for error in c.validate():
        print(error)
