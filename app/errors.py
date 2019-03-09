
class DuplicateUserException(Exception):
    def __init__(self):
        super().__init__('A user already exists with this user_name or email')
