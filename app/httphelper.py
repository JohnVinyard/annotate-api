import base64
from scratch import Session
import falcon
import logging
from errors import DuplicateEntityException, PermissionsError, ImmutableError
from string import Formatter


def decode_auth_header(auth):
    username, password = base64.b64decode(
        auth.replace('Basic ', '')).decode().split(':')
    return username, password


class EntityLinks(object):
    def __init__(self, entity_to_link_template_mapping):
        self.mapping = entity_to_link_template_mapping

    def _extract_keys_from_template_string(self, template):
        # KLUDGE: What happens if there are multiple keys in the template?
        return (x[1] for x in Formatter().parse(template))

    def convert_to_link(self, entity):
        link_template = self.mapping[entity.__class__]
        key = next(self._extract_keys_from_template_string(link_template))
        format_dict = {key: entity.identifier}
        return link_template.format(**format_dict)


class SessionMiddleware(object):
    def __init__(self, link_converter, *repositories):
        super().__init__()
        self.link_converter = link_converter
        self.repositories = repositories

    def _session(self):
        return Session(*self.repositories)

    def process_resource(self, req, resp, resource, params):
        # session = Session(*self.repositories).open()
        session = self._session().open()
        req.context['session'] = session
        params['session'] = session

    def process_response(self, req, resp, resource, req_succeeded):
        if not resource:
            return

        session = req.context['session']

        if not req_succeeded:
            session.abort()
            return

        try:
            # commit any changes to backing data stores
            session.close()
        except Exception as e:
            if isinstance(e, DuplicateEntityException):
                entity_cls = e.entity_cls

                with self._session() as session:
                    query = entity_cls.exists_query(**req.media)
                    entity = session.find_one(query)
                    uri = self.link_converter.convert_to_link(entity)
                    resp.set_header('Location', uri)
                    raise falcon.HTTPConflict()
            else:
                logging.error(e)
                raise
