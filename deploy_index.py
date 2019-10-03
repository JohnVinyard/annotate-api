import argparse
from deploygraph import Requirement, AlwaysUpdateException
from deploygraph.aws import \
    PublicInternetSecurityGroup, Box, AnacondaServer, SupervisordHelper, DNS, \
    TLS


class IndexBox(Box):
    def __init__(self, linux_image, security_group):
        super().__init__(
            'embedding-index-3d', linux_image, 't2.small', security_group)

# TODO: nginx
class IndexServer(AnacondaServer):
    def __init__(self, box, port, config):
        super().__init__(box, None, 'embedding-index-3d')
        self.config = config
        self.port = port
        self.supervisord = SupervisordHelper(
            'embedding-index-3d',
            'examples',
            'remote/')

    def fulfilled(self):
        """
        Check that the about page returns a 200
        """
        connection = self.box.connection()
        try:
            connection.run(f'httping http://localhost:{self.port}/low_id -c 1')
            return True
        except:
            return False

    def data(self):
        data = self.box.data()
        ip = data['internal_ip']
        return {
            'endpoint': f'http://{ip}:{self.port}',
            'supervisord_helper': self.supervisord,
            'config': self.config,
            'PublicIpAddress': data['PublicIpAddress'],
            'PublicDnsName': data['PublicDnsName']
        }

    def _inner_fulfill(self, connection):
        connection.run('mkdir -p remote/')
        connection.put('examples/spatial_index_api.py', 'remote/')
        connection.put('examples/hyperplane_tree.py', 'remote/')
        connection.put('examples/log.py', 'remote/')
        self.supervisord.prepare(connection, variables=self.config)
        with self._conda_env(connection):
            connection.run(
                'pip install falcon gunicorn supervisor')
            self.supervisord.start(connection)


class IndexApp(Requirement):
    def __init__(self, server):
        super().__init__(server)
        self.server = server

    def fulfilled(self):
        raise AlwaysUpdateException()

    def data(self):
        return self.server.data()

    def _conda_env(self, connection):
        return self.server._conda_env(connection)

    @property
    def port(self):
        return self.server.port

    @property
    def supervisord(self):
        return self.server.supervisord

    def fulfill(self):
        connection = self.server.connection()
        data = self.server.data()
        connection.put('examples/spatial_index_api.py', 'remote/')
        connection.put('examples/hyperplane_tree.py', 'remote/')
        connection.put('examples/log.py', 'remote/')
        self.supervisord.copy_config(connection, variables=data['config'])
        with self._conda_env(connection):
            self.supervisord.restart(connection)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--internal-port',
        default=8888)
    parser.add_argument(
        '--access-key',
        required=True)
    parser.add_argument(
        '--user-uri',
        required=True)
    parser.add_argument(
        '--tls-email',
        required=True)
    args = parser.parse_args()

    domain = 'exampleindex.cochlea.xyz'
    linux_image = 'ami-04169656fea786776'

    supervisor_config_vars = {
        'port': args.internal_port,
        'access_key': args.access_key,
        'user_uri': args.user_uri
    }

    public_internet = PublicInternetSecurityGroup()
    index_box = IndexBox(linux_image, public_internet)
    index_server = IndexServer(
        index_box, args.internal_port, supervisor_config_vars)
    index_app = IndexApp(index_server)
    dns = DNS(index_app, domain)
    tls = TLS(dns, args.tls_email)
    tls()
