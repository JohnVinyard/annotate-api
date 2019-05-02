from scratch import BaseMapper, BaseMapping
from model import UserType, User, Sound, Annotation, LicenseType


class EnumMapping(BaseMapping):
    def __init__(self, field, enum_class, *args, **kwargs):
        super().__init__(
            field,
            *args,
            to_storage_format=lambda instance: instance.value,
            from_storage_format=lambda value: enum_class(value),
            **kwargs)


class EntityMapping(BaseMapping):
    def __init__(self, field, entity_class, *args, **kwargs):
        self.entity_class = entity_class
        super().__init__(
            field,
            *args,
            to_storage_format=self._to_storage_format,
            from_storage_format=self._from_storage_format,
            **kwargs)

    def _to_storage_format(self, instance):
        return instance.id

    def _from_storage_format(self, value):
        return self.entity_class.partial_hydrate(id=value)


class UserMapper(BaseMapper):
    # TODO: Better, more formal way to specify mapper's target class than this
    entity_class = User

    _id = BaseMapping(User.id)
    date_created = BaseMapping(User.date_created)
    deleted = BaseMapping(User.deleted)
    user_name = BaseMapping(User.user_name)
    password = BaseMapping(User.password)
    user_type = EnumMapping(User.user_type, UserType)
    email = BaseMapping(User.email)
    about_me = BaseMapping(User.about_me)
    info_url = BaseMapping(User.info_url)


class SoundMapper(BaseMapper):
    entity_class = Sound

    _id = BaseMapping(Sound.id)
    date_created = BaseMapping(Sound.date_created)
    created_by = EntityMapping(Sound.created_by, User)
    info_url = BaseMapping(Sound.info_url)
    audio_url = BaseMapping(Sound.audio_url)
    license_type = EnumMapping(Sound.license_type, LicenseType)
    title = BaseMapping(Sound.title)
    duration_seconds = BaseMapping(Sound.duration_seconds)
    tags = BaseMapping(Sound.tags)


class AnnotationMapper(BaseMapper):
    entity_class = Annotation

    _id = BaseMapping(Annotation.id)
    date_created = BaseMapping(Annotation.date_created)
    created_by = EntityMapping(Annotation.created_by, User)
    sound_id = EntityMapping(Annotation.sound, Sound)
    start_seconds = BaseMapping(Annotation.start_seconds)
    duration_seconds = BaseMapping(Annotation.duration_seconds)
    tags = BaseMapping(Annotation.tags)
    data_url = BaseMapping(Annotation.data_url)
