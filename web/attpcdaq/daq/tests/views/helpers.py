from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from ...models import ConfigId, ECCServer, DataRouter, DataSource, Experiment


class RequiresLoginTestMixin(object):
    def setUp(self):
        super().setUp()

    def test_no_login(self, *args, **kwargs):
        request_data = kwargs.get('data')
        reverse_args = kwargs.get('rev_args')
        resp = self.client.get(reverse(self.view_name, args=reverse_args), data=request_data)
        self.assertEqual(resp.status_code, 302)


class NeedsExperimentTestMixin(object):
    def setUp(self):
        super().setUp()

    def test_no_experiment(self, *args, **kwargs):
        self.client.force_login(self.user)
        Experiment.objects.all().update(is_active=False)

        request_data = kwargs.get('data')
        reverse_args = kwargs.get('rev_args')
        resp = self.client.get(reverse(self.view_name, args=reverse_args), data=request_data, follow=True)
        self.assertEqual(resp.redirect_chain[0][1], 302)
        self.assertEqual(resp.redirect_chain[-1][0], reverse('daq/choose_experiment'))


class ManySourcesTestCaseBase(TestCase):
    def setUp(self):
        self.user = User(username='test', password='test1234')
        self.user.save()

        self.experiment = Experiment.objects.create(
            name='Test experiment',
            is_active=True,
        )

        self.ecc_ip_address = '123.45.67.8'
        self.ecc_port = '1234'
        self.data_router_ip_address = '123.456.78.9'
        self.data_router_port = '1111'
        self.selected_config = ConfigId.objects.create(
            describe='describe',
            prepare='prepare',
            configure='configure'
        )

        self.ecc_servers = []
        self.data_routers = []
        self.datasources = []
        for i in range(10):
            ecc = ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address=self.ecc_ip_address,
                port=self.ecc_port,
                experiment=self.experiment,
                selected_config=self.selected_config,
            )
            self.ecc_servers.append(ecc)

            router = DataRouter.objects.create(
                name='DataRouter{}'.format(i),
                ip_address=self.data_router_ip_address,
                port=self.data_router_port,
                experiment=self.experiment,
            )
            self.data_routers.append(router)

            source = DataSource.objects.create(
                name='CoBo[{}]'.format(i),
                ecc_server=ecc,
                data_router=router,
            )
            self.datasources.append(source)
