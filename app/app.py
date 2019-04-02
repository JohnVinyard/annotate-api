import falcon
from data import users_repo, sounds_repo, annotations_repo, NoCriteria
from model import User, ContextualValue, Sound, Annotation
from httphelper import decode_auth_header, SessionMiddleware
from customjson import JSONHandler
import urllib
from errors import DuplicateUserException, PermissionsError, ImmutableError


def basic_auth(req, resp, resource, params):
    auth = req.get_header('Authorization')
    if auth is None:
        raise falcon.HTTPUnauthorized()

    try:
        username, password = decode_auth_header(auth)
    except TypeError:
        raise falcon.HTTPUnauthorized()

    session = req.context['session']

    # This just about constitutes business logic, so it should be put in a
    # collection of queries somewhere, maybe
    query = \
        (User.user_name == username) \
        & (User.password == password) \
        & (User.deleted == False)

    try:
        user = next(session.filter(query=query, page_size=1, page_number=0))
        req.context['actor'] = user
        params['actor'] = user
    except StopIteration:
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


class SoundsResource(object):
    @falcon.before(basic_auth)
    def on_post(self, req, resp, session, actor):
        data = req.media
        data['created_by'] = actor

        # TODO: This looks exactly like UsersResource.post below.  Do some
        # refactoring
        try:
            sound = Sound.create(creator=actor, **data)
        except ValueError as e:
            desc = [(err[0], err[1].args[0]) for err in e.args]
            raise falcon.HTTPBadRequest(description=desc)
        resp.set_header('Location', f'/sounds/{sound.id}')
        resp.status = falcon.HTTP_CREATED


class UsersResource(object):
    def on_post(self, req, resp, session):
        """
        Create a new user
        """
        try:
            user = User.create(**req.media)
        except ValueError as e:
            desc = [(err[0], err[1].args[0]) for err in e.args]
            raise falcon.HTTPBadRequest(description=desc)
        resp.set_header('Location', f'/users/{user.id}')
        resp.status = falcon.HTTP_CREATED

    @falcon.before(basic_auth)
    def on_get(self, req, resp, session, actor):
        """
        List users
        """
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number') or 0
        user_type = req.get_param('user_type')

        page_size_min = 1
        page_size_max = 500

        if page_size < page_size_min or page_size > page_size_max:
            raise falcon.HTTPBadRequest(
                f'Page size must be between '
                f'{page_size_min} and {page_size_max}')

        try:
            query = \
                (User.user_type == user_type) \
                    if user_type else NoCriteria(User)
        except ValueError as e:
            raise falcon.HTTPBadRequest(e.args[0])

        query_result = session.filter(
            query,
            page_size,
            page_number,
            User.date_created.descending())

        results = {
            'items': [r.view(actor) for r in query_result.results],
            'total_count': query_result.total_count
        }

        if query_result.next_page is not None:
            query_params = {
                'page_size': page_size,
                'page_number': query_result.next_page,
                'user_type': user_type
            }
            query_params = {k: v for k, v in query_params.items() if v}
            encoded_params = urllib.parse.urlencode(query_params)
            results['next'] = f'/users?{encoded_params}'

        resp.media = results
        resp.status = falcon.HTTP_OK


class SoundResource(object):
    @falcon.before(basic_auth)
    def on_get(self, req, resp, sound_id, session, actor):
        # TODO: This is almost exactly the same code as GET /users/{user_id}
        # below and could use some refactoring
        query = (Sound.id == sound_id)
        try:
            sound = next(session.filter(query, page_size=1, page_number=0))
        except StopIteration:
            raise falcon.HTTPNotFound()

        sound_view = sound.view(actor)
        resp.media = sound_view
        resp.status = falcon.HTTP_OK

    @falcon.before(basic_auth)
    def on_head(self, req, resp, sound_id, session, actor):
        # TODO: This is almost exactly the same code as HEAD /users/{user_id}
        # below and could use some refactoring
        count = session.count(Sound.id == sound_id)
        if count == 1:
            resp.status = falcon.HTTP_NO_CONTENT
        else:
            raise falcon.HTTPNotFound()


class UserResource(object):
    @falcon.before(basic_auth)
    def on_get(self, req, resp, user_id, session, actor):
        """
        Get an individual user
        """
        query = (User.id == user_id) & (User.deleted == False)
        try:
            user_data = next(session.filter(query, page_size=1, page_number=0))
        except StopIteration:
            raise falcon.HTTPNotFound()

        user_view = user_data.view(actor)
        resp.media = user_view
        resp.status = falcon.HTTP_OK

    @falcon.before(basic_auth)
    def on_head(self, req, resp, user_id, session, actor):
        count = session.count(User.id == user_id)
        if count == 1:
            resp.status = falcon.HTTP_NO_CONTENT
        else:
            raise falcon.HTTPNotFound()

    @falcon.before(basic_auth)
    def on_delete(self, req, resp, user_id, session, actor):
        """
        Delete an individual user
        """

        # TODO: Business rules that make data needed to evaluate the rule
        # explicit, so that only that data need be fetched.  In this case,
        # the rule about who may delete whom only requires user id, which we
        # already have in this scenario.

        try:
            to_delete = next(session.filter(User.id == user_id))
        except StopIteration:
            raise falcon.HTTPNotFound()

        try:
            to_delete.deleted = ContextualValue(actor, True)
        except PermissionsError:
            raise falcon.HTTPForbidden()

    @falcon.before(basic_auth)
    def on_patch(self, req, resp, user_id, session, actor):
        """
        Update a user
        """
        query = (User.id == user_id) & (User.deleted == False)
        try:
            to_update = next(session.filter(query, page_size=1))
        except StopIteration:
            raise falcon.HTTPNotFound()

        try:
            to_update.update(actor, **req.media)
        except ValueError as e:
            # TODO: This code for transforming exceptions also appears in
            # POST /users and should be factored into a common location
            desc = [(err[0], err[1].args[0]) for err in e.args]
            raise falcon.HTTPBadRequest(description=desc)
        except PermissionsError:
            raise falcon.HTTPForbidden()


# TODO: Add error handlers to DRY out some of my exception handling code
# https://falcon.readthedocs.io/en/stable/api/api.html#falcon.API.add_error_handler
api = application = falcon.API(middleware=[
    SessionMiddleware(users_repo, sounds_repo, annotations_repo)
])

USER_URI_TEMPLATE = '/users/{user_id}'
SOUND_URI_TEMPLATE = '/sounds/{sound_id}'

ENTITIES_AS_LINKS = {
    User: USER_URI_TEMPLATE,
    Sound: SOUND_URI_TEMPLATE
}

extra_handlers = falcon.media.Handlers({
    'application/json': JSONHandler(ENTITIES_AS_LINKS),
})

api.resp_options.media_handlers = extra_handlers

# public endpoints
api.add_route('/', RootResource(users_repo, sounds_repo, annotations_repo))
api.add_route('/users', UsersResource())
api.add_route(USER_URI_TEMPLATE, UserResource())
api.add_route('/sounds', SoundsResource())
api.add_route(SOUND_URI_TEMPLATE, SoundResource())
