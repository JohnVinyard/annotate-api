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
import urllib.parse
import argparse
from deploygraph import Requirement, AlwaysUpdateException, retry
from urllib.parse import urlparse
import botocore


class PackagedPythonApp(Requirement):
    def __init__(self, path):
        super().__init__()
        self.environment_name = path
        self.path = path
        self.zipfile = None

    def fulfilled(self):
        return self.zipfile is not None

    def fulfill(self):
        create_venv = f'python3 -m venv {self.environment_name} --without-pip'
        activate_venv = f'. {self.environment_name}/bin/activate'
        update_pip = 'curl https://bootstrap.pypa.io/get-pip.py | python'
        install = f'pip3 install -r {self.environment_name}/requirements.txt'
        command = \
            f'{create_venv} && {activate_venv} && {update_pip} && {install}'
        os.system(command)
        self.zipfile = self._build_zipfile()

    def _build_zipfile(self):
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
        self.zipfile = bio
        return self.zipfile

    def data(self):
        self.zipfile.seek(0)
        return {'zipfile': self.zipfile}


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
                Handler=f'{self.function_module_name}.{self.entry_point_name}',
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
                'types': ['REGIONAL']
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


class RootResourceIntegration(BaseApiIntegration):
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
        deployment = deployments['items'][0]
        return deployment

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
        host = f'{api_id}.execute-api.{self.region}.amazonaws.com'
        uri = \
            f'https://{host}/{self.stage_name}/'
        host = urlparse(uri).netloc
        return {
            'deployment_id': deployment['id'],
            'api_id': data['api_id'],
            'resource_id': data['resource_id'],
            'lambda_function_name': data['lambda_function_name'],
            'uri': uri,
            'api_gateway_host': host
        }


class DomainName(Requirement):
    def __init__(self, domain_name, certificate_arn, types=['REGIONAL']):
        super().__init__()
        self.types = types
        self.certificate_arn = certificate_arn
        self.domain_name = domain_name
        self.client = boto3.client('apigateway')

    def _get_domain_name(self):
        return self.client.get_domain_name(domainName=self.domain_name)

    def fulfilled(self):
        try:
            self._get_domain_name()
            return True
        except botocore.exceptions.ClientError:
            return False

    def fulfill(self):
        self.client.create_domain_name(
            domainName=self.domain_name,
            regionalCertificateArn=self.certificate_arn,
            endpointConfiguration={
                'types': self.types
            })

    def data(self):
        domain_name = self._get_domain_name()
        return {
            'zone_id': domain_name['regionalHostedZoneId'],
            'domain_name': domain_name['regionalDomainName']
        }


class BasePathMapping(Requirement):
    def __init__(self, rest_api, domain_name):
        super().__init__(rest_api, domain_name)
        self.rest_api = rest_api
        self.domain_name = domain_name
        self.client = boto3.client('apigateway')
        self.base_path = '(none)'
        self.stage = 'test'

    def fulfill(self):
        api_id = self.rest_api.data()['api_id']
        self.client.create_base_path_mapping(
            domainName=self.domain_name.domain_name,
            basePath=self.base_path,
            restApiId=api_id,
            stage=self.stage)

    def _get_mapping(self):
        return self.client.get_base_path_mapping(
            domainName=self.domain_name.domain_name,
            basePath=self.base_path)

    def fulfilled(self):
        try:
            self._get_mapping()
            return True
        except botocore.exceptions.ClientError:
            return False

    def data(self):
        path_mapping = self._get_mapping()
        return {
            'base_path': path_mapping['basePath'],
            'rest_api_id': path_mapping['restApiId'],
            'stage': path_mapping['stage']
        }


class Alias(Requirement):
    def __init__(self, domain_name, deployment, path_mapping):
        super().__init__(domain_name, deployment, path_mapping)
        self.deployment = deployment
        self.domain_name = domain_name
        self.client = boto3.client('route53')

    def _alias_template(self, domain_name, hostname, zone_id):
        return {
            'Action': 'UPSERT',
            'ResourceRecordSet': {
                'Name': domain_name,
                'Type': 'A',
                'AliasTarget': {
                    'HostedZoneId': zone_id,
                    'EvaluateTargetHealth': False,
                    'DNSName': hostname
                },
            }
        }

    def _iter_zones(self):
        zones = self.client.list_hosted_zones()['HostedZones']
        zones = filter(lambda z: z['Name'] == 'cochlea.xyz.', zones)
        yield from zones

    def _fulfilled_predicate(self, record):
        if record['Name'] != self.domain_name.domain_name + '.':
            return False

        if record['Type'] != 'A':
            return False

        if 'AliasTarget' not in record:
            return False

        return True

    def fulfilled(self):
        for zone in self._iter_zones():
            resp = self.client.list_resource_record_sets(
                HostedZoneId=zone['Id'])
            records = resp['ResourceRecordSets']
            if not any(self._fulfilled_predicate(record) for record in records):
                return False

        return True

    def fulfill(self):
        domain_name_data = self.domain_name.data()
        api_gateway_zone = domain_name_data['zone_id']
        api_domain_name = domain_name_data['domain_name']

        for zone in self._iter_zones():
            cochlea_hosted_zone = zone['Id']
            self.client.change_resource_record_sets(
                HostedZoneId=cochlea_hosted_zone,
                ChangeBatch={
                    'Comment': 'Automatic DNS Update',
                    'Changes': [
                        self._alias_template(
                            self.domain_name.domain_name,
                            api_domain_name,
                            api_gateway_zone
                        )
                    ]
                }
            )

    @retry(tries=100, delay=20)
    def data(self):
        uri = f'https://{self.domain_name.domain_name}'
        resp = requests.get(uri)
        resp.raise_for_status()
        return {
            'uri': uri,
            'resp': resp.json()
        }


class BaseAtlasRequirement(Requirement):
    def __init__(self, username, api_key, project_name, *reqs):
        super().__init__(*reqs)
        self.project_name = project_name
        self.api_key = api_key
        self.username = username
        self.base_url = 'https://cloud.mongodb.com/api/atlas/v1.0/'
        self._project_id = None

    @property
    def project_id(self):
        if self._project_id is not None:
            return self._project_id

        resp = requests.get(
            url=os.path.join(self.base_url, f'groups'),
            auth=self.auth
        )
        self._project_id = next(filter(
            lambda x: x['name'] == self.project_name,
            resp.json()['results']))['id']
        return self._project_id

    @property
    def auth(self):
        return requests.auth.HTTPDigestAuth(self.username, self.api_key)


class DatabaseWhitelist(BaseAtlasRequirement):
    def __init__(self, username, api_key, project_name):
        super().__init__(username, api_key, project_name)
        self.cidr_block = '0.0.0.0/0'

    def fulfill(self):
        uri = os.path.join(self.base_url, f'groups/{self.project_id}/whitelist')
        resp = requests.post(
            url=uri,
            json=[
                {
                    'cidrBlock': self.cidr_block,
                }
            ],
            auth=self.auth)
        resp.raise_for_status()

    def _fetch(self):
        cidr_block = urllib.parse.quote_plus(self.cidr_block)
        uri = os.path.join(
            self.base_url, f'groups/{self.project_id}/whitelist/{cidr_block}')
        resp = requests.get(uri, auth=self.auth)
        return resp

    def fulfilled(self):
        resp = self._fetch()
        return resp.status_code == http.client.OK

    @retry(tries=100, delay=10)
    def data(self):
        return self._fetch().json()


class DatabaseAdmin(BaseAtlasRequirement):
    def __init__(
            self,
            username,
            api_key,
            project_name,
            db_user_name,
            db_user_password):
        super().__init__(username, api_key, project_name)
        self.db_user_password = db_user_password
        self.db_user_name = db_user_name

    def _fetch(self):
        uri = os.path.join(
            self.base_url,
            f'groups/{self.project_id}/databaseUsers/admin/{self.db_user_name}')
        resp = requests.get(uri, auth=self.auth)
        return resp

    def fulfilled(self):
        resp = self._fetch()
        return resp.status_code == http.client.OK

    def fulfill(self):
        uri = os.path.join(
            self.base_url, f'groups/{self.project_id}/databaseUsers')
        resp = requests.post(
            url=uri,
            json={
                'databaseName': 'admin',
                'groupId': self.project_id,
                'roles': [
                    {
                        'databaseName': 'admin',
                        'roleName': 'atlasAdmin'
                    }
                ],
                'username': self.db_user_name,
                'password': self.db_user_password
            },
            auth=self.auth)
        resp.raise_for_status()

    @retry(tries=100, delay=10)
    def data(self):
        return {
            'db_user_name': self.db_user_name,
            'db_user_password': self.db_user_password
        }


class Database(BaseAtlasRequirement):
    def __init__(
            self,
            username,
            api_key,
            project,
            cluster_name,
            instance_size,
            whitelist,
            db_user):

        super().__init__(username, api_key, project, whitelist, db_user)
        self.instance_size = instance_size
        self.cluster_name = cluster_name
        self.db_user = db_user

    def _get_cluster(self):
        url = os.path.join(
            self.base_url,
            f'groups/{self.project_id}/clusters/{self.cluster_name}')
        resp = requests.get(url=url, auth=self.auth)
        resp.raise_for_status()
        return resp

    def fulfilled(self):
        try:
            self._get_cluster()
            return True
        except Exception:
            return False

    def fulfill(self):
        # create the cluster
        resp = requests.post(
            url=os.path.join(self.base_url,
                             f'groups/{self.project_id}/clusters'),
            json={
                'name': self.cluster_name,
                'providerSettings': {
                    'instanceSizeName': self.instance_size,
                    'providerName': 'TENANT',
                    'backingProviderName': 'AWS',
                    'regionName': 'US_EAST_1'
                }
            },
            auth=self.auth)
        print(f'Cluster creation response {resp}')
        resp.raise_for_status()

    @retry(tries=100, delay=10)
    def data(self):
        cluster_data = self._get_cluster().json()
        parsed = urllib.parse.urlparse(cluster_data['mongoURIWithOptions'])

        user_data = self.db_user.data()
        db_user_name = user_data['db_user_name']
        db_user_password = user_data['db_user_password']

        netloc = f'{db_user_name}:{db_user_password}@{parsed.netloc}'
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
        default=boto3.client('ec2').describe_vpcs()['Vpcs'][0]['VpcId'])
    parser.add_argument(
        '--atlas-api-key',
        required=True)
    parser.add_argument(
        '--atlas-username',
        required=True)
    parser.add_argument(
        '--atlas-project-name',
        default='Project 0')
    parser.add_argument(
        '--mongodb-cluster-name',
        required=True)
    parser.add_argument(
        '--atlas-cluster-size',
        default='M2')
    parser.add_argument(
        '--db-user-name',
        required=True)
    parser.add_argument(
        '--db-user-password',
        required=True)
    parser.add_argument(
        '--lambda-function-module-name',
        default='prod')
    parser.add_argument(
        '--lambda-function-entry-point',
        default='lambda_handler')
    parser.add_argument(
        '--ssl-cert-arn',
        required=True)
    args = parser.parse_args()

    # database
    db_admin = DatabaseAdmin(
        args.atlas_username,
        args.atlas_api_key,
        args.atlas_project_name,
        args.db_user_name,
        args.db_user_password)
    db_whitelist = DatabaseWhitelist(
        args.atlas_username,
        args.atlas_api_key,
        args.atlas_project_name)
    db = Database(
        args.atlas_username,
        args.atlas_api_key,
        args.atlas_project_name,
        cluster_name=args.mongodb_cluster_name,
        instance_size=args.atlas_cluster_size,
        whitelist=db_whitelist,
        db_user=db_admin)

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

    root_method = RootResourceMethod(api)
    proxy_method = ProxyResourceMethod(proxy_resource)

    root_integration = RootResourceIntegration(
        args.aws_region, root_method, proxy_role)
    proxy_integration = ProxyResourceIntegration(
        args.aws_region, proxy_method, proxy_role)

    deployment = Deployment(
        args.aws_region, root_integration, proxy_integration)

    domain_name = DomainName('api.cochlea.xyz', args.ssl_cert_arn)
    path_mapping = BasePathMapping(api, domain_name)
    alias = Alias(domain_name, deployment, path_mapping)
    alias()

    # test deployment
    data = alias.data()
    print(data)

    # uri = data['uri']
    #
    # user_data = {
    #     'user_name': 'John',
    #     'password': 'password',
    #     'user_type': 'human',
    #     'email': 'john.vinyard@gmail.com',
    #     'about_me': 'Up and coming tennis star'
    # }
    #
    # resp = requests.post(os.path.join(uri, 'users'), json=user_data)
    # print(resp)
    #
    # user_uri = resp.headers['location']
    # resp = requests.get(os.path.join(uri, user_uri[1:]),
    #                     auth=('John', 'password'))
    # print(resp)
    # print(resp.json())
