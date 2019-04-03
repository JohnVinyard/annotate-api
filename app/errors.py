class DuplicateUserException(Exception):
    def __init__(self):
        super().__init__('A user already exists with this user_name or email')


class PermissionsError(Exception):
    def __init__(self, message):
        super().__init__(message)


class ImmutableError(Exception):
    def __init__(self, key):
        super().__init__(f'{key} is immutable')


class PartialEntityUpdate(Exception):
    def __init__(self, entity):
        super().__init__(
            'f{entity} is partial but was modified in this session')


class CompositeValidationError(ValueError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
