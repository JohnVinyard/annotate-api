import falcon
import logging
from data import users_repo, sounds_repo, annotations_repo, NoCriteria
from model import User, ContextualValue
from httphelper import decode_auth_header, SessionMiddleware
from customjson import JSONHandler
import urllib
from errors import DuplicateUserException, PermissionsError


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
        req.context['user'] = user
    except StopIteration:
        raise falcon.HTTPUnauthorized()


class RootResource(object):
    def __init__(self, user_repo, sound_repo, annotation_repo):
        self.annotation_repo = annotation_repo
        self.sound_repo = sound_repo
        self.user_repo = user_repo

    def on_get(self, req, resp):
        resp.media = {
            'totalSounds': len(self.sound_repo),
            'totalAnnotations': len(self.annotation_repo),
            'totalUsers': len(self.user_repo)
        }
        resp.status = falcon.HTTP_200

    def on_delete(self, req, resp):
        self.user_repo.delete_all()
        self.sound_repo.delete_all()
        self.annotation_repo.delete_all()
        resp.status = falcon.HTTP_NO_CONTENT


class UsersResource(object):
    def __init__(self, user_repo):
        self.user_repo = user_repo

    def on_post(self, req, resp):
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
    def on_get(self, req, resp):
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

        session = req.context['session']
        query_result = session.filter(
            query,
            page_size,
            page_number,
            User.date_created.descending())

        actor = req.context['user']
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


class UserResource(object):
    def __init__(self, user_repo):
        self.user_repo = user_repo

    @falcon.before(basic_auth)
    def on_get(self, req, resp, user_id):
        """
        Get an individual user
        """
        actor = req.context['user']
        session = req.context['session']

        query = (User.id == user_id) & (User.deleted == False)
        try:
            user_data = next(session.filter(query, page_size=1, page_number=0))
        except StopIteration:
            raise falcon.HTTPNotFound()

        user_view = user_data.view(actor)
        resp.media = user_view
        resp.status = falcon.HTTP_OK

    @falcon.before(basic_auth)
    def on_head(self, req, resp, user_id):
        session = req.context['session']
        count = session.count(User.id == user_id)
        if count == 1:
            resp.status = falcon.HTTP_NO_CONTENT
        else:
            raise falcon.HTTPNotFound()

    @falcon.before(basic_auth)
    def on_delete(self, req, resp, user_id):
        """
        Delete an individual user
        """

        # TODO: Business rules that make data needed to evaluate the rule
        # explicit, so that only that data need be fetched.  In this case,
        # the rule about who may delete whom only requires user id, which we
        # already have in this scenario.
        actor = req.context['user']
        session = req.context['session']
        try:
            to_delete = next(session.filter(User.id == user_id))
        except StopIteration:
            raise falcon.HTTPNotFound()

        try:
            to_delete.deleted = ContextualValue(actor, True)
        except PermissionsError:
            raise falcon.HTTPForbidden()

    @falcon.before(basic_auth)
    def on_patch(self, req, resp, user_id):
        """
        Update a user
        """
        raise NotImplementedError()


extra_handlers = falcon.media.Handlers({
    'application/json': JSONHandler(),
})

api = application = falcon.API(middleware=[
    SessionMiddleware(users_repo)
])
api.resp_options.media_handlers = extra_handlers

# public endpoints
api.add_route('/', RootResource(users_repo, sounds_repo, annotations_repo))
api.add_route('/users', UsersResource(users_repo))
api.add_route('/users/{user_id}', UserResource(users_repo))
