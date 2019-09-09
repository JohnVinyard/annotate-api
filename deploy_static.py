from deploy import Requirement, AlwaysUpdateException
import boto3
from botocore.exceptions import ClientError
import os
from botocore.config import Config
from botocore import UNSIGNED
import json
import argparse


class S3Bucket(Requirement):
    def __init__(self, bucket_name, region):
        super(S3Bucket, self).__init__()
        self.region = region
        self.bucket_name = bucket_name
        self.client = boto3.client('s3')

    @property
    def name(self):
        return self.bucket_name

    @property
    def hostname(self):
        return 'https://s3-{region}.amazonaws.com'.format(region=self.region)

    def data(self):
        return {
            'hostname': self.hostname,
            'bucket': self.bucket_name,
            'endpoint': '{hostname}/{bucket}'.format(
                hostname=self.hostname, bucket=self.bucket_name)
        }

    def fulfilled(self):
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False

    def fulfill(self):
        self.client.create_bucket(
            ACL='public-read',
            Bucket=self.bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': self.region
            })


class CorsConfig(Requirement):
    def __init__(self, bucket):
        super(CorsConfig, self).__init__(bucket)
        self.bucket = bucket
        self.client = boto3.client('s3')

    def fulfilled(self):
        try:
            self.client.get_bucket_cors(Bucket=self.bucket.name)
            return True
        except ClientError:
            return False

    def data(self):
        return self.bucket.data()

    def fulfill(self):
        self.client.put_bucket_cors(
            Bucket=self.bucket.name,
            CORSConfiguration={
                'CORSRules': [
                    {
                        'AllowedMethods': ['GET'],
                        'AllowedOrigins': ['*'],
                        'MaxAgeSeconds': 3000
                    }
                ]
            }
        )


class StaticResource(Requirement):
    def __init__(self, bucket, local_path, content_type):
        super().__init__(bucket)
        self.content_type = content_type
        self.local_path = local_path
        self.client = boto3.client('s3')
        self.bucket = bucket

        config = Config()
        config.signature_version = UNSIGNED
        self.url_generator = boto3.client('s3', config=config)

    @property
    def filename(self):
        filename = os.path.split(self.local_path)[-1]
        return f'/static/{filename}'

    def _get_file_contents(self):
        with open(self.local_path, 'rb') as f:
            body = f.read()
        return body

    def fulfill(self):
        self.client.put_object(
            Bucket=self.bucket.bucket_name,
            Body=self._get_file_contents(),
            Key=self.filename,
            ACL='public-read',
            ContentType=self.content_type
        )

    def fulfilled(self):
        raise AlwaysUpdateException()

    def data(self):
        uri = self.url_generator.generate_presigned_url(
            'get_object',
            ExpiresIn=0,
            Params={'Bucket': self.bucket.bucket_name, 'Key': self.filename})
        return {'uri': uri}


class SettingsResource(StaticResource):
    def __init__(self, bucket, local_path, content_type, settings):
        super().__init__(bucket, local_path, content_type)
        self.settings = settings

    def _get_file_contents(self):
        data = json.dumps(self.settings, indent=4)
        return f'var cochleaAppSettings = {data};'.encode()


class StaticApp(Requirement):
    def __init__(self, bucket, cors, *static_resources):
        super().__init__(bucket, cors, *static_resources)
        self.static_resources = static_resources

    def fulfill(self):
        pass

    def fulfilled(self):
        return True

    def data(self):
        return {
            'uris': [sr.data()['uri'] for sr in self.static_resources]
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--api-host',
        required=True)
    parser.add_argument(
        '--remote-search-host',
        required=True)
    args = parser.parse_args()

    bucket = S3Bucket('cochlea-static-app', 'us-west-1')
    cors = CorsConfig(bucket)
    html = StaticResource(bucket, 'nginx/static/index.html', 'text/html')
    css = StaticResource(bucket, 'nginx/static/style.css', 'text/css')
    javascript = StaticResource(
        bucket, 'nginx/static/app.js', 'text/javascript')
    settings = SettingsResource(
        bucket, 'nginx/static/settings.js', 'text/javascript', {
            'remoteSearchHost': args.remote_search_host,
            'apiHost': args.api_host
        })
    static_app = StaticApp(bucket, cors, html, css, javascript, settings)
    static_app()
    print(static_app.data())
