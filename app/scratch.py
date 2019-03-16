from errors import PermissionsError, ImmutableError
from identifier import user_id_generator
from password import password_hasher
import datetime
from model import UserType


class BaseRepository(object):
    # TODO: query syntax
    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    def upsert(self, item):
        raise NotImplementedError()

    def filter(self, predicate, page_size=100, page_number=0):
        raise NotImplementedError()

    def count(self, predicate):
        raise NotImplementedError()


class InMemoryRepository(BaseRepository):
    def __init__(self, cls):
        super().__init__(cls)
        self._data = {}

    def upsert(self, item):
        try:
            existing = self._data[item.id]
            existing.update(item)
        except KeyError:
            existing[item.id] = item

    def filter(self, predicate):
        # TODO: What do queries look like?
        raise NotImplemented()

    def count(self, predicate):
        raise NotImplemented()


class Session(object):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: Check for entities in the session
        # TODO: Create materialized views of events for each entity
        # TODO: validate any entities that will be created or updated
        # TODO: Perform updates
        pass


class BaseMapping(object):
    def __init__(
            self,
            field,
            storage_name=None,
            to_storage_format=None,
            from_storage_format=None):
        super().__init__()
        self.from_storage_format = from_storage_format
        self.to_storage_format = to_storage_format
        self.storage_name = storage_name
        self.field = field

    def to_storage(self, instance):
        value = self.field.__get__(instance, instance.__class__)
        try:
            value = self.to_storage_format(value)
        except TypeError:
            pass
        return self.storage_name, value

    def from_storage(self, storage_data):
        value = storage_data[self.storage_name]
        try:
            value = self.from_storage_format(value)
        except TypeError:
            pass
        return self.field.name, value


class BaseDescriptor(object):
    def __init__(
            self,
            name=None,
            default_value=None,
            required=False,
            visible=None):

        super().__init__()
        self._visible = visible
        self.required = required
        self.default_value = default_value
        self.name = name

    def __eq__(self, other):
        raise NotImplementedError('TODO: Query builder')

    def __ne__(self, other):
        raise NotImplementedError('TODO: Query builder')

    def __get__(self, instance, owner):
        if instance is None:
            return self
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

    def visible(self, instance, context):
        try:
            return self._visible(instance, context)
        except TypeError:
            return True


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


class MetaMapper(type):
    def __init__(cls, name, bases, attrs):
        cls._mapped_fields = dict()
        for key, value in attrs.items():
            if isinstance(value, BaseMapping):
                value.storage_name = key
                cls._mapped_fields[key] = value
        super(MetaMapper, cls).__init__(name, bases, attrs)


class BaseMapper(object, metaclass=MetaMapper):
    def __init__(self):
        super().__init__()

    @classmethod
    def to_storage(cls, entity):
        return dict(
            mapping.to_storage(entity)
            for mapping in cls._mapped_fields.values())

    @classmethod
    def from_storage(cls, data):
        transformed = dict(
            mapping.from_storage(data)
            for mapping in cls._mapped_fields.values())
        return cls.entity_class.hydrate(**transformed)


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
        """
        Build an instance, bypassing validation, setter logic, etc., likely when
        pulling back from a database.  Property name mapping/translation should
        happen *before* this.
        """
        obj = cls.__new__(cls)
        obj._data = kwargs
        obj._events = []
        return obj

    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)

    @property
    def events(self):
        return tuple(self._events)

    def validate(self):
        for field in self._metafields.values():
            try:
                field.validate(self)
            except Exception as e:
                yield field.name, e

    def view(self, context):
        return \
            {k: getattr(self, k) for k, v
             in self._metafields.items() if v.visible(self, context)}

    def __repr__(self):
        return '{cls}({data})'.format(
            cls=self.__class__.__name__, data=self._data)


class User(BaseEntity):
    id = BaseDescriptor(default_value=user_id_generator)

    date_created = BaseDescriptor(
        default_value=lambda: datetime.datetime.utcnow())

    deleted = BaseDescriptor(
        default_value=False,
        visible=lambda instance, context: False)

    name = BaseDescriptor(required=True)

    password = Transform(
        password_hasher,
        visible=lambda instance, context: False)

    user_type = Transform(UserType)

    email = Immutable(
        visible=lambda instance, context: instance.id == context.id)

    about_me = AboutMe()


class UserMapper(BaseMapper):

    # TODO: Better, more formal way to specify mapper's target class than this
    entity_class = User

    _id = BaseMapping(User.id)
    date_created = BaseMapping(User.date_created)
    deleted = BaseMapping(User.deleted)
    name = BaseMapping(User.name)
    password = BaseMapping(User.password)
    user_type = BaseMapping(
        User.user_type,
        to_storage_format=lambda instance: instance.value,
        from_storage_format=lambda value: UserType(value))
    email = BaseMapping(User.email)
    about_me = BaseMapping(User.about_me)


def test_event_log_and_validation():
    print('New ' + '*' * 100)
    c = User.create(
        name='John',
        password='password',
        email='hal@eta.com',
        user_type='human',
        about_me='I got problems')
    print(c)
    print('VIEW', c.view(c))
    print('EVENTS', c.events)

    print('DB ' + '*' * 100)
    c2 = User.hydrate(**c._data)
    print(c2)
    print('VIEW', c2.view(c))
    print('EVENTS', c2.events)
    c2.user_type = UserType.FEATUREBOT
    c2.about_me = ''
    c2.name = None

    print('ERRORS ' + '*' * 100)
    for error in c2.validate():
        print(error)

    print('VISIBILITY ' + '*' * 100)
    c3 = User.create(
        name='John',
        password='password',
        email='hal@eta.com',
        user_type='human',
        about_me='I got problems')
    print(c3.view(c))


if __name__ == '__main__':
    # test_event_log_and_validation()

    c = User.create(
        name='John',
        password='password',
        email='hal@eta.com',
        user_type='human',
        about_me='I got problems')
    print(c)

    data = UserMapper.to_storage(c)
    print(data)

    c2 = UserMapper.from_storage(data)
    print(c2)

    print(User.id == 'blah')

    # user_id1 = None
    # user_id2 = None
    #
    # with Session() as s:
    #     c = User.create(
    #         name='John',
    #         password='password',
    #         email='hal@eta.com',
    #         user_type='human',
    #         about_me='I got problems')
    #     user_id1 = c
