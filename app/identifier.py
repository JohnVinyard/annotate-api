import uuid


class UserIdGenerator(object):
    def __call__(self):
        return uuid.uuid4().hex

user_id_generator = UserIdGenerator()

__all__ = [
    user_id_generator
]