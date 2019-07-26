from app import Application
from string import Formatter
import yaml
import json

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
    def data(self):
        try:
            return list(yaml.load_all(self.func.__doc__))[0]
        except AttributeError:
            return {}


# TODO: list URL parameters from route
# TODO: list query string parameters
# TODO: list example POST bodies
# TODO: list example response bodies
# TODO: list possible responses
def generate_docs(content_type):
    methods = set(['on_get', 'on_post', 'on_head', 'on_patch', 'on_delete'])

    app = Application(None, None, None)

    for route, resource in app._doc_routes:

        for item in dir(resource):
            if item not in methods:
                continue
            func = getattr(resource, item)
            rm = ResourceMethod(route, func)
            print('========================================')
            print(rm.verb, rm.path)


            docs = rm.data
            print('description: ', docs.get('description', None))

            print('Url Params')
            for param, desc in docs.get('url_params', {}).items():
                print(param, desc)

            print('Query Params')
            for param in docs.get('query_params', {}).items():
                print(param)

            print('Responses')
            for response in docs.get('responses', []):
                print(response['status_code'])
                print(f'\t{response.get("description")}')
                method_name = response.get('example', {}).get('python', '')
                try:
                    model_example = getattr(resource, method_name)(content_type)
                    model = json.loads(model_example)
                    pretty = json.dumps(model, indent=4)
                    print(f'\t{pretty}')
                except (AttributeError, NotImplementedError):
                    pass


            # try:
            #     model_example_method_name = \
            #         rm.data['example_response']['python']
            #     model_example = getattr(
            #         resource, model_example_method_name)(content_type)
            #     print('EXAMPLE RESPONSE', model_example)
            # except (KeyError, TypeError) as e:
            #     print('ERROR', e)
            #     continue


if __name__ == '__main__':
    generate_docs('application/json')
