import argparse
from deploygraph import Requirement, AlwaysUpdateException
from deploygraph.aws import \
    PublicInternetSecurityGroup, Box, AnacondaServer, SupervisordHelper, DNS, \
    TLS, NamedStringIO


class IndexBox(Box):
    def __init__(self, linux_image, security_group):
        super().__init__(
            'embedding-index-3d', linux_image, 't2.small', security_group)


class IndexServer(AnacondaServer):
    def __init__(self, box, port, config, domain_name):
        super().__init__(box, None, 'embedding-index-3d')
        self.domain_name = domain_name
        self.config = config
        self.port = port
        self.box = box
        self.supervisord = SupervisordHelper(
            'embedding-index-3d',
            'examples',
            'remote/')

    def connection(self):
        return self.box.connection()

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
            'PublicDnsName': data['PublicDnsName'],
        }

    def _inner_fulfill(self, connection):
        connection.run('mkdir -p remote/')
        connection.put('examples/spatial_index_api.py', 'remote/')
        connection.put('examples/hyperplane_tree.py', 'remote/')
        connection.put('examples/log.py', 'remote/')

        # nginx setup
        connection.sudo('wget http://nginx.org/keys/nginx_signing.key')
        connection.sudo('apt-key add nginx_signing.key')

        connection.append_line(
            'deb http://nginx.org/packages/ubuntu xenial nginx',
            '/etc/apt/sources.list')
        connection.append_line(
            'deb-src http://nginx.org/packages/ubuntu xenial nginx',
            '/etc/apt/sources.list')

        self.apt_install(connection, 'nginx')
        with open('examples/nginx.conf', 'r') as f:
            content = f.read()
            with_replacements = content.format(
                server_name=self.domain_name,
                upstream=f'localhost:{self.port}')
            sio = NamedStringIO('nginx.conf', with_replacements)
            connection.sudo_put(sio, '/etc/nginx')

        self.supervisord.prepare(connection, variables=self.config)
        with self._conda_env(connection):
            connection.run(
                'pip install falcon gunicorn supervisor')
            self.supervisord.start(connection)

        # nginx start
        connection.sudo('nginx -t -c /etc/nginx/nginx.conf')
        connection.sudo('service nginx start')
        connection.sudo('service nginx reload')


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

    def connection(self):
        return self.server.connection()

    def fulfill(self):
        connection = self.server.connection()
        data = self.server.data()
        connection.put('examples/spatial_index_api.py', 'remote/')
        connection.put('examples/hyperplane_tree.py', 'remote/')
        connection.put('examples/log.py', 'remote/')
        self.supervisord.copy_config(connection, variables=data['config'])
        with self._conda_env(connection):
            self.supervisord.restart(connection)
        connection.sudo('service nginx reload')


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
        index_box, args.internal_port, supervisor_config_vars, domain)
    index_app = IndexApp(index_server)
    dns = DNS(index_app, domain, add_www=False)
    tls = TLS(dns, args.tls_email, add_www=False)
    tls()
