import falcon
import base64


def basic_auth(req, resp, resource, params):
    auth = req.get_header('Authorization')
    if auth is None:
        raise falcon.HTTPUnauthorized()

    try:
        username, password = base64.b64decode(
            auth.replace('Basic ', '')).split(':')
    except TypeError:
        raise falcon.HTTPUnauthorized()

        # TODO: How are passwords hashed?
        # TODO: Check for the user against the database
        # password = hashlib.sha256(password).hexdigest()
        # if username != Configuration.admin_username \
        #         or password != Configuration.admin_password:
        #     raise falcon.HTTPForbidden()


class RootResource(object):
    def on_get(self, req, resp):
        resp.media = {
            'totalSounds': 0,
            'totalAnnotations': 0
        }
        resp.status = falcon.HTTP_200


# TODO: Use this for basic auth
# @falcon.before(basic_auth)

api = application = falcon.API()

# public endpoints
api.add_route('/', RootResource())
