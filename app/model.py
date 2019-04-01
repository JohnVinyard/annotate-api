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
    HUMAN = 'human'
    FEATUREBOT = 'featurebot'
    DATASET = 'dataset'


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
        parsed = urlparse(value)
        if not all((parsed.scheme, parsed.netloc)):
            raise ValueError(f'{value} is not a valid {self.name}')


class BaseAppEntity(BaseEntity):
    id = BaseDescriptor(default_value=user_id_generator)
    date_created = Immutable(default_value=datetime.datetime.utcnow)

    @property
    def identity_query(self):
        return self.__class__.id == self.id

    @property
    def storage_key(self):
        # TODO: Can this be derived solely from the identity_query?
        return self.__class__, self.id


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


class LicenseType(Enum):
    BY = 'https://creativecommons.org/licenses/by/4.0'
    BY_SA = 'https://creativecommons.org/licenses/by-sa/4.0'
    BY_ND = 'https://creativecommons.org/licenses/by-nd/4.0'
    BY_NC = 'https://creativecommons.org/licenses/by-nc/4.0'
    BY_NC_SA = 'https://creativecommons.org/licenses/by-nc-sa/4.0'
    BY_NC_ND = 'https://creativecommons.org/licenses/by-nc-nd/4.0'


class SoundCreatedBy(Immutable):
    def validate(self, instance):
        user = instance.get(self.name)
        if user.user_type == UserType.FEATUREBOT:
            raise ValueError(f'{user.user_type} users may not create sounds')


class Sound(BaseAppEntity):
    # TODO: This should be a stored user
    # TODO: The user should not be a featurebot
    # TODO: It should be set with a user, but stored as an id
    # TODO: It should be returned in the output as a link
    created_by = SoundCreatedBy(required=True)
    # TODO: This should be a valid url
    info_url = URL(required=True)
    # TODO: This should be a valid url
    audio_url = URL(required=True)
    license_type = Immutable(value_transform=LicenseType, required=True)
    title = Immutable(required=True)
    duration_seconds = Immutable(required=True, value_transform=float)


class Annotation(BaseAppEntity):
    # TODO: This should be a stored user
    # TODO: It should be set with a user, but stored as an id
    # TODO: It should be returned in the output as a link
    created_by = Immutable(required=True)
    # TODO: This should be set with a stored sound entity
    sound_id = Immutable(required=True)
    start_seconds = Immutable(required=True, value_transform=float)
    duration_seconds = Immutable(required=True, value_transform=float)
    tags = Immutable(value_transform=tuple)
    # TODO: This should be null, or be a valid URL
    data_url = URL()
