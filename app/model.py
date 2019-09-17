import datetime
from password import password_hasher
from identifier import user_id_generator
from scratch import ContextualValue, BaseEntity, BaseDescriptor, Immutable, \
    never, always
from enum import Enum
import re
from urllib.parse import urlparse


def is_me(instance, context):
    return instance.id == context.id


class UserType(Enum):
    """
    Enumerates possible user types

    Attributes:
        HUMAN - A human user that will likely interact with the API via a GUI
        FEATUREBOT - An automated user that computes features for some or all
            sounds
        DATASET - An automated user that creates sounds and may add annotations
            to them in some cases
        AGGREGATOR - An automated user with read-only access that may index
            sounds and host a remote search API, or may compute statistics for
            some or all sounds or annotations/features
    """
    HUMAN = 'human'
    FEATUREBOT = 'featurebot'
    DATASET = 'dataset'
    AGGREGATOR = 'aggregator'


class AboutMe(BaseDescriptor):
    def validate(self, instance):
        value = instance.get(self.name)

        if value:
            return

        try:
            if instance.user_type == UserType.HUMAN:
                return
        except AttributeError:
            raise ValueError(
                f'Empty "{self.name}" is only valid for {UserType.HUMAN} '
                f'but no user_type was specified')

        if not value:
            raise ValueError(
                f'Field "{self.name}" must be specified '
                f'for datasets and featurebots')


class Email(Immutable):
    BASIC_EMAIL_PATTERN = re.compile(r'[^@]+@[^@]+\.[^@]+')

    def validate(self, instance):
        value = instance.get(self.name)
        if not re.fullmatch(Email.BASIC_EMAIL_PATTERN, value):
            raise ValueError(f'{value} is not a valid email address')


class URL(Immutable):
    def validate(self, instance):
        value = instance.get(self.name)
        if value is None:
            return
        parsed = urlparse(value)
        if not all((parsed.scheme, parsed.netloc)):
            raise ValueError(f'{value} is not a valid {self.name}')


class BaseAppEntity(BaseEntity):
    id = Immutable(default_value=user_id_generator)
    date_created = Immutable(
        default_value=lambda instance: datetime.datetime.utcnow())

    @property
    def identifier(self):
        return self.id

    @property
    def identity_query(self):
        return self.__class__.id == self.identifier

    @property
    def storage_key(self):
        # TODO: Can this be derived solely from the identity_query?
        return self.__class__, self.identifier

    @classmethod
    def exists_query(cls, **kwargs):
        raise NotImplementedError()


class User(BaseAppEntity):
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
    user_type = Immutable(value_transform=UserType, evaluate_context=is_me)
    email = Email(visible=is_me, evaluate_context=is_me)
    about_me = AboutMe(evaluate_context=is_me)
    info_url = URL()

    @classmethod
    def auth_query(cls, user_name, password):
        return (User.user_name == user_name) \
               & (User.password == password) \
               & (User.deleted == False)

    @classmethod
    def active_user_query(cls, user_id):
        return (User.id == user_id) & (User.deleted == False)

    @classmethod
    def exists_query(cls, user_name, email, **kwargs):
        return (User.user_name == user_name) | (User.email == email)

    def can_create_sound(self):
        return self.user_type in Sound.ALLOWED_CREATOR_TYPES

    def can_create_annotation(self):
        return self.user_type in Annotation.ALLOWED_CREATOR_TYPES


class LicenseType(Enum):
    BY = 'https://creativecommons.org/licenses/by/4.0'
    BY_SA = 'https://creativecommons.org/licenses/by-sa/4.0'
    BY_ND = 'https://creativecommons.org/licenses/by-nd/4.0'
    BY_NC = 'https://creativecommons.org/licenses/by-nc/4.0'
    BY_NC_SA = 'https://creativecommons.org/licenses/by-nc-sa/4.0'
    BY_NC_ND = 'https://creativecommons.org/licenses/by-nc-nd/4.0'


class Sound(BaseAppEntity):
    ALLOWED_CREATOR_TYPES = {UserType.HUMAN, UserType.DATASET}

    created_by = Immutable(
        required=True,
        evaluate_context=lambda instance, context:
            context.user_type in Sound.ALLOWED_CREATOR_TYPES)
    created_by_user_name = Immutable(
        default_value=lambda instance:
        instance.created_by.user_name)
    info_url = URL(required=True)
    audio_url = URL(required=True)
    low_quality_audio_url = URL(required=False)
    license_type = Immutable(value_transform=LicenseType, required=True)
    title = Immutable(required=True)
    duration_seconds = Immutable(required=True, value_transform=float)
    tags = Immutable()

    @classmethod
    def exists_query(cls, audio_url, **kwargs):
        return Sound.audio_url == audio_url


class Annotation(BaseAppEntity):

    ALLOWED_CREATOR_TYPES = \
        {UserType.HUMAN, UserType.DATASET, UserType.FEATUREBOT}

    created_by = Immutable(
        required=True,
        evaluate_context=lambda instance, context:
            context.user_type in Annotation.ALLOWED_CREATOR_TYPES)
    created_by_user_name = Immutable(
        default_value=lambda instance:
        instance.created_by.user_name)
    sound = Immutable(required=True)
    start_seconds = Immutable(required=True, value_transform=float)
    duration_seconds = Immutable(required=True, value_transform=float)
    end_seconds = Immutable(
        default_value=lambda instance:
        instance.start_seconds + instance.duration_seconds)
    data_url = URL(default_value=None)
    tags = Immutable(default_value=[])
