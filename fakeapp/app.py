from helper import do_something
import falcon


class TestResource(object):
    def __init__(self, mongo_client):
        super().__init__()
        self.mongo_client = mongo_client
        self.database = self.mongo_client.notesdb
        self.collection = self.database.notes

    def on_put(self, req, resp, doc_id):
        do_something()
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', 'POST, GET')
        doc = dict(req.media)
        doc.update(_id=doc_id)
        self.collection.replace_one({'_id': doc_id}, doc, upsert=True)
        resp.media = doc

    def on_get(self, req, resp, doc_id):
        do_something()
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', 'POST, GET')
        doc = self.collection.find_one({'_id': doc_id})

        if doc is None:
            resp.media = {'error': 'not found'}
            raise falcon.HTTPNotFound()

        resp.media = doc


class Application(falcon.API):
    def __init__(self, mongo_client):
        super().__init__()
        self.add_route('/test/{doc_id}', TestResource(mongo_client))
        self.add_route('/test/blah/{doc_id}', TestResource(mongo_client))
