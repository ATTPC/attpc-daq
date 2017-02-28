from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from unittest.mock import patch

from .helpers import RequiresLoginTestMixin, ManySourcesTestCaseBase
from ...models import ECCServer, DataRouter, DataSource, Experiment
from ...views.pages import easy_setup


class StatusTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/status'

    def _sorting_test_impl(self, model, context_item_name):
        self.client.force_login(self.user)

        # Add new instances to make sure they aren't just listed in the order they were added (i.e. by pk)
        for i in (15, 14, 13, 12, 11):
            model.objects.create(
                name='Item{}'.format(i),
                ip_address='117.0.0.1',
                port='1234',
                experiment=self.experiment,
            )

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 200)

        item_list = resp.context[context_item_name]
        names = [s.name for s in item_list]
        self.assertEqual(names, sorted(names))

    def test_ecc_list_is_sorted(self):
        self._sorting_test_impl(ECCServer, 'ecc_servers')

    def test_data_router_list_is_sorted(self):
        self._sorting_test_impl(DataRouter, 'data_routers')

    def _excludes_other_experiment_impl(self, model, context_item_name):
        self.client.force_login(self.user)
        other_expt = Experiment.objects.create(name='Test')
        other_object = model.objects.create(
            name='Other',
            ip_address='123.123.123.123',
            experiment=other_expt,
        )

        resp = self.client.get(reverse(self.view_name))
        self.assertNotIn(other_object, resp.context[context_item_name])

    def test_ecc_list_excludes_other_experiments(self):
        self._excludes_other_experiment_impl(ECCServer, 'ecc_servers')

    def test_data_router_list_excludes_other_experiments(self):
        self._excludes_other_experiment_impl(DataRouter, 'data_routers')


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
        self.cobo_ecc_log_path = '/path/to/ecc_file.log'
        self.cobo_router_log_path = '/path/to/router_file.log'
        self.cobo_config_root = '/path/to/configs'
        self.cobo_config_backup_root = '/backups'
        self.mutant_is_present = True
        self.mutant_ecc_ip = '100.200.300.400'
        self.mutant_data_router_ip = '500.600.700.800'
        self.mutant_ecc_log_path = '/path/to/mutant/ecc_file.log'
        self.mutant_router_log_path = '/path/to/mutant/router_file.log'
        self.mutant_config_root = '/path/to/mutant/configs'
        self.mutant_config_backup_root = '/mutant/backups'
        self.experiment = Experiment.objects.create(
            name='Test',
        )

    def run_easy_setup(self):
        easy_setup(
            experiment=self.experiment,
            num_cobos=self.num_cobos,
            one_ecc_server=self.one_ecc_server,
            first_cobo_ecc_ip=self.first_cobo_ecc_ip,
            first_cobo_data_router_ip=self.first_cobo_data_router_ip,
            cobo_ecc_log_path=self.cobo_ecc_log_path,
            cobo_router_log_path=self.cobo_router_log_path,
            cobo_config_root=self.cobo_config_root,
            cobo_config_backup_root=self.cobo_config_backup_root,
            mutant_is_present=self.mutant_is_present,
            mutant_ecc_ip=self.mutant_ecc_ip,
            mutant_data_router_ip=self.mutant_data_router_ip,
            mutant_ecc_log_path=self.mutant_ecc_log_path,
            mutant_router_log_path=self.mutant_router_log_path,
            mutant_config_root=self.mutant_config_root,
            mutant_config_backup_root=self.mutant_config_backup_root,
        )

    def check_all_eccs_present(self):
        ecc_count = ECCServer.objects.filter(experiment=self.experiment).count()
        if self.one_ecc_server:
            self.assertEqual(ecc_count, 1)
        else:
            if self.mutant_is_present:
                self.assertEqual(ecc_count, self.num_cobos + 1)
            else:
                self.assertEqual(ecc_count, self.num_cobos)

    def check_all_data_routers_present(self):
        data_router_count = DataRouter.objects.filter(experiment=self.experiment).count()
        if self.mutant_is_present:
            self.assertEqual(data_router_count, self.num_cobos + 1)
        else:
            self.assertEqual(data_router_count, self.num_cobos)

    def check_all_data_sources_present(self):
        data_source_count = (
            DataSource.objects
            .filter(ecc_server__experiment=self.experiment, data_router__experiment=self.experiment)
            .count()
        )
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
        ecc_servers = ECCServer.objects.filter(experiment=self.experiment)
        cobo_eccs = ecc_servers.filter(datasource__name__icontains='cobo').distinct().order_by('ip_address')

        self.check_ip_addresses(cobo_eccs, self.first_cobo_ecc_ip)

        for ecc in cobo_eccs:
            self.assertEqual(ecc.log_path, self.cobo_ecc_log_path)
            self.assertEqual(ecc.config_root, self.cobo_config_root)
            self.assertEqual(ecc.config_backup_root, self.cobo_config_backup_root)

        if self.one_ecc_server:
            self.assertEqual(ecc_servers.count(), 1)

        if self.mutant_is_present and not self.one_ecc_server:
            mutant_ecc = ecc_servers.get(datasource__name__icontains='mutant')
            self.assertEqual(mutant_ecc.ip_address, self.mutant_ecc_ip)
            self.assertEqual(mutant_ecc.log_path, self.mutant_ecc_log_path)
            self.assertEqual(mutant_ecc.config_root, self.mutant_config_root)
            self.assertEqual(mutant_ecc.config_backup_root, self.mutant_config_backup_root)

    def check_data_routers(self):
        cobo_routers = (
            DataRouter.objects
            .filter(experiment=self.experiment, datasource__name__icontains='cobo')
            .distinct()
            .order_by('ip_address')
        )
        self.check_ip_addresses(cobo_routers, self.first_cobo_data_router_ip)
        for r in cobo_routers:
            self.assertEqual(r.connection_type, DataRouter.TCP)

        if self.mutant_is_present:
            mutant_router = DataRouter.objects.get(experiment=self.experiment, datasource__name__icontains='mutant')
            self.assertEqual(mutant_router.ip_address, self.mutant_data_router_ip)
            self.assertEqual(mutant_router.connection_type, DataRouter.FDT)

    def check_data_sources(self):
        cobos = DataSource.objects.filter(
            name__contains='CoBo',
            ecc_server__experiment=self.experiment,
            data_router__experiment=self.experiment,
        )
        for cobo in cobos:
            self.assertRegex(cobo.name, r'CoBo\[(\d)\]')
            self.assertIsNotNone(cobo.ecc_server)
            self.assertIsNotNone(cobo.data_router)

        if self.mutant_is_present:
            mutant = DataSource.objects.get(
                name__icontains='mutant',
                ecc_server__experiment=self.experiment,
                data_router__experiment=self.experiment
            )
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

    def test_only_affects_current_experiment(self):
        other_expt = Experiment.objects.create(
            name='Another experiment',
        )
        ecc = ECCServer.objects.create(
            name='Some ecc',
            ip_address='123.123.123.123',
            experiment=other_expt,
        )
        router = DataRouter.objects.create(
            name='Some router',
            ip_address='123.123.123.123',
            experiment=other_expt,
        )
        DataSource.objects.create(
            ecc_server=ecc,
            data_router=router,
        )

        self.run_easy_setup()
        self.assertTrue(ECCServer.objects.filter(experiment=other_expt).exists())
        self.assertTrue(DataRouter.objects.filter(experiment=other_expt).exists())
        self.assertTrue(DataSource.objects.filter(ecc_server__experiment=other_expt).exists())
        self.assertTrue(DataSource.objects.filter(data_router__experiment=other_expt).exists())

    def test_no_name_collisions(self):
        old_expt = self.experiment
        self.easy_setup_test_impl()

        new_expt = Experiment.objects.create(name='Some other experiment')
        self.experiment = new_expt
        self.easy_setup_test_impl()


@patch('attpcdaq.daq.views.pages.WorkerInterface')
class LogViewerTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        self.view_name = 'daq/show_log'

        self.experiment = Experiment.objects.create(
            name='Test',
        )

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.456.789.1',
            experiment=self.experiment,
        )
        self.data_router = DataRouter.objects.create(
            name='DataRouter',
            ip_address='123.456.789.0',
            experiment=self.experiment,
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


class ExperimentChoiceViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='test',
            password='test1234',
        )
        self.experiment0 = Experiment.objects.create(name='expt0')
        self.experiment1 = Experiment.objects.create(name='expt1')

        self.view_name = 'daq/choose_experiment'

    def test_redirects_if_ecc_running(self):
        ecc = ECCServer.objects.create(
            name='ecc',
            ip_address='123.123.123.123',
            experiment=self.experiment0,
            state=ECCServer.READY,
        )

        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name), follow=True)
        self.assertEqual(resp.redirect_chain[0][1], 302)
        self.assertEqual(resp.redirect_chain[-1][0], reverse('daq/cannot_change_experiment'))
