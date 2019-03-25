import datetime
from password import password_hasher
from identifier import user_id_generator
from scratch import ContextualValue, BaseEntity, BaseDescriptor, Immutable, \
    never, always
from enum import Enum
import re


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


class User(BaseEntity):
    id = BaseDescriptor(default_value=user_id_generator)

    date_created = Immutable(default_value=lambda: datetime.datetime.utcnow())

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

    @property
    def identity_query(self):
        return User.id == self.id

    @property
    def storage_key(self):
        # TODO: Can this be derived solely from the identity_query?
        return self.__class__, self.id
