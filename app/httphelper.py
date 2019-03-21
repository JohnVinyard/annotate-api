import base64
from scratch import Session
import falcon
import logging


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
        logging.error(session)

    def process_response(self, req, resp, resource, req_succeeded):
        session = req.context['session']
        logging.error(session)

        if not req_succeeded:
            session.abort()
            return

        try:
            # commit any changes to backing data stores
            session.close()
        except Exception as e:
            logging.error(e)
            # there were one or more problems with the entities in the session
            # don't commit any updates and return an HTTP error
            # TODO: Translate specific exceptions into appropriate HTTP errors
            raise falcon.HTTPBadRequest()
