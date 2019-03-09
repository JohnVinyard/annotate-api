from pymongo import MongoClient, IndexModel, DESCENDING
from pymongo.errors import DuplicateKeyError
from model import UserData, UserType
from password import password_hasher
from errors import DuplicateUserException

client = MongoClient('mongo')
db = client.annotate
db.users.create_indexes([
    IndexModel('user_type', name='user_type'),
    IndexModel('date_created', name='date_created'),
    IndexModel('password', name='password'),
    IndexModel('user_name', name='user_name', unique=True),
    IndexModel('email', name='email', unique=True)
])

db.sounds.create_indexes([
    IndexModel('date_created', name='date_created')
])

db.annotations.create_indexes([
    IndexModel('date_created', name='date_created')
])

users_db = db.users
sounds_db = db.sounds
annotations_db = db.annotations


class BaseMongoRepository(object):
    def __init__(self, collection):
        self.collection = collection

    def __len__(self):
        return self.collection.estimated_document_count()

    def delete_all(self):
        return self.collection.delete_many({})


class UserRepository(BaseMongoRepository):
    def __init__(self, collection):
        super().__init__(collection)

    def get_user(self, user_id):
        user_data = self.collection.find_one({'_id': user_id})
        if user_data is None:
            raise KeyError(user_id)
        return UserData(**user_data)

    def user_exists(self, user_id):
        return self.collection.count_documents({'_id': user_id}) == 1

    def add_user(self, user_create_data):
        insert_data = dict(user_create_data.__dict__)
        insert_data['_id'] = insert_data['id']
        del insert_data['id']
        try:
            self.collection.insert_one(insert_data)
        except DuplicateKeyError:
            raise DuplicateUserException()

    def authenticate(self, user_name, password):
        password = password_hasher(password)
        user_data = self.collection.find_one(
            {'user_name': user_name, 'password': password})
        if user_data is None:
            raise ValueError('user_name and password combination is not valid')
        return UserData(**user_data)

    def list_users(
            self,
            user_type=None,
            page_size=25,
            page_number=0):

        query = {}

        if user_type:
            user_type = UserType(user_type)
            query['user_type'] = user_type.value

        total_count = self.collection.count_documents(query)

        results = self.collection.find(
            query, sort=[('date_created', DESCENDING)])\
            .skip(page_number * page_size)\
            .limit(page_size)

        results = list(map(lambda x: UserData(**x), results))
        current_pos = (page_number * page_size) + len(results)
        next_page = page_number + 1 if current_pos < total_count else None
        return total_count, results, next_page

    def update_user(self, user_id, user_update_data):
        raise NotImplementedError()


class SoundRepository(BaseMongoRepository):
    def __init__(self, collection):
        super().__init__(collection)


class AnnotationRepository(BaseMongoRepository):
    def __init__(self, collection):
        super().__init__(collection)


users_repo = UserRepository(users_db)
sounds_repo = SoundRepository(sounds_db)
annotations_repo = AnnotationRepository(annotations_db)

__all__ = [
    users_repo,
    sounds_repo,
    annotations_repo
]
