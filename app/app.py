import falcon
from data import users_repo, sounds_repo, annotations_repo
from model import UserCreationData


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
        create_data = UserCreationData(*req.media)
        users_repo.add_user(create_data)
        resp.set_header('Location', '/users/{id}'.format(id=create_data.id))
        resp.status = falcon.HTTP_CREATED

    def on_get(self, req, resp):
        """
        List users
        """
        raise NotImplementedError()


class UserResource(object):
    def __init__(self, user_repo):
        self.user_repo = user_repo

    def on_get(self, req, resp, user_id):
        """
        Get an individual user
        """
        user_data = users_repo.get_user(user_id)
        resp.media = user_data.__dict__
        resp.status = falcon.HTTP_OK

    def on_delete(self, req, resp, user_id):
        """
        Delete an individual user
        """
        raise NotImplementedError()

    def on_patch(self, req, resp, user_id):
        """
        Update a user
        """
        raise NotImplementedError()


api = application = falcon.API()

# public endpoints
api.add_route('/', RootResource(users_repo, sounds_repo, annotations_repo))
api.add_route('/users', UsersResource(users_repo))
api.add_route('/users/{user_id}', UserResource(users_repo))
