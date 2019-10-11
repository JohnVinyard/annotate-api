from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING, UpdateOne
from pymongo.errors import BulkWriteError
from scratch import \
    NoCriteria, BaseMapper, BaseMapping, QueryResult, BaseRepository, Query, \
    SortOrder
from model import User, UserType, Sound, Annotation
from errors import DuplicateEntityException
from mapping import UserMapper, SoundMapper, AnnotationMapper
import time

# TODO: Does BaseRepository need cls and mapper arguments anymore?
class MongoRepository(BaseRepository):
    OPERATOR_MAPPING = {
        Query.AND: '$and',
        Query.OR: '$or',
        Query.EQUAL_TO: '$eq',
        Query.NOT_EQUAL_TO: '$ne',
        Query.GREATER_THAN: '$gt',
        Query.GREATER_THAN_OR_EQUAL_TO: '$gte',
        Query.LESS_THAN: '$lt',
        Query.LESS_THAN_OR_EQUAL_TO: '$lte'
    }

    BOOLEAN_OPS = {Query.AND, Query.OR}
    COMPARISON_OPS = {
        Query.EQUAL_TO,
        Query.NOT_EQUAL_TO,
        Query.GREATER_THAN,
        Query.GREATER_THAN_OR_EQUAL_TO,
        Query.LESS_THAN,
        Query.LESS_THAN_OR_EQUAL_TO
    }

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

        if mongo_op == '$or' and query.negated:
            mongo_op = '$nor'

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
        try:
            self.collection.bulk_write(mongo_updates, ordered=False)
        except BulkWriteError as e:
            write_errors = e.details['writeErrors']
            if any('duplicate' in we['errmsg'] for we in write_errors):
                raise DuplicateEntityException(self.cls)
            else:
                raise

    def filter(
            self,
            query,
            page_size=100,
            page_number=0,
            sort=None,
            total_count=True):

        mongo_query = self._transform_query(query)
        sort = self._transform_sort(sort)
        # total_count = self._count(mongo_query) if total_count else None
        start = time.time()

        results = self.collection \
            .find(mongo_query, sort=sort) \
            .skip(page_number * page_size) \
            .limit(page_size)
        total_count = results.count() if total_count else None
        results = list(results)

        stop = time.time() - start
        result = QueryResult(results, page_number, page_size, total_count)
        result.inner_query = stop
        result.sort = sort
        result.query = mongo_query
        return result

    def _count(self, mongo_query):
        return self.collection.count_documents(mongo_query)

    def count(self, query):
        mongo_query = self._transform_query(query)
        return self._count(mongo_query)

    def __len__(self):
        return self.collection.estimated_document_count()

    def delete_all(self):
        return self.collection.delete_many({})


class UserRepository(MongoRepository):
    def __init__(self, collection):
        super().__init__(User, UserMapper, collection)


class SoundRepository(MongoRepository):
    def __init__(self, collection):
        super().__init__(Sound, SoundMapper, collection)


class AnnotationRepository(MongoRepository):
    def __init__(self, collection):
        super().__init__(Annotation, AnnotationMapper, collection)


def build_repositories(connection_string):
    client = MongoClient(connection_string)
    db = client.annotate

    def index_model(mapped_field, unique=False):
        key = mapped_field.storage_name
        return IndexModel(key, name=key, unique=unique)

    db.users.create_indexes([
        index_model(UserMapper.user_type),
        index_model(UserMapper.password),
        index_model(UserMapper.user_name, unique=True),
        index_model(UserMapper.email, unique=True)
    ])

    db.sounds.create_indexes([
        index_model(SoundMapper.created_by),
        index_model(SoundMapper.audio_url, unique=True),
        index_model(SoundMapper.tags)
    ])

    db.annotations.create_indexes([
        index_model(AnnotationMapper.created_by),
        index_model(AnnotationMapper.sound_id),
        index_model(AnnotationMapper.tags),
        IndexModel([
            (AnnotationMapper.sound_id.storage_name, ASCENDING),
            (AnnotationMapper.start_seconds.storage_name, ASCENDING)
        ], name='start_seconds'),
        IndexModel([
            (AnnotationMapper.sound_id.storage_name, ASCENDING),
            (AnnotationMapper.end_seconds.storage_name, ASCENDING)
        ], name='end_seconds')

    ])

    users_db = db.users
    sounds_db = db.sounds
    annotations_db = db.annotations

    users_repo = UserRepository(users_db)
    sounds_repo = SoundRepository(sounds_db)
    annotations_repo = AnnotationRepository(annotations_db)

    return users_repo, sounds_repo, annotations_repo
