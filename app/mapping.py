from scratch import BaseMapper, BaseMapping
from model import UserType, User, Sound, Annotation


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


class SoundMapper(BaseMapper):
    entity_class = Sound

    _id = BaseMapping(Sound.id)
    date_created = BaseMapping(Sound.date_created)
    created_by = BaseMapping(Sound.created_by)
    info_url = BaseMapping(Sound.info_url)
    audio_url = BaseMapping(Sound.audio_url)
    license_type = BaseMapping(Sound.license_type)
    title = BaseMapping(Sound.title)
    duration_seconds = BaseMapping(Sound.duration_seconds)


class AnnotationMapper(BaseMapper):
    entity_class = Annotation

    _id = BaseMapping(Annotation.id)
    date_created = BaseMapping(Annotation.date_created)
    created_by = BaseMapping(Annotation.created_by)
    sound_id = BaseMapping(Annotation.sound_id)
    start_seconds = BaseMapping(Annotation.start_seconds)
    duration_seconds = BaseMapping(Annotation.duration_seconds)
    tags = BaseMapping(Annotation.tags)
    data_url = BaseMapping(Annotation.data_url)
