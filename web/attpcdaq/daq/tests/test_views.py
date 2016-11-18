from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from unittest.mock import patch
from datetime import datetime
import tempfile
import json
from ..models import DataSource, ECCServer, DataRouter, ConfigId, Experiment, RunMetadata
from .. import views


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

