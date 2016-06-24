from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from unittest.mock import patch
from datetime import datetime
from ..models import DataRouter, DataSource, ConfigId, Experiment, RunMetadata
from .utilities import FakeResponseState, FakeResponseText
from .. import views


@patch('attpcdaq.daq.models.SoapClient')
class SourceGetStateViewTestCase(TestCase):
    def setUp(self):
        self.source_name = 'CoBo[0]'
        self.ecc_ip_address = '123.45.67.8'
        self.ecc_port = '1234'
        self.datarouter = DataRouter(name='dataRouter0',
                                     ip_address='123.456.78.9',
                                     port='1111')
        self.datarouter.save()
        self.selected_config = ConfigId(describe='describe',
                                        prepare='prepare',
                                        configure='configure')
        self.selected_config.save()
        self.datasource = DataSource(name=self.source_name,
                                     ecc_ip_address=self.ecc_ip_address,
                                     ecc_port=self.ecc_port,
                                     data_router=self.datarouter,
                                     selected_config=self.selected_config)
        self.datasource.save()

        self.user = User(username='test', password='test1234')
        self.user.save()

    def test_not_logged_in(self, mock_client):
        resp = self.client.get(reverse('daq/source_get_state'), {'pk': self.datasource.pk})
        self.assertEqual(resp.status_code, 302)

    def test_good(self, mock_client):
        mock_instance = mock_client.return_value
        mock_instance.service.GetState.return_value = FakeResponseState(state=DataSource.RUNNING)

        self.client.force_login(self.user)
        resp = self.client.get(reverse('daq/source_get_state'), {'pk': self.datasource.pk})
        self.assertEqual(resp.resolver_match.func, views.source_get_state)

        self.datasource.refresh_from_db()

        response_json = resp.json()
        expected_json = {'success': True,
                         'pk': self.datasource.pk,
                         'error_message': '',
                         'state': self.datasource.state,
                         'state_name': self.datasource.get_state_display(),
                         'transitioning': False}

        self.assertEqual(response_json, expected_json)

        self.assertEqual(self.datasource.state, DataSource.RUNNING)

    def test_without_pk(self, mock_client):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('daq/source_get_state'))
        self.assertEqual(resp.status_code, 400)

        response_json = resp.json()
        self.assertFalse(response_json['success'])
        self.assertRegex(response_json['error_message'], '.*data source pk.*')

    def test_put(self, mock_client):
        self.client.force_login(self.user)
        resp = self.client.put(reverse('daq/source_get_state'))
        self.assertEqual(resp.status_code, 405)

    def test_with_error(self, mock_client):
        self.client.force_login(self.user)
        mock_instance = mock_client.return_value
        error_message = 'An error happened'
        mock_instance.service.GetState.return_value = \
            FakeResponseState(error_code=1, error_message=error_message)

        resp = self.client.get(reverse('daq/source_get_state'), {'pk': self.datasource.pk})
        self.assertEqual(resp.status_code, 200)

        response_json = resp.json()
        expected_json = {'success': False,
                         'pk': self.datasource.pk,
                         'error_message': error_message,
                         'state': self.datasource.state,
                         'state_name': self.datasource.get_state_display(),
                         'transitioning': False}

        self.assertEqual(response_json, expected_json)


class ManySourcesTestCaseBase(TestCase):
    def setUp(self):
        self.ecc_ip_address = '123.45.67.8'
        self.ecc_port = '1234'
        self.selected_config = ConfigId(describe='describe',
                                        prepare='prepare',
                                        configure='configure')
        self.selected_config.save()

        self.datasources = []
        for i in range(10):
            dr = DataRouter(name='dataRouter{}'.format(i),
                            ip_address='123.456.78.9',
                            port='1111')
            dr.save()

            d = DataSource(name='CoBo[{}]'.format(i),
                           ecc_ip_address=self.ecc_ip_address,
                           ecc_port=self.ecc_port,
                           data_router=dr,
                           selected_config=self.selected_config)
            d.save()
            self.datasources.append(d)

        self.user = User(username='test', password='test1234')
        self.user.save()

        self.experiment = Experiment.objects.create(name='Test experiment',
                                                    user=self.user)


@patch('attpcdaq.daq.models.SoapClient')
class RefreshStateAllViewTestCase(ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_refresh_state_all'

    def test_no_login(self, mock_client):
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 302)

    def test_post(self, mock_client):
        self.client.force_login(self.user)
        resp = self.client.post(reverse(self.view_name))
        self.assertEqual(resp.status_code, 405)

    def test_good_request(self, mock_client):
        self.client.force_login(self.user)
        mock_instance = mock_client.return_value
        mock_instance.service.GetState.return_value = \
            FakeResponseState(state=DataSource.RUNNING,
                              trans=False)

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

    def test_response_contains_run_info(self, mock_client):
        self.client.force_login(self.user)
        mock_instance = mock_client.return_value
        mock_instance.service.GetState.return_value = \
            FakeResponseState(state=DataSource.RUNNING,
                              trans=False)

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


@patch('attpcdaq.daq.models.SoapClient')
class SourceChangeStateAllTestCase(ManySourcesTestCaseBase):
    def setUp(self):
        super().setUp()
        self.view_name = 'daq/source_change_state_all'

    def test_no_login(self, mock_client):
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 302)

    def test_get(self, mock_client):
        self.client.force_login(self.user)
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 405)

    def test_response_content(self, mock_client):
        self.client.force_login(self.user)
        mock_instance = mock_client.return_value
        mock_instance.service.Describe.return_value = \
            FakeResponseText()

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

    def test_with_no_runs(self, mock_client):
        self.client.force_login(self.user)
        mock_instance = mock_client.return_value
        mock_instance.service.Describe.return_value = \
            FakeResponseText()

        resp = self.client.post(reverse(self.view_name), {'target_state': DataSource.DESCRIBED})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()['run_number'])


class StatusTestCase(ManySourcesTestCaseBase):

    def setUp(self):
        super().setUp()
        self.view_name = 'daq/status'

    def test_sources_are_sorted_in_table(self):
        self.client.force_login(self.user)

        # Add new sources to make sure they aren't just listed in the order they were added (i.e. by pk)
        for i in (15, 14, 13, 12, 11):
            dr = DataRouter.objects.create(name='dataRouter{}'.format(i),
                                           ip_address='123.456.78.9',
                                           port='1111')
            d = DataSource.objects.create(name='CoBo[{}]'.format(i),
                                          ecc_ip_address=self.ecc_ip_address,
                                          ecc_port=self.ecc_port,
                                          data_router=dr,
                                          selected_config=self.selected_config)

        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 200)

        source_list = resp.context['data_sources']
        names = [s.name for s in source_list]
        self.assertEqual(names, sorted(names))
