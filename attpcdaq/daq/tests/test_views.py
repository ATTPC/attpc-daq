from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from unittest.mock import patch
from ..models import DataRouter, DataSource, ConfigId, Experiment, RunMetadata
from .utilities import FakeResponseState
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


@patch('attpcdaq.daq.models.SoapClient')
class RefreshStateAllViewTestCase(TestCase):
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

        self.view_name = 'daq/source_refresh_state_all'

    def test_no_login(self, mock_client):
        resp = self.client.get(reverse(self.view_name))
        self.assertEqual(resp.status_code, 302)

    def test_put(self, mock_client):
        self.client.force_login(self.user)
        resp = self.client.put(reverse(self.view_name))
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