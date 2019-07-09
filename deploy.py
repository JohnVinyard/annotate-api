import time
import boto3
import os
from io import BytesIO
from zipfile import ZipFile
import glob
import sys
import shutil
import json
import botocore

LINUX_IMAGE = 'ami-04169656fea786776'
REGION = 'us-west-1'


class AlwaysUpdateException(Exception):
    pass


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def ok(msg):
        print(Colors.OKBLUE + msg + Colors.ENDC)

    @staticmethod
    def success(msg):
        print(Colors.OKGREEN + msg + Colors.ENDC)

    @staticmethod
    def bad(msg):
        print(Colors.FAIL + msg + Colors.ENDC)

    @staticmethod
    def format(msg, code):
        return code + msg + Colors.ENDC


def retry(tries, delay):
    def decorator(f):
        def x(*args, **kwargs):
            for i in range(tries):
                try:
                    return f(*args, **kwargs)
                except:
                    instance = args[0]
                    cls = instance.__class__.__name__
                    func_name = f.__name__
                    Colors.bad(
                        'try {i} of {tries} failed for {cls}.{func_name}()'
                            .format(**locals()))
                    if i == tries - 1:
                        raise
                    else:
                        time.sleep(delay)

        return x

    return decorator


class Requirement(object):
    def __init__(self, *dependencies):
        super(Requirement, self).__init__()
        self.dependencies = dependencies

    def fulfilled(self):
        raise NotImplementedError()

    def fulfill(self):
        raise NotImplementedError()

    def data(self):
        raise NotImplementedError()

    def _check_n(self, n, delay=1):
        for _ in range(n):
            if self.fulfilled():
                return True
            time.sleep(delay)
        return False

    def __call__(self):

        for dependency in self.dependencies:
            # TODO: remove this None check. this is just for development
            if dependency is not None:
                dependency()

        try:
            if self.fulfilled():
                Colors.ok('Requirement {cls} already fulfilled!'.format(
                    cls=self.__class__.__name__))
                return
        except AlwaysUpdateException:
            # this requirement should always re-run
            pass

        self.fulfill()

        try:
            if not self._check_n(10, delay=1):
                msg = 'Requirement {cls} not fulfilled after operation'
                raise RuntimeError(
                    (Colors.FAIL + msg + Colors.ENDC)
                        .format(cls=self.__class__.__name__))
        except AlwaysUpdateException:
            pass

        Colors.success(
            'Requirement {cls} fulfilled after operation'
                .format(cls=self.__class__.__name__))


class PackagedPythonApp(Requirement):
    def __init__(self, path, environment_name):
        super().__init__()
        self.environment_name = environment_name
        self.path = path

    def fulfilled(self):
        raise AlwaysUpdateException()

    def fulfill(self):
        create_venv = f'python3 -m venv {self.environment_name}'
        activate_venv = f'. {self.environment_name}/bin/activate'
        update_pip = 'curl https://bootstrap.pypa.io/get-pip.py | python'
        install = f'pip3 install -r {self.environment_name}/requirements.txt'
        command = \
            f'{create_venv} && {activate_venv} && {update_pip} && {install}'
        os.system(command)

    def data(self):
        bio = BytesIO()
        with ZipFile(bio, mode='w') as zipfile:

            # copy the contents of the site-packages directory
            major = sys.version_info.major
            minor = sys.version_info.minor
            site_packages = os.path.join(
                self.path, f'lib/python{major}.{minor}/site-packages')
            for dirpath, dirnames, filenames in os.walk(site_packages):
                for filename in filenames:
                    fullpath = os.path.join(dirpath, filename)
                    archive_path = os.path.relpath(fullpath, site_packages)
                    zipfile.write(fullpath, arcname=archive_path)

            # copy all python files
            for filename in os.listdir(self.path):
                filepath = os.path.join(self.path, filename)
                if glob.fnmatch.fnmatch(filename, '*.py'):
                    zipfile.write(filepath, arcname=filename)

        bio.seek(0)

        shutil.rmtree(os.path.join(self.path, 'bin'))
        shutil.rmtree(os.path.join(self.path, 'include'))
        shutil.rmtree(os.path.join(self.path, 'lib'))
        os.unlink(os.path.join(self.path, 'lib64'))
        os.remove(os.path.join(self.path, 'pyvenv.cfg'))
        return {'zipfile': bio}


class LambdaExecutionRole(Requirement):
    def __init__(self):
        super().__init__()
        self.client = boto3.client('iam')
        self.role_name = 'LambdaBasicExecution'
        self.policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': '',
                    'Effect': 'Allow',
                    'Principal': {
                        'Service': 'lambda.amazonaws.com'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }

    def _fetch_role(self):
        resp = self.client.get_role(RoleName=self.role_name)
        return resp

    def fulfill(self):
        resp = self.client.create_role(
            RoleName=self.role_name,
            AssumeRolePolicyDocument=json.dumps(self.policy_document)
        )

    def fulfilled(self):
        try:
            return self._fetch_role()
        except:
            return False

    @retry(tries=100, delay=1)
    def data(self):
        role = self._fetch_role()
        return {'role_arn': role['Role']['Arn']}


class LambdaApi(Requirement):
    def __init__(self, function_name, packaged_app, execution_role):
        super().__init__(packaged_app, execution_role)
        self.function_name = function_name
        self.execution_role = execution_role
        self.packaged_app = packaged_app
        self.client = boto3.client('lambda')

    def _fetch_function(self):
        return self.client.get_function(FunctionName=self.function_name)

    def fulfilled(self):
        try:
            return self._fetch_function()
        except:
            return False

    @retry(tries=10, delay=2)
    def _create_function(self, role_arn, zip_data):
        self.client.create_function(
            FunctionName=self.function_name,
            Runtime='python3.6',
            Role=role_arn,
            Handler='main.lambda_handler',
            Code={
                'ZipFile': zip_data
            }
        )

    def fulfill(self):
        role_arn = self.execution_role.data()['role_arn']
        zip_data = self.packaged_app.data()['zipfile'].read()
        self._create_function(role_arn, zip_data)

    @retry(tries=100, delay=10)
    def data(self):
        function_arn = self._fetch_function()['Configuration']['FunctionArn']
        return {'function_arn': function_arn}


class ApiGateway(Requirement):
    def __init__(self, name, description, version, lambda_function):
        super().__init__(lambda_function)
        self.version = version
        self.description = description
        self.name = name
        self.client = boto3.client('apigateway')

    def _fetch_api(self):
        resp = self.client.get_rest_apis()
        api = next(filter(lambda x: x['name'] == self.name, resp['items']))
        return api

    def fulfilled(self):
        try:
            self._fetch_api()
            return True
        except StopIteration:
            return False

    @retry(tries=100, delay=10)
    def data(self):
        api_id = self._fetch_api()['id']
        resources = self.client.get_resources(restApiId=api_id)
        root_resource = \
            next(filter(lambda item: item['path'] == '/', resources['items']))
        root_resource_id = root_resource['id']
        return {
            'api_id': self._fetch_api()['id'],
            'root_resource_id': root_resource_id
        }

    def fulfill(self):
        self.client.create_rest_api(
            name=self.name,
            description=self.description,
            version=self.version,
            endpointConfiguration={
                'types': ['EDGE']
            }
        )


class ApiProxyResource(Requirement):
    def __init__(self, api_gateway):
        super().__init__(api_gateway)
        self.client = boto3.client('apigateway')
        self.api_gateway = api_gateway

    def _fetch_resource(self):
        data = self.api_gateway.data()
        resources = self.client.get_resources(restApiId=data['api_id'])
        return next(filter(
            lambda item: item['path'] == '/{proxy+}', resources['items']))

    def fulfilled(self):
        try:
            return self._fetch_resource()
        except StopIteration:
            return False

    def fulfill(self):
        data = self.api_gateway.data()
        self.client.create_resource(
            restApiId=data['api_id'],
            parentId=data['root_resource_id'],
            pathPart='{proxy+}'
        )

    @retry(tries=100, delay=10)
    def data(self):
        resource = self._fetch_resource()
        return {
            'resource_id': resource['id'],
            'api_id': self.api_gateway.data()['api_id']
        }


class ApiResourceMethod(Requirement):
    def __init__(self, proxy_resource):
        super().__init__(proxy_resource)
        self.proxy_resource = proxy_resource
        self.client = boto3.client('apigateway')

    def fulfill(self):
        data = self.proxy_resource.data()
        self.client.put_method(
            restApiId=data['api_id'],
            resourceId=data['resource_id'],
            httpMethod='ANY',
            authorizationType='NONE')

    def _fetch_method(self):
        data = self.proxy_resource.data()
        return self.client.get_method(
            restApiId=data['api_id'],
            resourceId=data['resource_id'],
            httpMethod='ANY')

    def fulfilled(self):
        try:
            return self._fetch_method()
        except:
            return False

    @retry(tries=100, delay=10)
    def data(self):
        data = self.proxy_resource.data()
        return data


class ApiIntegration(Requirement):
    def __init__(self, api_resource_method):
        super().__init__(api_resource_method)
        self.api_resource_method = api_resource_method
        self.uri_template = \
            'arn:aws:apigateway:{aws-region}:lambda:path/{api-version}/functions/arn:aws:lambda:{aws-region}:{aws-acct-id}:function:{lambda-function-name}/invocations'.format(**uri_data)

    def fulfill(self):
        pass

    def fulfilled(self):
        pass

    @retry(tries=100, delay=10)
    def data(self):
        pass

# https://github.com/boto/boto3/issues/572
# https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html

if __name__ == '__main__':
    packaged_app = PackagedPythonApp('fakeapp', 'fakeapp')
    execution_role = LambdaExecutionRole()
    lambda_api = LambdaApi('api', packaged_app, execution_role)
    api = ApiGateway(
        'cochlea_api',
        'gateway to cochlea annotation api',
        '1.0',
        lambda_api)
    proxy_resource = ApiProxyResource(api)
    method = ApiResourceMethod(proxy_resource)
    method()
