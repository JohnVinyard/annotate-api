from pymongo import MongoClient, IndexModel

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