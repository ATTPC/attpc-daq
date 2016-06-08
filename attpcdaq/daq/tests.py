from django.test import TestCase
from .models import ECCServer, DataRouter, DataSource


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
    @classmethod
    def setUpTestData(cls):
        eccs = [ECCServer.objects.create(name='ECC{}'.format(i),
                                         ip_address='192.168.41.{}'.format(i+60),
                                         port=8083,
                                         ) for i in range(10)]
