from .helper import do_something
import falcon


class TestResource(object):
    def on_get(self, req, resp):
        do_something()
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', 'POST, GET')
        resp.media = {
            'STATUS': 'GET WORKED',
            'QUERY': req.get_param('query')
        }

    def on_post(self, req, resp):
        do_something()
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', 'POST, GET')
        resp.media = req.media


class Application(falcon.API):
    def __init__(self):
        super().__init__()
        self.add_route('/test', TestResource())
        self.add_route('/test/blah', TestResource())