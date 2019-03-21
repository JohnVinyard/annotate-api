from errors import PermissionsError, ImmutableError
from identifier import user_id_generator
from password import password_hasher
import datetime
import threading
import re
from collections import defaultdict
from pymongo import UpdateOne, ASCENDING, DESCENDING
from enum import Enum
import logging

thread_local = threading.local()


class UserType(Enum):
    HUMAN = 'human'
    FEATUREBOT = 'featurebot'
    DATASET = 'dataset'


def identity(x):
    return x


def never(*args, **kwargs):
    return False


def always(*args, **kwargs):
    return True


def is_me(instance, context):
    return instance.id == context.id


class BaseRepository(object):
    def __init__(self, cls, mapper):
        super().__init__()
        self.mapper = mapper
        self.cls = cls

    def upsert(self, item):
        raise NotImplementedError()

    def filter(self, predicate, page_size=100, page_number=0, sort=None):
        raise NotImplementedError()

    def count(self, predicate):
        raise NotImplementedError()

    # TODO: Perhaps count() should just accept a query with no criteria, which
    # would keep the interface simpler
    def __len__(self):
        raise NotImplementedError()


class SortOrder(Enum):
    ASCENDING = 'ascending'
    DESCENDING = 'descending'


class SortedField(object):
    def __init__(self, field, order):
        self.order = order
        self.field = field

    def __repr__(self):
        return f'{self.__class__.__name__}({self.field}, {self.order})'


class NoCriteria(object):
    def __init__(self, cls):
        self._entity_cls = cls

    def to_lambda(self, varname, mapper, raw=False):
        import ast
        l = f'lambda {varname}: True'
        if raw:
            return l
        tree = ast.parse(l, filename='<ast>', mode='eval')
        return eval(compile(tree, filename='<ast>', mode='eval'))

    @property
    def entity_class(self):
        return self._entity_cls


class Query(object):
    OR = 'or'
    AND = 'and'
    EQUAL_TO = '=='
    NOT_EQUAL_TO = '!='

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
            self._entity_cls = self.field.owner_cls
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

    @property
    def entity_class(self):
        classes = set()
        stack = [self.lhs, self.rhs]
        while stack:
            node = stack.pop()
            try:
                classes.add(node.owner_cls)
            except AttributeError:
                pass

            try:
                stack.extend([node.lhs, node.rhs])
            except AttributeError:
                pass

        if not classes:
            raise ValueError('No entity class criteria in query')

        if len(classes) > 1:
            raise ValueError('Multi-class queries are not currently supported')

        return next(iter(classes))

    def __and__(self, other):
        return Query(self, other, Query.AND)

    def __or__(self, other):
        return Query(self, other, Query.OR)

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


class QueryResult(object):
    def __init__(self, total_count, results, page_number, page_size):
        self.total_count = total_count
        self.results = results
        current_pos = (page_number * page_size) + len(results)
        self.next_page = page_number + 1 if current_pos < total_count else None
        self.pos = 0

    def __iter__(self):
        return iter(self.results)

    def __next__(self):
        try:
            item = self.results[self.pos]
            self.pos += 1
            return item
        except IndexError:
            raise StopIteration()


# TODO: Does BaseRepository need cls and mapper arguments anymore?
class MongoRepository(BaseRepository):
    OPERATOR_MAPPING = {
        Query.AND: '$and',
        Query.OR: '$or',
        Query.EQUAL_TO: '$eq',
        Query.NOT_EQUAL_TO: '$ne'
    }

    BOOLEAN_OPS = {Query.AND, Query.OR}
    COMPARISON_OPS = {Query.EQUAL_TO, Query.NOT_EQUAL_TO}

    SORT_ORDER_MAPPING = {
        SortOrder.ASCENDING: ASCENDING,
        SortOrder.DESCENDING: DESCENDING
    }

    def __init__(self, cls, mapper, collection):
        super().__init__(cls, mapper)
        self.collection = collection

    def _transform_query(self, query):
        if isinstance(query, NoCriteria):
            return {}

        mongo_op = MongoRepository.OPERATOR_MAPPING[query.op]
        if query.op in MongoRepository.BOOLEAN_OPS:
            criteria = map(self._transform_query, (query.lhs, query.rhs))
            conditions = []
            for criterion in criteria:
                if mongo_op in criterion:
                    conditions.extend(criterion[mongo_op])
                else:
                    conditions.append(criterion)
            return {mongo_op: conditions}
        elif query.op in MongoRepository.COMPARISON_OPS:
            storage_data = self.mapper.storage_data(query.field)
            storage_name = storage_data.storage_name
            storage_value = storage_data.to_storage_format(query.literal_value)
            return {storage_name: {mongo_op: storage_value}}
        else:
            raise ValueError(f'Op "{query.op}" is not currently supported')

    def _transform_sort(self, sort_order):
        if sort_order is None:
            return sort_order
        storage_data = self.mapper.storage_data(sort_order.field)
        storage_name = storage_data.storage_name
        order = MongoRepository.SORT_ORDER_MAPPING[sort_order.order]
        return [(storage_name, order)]

    def upsert(self, *updates):
        # TODO: These first two lines are exactly what's in InMemoryRepository
        # and should be factored out into Session. Session transforms to the
        # correct entity class on the way out, so why not transform to the
        # underlying storage format before passing along here?
        mongo_updates = []
        for query, update in updates:
            storage_updates = self.mapper.transform_updates(update.values())
            mongo_update = UpdateOne(
                self._transform_query(query),
                {'$set': storage_updates},
                upsert=True)
            mongo_updates.append(mongo_update)
        self.collection.bulk_write(mongo_updates)

    def filter(self, query, page_size=100, page_number=0, sort=None):
        mongo_query = self._transform_query(query)
        sort = self._transform_sort(sort)
        total_count = self._count(mongo_query)
        results = self.collection \
            .find(mongo_query, sort=sort) \
            .skip(page_number * page_size) \
            .limit(page_size)
        results = list(results)
        return QueryResult(total_count, results, page_number, page_size)

    def _count(self, mongo_query):
        return self.collection.count_documents(mongo_query)

    def count(self, query):
        mongo_query = self._transform_query(query)
        return self._count(mongo_query)

    def __len__(self):
        return self.collection.estimated_document_count()

    def delete_all(self):
        return self.collection.delete_many({})


class InMemoryRepository(BaseRepository):
    def __init__(self, cls, mapper):
        super().__init__(cls, mapper)
        self._data = {}

    def __len__(self):
        return len(self._data)

    def upsert(self, *updates):
        for query, update in updates:
            storage_updates = self.mapper.transform_updates(update.values())

            try:
                data = next(self.filter(query))
                data.update(**storage_updates)
                # this is an existing document. update it
            except StopIteration:
                # this is a new document.  insert it
                self._data[query.literal_value] = storage_updates

    def filter(self, query, page_size=100, page_number=0, sort=None):
        f = query.to_lambda('item', self.mapper)
        results = list(filter(f, self._data.values()))

        if sort:
            storage_data = self.mapper.storage_data[sort.field]
            storage_name = storage_data.storage_name
            results = sorted(
                results,
                key=lambda x: x[storage_name],
                reverse=sort.order == SortOrder.DESCENDING)

        total_count = len(results)
        start_pos = page_number * page_size
        page = results[start_pos: start_pos + page_size]
        return QueryResult(total_count, page, page_number, page_size)

    def count(self, query):
        return len(tuple(self.filter(query)))


class Session(object):
    def __init__(self, *repositories):
        super().__init__()
        self.__entities = {}
        self._repositories = {r.cls: r for r in repositories}

    def track(self, entity):
        self.__entities.setdefault(entity.storage_key, entity)

    def filter(self, query, page_size=100, page_number=0, sort=None):
        repo = self._repositories[query.entity_class]
        query_result = repo.filter(
            query, page_size=page_size, page_number=page_number, sort=sort)
        transformed_results = []
        for result in query_result.results:
            result = repo.mapper.from_storage(result)
            result = self.__entities[result.storage_key]
            transformed_results.append(result)
        query_result.results = transformed_results
        return query_result
        # for item in results:
        #     e = repo.mapper.from_storage(item)
        #     yield self.__entities[e.storage_key]

    def count(self, query):
        repo = self._repositories[query.entity_class]
        return repo.count(query)

    def open(self):
        thread_local.session = self
        return self

    def abort(self):
        thread_local.session = None

    def close(self):
        thread_local.session = None

        if not self.__entities:
            # no entities were created in the session so we're done
            return

        # create a flattened, materialized view of all the updates that have
        # happened during this session
        updates = {
            e: self._flatten_updates(e)
            for e in self.__entities.values() if e._events}

        if not updates:
            logging.error('No updates')
            # there were entities in the session, but no updates or inserts need
            # be performed
            return

        # validate any entities that will be created or updated
        for entity in updates.keys():
            entity.raise_for_errors()

        logging.error('No errors, great!')

        # Divide updates up according to repository and pass them in batch
        updates_by_entity = defaultdict(list)
        for entity, update in updates.items():
            updates_by_entity[entity.__class__].append(
                (entity.identity_query, update))
        logging.error(updates_by_entity)

        for entity_cls, updates in updates_by_entity.items():
            repo = self._repositories[entity_cls]
            logging.error(updates)
            repo.upsert(*updates)

    def __enter__(self):
        return self.open()

    @staticmethod
    def _flatten_updates(entity):
        # this exists primarily to discard multiple writes to the same field,
        # the last of which always wins
        return \
            {field.name: (field, value) for _, field, value in entity._events}

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.close()


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
        self.evaluate_context = evaluate_context or always
        self.value_transform = value_transform or identity
        self._visible = visible or always
        self.required = required
        self.default_value = default_value
        self.name = name
        self.owner_cls = None

    def ascending(self):
        return SortedField(self, SortOrder.ASCENDING)

    def descending(self):
        return SortedField(self, SortOrder.DESCENDING)

    def __eq__(self, other):
        return Query(self, other, Query.EQUAL_TO)

    def __ne__(self, other):
        return Query(self, other, Query.NOT_EQUAL_TO)

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
                'Field "{name}" must be specified for datasets and featurebots'
                    .format(name=self.name))


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
    def transform_updates(cls, updates):
        storage_updates = {}
        for update_data in updates:
            field, value = update_data
            storage_data = cls.storage_data(field)
            storage_updates[storage_data.storage_name] = \
                storage_data.to_storage_format(value)
        return storage_updates

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
                value.owner_cls = cls
                cls._metafields[key] = value
        super(MetaEntity, cls).__init__(name, bases, attrs)


class BaseEntity(object, metaclass=MetaEntity):
    def __init__(self, creator=None, **kwargs):
        super().__init__()
        self._events = []
        self._data = {}

        creator = creator or self

        # filter any missing values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # set default values if values weren't provided to __init_
        for k, v in self._metafields.items():
            if v.default_value is not None and k not in kwargs:
                try:
                    contextual_value = ContextualValue(
                        creator, v.default_value())
                    self.__setattr__(k, contextual_value)
                except TypeError:
                    contextual_value = ContextualValue(creator, v.default_value)
                    self.__setattr__(k, contextual_value)

        # set values explicitly provided to __init__
        for k, v in kwargs.items():
            contextual_value = ContextualValue(creator, v)
            self.__setattr__(k, contextual_value)

        self.raise_for_errors()
        self._track()

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

    date_created = Immutable(default_value=lambda: datetime.datetime.utcnow())

    deleted = BaseDescriptor(
        default_value=False,
        visible=never,
        evaluate_context=is_me)

    user_name = Immutable(required=True)

    password = BaseDescriptor(
        visible=never,
        value_transform=password_hasher,
        required=True,
        evaluate_context=is_me)

    user_type = BaseDescriptor(value_transform=UserType, evaluate_context=is_me)

    email = Email(visible=is_me, evaluate_context=is_me)

    about_me = AboutMe(evaluate_context=is_me)

    @property
    def identity_query(self):
        return User.id == self.id

    @property
    def storage_key(self):
        # TODO: Can this be derived solely from the identity_query?
        return self.__class__, self.id


class UserMapper(BaseMapper):
    # TODO: Better, more formal way to specify mapper's target class than this
    entity_class = User

    _id = BaseMapping(User.id)
    date_created = BaseMapping(User.date_created)
    deleted = BaseMapping(User.deleted)
    user_name = BaseMapping(User.user_name)
    password = BaseMapping(User.password)
    user_type = BaseMapping(
        User.user_type,
        to_storage_format=lambda instance: instance.value,
        from_storage_format=lambda value: UserType(value))
    email = BaseMapping(User.email)
    about_me = BaseMapping(User.about_me)


if __name__ == '__main__':
    q = Query()
    # qr = QueryResult(100, list(range(10)), 0, 100)
    # for i in range(100):
    #     print(next(qr))
