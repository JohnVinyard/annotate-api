from pymongo import MongoClient, IndexModel
from model import UserData

client = MongoClient('mongo')
db = client.annotate
db.users.create_indexes([
    IndexModel('user_type', name='user_type'),
    IndexModel('date_created', name='date_created')
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
        return UserData(**user_data)

    def add_user(self, user_create_data):
        insert_data = dict(user_create_data.__dict__)
        insert_data['_id'] = insert_data['id']
        del insert_data['id']
        self.collection.insert_one(insert_data)

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