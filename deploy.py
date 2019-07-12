import time
import boto3
import os
from io import BytesIO
from zipfile import ZipFile
import glob
import sys
import shutil
import json
import requests
import http
import urllib
import argparse


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
    def __init__(self, path):
        super().__init__()
        self.environment_name = path
        self.path = path

    def fulfilled(self):
        raise AlwaysUpdateException()

    def fulfill(self):
        create_venv = f'python3 -m venv {self.environment_name} --without-pip'
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


class BaseRole(Requirement):
    def __init__(self):
        super().__init__()
        self.client = boto3.client('iam')
        self.role_name = None
        self.policy_document = None

    def _fetch_role(self):
        resp = self.client.get_role(RoleName=self.role_name)
        return resp

    def fulfill(self):
        self.client.create_role(
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


class ApiGatewayProxyRole(BaseRole):
    def __init__(self):
        super().__init__()
        self.role_name = 'ApiGatewayProxyRole'
        self.policy_name = 'LambdaInvokeFunction'
        self.policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "apigateway.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                },
            ]
        }

        self.role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "lambda:InvokeFunction",
                    "Resource": "*"
                }
            ]
        }

    def fulfill(self):
        super().fulfill()
        self.client.put_role_policy(
            RoleName=self.role_name,
            PolicyName=self.policy_name,
            PolicyDocument=json.dumps(self.role_policy_document)
        )


class LambdaExecutionRole(BaseRole):
    def __init__(self):
        super().__init__()
        self.role_name = 'LambdaBasicExecution'
        self.policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }


class LambdaApi(Requirement):
    def __init__(
            self,
            function_name,
            packaged_app,
            execution_role,
            db,
            function_module_name='main',
            entry_point_name='lambda_handler'):

        super().__init__(packaged_app, execution_role, db)
        self.entry_point_name = entry_point_name
        self.function_module_name = function_module_name
        self.db = db
        self.function_name = function_name
        self.execution_role = execution_role
        self.packaged_app = packaged_app
        self.client = boto3.client('lambda')

    def _fetch_function(self):
        return self.client.get_function(FunctionName=self.function_name)

    def fulfilled(self):
        raise AlwaysUpdateException()

    def _environment_variables(self):
        return {
            'connection_string': db.data()['connection_string']
        }

    @retry(tries=10, delay=2)
    def _create_function(self, role_arn, zip_data):
        self.client.create_function(
            FunctionName=self.function_name,
            Runtime='python3.6',
            Role=role_arn,
            Handler=f'{self.function_module_name}.{self.entry_point_name}',
            Code={
                'ZipFile': zip_data
            },
            Environment={
                'Variables': self._environment_variables()
            }
        )

    def fulfill(self):
        zip_data = self.packaged_app.data()['zipfile'].read()
        try:
            self.client.get_function(FunctionName=self.function_name)
            self.client.update_function_code(
                FunctionName=self.function_name,
                ZipFile=zip_data
            )
            self.client.update_function_configuration(
                FunctionName=self.function_name,
                Environment={
                    'Variables': self._environment_variables()
                }
            )
            print('updated function')
        except self.client.exceptions.ResourceNotFoundException:
            role_arn = self.execution_role.data()['role_arn']
            self._create_function(role_arn, zip_data)
            print('created function')

    @retry(tries=100, delay=10)
    def data(self):
        function_arn = self._fetch_function()['Configuration']['FunctionArn']
        return {
            'function_arn': function_arn,
            'function_name': self.function_name
        }


class ApiGateway(Requirement):
    def __init__(self, name, description, version, lambda_function):
        super().__init__(lambda_function)
        self.version = version
        self.description = description
        self.name = name
        self.client = boto3.client('apigateway')
        self.lambda_function = lambda_function

    def _fetch_api(self):
        resp = self.client.get_rest_apis()
        api = next(filter(lambda x: x['name'] == self.name, resp['items']))
        return api

    def _root_resource_id(self):
        api_id = self._fetch_api()['id']
        resources = self.client.get_resources(restApiId=api_id)
        root_resource = \
            next(filter(lambda item: item['path'] == '/', resources['items']))
        root_resource_id = root_resource['id']
        return api_id, root_resource_id

    def fulfilled(self):
        try:
            self._fetch_api()
            return True
        except StopIteration:
            return False

    @retry(tries=100, delay=10)
    def data(self):
        api_id, root_resource_id = self._root_resource_id()
        return {
            'api_id': api_id,
            'root_resource_id': root_resource_id,
            'lambda_function_name': self.lambda_function.function_name
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
        data = self.api_gateway.data()
        return {
            'resource_id': resource['id'],
            'api_id': data['api_id'],
            'root_resource_id': data['root_resource_id'],
            'lambda_function_name': data['lambda_function_name']
        }


class BaseApiResourceMethod(Requirement):
    def __init__(self, resource, resource_name):
        super().__init__(resource)
        self.resource_name = resource_name
        self.resource = resource
        self.client = boto3.client('apigateway')

    def fulfill(self):
        data = self.resource.data()
        self.client.put_method(
            restApiId=data['api_id'],
            resourceId=data[self.resource_name],
            httpMethod='ANY',
            authorizationType='NONE')

    def _fetch_method(self):
        data = self.resource.data()
        return self.client.get_method(
            restApiId=data['api_id'],
            resourceId=data[self.resource_name],
            httpMethod='ANY')

    def fulfilled(self):
        try:
            return self._fetch_method()
        except:
            return False

    @retry(tries=100, delay=10)
    def data(self):
        data = self.resource.data()
        return data


class RootResourceMethod(BaseApiResourceMethod):
    def __init__(self, api_gateway):
        super().__init__(api_gateway, 'root_resource_id')


class ProxyResourceMethod(BaseApiResourceMethod):
    def __init__(self, proxy_resource):
        super().__init__(proxy_resource, 'resource_id')


class BaseApiIntegration(Requirement):
    def __init__(self, region, api_resource_method, proxy_role, resource_name):
        super().__init__(api_resource_method, proxy_role)
        self.resource_name = resource_name
        self.proxy_role = proxy_role
        self.client = boto3.client('apigateway')
        self.lambda_client = boto3.client('lambda')
        self.api_resource_method = api_resource_method
        self.region = region
        self.uri_template = \
            'arn:aws:apigateway:{aws-region}:lambda:path/{api-version}/functions/arn:aws:lambda:{aws-region}:{aws-acct-id}:function:{lambda-function-name}/invocations'

    def fulfill(self):
        data = self.api_resource_method.data()
        # TODO: There's some hard-coded stuff that should be factored out
        uri = self.uri_template.format(**{
            'aws-region': self.region,
            'api-version': self.lambda_client.meta.service_model.api_version,
            'lambda-function-name': data['lambda_function_name'],
            'aws-acct-id': boto3.client('sts').get_caller_identity()['Account']
        })
        role_arn = self.proxy_role.data()['role_arn']
        self.client.put_integration(
            restApiId=data['api_id'],
            resourceId=data[self.resource_name],
            httpMethod='ANY',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=uri,
            credentials=role_arn)

    def _get_integration(self):
        data = self.api_resource_method.data()
        return self.client.get_integration(
            restApiId=data['api_id'],
            resourceId=data[self.resource_name],
            httpMethod='ANY')

    def fulfilled(self):
        try:
            return self._get_integration()
        except:
            return False

    @retry(tries=100, delay=10)
    def data(self):
        data = self.api_resource_method.data()
        return data


class RootResourceInegration(BaseApiIntegration):
    def __init__(self, region, api_resource_methd, proxy_role):
        super().__init__(
            region, api_resource_methd, proxy_role, 'root_resource_id')


class ProxyResourceIntegration(BaseApiIntegration):
    def __init__(self, region, api_resource_methd, proxy_role):
        super().__init__(
            region, api_resource_methd, proxy_role, 'resource_id')


class Deployment(Requirement):
    def __init__(self, region, root_integration, proxy_integration):
        super().__init__(root_integration, proxy_integration)
        self.proxy_integration = proxy_integration
        self.root_integration = root_integration
        self.client = boto3.client('apigateway')
        self.stage_name = 'test'
        self.region = region

    def _get_deployment(self):
        data = self.proxy_integration.data()
        deployments = self.client.get_deployments(
            restApiId=data['api_id']
        )
        return deployments['items'][0]

    def fulfilled(self):
        try:
            return self._get_deployment()
        except IndexError:
            return False

    def fulfill(self):
        data = self.proxy_integration.data()
        self.client.create_deployment(
            restApiId=data['api_id'],
            stageName=self.stage_name
        )

    @retry(tries=100, delay=10)
    def data(self):
        deployment = self._get_deployment()
        data = self.proxy_integration.data()
        api_id = data['api_id']
        uri = \
            f'https://{api_id}.execute-api.{self.region}.amazonaws.com/{self.stage_name}/'
        return {
            'deployment_id': deployment['id'],
            'api_id': data['api_id'],
            'resource_id': data['resource_id'],
            'lambda_function_name': data['lambda_function_name'],
            'uri': uri
        }


class DatabaseWhitelist(Requirement):
    def __init__(self):
        super().__init__()

    def fulfill(self):
        pass

    def fulfilled(self):
        pass

    @retry(tries=100, delay=10)
    def data(self):
        pass


class DatabaseAdmin(Requirement):
    def __init__(self):
        super().__init__()

    def fulfilled(self):
        pass

    def fulfill(self):
        pass

    @retry(tries=100, delay=10)
    def data(self):
        pass


class Database(Requirement):
    def __init__(
            self,
            project,
            username,
            api_key,
            cluster_name,
            instance_size,
            db_user_name,
            db_user_password):

        super().__init__()
        self.db_user_password = db_user_password
        self.db_user_name = db_user_name
        self.instance_size = instance_size
        self.cluster_name = cluster_name
        self.api_key = api_key
        self.username = username
        self.project = project
        self.base_url = 'https://cloud.mongodb.com/api/atlas/v1.0/'

    def _get_project_id(self):
        resp = requests.get(
            url=os.path.join(self.base_url, f'groups'),
            auth=requests.auth.HTTPDigestAuth(self.username, self.api_key)
        )
        return next(filter(
            lambda x: x['name'] == self.project, resp.json()['results']))['id']

    def _get_cluster(self):
        project_id = self._get_project_id()
        url = os.path.join(
            self.base_url, f'groups/{project_id}/clusters/{self.cluster_name}')
        resp = requests.get(
            url=url,
            auth=requests.auth.HTTPDigestAuth(self.username, self.api_key))
        resp.raise_for_status()
        return resp

    def fulfilled(self):
        try:
            self._get_cluster()
            return True
        except Exception:
            return False

    # TODO: This should be three separate dependencies
    def fulfill(self):
        # create the cluster
        project_id = self._get_project_id()
        resp = requests.post(
            url=os.path.join(self.base_url, f'groups/{project_id}/clusters'),
            json={
                'name': self.cluster_name,
                'providerSettings': {
                    'instanceSizeName': self.instance_size,
                    'providerName': 'TENANT',
                    'backingProviderName': 'AWS',
                    'regionName': 'US_EAST_1'
                }
            },
            auth=requests.auth.HTTPDigestAuth(self.username, self.api_key)
        )
        print(f'Cluster creation response {resp}')
        resp.raise_for_status()

        # create the whitelist
        resp = requests.post(
            url=os.path.join(self.base_url, f'groups/{project_id}/whitelist'),
            json=[
                {
                    'cidrBlock': '0.0.0.0/0',

                }
            ],
            auth=requests.auth.HTTPDigestAuth(self.username, self.api_key)
        )
        print(f'Whitelist creation response {resp}')
        if resp.status_code not in (http.client.CREATED, http.client.CONFLICT):
            resp.raise_for_status()

        # create db user
        resp = requests.post(
            url=os.path.join(self.base_url, f'groups/{project_id}/databaseUsers'),
            json={
                'databaseName': 'admin',
                'groupId': project_id,
                'roles': [
                    {
                        'databaseName': 'admin',
                        'roleName': 'atlasAdmin'
                    }
                ],
                'username': self.db_user_name,
                'password': self.db_user_password
            },
            auth=requests.auth.HTTPDigestAuth(self.username, self.api_key)
        )
        print(f'User creation response {resp}')
        if resp.status_code not in (http.client.CREATED, http.client.CONFLICT):
            resp.raise_for_status()

    @retry(tries=100, delay=10)
    def data(self):
        cluster_data = self._get_cluster().json()
        parsed = urllib.parse.urlparse(cluster_data['mongoURIWithOptions'])
        netloc = f'{self.db_user_name}:{self.db_user_password}@{parsed.netloc}'
        parsed = parsed._replace(netloc=netloc)
        connection_string = urllib.parse.urlunparse(parsed)
        return {
            'connection_string': connection_string
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--aws-region',
        default=boto3.session.Session().region_name)
    parser.add_argument(
        '--aws-vpc-id',
        default=boto3.client('ec2').describe_vpcs()['Vpcs'][0]['VpcId']
    )
    parser.add_argument(
        '--atlas-api-key',
        required=True)
    parser.add_argument(
        '--atlas-username',
        required=True)
    parser.add_argument(
        '--mongodb-cluster-name',
        required=True
    )
    parser.add_argument(
        '--atlas-cluster-size',
        default='M2'
    )
    parser.add_argument(
        '--db-user-name',
        required=True
    )
    parser.add_argument(
        '--db-user-password',
        required=True
    )
    parser.add_argument(
        '--lambda-function-module-name',
        default='main'
    )
    parser.add_argument(
        '--lambda-function-entry-point',
        default='lambda_handler'
    )
    args = parser.parse_args()

    # database
    db = Database(
        project='Project 0',
        username=args.atlas_username,
        api_key=args.atlas_api_key,
        cluster_name=args.mongodb_cluster_name,
        instance_size=args.atlas_cluster_size,
        db_user_name=args.db_user_name,
        db_user_password=args.db_user_password)

    # application code
    packaged_app = PackagedPythonApp('app')

    # lambda
    execution_role = LambdaExecutionRole()
    lambda_api = LambdaApi(
        'api',
        packaged_app,
        execution_role,
        db,
        args.lambda_function_module_name,
        args.lambda_function_entry_point)

    # api gateway
    api = ApiGateway(
        'cochlea_api',
        'gateway to cochlea annotation api',
        '1.0',
        lambda_api)
    proxy_resource = ApiProxyResource(api)
    proxy_role = ApiGatewayProxyRole()

    # method = ApiResourceMethod(proxy_resource)
    # integration = ApiIntegration(args.aws_region, method, proxy_role)

    root_method = RootResourceMethod(api)
    proxy_method = ProxyResourceMethod(proxy_resource)

    root_integration = RootResourceInegration(
        args.aws_region, root_method, proxy_role)
    proxy_integration = ProxyResourceIntegration(
        args.aws_region, proxy_method, proxy_role)

    deployment = Deployment(
        args.aws_region, root_integration, proxy_integration)
    deployment()

    # test deployment
    data = deployment.data()
    uri = data['uri']
    print(uri)

    resp = requests.get(uri)
    print(resp.status_code)
    print(resp.json())

    user_data = {
        'user_name': 'John',
        'password': 'password',
        'user_type': 'human',
        'email': 'john.vinyard@gmail.com',
        'about_me': 'Up and coming tennis star'
    }

    resp = requests.post(os.path.join(uri, 'users'), json=user_data)
    print(resp)

    user_uri = resp.headers['location']
    resp = requests.get(os.path.join(uri, user_uri[1:]), auth=('John', 'password'))
    print(resp)
    print(resp.json())