import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from botocore import UNSIGNED


class ObjectStorageClient(object):
    def __init__(self, endpoint, region, access_key, secret, bucket):
        self.bucket = bucket
        self.secret = secret
        self.access_key = access_key
        self.region = region
        self.endpoint = endpoint

        config = Config()
        config.signature_version = UNSIGNED

        self.s3 = boto3.client(
            service_name='s3',
            endpoint_url=self.endpoint,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret)

        self.url_generator = boto3.client('s3', config=config)

    def ensure_bucket_exists(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.s3.create_bucket(
                ACL='public-read',
                Bucket=self.bucket)
            self.s3.put_bucket_cors(
                Bucket=self.bucket,
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

    def put_object(self, key, body, content_type):
        self.s3.put_object(
            Bucket=self.bucket,
            Body=body,
            Key=key,
            ACL='public-read',
            ContentType=content_type)
        return self.url_generator.generate_presigned_url(
            'get_object',
            ExpiresIn=0,
            Params={'Bucket': self.bucket, 'Key': key})
