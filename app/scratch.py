from errors import PermissionsError, ImmutableError
from identifier import user_id_generator
from password import password_hasher
import datetime
from model import UserType
import threading
import re
from collections import defaultdict

thread_local = threading.local()


def identity(x):
    return x


class BaseRepository(object):
    def __init__(self, cls, mapper):
        super().__init__()
        self.mapper = mapper
        self.cls = cls

    def upsert(self, item):
        raise NotImplementedError()

    def filter(self, predicate, page_size=100, page_number=0):
        raise NotImplementedError()

    def count(self, predicate):
        raise NotImplementedError()


class InMemoryRepository(BaseRepository):
    def __init__(self, cls, mapper):
        super().__init__(cls, mapper)
        self._data = {}

    def upsert(self, *updates):
        for query, update in updates:

            # TODO: This needs to be factored out into BaseMapper
            storage_updates = {}
            for name, update_data in update.items():
                field, value = update_data
                storage_data = self.mapper.storage_data(field)
                storage_updates[storage_data.storage_name] = \
                    storage_data.to_storage_format(value)

            try:
                data = next(self._filter(query))
                data.update(**storage_updates)
                # this is an existing document. update it
            except StopIteration:
                # this is a new document.  insert it
                self._data[query.literal_value] = storage_updates

    def _filter(self, query):
        f = query.to_lambda('item', self.mapper)
        return filter(f, self._data.values())

    def filter(self, query):
        return map(self.mapper.from_storage, self._filter(query))

    def count(self, query):
        # No need to transform results into entity classes just to count them
        return len(tuple(self._filter(query)))


class Session(object):
    def __init__(self, *repositories):
        super().__init__()
        self.__entities = []
        self._repositories = {r.cls: r for r in repositories}

    def report(self):
        total = len(self.__entities)
        modified = len(tuple(filter(lambda e: e._events, self.__entities)))
        return f'Entities: {total}, Modified: {modified}'

    def track(self, entity):
        self.__entities.append(entity)

    def filter(self, query):
        raise NotImplementedError()

    def count(self, query):
        raise NotImplementedError()

    def __enter__(self):
        thread_local.session = self
        return self

    def _flatten_updates(self, entity):
        # this exists primarily to discard multiple writes to the same field,
        # the last of which always wins
        return \
            {field.name: (field, value) for _, field, value in entity._events}

    def __exit__(self, exc_type, exc_val, exc_tb):
        thread_local.session = None

        if not self.__entities:
            # no entities were created in the session so we're done
            print('No entities in session')
            return

        # TODO: What about multiple Python instances that point to the same
        # persisted record?
        # create a flattened, materialized view of all the updates that have
        # happened during this session
        updates = {
            e: self._flatten_updates(e)
            for e in self.__entities if e._events}

        if not updates:
            # there were entities in the session, but no updates or inserts need
            # be performed
            print('No updates in session')
            return

        # validate any entities that will be created or updated
        for entity in updates.keys():
            entity.raise_for_errors()

        # Divide updates up according to repository and pass them in batch
        updates_by_entity = defaultdict(list)
        for entity, update in updates.items():
            updates_by_entity[entity.__class__].append(
                (entity.identity_query, update))

        for entity_cls, updates in updates_by_entity.items():
            repo = self._repositories[entity_cls]
            repo.upsert(*updates)


class BaseMapping(object):
    def __init__(
            self,
            field,
            storage_name=None,
            to_storage_format=None,
            from_storage_format=None):
        super().__init__()
        self.from_storage_format = from_storage_format or identity
        self.to_storage_format = to_storage_format or identity
        self.storage_name = storage_name
        self.field = field

    def to_storage(self, instance):
        value = self.field.__get__(instance, instance.__class__)
        value = self.to_storage_format(value)
        return self.storage_name, value

    def from_storage(self, storage_data):
        value = storage_data[self.storage_name]
        value = self.from_storage_format(value)
        return self.field.name, value


class Query(object):
    def __init__(self, lhs, rhs, op):
        super().__init__()
        self.op = op
        self.rhs = rhs
        self.lhs = lhs

        self.operands = (self.lhs, self.rhs)

        # TODO: This code is pretty ugly.  Take another stab at refactoring this
        try:
            def descriptor_criteria(x):
                return isinstance(x, BaseDescriptor)

            self.field = next(filter(descriptor_criteria, self.operands))
        except StopIteration:
            pass

        try:
            def criteria(x):
                return \
                    not isinstance(x, BaseDescriptor) \
                    and not isinstance(x, Query)

            self.literal_value = next(filter(criteria, self.operands))
        except StopIteration:
            pass

        try:
            self.literal_value = self.field.value_transform(self.literal_value)
            self.lhs = self.field
            self.rhs = self.literal_value
        except AttributeError:
            pass

    def __and__(self, other):
        return Query(self, other, 'and')

    def __or__(self, other):
        return Query(self, other, 'or')

    def __repr__(self):
        return '({lhs} {op} {rhs})'.format(**self.__dict__)

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def _transform_operand(operand, varname, mapper, other_operand):
        try:
            # the operand is another query
            return operand._to_lambda(varname, mapper)
        except AttributeError:
            pass

        try:
            # the operand is a descriptor.
            storage_name = mapper.storage_data(operand).storage_name
            return f'{varname}["{storage_name}"]'
        except (AttributeError, KeyError):
            pass

        try:
            operand = mapper \
                .storage_data(other_operand).to_storage_format(operand)
        except (AttributeError, KeyError):
            pass

        # the operand is a literal value
        return repr(operand)

    def _to_lambda(self, varname, mapper):
        # KLUDGE: This is just temporary, and is for testing against the
        # in-memory repository
        lhs = self._transform_operand(
            self.lhs, varname, mapper, self.rhs)
        rhs = self._transform_operand(
            self.rhs, varname, mapper, self.lhs)
        op = self.op
        return f'{lhs} {op} {rhs}'

    def to_lambda(self, varname, mapper, raw=False):
        import ast
        expr = self._to_lambda(varname, mapper)
        l = f'lambda {varname}: {expr}'

        if raw:
            return l

        tree = ast.parse(l, filename='<ast>', mode='eval')
        return eval(compile(tree, filename='<ast>', mode='eval'))


class ContextualValue(object):
    def __init__(self, context, value):
        self.value = value
        self.context = context
        super().__init__()


class BaseDescriptor(object):
    def __init__(
            self,
            name=None,
            default_value=None,
            required=False,
            visible=None,
            value_transform=None,
            evaluate_context=None):

        super().__init__()

        def always_ok(instance, context):
            return True

        self.evaluate_context = evaluate_context or always_ok
        self.value_transform = value_transform or identity
        self._visible = visible or always_ok
        self.required = required
        self.default_value = default_value
        self.name = name

    def __eq__(self, other):
        return Query(self, other, '==')

    def __ne__(self, other):
        return Query(self, other, '!=')

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = instance._data[self.name]
        return value

    def __set__(self, instance, value):
        if not isinstance(value, ContextualValue):
            value = ContextualValue(context=None, value=value)

        try:
            if not self.evaluate_context(instance, value.context):
                raise PermissionsError(
                    'Cannot set field "{name}" with context {context}'
                    .format(name=self.name, context=value.context))
        except AttributeError:
            raise ValueError(
                'You must supply a context when setting field "{name}"'
                .format(name=self.name))

        value = value.value
        value = self.value_transform(value)
        instance._data[self.name] = value
        instance._events.append(('set', self, value))

    def validate(self, instance):
        if not self.required:
            return

        if not instance.get(self.name, None):
            raise ValueError(f'{self.name} is required')

    def visible(self, instance, context):
        return self._visible(instance, context)

    def __repr__(self):
        return 'Descriptor({name})'.format(**self.__dict__)


class AboutMe(BaseDescriptor):
    def validate(self, instance):

        if instance.user_type == UserType.HUMAN:
            return

        if not instance.get(self.name):
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


class Email(Immutable):
    BASIC_EMAIL_PATTERN = re.compile(r'[^@]+@[^@]+\.[^@]+')

    def validate(self, instance):
        value = instance.get(self.name)
        if not re.fullmatch(Email.BASIC_EMAIL_PATTERN, value):
            raise ValueError(f'{value} is not a valid email address')


class MetaMapper(type):
    def __init__(cls, name, bases, attrs):

        cls._mapped_fields = dict()
        for key, value in attrs.items():
            if isinstance(value, BaseMapping):
                value.storage_name = key
                cls._mapped_fields[key] = value

        cls._inverse_mapped_fields = dict()
        for key, value in cls._mapped_fields.items():
            cls._inverse_mapped_fields[value.field.name] = attrs[key]

        super(MetaMapper, cls).__init__(name, bases, attrs)


class BaseMapper(object, metaclass=MetaMapper):
    def __init__(self):
        super().__init__()

    @classmethod
    def storage_data(cls, field):
        return cls._inverse_mapped_fields[field.name]

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
            contextual_value = ContextualValue(self, v)
            self.__setattr__(k, contextual_value)

        for k, v in self._metafields.items():
            if v.default_value is not None and k not in self._data:
                try:
                    contextual_value = ContextualValue(self, v.default_value())
                    self.__setattr__(k, contextual_value)
                except TypeError:
                    contextual_value = ContextualValue(self, v.default_value)
                    self.__setattr__(k, contextual_value)
        self._track()
        self.raise_for_errors()

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
        obj._track()
        return obj

    def _track(self):
        try:
            thread_local.session.track(self)
        except AttributeError:
            pass

    def get(self, key, default=None):
        return self._data.get(key, default)

    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)

    @property
    def events(self):
        return tuple(self._events)

    @property
    def identity_query(self):
        raise NotImplementedError()

    def validate(self):
        for field in self._metafields.values():
            try:
                field.validate(self)
            except Exception as e:
                yield field.name, e

    def raise_for_errors(self):
        errors = tuple(self.validate())
        if errors:
            raise ValueError(errors)

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
        visible=lambda instance, context: False,
        evaluate_context=lambda instance, context: instance.id == context.id)

    name = BaseDescriptor(required=True)

    password = BaseDescriptor(
        visible=lambda instance, context: False,
        value_transform=password_hasher)

    user_type = BaseDescriptor(value_transform=UserType)

    email = Email(
        visible=lambda instance, context: instance.id == context.id)

    about_me = AboutMe()

    @property
    def identity_query(self):
        return User.id == self.id


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

    repo = InMemoryRepository(User, UserMapper)

    user_id1 = None
    user_id2 = None

    with Session(repo) as s:
        c = User.create(
            name='John',
            password='password',
            email='hal@eta.com',
            user_type=UserType.DATASET,
            about_me='I got problems')
        user_id1 = c.id

    with Session(repo) as s:
        pass

    with Session(repo) as s:
        c = next(repo.filter(User.id == user_id1))

    # TODO: Bad new user
    try:
        with Session(repo) as s:
            c = User.create(
                name='John',
                password='password',
                email='hal',
                user_type=UserType.DATASET,
                about_me='')
            user_id2 = c.id
    except ValueError as e:
        print(e)

    # TODO: Good new user
    with Session(repo) as s:
        c = User.create(
            name='Rebekah',
            password='password2',
            email='beks@eta.com',
            user_type=UserType.DATASET,
            about_me='I got problems')
        user_id2 = c.id

    # TODO: Bad update to existing user
    try:
        with Session(repo) as s:
            c = next(repo.filter(User.id == user_id2))
            c.about_me = ''
    except ValueError as e:
        print(e)

    # TODO: Good update to existing user
    with Session(repo) as s:
        c = next(repo.filter(User.id == user_id2))
        c.about_me = 'Here is my updated about me text'

    # TODO: view business logic
    with Session(repo) as s:
        c1 = next(repo.filter(User.id == user_id1))
        c2 = next(repo.filter(User.id == user_id2))
        print(c1.view(c1))
        print(c1.view(c2))
    print(repo._data)

    # TODO: authentication (query that includes password)
    with Session(repo) as s:
        # TODO: Tests for different query construction errors and scenarios
        query = (User.id == user_id1) & (User.password == 'password')
        print(query.to_lambda('x', UserMapper, raw=True))
        c = next(repo.filter(query))
        print(c)

    # TODO: delete business logic
    with Session(repo) as s:
        c1 = next(repo.filter(User.id == user_id1))
        c2 = next(repo.filter(User.id == user_id2))
        c1.deleted = ContextualValue(c1, True)

    print(repo._data)


    # TODO: multiple instances pointing to the same record
    # TODO: multiple users created in a session
    # TODO: one user created and one user updated in a session
