from app import Application
from string import Formatter
import yaml
import json
from io import StringIO
from http import client


def extract_yaml(has_doc):
    return list(yaml.load_all(has_doc.__doc__))[0]


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
            return extract_yaml(self.func)
        except AttributeError:
            return {}


def markdown_heading(text, level):
    return f'{"#" * level} {text}\n'


def markdown_parameter_table(params):
    s = '|Name|Description|\n'
    s += '|---|---|\n'
    for k, v in params.items():
        s += f'|`{k}`|{v}|\n'
    return s


def generate_docs(app_name, content_type):
    methods = set(['on_get', 'on_post', 'on_head', 'on_patch', 'on_delete'])

    sio = StringIO()

    sio.write(markdown_heading(app_name, 1))

    app = Application(None, None, None)
    app_info = extract_yaml(app.__class__)

    print(app_info['description'], file=sio)

    for route, resource in app._doc_routes:

        for item in dir(resource):
            if item not in methods:
                continue
            func = getattr(resource, item)
            rm = ResourceMethod(route, func)

            sio.write(markdown_heading(f'`{rm.verb} {rm.path}`', 2))

            docs = rm.data
            print(docs.get('description', ''), file=sio)

            url_params = docs.get('url_params', {})
            if url_params:
                print(markdown_heading('URL Parameters', 3), file=sio)
                print(markdown_parameter_table(url_params), file=sio)

            query_params = docs.get('query_params', {})
            if query_params:
                print(markdown_heading('Query Parameters', 3), file=sio)
                print(markdown_parameter_table(query_params), file=sio)

            request_body = \
                docs.get('example_request_body', {}).get('python', '')
            try:
                model_example = getattr(resource, request_body)()
                print(markdown_heading('Example Request Body', 3), file=sio)
                pretty = json.dumps(model_example, indent=4)
                print(f'```json\n{pretty}\n```', file=sio)
            except (AttributeError, NotImplementedError):
                pass

            print(markdown_heading('Responses', 3), file=sio)
            for response in docs.get('responses', []):
                status_code = int(response['status_code'])
                status = client.responses[status_code]
                print(markdown_heading(f'`{status_code} {status}`', 4), file=sio)
                print(response.get('description'), file=sio)
                method_name = response.get('example', {}).get('python', '')
                try:
                    model_example = getattr(resource, method_name)(content_type)
                    model = json.loads(model_example)
                    pretty = json.dumps(model, indent=4)
                    print(markdown_heading('Example Response', 5), file=sio)
                    print(f'```json\n{pretty}\n```', file=sio)
                except (AttributeError, NotImplementedError):
                    pass
    sio.seek(0)
    print(sio.read())


if __name__ == '__main__':
    generate_docs('Cochlea', 'application/json')
