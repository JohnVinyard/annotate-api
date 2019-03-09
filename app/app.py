import falcon
from data import users_repo, sounds_repo, annotations_repo
from model import UserCreationData
from httphelper import decode_auth_header
from customjson import JSONWithDateTimeHandler
import urllib
from errors import DuplicateUserException


def basic_auth(req, resp, resource, params):
    auth = req.get_header('Authorization')
    if auth is None:
        raise falcon.HTTPUnauthorized()

    try:
        username, password = decode_auth_header(auth)
    except TypeError:
        raise falcon.HTTPUnauthorized()

    try:
        user = users_repo.authenticate(username, password)
    except ValueError:
        raise falcon.HTTPUnauthorized()

    req.context['user'] = user


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
        create_data = UserCreationData(**req.media)

        try:
            users_repo.add_user(create_data)
        except DuplicateUserException:
            raise falcon.HTTPConflict()

        resp.set_header('Location', '/users/{id}'.format(id=create_data.id))
        resp.status = falcon.HTTP_CREATED

    @falcon.before(basic_auth)
    def on_get(self, req, resp):
        """
        List users
        """
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number') or 0
        user_type = req.get_param('user_type')

        try:
            total_count, users, next_page = self.user_repo.list_users(
                page_size=page_size,
                page_number=page_number,
                user_type=user_type)
        except ValueError:
            raise falcon.HTTPBadRequest()

        users = list(map(lambda x: x.__dict__, users))

        results = {
            'items': users,
            'total_count': total_count
        }

        if next_page is not None:
            query_params = {
                'page_size': page_size,
                'page_number': next_page,
                'user_type': user_type
            }
            query_params = {k: v for k, v in query_params.items() if v}
            results['next'] = '/users?{query}'.format(
                query=urllib.parse.urlencode(query_params))

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
        try:
            user_data = users_repo.get_user(user_id)
            resp.media = user_data.__dict__
            resp.status = falcon.HTTP_OK
        except KeyError:
            raise falcon.HTTPNotFound()

    @falcon.before(basic_auth)
    def on_head(self, req, resp, user_id):
        if self.user_repo.user_exists(user_id):
            resp.status = falcon.HTTP_NO_CONTENT
        else:
            raise falcon.HTTPNotFound()

    @falcon.before(basic_auth)
    def on_delete(self, req, resp, user_id):
        """
        Delete an individual user
        """
        raise NotImplementedError()

    @falcon.before(basic_auth)
    def on_patch(self, req, resp, user_id):
        """
        Update a user
        """
        raise NotImplementedError()


extra_handlers = falcon.media.Handlers({
    'application/json': JSONWithDateTimeHandler(),
})

api = application = falcon.API()
api.resp_options.media_handlers = extra_handlers

# public endpoints
api.add_route('/', RootResource(users_repo, sounds_repo, annotations_repo))
api.add_route('/users', UsersResource(users_repo))
api.add_route('/users/{user_id}', UserResource(users_repo))
