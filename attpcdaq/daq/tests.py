from django.test import TestCase
from .models import ECCServer, DataRouter, DataSource, ConfigId


class ECCServerModelTestCase(TestCase):
    def setUp(self):
        self.name = 'ECC0'
        self.ip = '127.0.0.1'
        self.port = '8083'
        self.ecc0 = ECCServer.objects.create(name=self.name, ip_address=self.ip, port=self.port)

    def test_url(self):
        expected = 'http://' + self.ip + ':' + self.port + '/'
        result = self.ecc0.url
        self.assertEqual(expected, result)


class StatusViewTestCase(TestCase):
    def setUp(self):
        self.ecc = ECCServer.objects.create(name='ECC0', ip_address='127.0.0.1', port='8083')
        self.data_router = DataRouter.objects.create(name='dataRouter0', ip_address='127.0.0.1',
                                                     port='46005', type='TCP')
        self.config = ConfigId(describe='desc', prepare='prep', configure='conf', ecc_server=self.ecc)

    def test_template_render(self):
        pass
