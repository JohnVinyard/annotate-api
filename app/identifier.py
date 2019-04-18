import time
import os
import binascii


class UserIdGenerator(object):
    def __call__(self):
        time_bits = '{:x}'.format(int(time.time() * 1e6))
        random_bits = binascii.hexlify(os.urandom(8)).decode()
        identifier = time_bits + random_bits
        return identifier

user_id_generator = UserIdGenerator()

__all__ = [
    user_id_generator
]