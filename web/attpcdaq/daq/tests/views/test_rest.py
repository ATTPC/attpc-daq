from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, call
import logging

from ...models import ECCServer, DataRouter, Experiment, ConfigId
from ...views.rest import ECCServerViewSet


def log_file_test_impl(testcase : TestCase, target, url):
    with patch('attpcdaq.daq.views.rest.WorkerInterface') as mock_wi_class:
        sample_log_content = 'Sample text'
        wi_context_mgr = mock_wi_class.return_value.__enter__.return_value
        wi_context_mgr.tail_file.return_value = sample_log_content

        resp = testcase.client.get(url)

        testcase.assertEqual(resp.status_code, 200)
        mock_wi_class.assert_called_once_with(target.ip_address)
        wi_context_mgr.tail_file.assert_called_once_with(target.log_path)
        testcase.assertEqual(resp.json()['content'], sample_log_content)


class DataRouterViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='test',
            password='test1234',
        )
        self.client.force_login(self.user)
        DataRouter.objects.create(
            name='DataRouter0',
            ip_address='123.123.123.123',
        )

    def test_log_file(self):
        router = DataRouter.objects.first()
        url = '/daq/api/data_routers/{}/log_file/'.format(router.pk)
        log_file_test_impl(testcase=self, target=router, url=url)


class ECCServerViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='test',
            password='test1234',
        )
        self.client.force_login(self.user)
        for i in range(10):
            ecc = ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address='123.123.123.123',
            )
            config = ConfigId.objects.create(
                describe='describe',
                prepare='prepare',
                configure='configure',
                ecc_server=ecc,
            )
            ecc.selected_config = config
            ecc.save()

            DataRouter.objects.create(
                name='DataRouter{}'.format(i),
                ip_address='123.123.123.321',
                is_online=True,
                staging_directory_is_clean=True,
            )

        self.transitions = ['describe', 'prepare', 'configure', 'start', 'stop', 'reset']
        self.experiment = Experiment.objects.create(
            name='Test experiment',
            user=self.user,
        )

    def test_log_file(self):
        ecc = ECCServer.objects.first()
        url = '/daq/api/ecc_servers/{}/log_file/'.format(ecc.pk)
        log_file_test_impl(testcase=self, target=ecc, url=url)

    def _change_state_test_impl(self, ecc, transition):
        with patch('attpcdaq.daq.views.rest.eccserver_change_state_task') as mock_task:
            target_state = ECCServerViewSet._get_target_state_from_transition(ecc.state, transition)
            url = '/daq/api/ecc_servers/{pk:d}/{tr:s}/'.format(pk=ecc.pk, tr=transition)
            resp = self.client.post(url)
            self.assertEqual(resp.status_code, 200)
            respjson = resp.json()
            self.assertTrue(respjson['success'])
            mock_task.delay.assert_called_once_with(ecc.pk, target_state)
            mock_task.reset_mock()

    def test_change_state(self):
        ecc = ECCServer.objects.first()
        for transition in self.transitions:
            self._change_state_test_impl(ecc, transition)

    @patch('attpcdaq.daq.views.rest.eccserver_change_state_task')
    def test_change_state_exception_handling(self, mock_task):
        ecc = ECCServer.objects.first()
        transition = self.transitions[0]

        mock_task.delay.side_effect = ValueError()

        url = '/daq/api/ecc_servers/{pk:d}/{tr:s}/'.format(pk=ecc.pk, tr=transition)

        with self.assertLogs(logger='attpcdaq.daq.views.rest', level=logging.ERROR):
            resp = self.client.post(url)

        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.json()['success'])

    def _change_state_all_test_impl(self, transition):
        with patch('attpcdaq.daq.views.rest.eccserver_change_state_task') as mock_state_task, \
                patch('attpcdaq.daq.views.rest.organize_files_all_task') as mock_files_task:

            target_state = ECCServerViewSet._get_target_state_from_transition(ECCServer.IDLE, transition)
            url = '/daq/api/ecc_servers/{tr:s}/'.format(tr=transition)
            resp = self.client.post(url)
            self.assertEqual(resp.status_code, 200)

            respjson = resp.json()
            self.assertTrue(respjson['success'])

            expected_calls = [call(e.pk, target_state) for e in ECCServer.objects.all()]
            mock_state_task.delay.assert_has_calls(expected_calls, any_order=True)
            mock_state_task.reset_mock()

            if transition == 'start':
                self.assertTrue(self.experiment.is_running)

            if transition == 'stop':
                mock_files_task.delay.assert_called_once_with(self.experiment.name, self.experiment.latest_run.run_number)
                self.assertFalse(self.experiment.is_running)

    def test_change_state_all(self):
        for transition in self.transitions:
            self._change_state_all_test_impl(transition)

    @patch('attpcdaq.daq.views.rest.eccserver_change_state_task')
    def test_data_routers_not_ready(self, mock_task):
        router = DataRouter.objects.first()
        router.staging_directory_is_clean = False
        router.save()

        url = '/daq/api/ecc_servers/start/'

        with self.assertLogs('attpcdaq.daq.views.rest', logging.ERROR) as cm:
            resp = self.client.post(url)

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], r'not ready')  # Logged the error
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.json()['success'])
        mock_task.delay.assert_not_called()  # Make sure Celery task wasn't called
