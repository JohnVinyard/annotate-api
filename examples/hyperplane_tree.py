from __future__ import division, print_function
from scipy.spatial.distance import cdist
import heapq
import numpy as np
import random


def batch_unit_norm(b, epsilon=1e-8):
    """
    Give all vectors unit norm along the last dimension
    """
    return b / np.linalg.norm(b, axis=-1, keepdims=True) + epsilon


def unit_vectors(n_examples, n_dims):
    """
    Create n_examples of synthetic data on the unit
    sphere in n_dims
    """
    dense = np.random.normal(0, 1, (n_examples, n_dims))
    return batch_unit_norm(dense)


def hyperplanes(n_planes, n_dims):
    """
    Return n_planes plane vectors, which describe
    hyperplanes in n_dims space that are perpendicular
    to lines running from the origin to each point
    """
    return unit_vectors(n_planes, n_dims)


def random_projection(plane_vectors, data, pack=True, binarize=True):
    """
    Return bit strings for a batch of vectors, with each
    bit representing which side of each hyperplane the point
    falls on
    """

    flattened = data.reshape((len(data), plane_vectors.shape[-1]))
    x = np.dot(plane_vectors, flattened.T).T
    if not binarize:
        return x

    output = np.zeros((len(data), len(plane_vectors)), dtype=np.uint8)
    output[np.where(x > 0)] = 1

    if pack:
        output = np.packbits(output, axis=-1).view(np.uint64)

    return output


class HyperPlaneNode(object):
    def __init__(self, shape, data=None):
        super(HyperPlaneNode, self).__init__()
        self.dimensions = shape

        # choose one plane, at random, for this node
        self.plane = hyperplanes(1, shape)

        self.data = \
            data if data is not None else np.zeros((0,), dtype=np.uint64)

        self.left = None
        self.right = None

    def __eq__(self, other):
        return \
            np.all(self.data == other.data) \
            and np.all(self.plane == other.plane) \
            and self.left == other.left \
            and self.right == other.right

    def __len__(self):
        return len(self.data)

    @property
    def is_leaf(self):
        return self.left is None and self.right is None

    @property
    def children(self):
        return self.left, self.right

    def distance(self, query):
        dist = random_projection(
            self.plane, query, pack=False, binarize=False).reshape(-1)
        return dist

    def route(self, data, indices=None):
        if indices is None:
            indices = self.data
        data = data[indices]

        dist = self.distance(data)
        left_indices = indices[dist > 0]
        right_indices = indices[dist <= 0]
        return left_indices, right_indices

    def create_children(self, data):
        left_indices, right_indices = self.route(data)
        self.left = HyperPlaneNode(self.dimensions, left_indices)
        self.right = HyperPlaneNode(self.dimensions, right_indices)


class MultiHyperPlaneTree(object):
    def __init__(self, data, smallest_node, n_trees=10):
        super(MultiHyperPlaneTree, self).__init__()
        self.dimensions = data.shape[1]
        self.data = data
        indices = np.arange(0, len(data), dtype=np.uint64)
        self.smallest_node = smallest_node

        self.roots = \
            [HyperPlaneNode(self.dimensions, indices) for _ in range(n_trees)]
        build_queue = list(self.roots)

        while build_queue:
            node = build_queue.pop()

            if len(node) <= smallest_node:
                continue
            else:
                node.create_children(self.data)
                build_queue.extend(node.children)

    def __setstate__(self, state):
        mhpt = MultiHyperPlaneTree(
            state['data'], state['smallest_node'], state['n_trees'])
        graph = state['graph']

    def __getstate__(self):
        def node_state(node):
            return node.plane, node.data

        graph = dict()
        queue = [root for root in self.roots]
        while queue:
            next_node = queue.pop()
            item = []
            left = next_node.left
            right = next_node.right

            if left:
                queue.append(left)
                item.append(node_state(left))
            else:
                item.append(None)

            if right:
                queue.append(right)
                item.append(node_state(right))
            else:
                item.append(None)

            # TODO: What should the key be here?
            graph[next_node] = item

        roots = [node_state(r) for r in self.roots]
        return {
            # TODO: roots should just be the node keys
            'roots': roots,
            'graph': graph,
            'smallest_node': self.smallest_node,
            'n_trees': len(roots),
            'data': self.data
        }

    def __eq__(self, other):
        return all(s == r for (s, r) in zip(self.roots, other.roots))

    def __len__(self):
        return len(self.data)

    def append(self, chunk):

        # compute the new set of indices that need to be added to the tree
        new_indices = np.arange(0, len(chunk), dtype=np.uint64) + len(self.data)

        # ensure that the chunk of vectors are added to the available vector
        # data
        self.data = np.concatenate([self.data, chunk])

        # initialize the search queue with all root nodes
        search_queue = list([(r, new_indices) for r in self.roots])

        while search_queue:

            # add the indices to the node's data
            node, indices = search_queue.pop()

            node.data = np.concatenate([node.data, indices])

            if len(node) <= self.smallest_node:
                # this will be a leaf node.  There's no need to further route
                # the data or add further child nodes (for now)
                continue

            if node.is_leaf:
                # we'll be creating new child nodes.  At this point, we need
                # to route *all* of the data currently owned by this node
                node.create_children(self.data)
            else:
                # this node already has children, so it's only necessary to
                # route new indices
                left_indices, right_indices = node.route(self.data, indices)
                search_queue.append((node.left, left_indices))
                search_queue.append((node.right, right_indices))

    def search_with_priority_queue(
            self,
            query,
            n_results,
            threshold,
            return_distances=False,
            return_vectors=False):

        query = query.reshape(1, self.dimensions)

        indices = set()

        # this is kinda arbitrary.
        # How do I pick this intelligently?
        to_consider = n_results * 100

        # put the root nodes in the queue

        # KLUDGE: Assign arbitrary values to each root node, taking on values
        # larger than the greatest possible cosine distance to ensure that
        # each root node is processed first

        # KLUDGE: Add a random number in the second position to ensure that
        # hyperplane nodes are never compared in the event of identical
        # distances
        heap = [
            (-((i + 1) * 10), random.random(), root)
            for i, root in enumerate(self.roots)
        ]

        # traverse the tree, finding candidate indices
        while heap and (len(indices) < to_consider):
            current_distance, _, current_node = heapq.heappop(heap)

            if current_node.is_leaf:
                indices.update(current_node.data)
                continue

            dist = current_node.distance(query)
            abs_dist = np.abs(dist)
            below_threshold = abs_dist < threshold

            # KLUDGE: Add a random number in the second position to ensure that
            # hyperplane nodes are never compared in the event of identical
            # distances
            if dist > 0 or below_threshold:
                heapq.heappush(
                    heap, (-abs_dist, random.random(), current_node.left))

            if dist <= 0 or below_threshold:
                heapq.heappush(
                    heap, (-abs_dist, random.random(), current_node.right))

        # perform a brute-force distance search over a subset of the data
        indices = np.array(list(indices), dtype=np.uint64)
        data = self.data[indices]
        dist = cdist(query, data, metric='cosine').squeeze()
        partitioned_indices = np.argpartition(dist, n_results)[:n_results]
        sorted_indices = np.argsort(dist[partitioned_indices])
        srt_indices = partitioned_indices[sorted_indices]

        final_indices = indices[srt_indices]

        if return_vectors:
            return final_indices, self.data[final_indices]
        elif return_distances:
            return final_indices, dist[sorted_indices]
        else:
            return final_indices


import pickle
import sys

if __name__ == '__main__':
    sys.setrecursionlimit(100)

    tree = MultiHyperPlaneTree(
        data=np.zeros((0, 3), dtype=np.float32),
        smallest_node=1024,
        n_trees=5)

    while True:
        samples = unit_vectors(1000, 3)
        tree.append(samples)
        s = pickle.dumps(tree)
        recovered = pickle.loads(s)
        print(tree.data.shape, tree == recovered)
