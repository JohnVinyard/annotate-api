from scratch import BaseMapper, BaseMapping
from model import UserType, User


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
