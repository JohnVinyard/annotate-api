import falcon
from hyperplane_tree import MultiHyperPlaneTree
import numpy as np
import time
import os


class Index(object):
    def __init__(self, seconds_per_chunk, user_uri):
        super().__init__()
        self.user_uri = user_uri
        self.seconds_per_chunk = seconds_per_chunk
        self.tree = None
        self.reset()
        self.ids = []
        self.offsets = []
        self.current_offset = 0

    def reset(self):
        self.tree = MultiHyperPlaneTree(
            data=np.zeros((0, 3), dtype=np.float32),
            smallest_node=1024,
            n_trees=5)

    def append(self, _id, data):
        self.ids.append(_id)
        self.offsets.append(self.current_offset)
        self.current_offset += len(data)
        self.tree.append(data.astype(np.float32))

    def search(self, query, n_results):

        # get the raw indices from the underlying hyperplane tree along with
        # associated vectors
        indices, vectors = self.tree.search_with_priority_queue(
            query, threshold=0.001, n_results=n_results, return_vectors=True)

        # using the raw indices, find the sound id of each result
        id_indices = np.searchsorted(
            self.offsets, indices, side='right') - 1
        _ids = [self.ids[i] for i in id_indices]

        # find the start offset for each sound id in the result list
        base_offsets = [self.offsets[i] for i in id_indices]

        # find the offset in seconds of each result
        time_offsets = [
            (i - bo) * self.seconds_per_chunk
            for (i, bo) in zip(indices, base_offsets)
            ]

        results = []
        for _id, time_offset, vector in zip(_ids, time_offsets, vectors):
            sound_uri = f'/sounds/{_id}'
            results.append({
                'created_by': self.user_uri,
                'sound': sound_uri,
                'start_seconds': time_offset,
                'duration_seconds': self.seconds_per_chunk,
                'end_seconds': time_offset + self.seconds_per_chunk,
                'point': list(vector.astype(np.float64))
            })

        return results


class CorsMiddleware(object):
    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header(
            'Access-Control-Allow-Methods', 'POST, GET, DELETE, PATCH')
        resp.set_header('Access-Control-Allow-Headers', 'Authorization')


class AuthMiddleware(object):
    def __init__(self, access_key):
        self.access_key = access_key

    def process_resource(self, req, resp, resource, params):
        try:
            handler = getattr(resource, f'on_{req.method.lower()}')
            if handler.anonymous:
                return
        except AttributeError:
            pass

        auth = req.get_header('Authorization')
        if auth != self.access_key:
            raise falcon.HTTPUnauthorized()


def anonymous(f):
    f.anonymous = True
    return f


class Resource(object):
    def __init__(self, index):
        super().__init__()
        self.index = index

    def on_delete(self, req, resp):
        self.index.reset()
        resp.status_code = falcon.HTTP_NO_CONTENT

    @anonymous
    def on_get(self, req, resp):
        try:
            nresults = int(req.params['nresults'])
        except (KeyError, IndexError):
            nresults = 100
        point = [
            req.get_param_as_float('x'),
            req.get_param_as_float('y'),
            req.get_param_as_float('z')
        ]
        query = np.array(point, dtype=np.float32)
        start = time.time()
        results = self.index.search(query, n_results=nresults)
        resp.media = {
            'items': results,
            'total_count': len(results),
            'time': time.time() - start
        }


class CreateResource(object):
    def __init__(self, index):
        super().__init__()
        self.index = index

    def on_put(self, req, resp, sound_id):
        data = np.fromstring(
            req.bounded_stream.read(),
            dtype=np.float32).reshape((-1, 3))
        self.index.append(sound_id, data)
        resp.status_code = falcon.HTTP_CREATED


class Application(falcon.API):
    def __init__(self, index, access_key):
        super().__init__(
            middleware=[CorsMiddleware(), AuthMiddleware(access_key)])
        self.add_route('/', Resource(index))
        self.add_route('/{sound_id}', CreateResource(index))


access_key = os.environ['ACCESS_KEY']
user_uri = os.environ['USER_URI']
seconds_per_chunk = 0.743038541824
api = application = Application(Index(seconds_per_chunk, user_uri), access_key)
