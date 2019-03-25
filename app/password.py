import hashlib


# TODO: Use bycrypt or some better hashing scheme
class PasswordHasher(object):
    def __call__(self, password):
        if not password:
            return password
        return hashlib.sha3_256(password.encode()).hexdigest()


password_hasher = PasswordHasher()

__all__ = [
    password_hasher
]
