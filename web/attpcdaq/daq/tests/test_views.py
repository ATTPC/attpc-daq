from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from unittest.mock import patch
from datetime import datetime
from ..models import DataSource, ConfigId, Experiment, RunMetadata
from .utilities import FakeResponseState, FakeResponseText
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
        self.selected_config = ConfigId(describe='describe',
                                        prepare='prepare',
                                        configure='configure')
        self.selected_config.save()

        self.datasources = []
        for i in range(10):
            d = DataSource(name='CoBo[{}]'.format(i),
                           ecc_ip_address=self.ecc_ip_address,
                           ecc_port=self.ecc_port,
                           data_router_ip_address=self.data_router_ip_address,
                           data_router_port=self.data_router_port,
                           selected_config=self.selected_config)
            d.save()
            self.datasources.append(d)

        self.user = User(username='test', password='test1234')
        self.user.save()

        self.experiment = Experiment.objects.create(name='Test experiment',
                                                    user=self.user)


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
        for source in self.datasources:
            source.state = DataSource.RUNNING
            source.save()

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.resolver_match.func, views.refresh_state_all)

        response_json = resp.json()
        self.assertEqual(response_json['overall_state'], DataSource.RUNNING)
        self.assertEqual(response_json['overall_state_name'], DataSource.STATE_DICT[DataSource.RUNNING])

        for res in response_json['individual_results']:
            pk = int(res['pk'])
            source = DataSource.objects.get(pk=pk)
            self.assertEqual(res['state'], source.state)
            self.assertEqual(res['state'], DataSource.RUNNING)
            self.assertEqual(res['state_name'], source.get_state_display())
            self.assertEqual(res['transitioning'], source.is_transitioning)
            self.assertTrue(res['success'])
            self.assertEqual(res['error_message'], '')

    def test_response_contains_run_info(self):
        self.client.force_login(self.user)

        for source in self.datasources:
            source.state = DataSource.RUNNING
            source.save()

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


@patch('attpcdaq.daq.views.datasource_change_state_task.delay')
class SourceChangeStateAllTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_change_state_all'

    def test_get(self, _):
        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 405)

    def test_response_content(self, mock_task_delay):
        self.client.force_login(self.user)

        run0 = RunMetadata.objects.create(run_number=0, experiment=self.experiment)

        resp = self.client.post(reverse(self.view_name), {'target_state': DataSource.DESCRIBED})

        self.assertEqual(resp.resolver_match.func, views.source_change_state_all)
        self.assertEqual(resp.status_code, 200)

        resp_json = resp.json()

        self.assertTrue(resp_json['success'])
        self.assertEqual(resp_json['run_number'], run0.run_number)
        self.assertEqual(resp_json['start_time'], run0.start_datetime)
        self.assertEqual(resp_json['overall_state'], DataSource.IDLE)
        self.assertEqual(resp_json['overall_state_name'], DataSource.STATE_DICT[DataSource.IDLE])

        for res in resp_json['individual_results']:
            pk = int(res['pk'])
            source = DataSource.objects.get(pk=pk)
            self.assertEqual(res['state'], source.state)
            self.assertEqual(res['state'], DataSource.IDLE)
            self.assertEqual(res['state_name'], source.get_state_display())
            self.assertEqual(res['transitioning'], True)
            self.assertTrue(res['success'])
            self.assertEqual(res['error_message'], '')

    def test_with_no_runs(self, mock_task_delay):
        self.client.force_login(self.user)

        resp = self.client.post(reverse(self.view_name), {'target_state': DataSource.DESCRIBED})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()['run_number'])


class StatusTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/status'

    def test_sources_are_sorted_in_table(self):
        self.client.force_login(self.user)

        # Add new sources to make sure they aren't just listed in the order they were added (i.e. by pk)
        for i in (15, 14, 13, 12, 11):
            d = DataSource.objects.create(name='CoBo[{}]'.format(i),
                                          ecc_ip_address=self.ecc_ip_address,
                                          ecc_port=self.ecc_port,
                                          data_router_ip_address=self.data_router_ip_address,
                                          data_router_port=self.data_router_port,
                                          selected_config=self.selected_config)

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 200)

        source_list = resp.context['data_sources']
        names = [s.name for s in source_list]
        self.assertEqual(names, sorted(names))


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


class DataSourceListTestCase(RequiresLoginTestMixin, ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/data_source_list'

    def test_sources_are_sorted_in_table(self):
        self.client.force_login(self.user)

        # Add new sources to make sure they aren't just listed in the order they were added (i.e. by pk)
        for i in (15, 14, 13, 12, 11):
            d = DataSource.objects.create(name='CoBo[{}]'.format(i),
                                          ecc_ip_address=self.ecc_ip_address,
                                          ecc_port=self.ecc_port,
                                          data_router_ip_address=self.data_router_ip_address,
                                          data_router_port=self.data_router_port,
                                          selected_config=self.selected_config)

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 200)

        source_list = resp.context['datasource_list']
        names = [s.name for s in source_list]
        self.assertEqual(names, sorted(names))


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