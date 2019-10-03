from deploygraph import Requirement, AlwaysUpdateException, retry
import boto3
from botocore.exceptions import ClientError
import os
from botocore.config import Config
from botocore import UNSIGNED
import json
import argparse
import re
import requests


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
        return filename
        # return f'/static/{filename}'

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


class StaticResourceWithReplacements(StaticResource):
    def __init__(self, bucket, local_path, content_type, replacements):
        super().__init__(bucket, local_path, content_type)
        self.replacements = replacements

    def _get_file_contents(self):
        content = super()._get_file_contents().decode()
        for pattern, replacement in self.replacements.items():
            content = re.sub(pattern, replacement, content)
        return content


class SettingsResource(StaticResource):
    def __init__(self, bucket, local_path, content_type, settings):
        super().__init__(bucket, local_path, content_type)
        self.settings = settings
        self.bucket = bucket

    def _get_file_contents(self):
        data = json.dumps(self.settings, indent=4)
        return f'var cochleaAppSettings = {data};'.encode()


class StaticApp(Requirement):
    def __init__(self, bucket, cors, *static_resources):
        super().__init__(bucket, cors, *static_resources)
        self.static_resources = static_resources
        self.bucket = bucket

    def fulfill(self):
        pass

    def fulfilled(self):
        return True

    def data(self):
        bucket_data = self.bucket.data()
        return {
            'uris': [sr.data()['uri'] for sr in self.static_resources],
            'bucket_endpoint': bucket_data['endpoint'],
            'bucket_name': bucket_data['bucket']
        }


class CloudFrontDistribution(Requirement):
    # This is always the hosted zone for cloudfront, apparently
    # https://stackoverflow.com/questions/39665214/get-hosted-zone-for-cloudfront-distribution
    HOSTED_ZONE = 'Z2FDTNDATAQYW2'

    def __init__(self, static_app, ssl_cert_arn):
        super().__init__(static_app)
        self.ssl_cert_arn = ssl_cert_arn
        self.hostname = 'exampleapp.cochlea.xyz'
        self.client = boto3.client('cloudfront')
        self.static_app = static_app
        self.description = 'static site'

    def _get_distribution(self):
        try:
            items = self.client.list_distributions()['DistributionList'][
                'Items']
        except KeyError:
            return None

        for item in items:
            if self.hostname in item['Aliases']['Items']:
                return item
        return None

    def fulfill(self):
        bucket_name = self.static_app.data()['bucket_name']
        domain = f'{bucket_name}.s3.amazonaws.com'

        self.client.create_distribution(
            DistributionConfig=dict(
                ViewerCertificate=dict(
                    ACMCertificateArn=self.ssl_cert_arn,
                    SSLSupportMethod='sni-only'
                ),
                CustomErrorResponses=dict(
                    Quantity=1,
                    Items=[
                        dict(
                            ErrorCode=404,
                            ResponsePagePath='/index.html',
                            ResponseCode='200',
                            ErrorCachingMinTTL=1000
                        )
                    ]
                ),
                CallerReference='firstOne',
                Aliases=dict(Quantity=1,
                             Items=[self.hostname]),
                DefaultRootObject='index.html',
                Comment=self.description,
                Enabled=True,
                Origins=dict(
                    Quantity=1,
                    Items=[dict(
                        Id='1',
                        DomainName=domain,
                        S3OriginConfig=dict(
                            OriginAccessIdentity=''))
                    ]),
                DefaultCacheBehavior=dict(
                    TargetOriginId='1',
                    ViewerProtocolPolicy='redirect-to-https',
                    TrustedSigners=dict(Quantity=0,
                                        Enabled=False),
                    ForwardedValues=dict(
                        Cookies={'Forward': 'all'},
                        Headers=dict(Quantity=0),
                        QueryString=False,
                        QueryStringCacheKeys=dict(
                            Quantity=0),
                    ),
                    MinTTL=1000)
            )
        )

    def fulfilled(self):
        dist = self._get_distribution()
        print(dist)
        return dist is not None

    @retry(tries=100, delay=10)
    def data(self):
        data = self._get_distribution()
        return {
            'domain_name': data['DomainName'],
            'zone': self.HOSTED_ZONE
        }


class Alias(Requirement):
    def __init__(self, domain_name, cloud_formation_dist):
        super().__init__(cloud_formation_dist)
        self.domain_name = domain_name
        self.cloud_formation_dist = cloud_formation_dist
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
        if record['Name'] != self.domain_name + '.':
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
        distribution_data = self.cloud_formation_dist.data()

        for zone in self._iter_zones():
            cochlea_hosted_zone = zone['Id']
            self.client.change_resource_record_sets(
                HostedZoneId=cochlea_hosted_zone,
                ChangeBatch={
                    'Comment': 'Automatic DNS Update',
                    'Changes': [
                        self._alias_template(
                            self.domain_name,
                            distribution_data['domain_name'],
                            distribution_data['zone']
                        )
                    ]
                }
            )

    @retry(tries=100, delay=10)
    def data(self):
        dist_data = self.cloud_formation_dist.data()
        uri = f'https://{self.domain_name}'
        resp = requests.get(uri)
        resp.raise_for_status()
        return {
            'uri': uri,
            'resp': resp.json(),
            'cloud_formation_uri': dist_data['domain_name']
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--api-host',
        required=True)
    parser.add_argument(
        '--remote-search-host',
        required=True)
    parser.add_argument(
        '--ssl-cert-arn',
        required=True)
    args = parser.parse_args()

    bucket = S3Bucket('cochlea-static-app', 'us-west-1')
    cors = CorsConfig(bucket)
    html = StaticResourceWithReplacements(
        bucket, 'nginx/static/index.html', 'text/html', {'/static': ''})
    css = StaticResource(bucket, 'nginx/static/style.css', 'text/css')

    javascript1 = StaticResource(
        bucket, 'nginx/static/app.js', 'text/javascript')
    javascript2 = StaticResource(
        bucket, 'nginx/static/app2.js', 'text/javascript')
    svg = StaticResource(
        bucket, 'nginx/static/cochlea.svg', 'image/svg+xml')

    settings = SettingsResource(
        bucket, 'nginx/static/settings.js', 'text/javascript', {
            'remoteSearchHost': args.remote_search_host,
            'apiHost': args.api_host,
            'basePath': ''
        })
    static_app = StaticApp(
        bucket, cors, html, css, javascript1, javascript2, svg, settings)
    distribution = CloudFrontDistribution(static_app, args.ssl_cert_arn)
    alias = Alias('exampleapp.cochlea.xyz', distribution)
    alias()
    print(alias.data())
