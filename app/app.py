import falcon
from data import users_repo, sounds_repo, annotations_repo, NoCriteria
from model import User, ContextualValue, Sound, Annotation
from httphelper import decode_auth_header, SessionMiddleware, EntityLinks
from customjson import JSONHandler
import urllib
from errors import \
    PermissionsError, CompositeValidationError, EntityNotFoundError

USER_URI_TEMPLATE = '/users/{user_id}'
SOUND_URI_TEMPLATE = '/sounds/{sound_id}'

ENTITIES_AS_LINKS = {
    User: USER_URI_TEMPLATE,
    Sound: SOUND_URI_TEMPLATE
}


class AppEntityLinks(EntityLinks):
    def __init__(self):
        super().__init__(ENTITIES_AS_LINKS)


def basic_auth(req, resp, resource, params):
    auth = req.get_header('Authorization')
    if auth is None:
        raise falcon.HTTPUnauthorized()

    try:
        username, password = decode_auth_header(auth)
    except TypeError:
        raise falcon.HTTPUnauthorized()

    session = params['session']
    query = User.auth_query(username, password)

    try:
        user = session.find_one(query)
        req.context['actor'] = user
        params['actor'] = user
    except EntityNotFoundError:
        raise falcon.HTTPUnauthorized()


class RootResource(object):
    def __init__(self, user_repo, sound_repo, annotation_repo):
        self.annotation_repo = annotation_repo
        self.sound_repo = sound_repo
        self.user_repo = user_repo
        super().__init__()

    def on_get(self, req, resp, session):
        resp.media = {
            'totalSounds': session.count(Sound.all_query()),
            'totalAnnotations': session.count(Annotation.all_query()),
            'totalUsers': session.count(User.all_query())
        }
        resp.status = falcon.HTTP_200

    def on_delete(self, req, resp, session):
        self.user_repo.delete_all()
        self.sound_repo.delete_all()
        self.annotation_repo.delete_all()
        resp.status = falcon.HTTP_NO_CONTENT


def composite_validation_error(e, req, resp, params):
    desc = [(err[0], err[1].args[0]) for err in e.args]
    raise falcon.HTTPBadRequest(description=desc)


def not_found_error(e, req, resp, params):
    raise falcon.HTTPNotFound()


def list_entity(
        req,
        resp,
        session,
        actor,
        query,
        result_order,
        link_template,
        additional_params=None):
    page_size = req.get_param_as_int('page_size') or 100
    page_number = req.get_param_as_int('page_number') or 0

    page_size_min = 1
    page_size_max = 500

    if page_size < page_size_min or page_size > page_size_max:
        raise falcon.HTTPBadRequest(
            f'Page size must be between '
            f'{page_size_min} and {page_size_max}')

    additional_params = additional_params or {}
    low_id = req.get_param('low_id')
    if low_id is not None:
        query = query & (query.entity_class.id > low_id)
        additional_params['low_id'] = low_id

    query_result = session.filter(
        query,
        page_size,
        page_number,
        result_order)

    results = {
        'items': [r.view(actor) for r in query_result.results],
        'total_count': query_result.total_count
    }

    if query_result.next_page is not None:
        query_params = {
            'page_size': page_size,
            'page_number': query_result.next_page,
        }
        query_params.update(**additional_params)
        query_params = {k: v for k, v in query_params.items() if v}
        encoded_params = urllib.parse.urlencode(query_params)
        results['next'] = link_template.format(encoded_params=encoded_params)

    resp.media = results
    resp.status = falcon.HTTP_OK


class SoundsResource(object):
    @falcon.before(basic_auth)
    def on_post(self, req, resp, session, actor):
        data = req.media
        data['created_by'] = actor
        sound = Sound.create(creator=actor, **data)
        resp.set_header('Location', f'/sounds/{sound.id}')
        resp.status = falcon.HTTP_CREATED

    @falcon.before(basic_auth)
    def on_get(self, req, resp, session, actor):
        created_by_key = Sound.created_by.name

        user_id = req.get_param(created_by_key)
        additional_params = {}

        if user_id:
            query = Sound.created_by == User.partial_hydrate(id=user_id)
            additional_params[created_by_key] = user_id
        else:
            query = Sound.all_query()

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Sound.date_created.ascending(),
            '/sounds?{encoded_params}',
            additional_params=additional_params)


def view_entity(session, actor, query):
    # TODO: There should be an option to exclude the total count here
    entity = session.find_one(query)
    view = entity.view(actor)
    return view


def get_entity(resp, session, actor, query):
    view = view_entity(session, actor, query)
    resp.media = view
    resp.status = falcon.HTTP_OK


def head_entity(resp, session, query):
    count = session.count(query)
    if count != 1:
        raise falcon.HTTPNotFound()
    resp.status = falcon.HTTP_NO_CONTENT


class SoundAnnotationsResource(object):
    """
    Create and list annotations associated with a sound
    """

    @falcon.before(basic_auth)
    def on_post(self, req, resp, sound_id, session, actor):
        """
        Create new annotations for a sound
        """
        sound = session.find_one(Sound.id == sound_id)
        for annotation in req.media['annotations']:
            annotation['created_by'] = actor
            annotation['sound'] = sound
            Annotation.create(
                creator=actor,
                **annotation)
        resp.set_header('Location', f'/sounds/{sound_id}/annotations')
        resp.status = falcon.HTTP_CREATED

    @falcon.before(basic_auth)
    def on_get(self, req, resp, sound_id, session, actor):
        """
        List annotations for a sound
        """
        sound = session.find_one(Sound.id == sound_id)
        query = Annotation.sound == sound

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Annotation.date_created.ascending(),
            f'/sounds/{sound_id}/annotations?{{encoded_params}}')


class UserSoundsResource(object):
    """
    List sounds created by a user
    """

    @falcon.before(basic_auth)
    def on_get(self, req, resp, user_id, session, actor):
        user = session.find_one(User.id == user_id)
        query = Sound.created_by == user

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Sound.date_created.ascending(),
            f'/users/{user_id}/sounds?{{encoded_params}}')


class UserAnnotationResource(object):
    """
    List annotations created by a user
    """

    @falcon.before(basic_auth)
    def on_get(self, req, resp, user_id, session, actor):
        user = session.find_one(User.id == user_id)
        query = Annotation.created_by == user

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Annotation.date_created.ascending(),
            f'/users/{user_id}/annotations?{{encoded_params}}')


class UsersResource(object):
    def on_post(self, req, resp, session):
        """
        Create a new user
        """
        user = User.create(**req.media)
        resp.set_header('Location', f'/users/{user.id}')
        resp.status = falcon.HTTP_CREATED

    @falcon.before(basic_auth)
    def on_get(self, req, resp, session, actor):
        user_type = req.get_param(User.user_type.name)

        base_query = User.deleted == False
        if user_type:
            try:
                query = (base_query & (User.user_type == user_type))
            except ValueError as e:
                raise falcon.HTTPBadRequest(e.args[0])
        else:
            query = base_query

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            User.date_created.descending(),
            '/users?{encoded_params}',
            additional_params={User.user_type.name: user_type})


class SoundResource(object):
    @falcon.before(basic_auth)
    def on_get(self, req, resp, sound_id, session, actor):
        get_entity(resp, session, actor, Sound.id == sound_id)

    @falcon.before(basic_auth)
    def on_head(self, req, resp, sound_id, session, actor):
        head_entity(resp, session, Sound.id == sound_id)


class UserResource(object):
    @falcon.before(basic_auth)
    def on_get(self, req, resp, user_id, session, actor):
        get_entity(resp, session, actor, User.active_user_query(user_id))

    @falcon.before(basic_auth)
    def on_head(self, req, resp, user_id, session, actor):
        head_entity(resp, session, User.active_user_query(user_id))

    @falcon.before(basic_auth)
    def on_delete(self, req, resp, user_id, session, actor):
        """
        Delete an individual user
        """
        to_delete = session.find_one(User.id == user_id)
        to_delete.deleted = ContextualValue(actor, True)

    @falcon.before(basic_auth)
    def on_patch(self, req, resp, user_id, session, actor):
        """
        Update a user
        """
        query = User.active_user_query(user_id)
        to_update = session.find_one(query)
        to_update.update(actor, **req.media)


app_entity_links = AppEntityLinks()

api = application = falcon.API(middleware=[
    SessionMiddleware(
        app_entity_links, users_repo, sounds_repo, annotations_repo)
])

extra_handlers = falcon.media.Handlers({
    'application/json': JSONHandler(app_entity_links),
})

api.resp_options.media_handlers = extra_handlers

# public endpoints
api.add_route('/', RootResource(users_repo, sounds_repo, annotations_repo))
api.add_route('/users', UsersResource())
api.add_route(USER_URI_TEMPLATE, UserResource())
api.add_route('/sounds', SoundsResource())
api.add_route(SOUND_URI_TEMPLATE, SoundResource())
api.add_route('/sounds/{sound_id}/annotations', SoundAnnotationsResource())
api.add_route('/users/{user_id}/sounds', UserSoundsResource())
api.add_route('/users/{user_id}/annotations', UserAnnotationResource())


# custom errors
def permissions_error(ex, req, resp, params):
    raise falcon.HTTPForbidden(ex.args[0])


api.add_error_handler(PermissionsError, permissions_error)
api.add_error_handler(
    CompositeValidationError, composite_validation_error)
api.add_error_handler(EntityNotFoundError, not_found_error)
