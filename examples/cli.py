import argparse


class DefaultArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(add_help=False)
        self.add_argument(
            '--password',
            required=True,
            help='user password')
        self.add_argument(
            '--metadata-path',
            required=True,
            help='path to dataset on disk')
        self.add_argument(
            '--annotate-api-endpoint',
            required=True,
            help='scheme, hostname and optional port for annotation API')
        self.add_argument(
            '--s3-endpoint',
            required=True,
            help='scheme, hostname and optional port of s3 endpoint')
        self.add_argument(
            '--s3-region',
            required=False,
            default=None)
        self.add_argument(
            '--aws-access-key-id',
            required=False,
            default=None)
        self.add_argument(
            '--aws-secret-access-key',
            required=False,
            default=None)


