from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from unittest.mock import patch
from datetime import datetime
import json
import tempfile

from .helpers import RequiresLoginTestMixin, ManySourcesTestCaseBase
from ...models import ECCServer, DataRouter, RunMetadata, Experiment
from ... import views


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