from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from unittest.mock import patch

from .helpers import RequiresLoginTestMixin, ManySourcesTestCaseBase
from ...models import ECCServer, DataRouter, DataSource
from ...views.pages import easy_setup


class StatusTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/status'


class ChooseConfigTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/choose_config'

    def test_no_login(self, *args, **kwargs):
        super().test_no_login(rev_args=(1,))


class ExperimentSettingsTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/experiment_settings'


class EasySetupTestCase(TestCase):
    def setUp(self):
        self.num_cobos = 10
        self.one_ecc_server = True
        self.first_cobo_ecc_ip = '123.456.789.100'
        self.first_cobo_data_router_ip = '123.456.800.100'
        self.mutant_is_present = True
        self.mutant_ecc_ip = '100.200.300.400'
        self.mutant_data_router_ip = '500.600.700.800'

    def run_easy_setup(self):
        easy_setup(
            num_cobos=self.num_cobos,
            one_ecc_server=self.one_ecc_server,
            first_cobo_ecc_ip=self.first_cobo_ecc_ip,
            first_cobo_data_router_ip=self.first_cobo_data_router_ip,
            mutant_is_present=self.mutant_is_present,
            mutant_ecc_ip=self.mutant_ecc_ip,
            mutant_data_router_ip=self.mutant_data_router_ip,
        )

    def check_all_eccs_present(self):
        ecc_count = ECCServer.objects.count()
        if self.one_ecc_server:
            self.assertEqual(ecc_count, 1)
        else:
            if self.mutant_is_present:
                self.assertEqual(ecc_count, self.num_cobos + 1)
            else:
                self.assertEqual(ecc_count, self.num_cobos)

    def check_all_data_routers_present(self):
        data_router_count = DataRouter.objects.count()
        if self.mutant_is_present:
            self.assertEqual(data_router_count, self.num_cobos + 1)
        else:
            self.assertEqual(data_router_count, self.num_cobos)

    def check_all_data_sources_present(self):
        data_source_count = DataSource.objects.count()
        if self.mutant_is_present:
            self.assertEqual(data_source_count, self.num_cobos + 1)
        else:
            self.assertEqual(data_source_count, self.num_cobos)

    def check_ip_addresses(self, objects, first_ip):
        first_ip_end = int(first_ip.split('.')[-1])

        for i, obj in enumerate(objects):
            last_part = int(str(obj.ip_address).split('.')[-1])
            self.assertEqual(last_part, first_ip_end + i)

    def check_ecc_servers(self):
        if self.one_ecc_server:
            self.check_ip_addresses(ECCServer.objects.all().order_by('ip_address'),
                                    self.first_cobo_ecc_ip)
        else:
            cobos = DataSource.objects.filter(name__contains='CoBo').select_related('ecc_server')
            cobo_eccs = [ds.ecc_server for ds in cobos]
            self.check_ip_addresses(cobo_eccs, self.first_cobo_ecc_ip)

            if self.mutant_is_present:
                mutant_ecc = DataSource.objects.get(name__icontains='mutant').ecc_server
                self.assertEqual(mutant_ecc.ip_address, self.mutant_ecc_ip)

    def check_data_routers(self):
        cobos = DataSource.objects.filter(name__contains='CoBo').select_related('data_router')
        cobo_routers = [ds.data_router for ds in cobos]
        self.check_ip_addresses(cobo_routers, self.first_cobo_data_router_ip)
        for r in cobo_routers:
            self.assertEqual(r.connection_type, DataRouter.TCP)

        if self.mutant_is_present:
            mutant_router = DataSource.objects.get(name__icontains='mutant').data_router
            self.assertEqual(mutant_router.ip_address, self.mutant_data_router_ip)
            self.assertEqual(mutant_router.connection_type, DataRouter.FDT)

    def check_data_sources(self):
        cobos = DataSource.objects.filter(name__contains='CoBo')
        for cobo in cobos:
            self.assertRegex(cobo.name, r'CoBo\[(\d)\]')
            self.assertIsNotNone(cobo.ecc_server)
            self.assertIsNotNone(cobo.data_router)

        if self.mutant_is_present:
            mutant = DataSource.objects.get(name__icontains='mutant')
            self.assertRegex(mutant.name, 'Mutant\[master\]')
            self.assertIsNotNone(mutant.ecc_server)
            self.assertIsNotNone(mutant.data_router)

    def easy_setup_test_impl(self):
        self.run_easy_setup()
        self.check_all_eccs_present()
        self.check_all_data_routers_present()
        self.check_all_data_sources_present()
        self.check_ecc_servers()
        self.check_data_routers()
        self.check_data_sources()

    def test_one_ecc_no_mutant(self):
        self.one_ecc_server = True
        self.mutant_is_present = False
        self.easy_setup_test_impl()

    def test_one_ecc_with_mutant(self):
        self.one_ecc_server = True
        self.mutant_is_present = True
        self.easy_setup_test_impl()

    def test_many_ecc_no_mutant(self):
        self.one_ecc_server = False
        self.mutant_is_present = False
        self.easy_setup_test_impl()

    def test_many_ecc_with_mutant(self):
        self.one_ecc_server = False
        self.mutant_is_present = True
        self.easy_setup_test_impl()


@patch('attpcdaq.daq.views.pages.WorkerInterface')
class LogViewerTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        self.view_name = 'daq/show_log'

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.456.789.1',
        )
        self.data_router = DataRouter.objects.create(
            name='DataRouter',
            ip_address='123.456.789.0',
        )
        self.user = User.objects.create(
            username='test',
            password='test1234',
        )

    def test_no_login(self, *args, **kwargs):
        super().test_no_login(rev_args=('ecc', 0))

    def _log_test_impl(self, mock_worker_interface, target):
        self.client.force_login(self.user)
        fake_log = "Test data"

        wi = mock_worker_interface.return_value
        wi_as_context_mgr = wi.__enter__.return_value
        wi_as_context_mgr.tail_file.return_value = fake_log

        if isinstance(target, ECCServer):
            url = reverse('daq/show_log', args=('ecc', target.pk))
        elif isinstance(target, DataRouter):
            url = reverse('daq/show_log', args=('data_router', target.pk))
        else:
            raise ValueError('Invalid target class')

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(resp.context['log_content'], fake_log)
        mock_worker_interface.assert_called_once_with(target.ip_address)
        wi_as_context_mgr.tail_file.assert_called_once_with(target.log_path)

    def test_ecc_log(self, mock_worker_interface):
        self._log_test_impl(mock_worker_interface, self.ecc)

    def test_data_router_log(self, mock_worker_interface):
        self._log_test_impl(mock_worker_interface, self.data_router)