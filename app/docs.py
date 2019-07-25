from app import Application
from string import Formatter
import inspect
import ast


class ResourceMethod(object):
    def __init__(self, path, func):
        super().__init__()
        self.path = path
        self.func = func

    @property
    def url_parameters(self):
        formatter = Formatter()
        return list(filter(
            lambda x: x, (x[1] for x in formatter.parse(self.path))))

    @property
    def verb(self):
        return self.func.__name__.split('_')[-1].upper()

    @property
    def description(self):
        return self.func.__doc__

    @property
    def ast(self):
        source = inspect.getsource(self.func).lstrip()
        print(source)
        tree = ast.parse(source)
        print(tree)


# TODO: list URL parameters from route
# TODO: list query string parameters
# TODO: list example POST bodies
# TODO: list example response bodies
# TODO: list possible responses
def generate_docs():
    methods = set(['on_get', 'on_post', 'on_head', 'on_patch', 'on_delete'])

    app = Application(None, None, None)

    for route, resource in app._doc_routes:

        for item in dir(resource):
            if item not in methods:
                continue
            func = getattr(resource, item)
            rm = ResourceMethod(route, func)
            print('========================================')
            print(rm.verb, rm.path, rm.url_parameters, rm.description)
            print(rm.ast)


if __name__ == '__main__':
    generate_docs()
