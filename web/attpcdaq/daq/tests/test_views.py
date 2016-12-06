from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from unittest.mock import patch
from datetime import datetime
import tempfile
import json
from ..models import DataSource, ECCServer, DataRouter, ConfigId, Experiment, RunMetadata
from .. import views
from ..views.pages import easy_setup
import re


class RequiresLoginTestMixin(object):
    def setUp(self):
        super().setUp()

    def test_no_login(self, *args, **kwargs):
        request_data = kwargs.get('data')
        reverse_args = kwargs.get('rev_args')
        resp = self.client.get(reverse(self.view_name, args=reverse_args), data=request_data)
        self.assertEqual(resp.status_code, 302)


class ManySourcesTestCaseBase(TestCase):
    def setUp(self):
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
            )
            self.ecc_servers.append(ecc)

            router = DataRouter.objects.create(
                name='DataRouter{}'.format(i),
                ip_address=self.data_router_ip_address,
                port=self.data_router_port,
            )
            self.data_routers.append(router)

            source = DataSource.objects.create(
                name='CoBo[{}]'.format(i),
                ecc_server=ecc,
                data_router=router,
            )
            self.datasources.append(source)

        self.user = User(username='test', password='test1234')
        self.user.save()

        self.experiment = Experiment.objects.create(
            name='Test experiment',
            user=self.user
        )


class RefreshStateAllViewTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_refresh_state_all'

    def test_post(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse(self.view_name))
        self.assertEqual(resp.status_code, 405)

    def test_good_request(self):
        self.client.force_login(self.user)
        for ecc in self.ecc_servers:
            ecc.state = ECCServer.RUNNING
            ecc.save()

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.resolver_match.func, views.refresh_state_all)

        response_json = resp.json()
        self.assertEqual(response_json['overall_state'], ECCServer.RUNNING)
        self.assertEqual(response_json['overall_state_name'], ECCServer.STATE_DICT[ECCServer.RUNNING])

        for res in response_json['ecc_server_status_list']:
            pk = int(res['pk'])
            ecc_server = ECCServer.objects.get(pk=pk)
            self.assertEqual(res['state'], ECCServer.RUNNING)
            self.assertEqual(res['state_name'], ecc_server.get_state_display())
            self.assertEqual(res['transitioning'], ecc_server.is_transitioning)
            self.assertTrue(res['success'])
            self.assertEqual(res['error_message'], '')

        for res in response_json['data_router_status_list']:
            pk = int(res['pk'])
            router = DataRouter.objects.get(pk=pk)
            self.assertEqual(res['is_online'], router.is_online)
            self.assertEqual(res['is_clean'], router.staging_directory_is_clean)
            self.assertTrue(res['success'])

    def test_response_contains_run_info(self):
        self.client.force_login(self.user)

        for ecc_server in self.ecc_servers:
            ecc_server.state = ECCServer.RUNNING
            ecc_server.save()

        run0 = RunMetadata.objects.create(run_number=0,
                                          experiment=self.experiment,
                                          start_datetime=datetime.now())

        resp = self.client.get(reverse(self.view_name))

        resp_json = resp.json()
        self.assertEqual(resp_json['run_number'], run0.run_number)
        self.assertEqual(resp_json['start_time'], run0.start_datetime.strftime('%b %d %Y, %H:%M:%S'))  # This is perhaps not the best
        self.assertEqual(resp_json['run_duration'], run0.duration_string)


class SourceChangeStateTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_change_state'


@patch('attpcdaq.daq.views.api.eccserver_change_state_task.delay')
class SourceChangeStateAllTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_change_state_all'

    def test_get(self, _):
        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 405)

    def test_with_no_runs(self, mock_task_delay):
        self.client.force_login(self.user)

        resp = self.client.post(reverse(self.view_name), {'target_state': ECCServer.DESCRIBED})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()['run_number'])


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


class AddDataSourceViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/add_source'


class UpdateDataSourceViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/update_source'

    def test_no_login(self, *args, **kwargs):
        super().test_no_login(rev_args=(1,))


class RemoveDataSourceViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/remove_source'

    def test_no_login(self, *args, **kwargs):
        super().test_no_login(rev_args=(1,))


class ListRunMetadataViewTestCase(RequiresLoginTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/run_list'

        self.user = User.objects.create(username='testUser', password='test1234')
        self.experiment = Experiment.objects.create(name='Test experiment', user=self.user)

        self.runs = []
        for i in (0, 3, 1, 2, 5, 4, 7, 9, 8):  # In a random order to test sorting
            r = RunMetadata.objects.create(run_number=i,
                                           start_datetime=datetime.now(),
                                           stop_datetime=datetime.now(),
                                           experiment=self.experiment)
            self.runs.append(r)

    def test_runs_are_sorted_by_run_number(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 200)

        run_list = resp.context['runmetadata_list']
        run_nums = [run.run_number for run in run_list]
        self.assertEqual(sorted(run_nums), run_nums)

    def test_runs_are_only_for_this_experiment(self):
        self.client.force_login(self.user)

        newuser = User.objects.create(username='newExperiment', password='new12345')
        newexpt = Experiment.objects.create(name='Another experiment', user=newuser)
        newrun = RunMetadata.objects.create(run_number=0,
                                            start_datetime=datetime.now(),
                                            stop_datetime=datetime.now(),
                                            experiment=newexpt)

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 200)

        run_list = resp.context['runmetadata_list']
        self.assertNotIn(newrun, run_list)


class UploadDataSourceListTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/upload_datasource_list'

    def _get_data(self):
        download_resp = self.client.get(reverse('daq/download_datasource_list'))

        data = download_resp.json()
        for node in data:
            if 'pk' in node:
                del node['pk']

        return data

    def test_upload_when_db_list_full(self):
        self.client.force_login(self.user)

        data = self._get_data()

        with tempfile.NamedTemporaryFile(mode='w+') as fp:
            json.dump(data, fp)
            fp.seek(0)
            upload_resp = self.client.post(reverse(self.view_name), data={'data_source_list': fp})

        data_new = self._get_data()
        self.assertEqual(data, data_new)


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
