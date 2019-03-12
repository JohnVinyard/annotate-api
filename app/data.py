from pymongo import MongoClient, IndexModel, DESCENDING
from pymongo.errors import DuplicateKeyError
from model import UserData, UserType
from password import password_hasher
from errors import DuplicateUserException, PermissionsError

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


# TODO: Get rid of any hard-coded property names in this class, instead relying
# on metadata from the models
class UserRepository(BaseMongoRepository):
    def __init__(self, collection):
        super().__init__(collection)

    def _user_query(self, user_id, **kwargs):
        base_query = {'_id': user_id, 'deleted': False}
        return {**base_query, **kwargs}

    def get_user(self, actor, user_id):
        user_data = self.collection.find_one(self._user_query(user_id))
        if user_data is None:
            raise KeyError(user_id)
        return actor.view(UserData(**user_data))

    def user_exists(self, user_id):
        return self.collection.count_documents(self._user_query(user_id)) == 1

    def add_user(self, user_create_data):
        insert_data = dict(user_create_data.__dict__)
        insert_data['_id'] = insert_data['id']
        del insert_data['id']
        try:
            self.collection.insert_one(insert_data)
        except DuplicateKeyError:
            raise DuplicateUserException()

    def delete_user(self, actor, user_id):
        # TODO: This method crystallizes all the current problems:
        #   - There's business logic here in the repo.  It should be part of User
        #   - In order to apply the business logic, I'd have to fetch the other user
        #   - It's much more efficient to perform the update in this way, directly using the database
        #   - There are hard-coded property names being referenced
        delete_target = UserData(_id=user_id)
        actor.delete_user(delete_target)
        self.collection.find_and_modify(
            self._user_query(user_id), {'deleted': True})

    def authenticate(self, user_name, password):
        password = password_hasher(password)
        user_data = self.collection.find_one(
            {'user_name': user_name, 'password': password, 'deleted': False})
        if user_data is None:
            raise ValueError('user_name and password combination is not valid')
        return UserData(**user_data)

    def list_users(
            self,
            user_type=None,
            page_size=25,
            page_number=0):

        page_size_min = 1
        page_size_max = 500

        if page_size < page_size_min or page_size > page_size_max:
            raise ValueError(
                f'Page size must be between '
                f'{page_size_min} and {page_size_max}')

        query = {}

        if user_type:
            user_type = UserType(user_type)
            query['user_type'] = user_type.value

        total_count = self.collection.count_documents(query)

        results = self.collection.find(
            query, sort=[('date_created', DESCENDING)]) \
            .skip(page_number * page_size) \
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
