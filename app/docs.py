from app import Application
from string import Formatter


# TODO: list URL parameters from route
# TODO: list query string parameters
# TODO: list example POST bodies
# TODO: list example response bodies
# TODO: list possible responses
def generate_docs():
    formatter = Formatter()
    methods = set(['on_get', 'on_post', 'on_head', 'on_patch', 'on_delete'])

    app = Application(None, None, None)

    for route, resource in app._doc_routes:
        print('=================================')
        url_params = list(filter(
            lambda x: x, (x[1] for x in formatter.parse(route))))
        print(route)
        print(url_params)

        for item in dir(resource):
            if item not in methods:
                continue

            method = item.split('_')[-1].upper()
            print(f'\t{method}')
            func = getattr(resource, item).__doc__
            if func:
                print(f'\t{func}')


if __name__ == '__main__':
    generate_docs()
