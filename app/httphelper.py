import base64
from scratch import Session
import falcon
import logging
from errors import DuplicateUserException, PermissionsError, ImmutableError


def decode_auth_header(auth):
    username, password = base64.b64decode(
        auth.replace('Basic ', '')).decode().split(':')
    return username, password


class SessionMiddleware(object):
    def __init__(self, *repositories):
        super().__init__()
        self.repositories = repositories

    def process_resource(self, req, resp, resource, params):
        session = Session(*self.repositories).open()
        req.context['session'] = session

    def process_response(self, req, resp, resource, req_succeeded):
        session = req.context['session']

        if not req_succeeded:
            session.abort()
            return

        try:
            # commit any changes to backing data stores
            session.close()
        except Exception as e:
            if isinstance(e, DuplicateUserException):
                raise falcon.HTTPConflict()
            elif isinstance(e, PermissionsError):
                raise falcon.HTTPForbidden()
            elif isinstance(e, ImmutableError):
                raise falcon.HTTPBadRequest()
            else:
                logging.error(e)
                raise
