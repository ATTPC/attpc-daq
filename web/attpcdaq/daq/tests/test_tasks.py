"""Unit tests for Celery tasks"""

from django.test import TestCase
from unittest.mock import patch
import logging
from celery.exceptions import SoftTimeLimitExceeded

from ..tasks import organize_files_task, eccserver_refresh_state_task, eccserver_change_state_task
from ..tasks import check_ecc_server_online_task
from ..models import ECCServer, DataRouter, DataSource, Experiment


@patch('attpcdaq.daq.tasks.ECCServer.refresh_state')
class EccServerRefreshStateTaskTestCase(TestCase):
    def setUp(self):
        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
        )

    def test_refresh_state(self, mock_method):
        eccserver_refresh_state_task(self.ecc.pk)
        mock_method.assert_called_once_with()

    def test_with_invalid_ecc_pk(self, _):
        with self.assertLogs(level=logging.ERROR):
            eccserver_refresh_state_task(self.ecc.pk + 10)

    def test_raised_exception(self, mock_method):
        mock_method.side_effect = ValueError
        with self.assertLogs(level=logging.ERROR):
            eccserver_refresh_state_task(self.ecc.pk)

    def test_soft_time_limit_exceeded(self, mock_method):
        mock_method.side_effect = SoftTimeLimitExceeded
        with self.assertLogs(level=logging.ERROR) as cm:
            eccserver_refresh_state_task(self.ecc.pk)
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], r'Time limit')


@patch('attpcdaq.daq.tasks.ECCServer.change_state')
class EccServerChangeStateTaskTestCase(TestCase):
    def setUp(self):
        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            state=ECCServer.IDLE,
        )
        self.target_state = ECCServer.DESCRIBED

    def test_change_state(self, mock_method):
        eccserver_change_state_task(self.ecc.pk, self.target_state)
        mock_method.assert_called_once_with(self.target_state)

    def test_with_invalid_ecc_pk(self, _):
        with self.assertLogs(level=logging.ERROR):
            eccserver_change_state_task(self.ecc.pk + 10, self.target_state)

    def test_raised_exception(self, mock_method):
        mock_method.side_effect = ValueError
        with self.assertLogs(level=logging.ERROR):
            eccserver_change_state_task(self.ecc.pk, self.target_state)

    def test_soft_time_limit_exceeded(self, mock_method):
        mock_method.side_effect = SoftTimeLimitExceeded
        with self.assertLogs(level=logging.ERROR) as cm:
            eccserver_change_state_task(self.ecc.pk, self.target_state)
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], r'Time limit')


@patch('attpcdaq.daq.tasks.WorkerInterface')
class CheckEccServerOnlineTaskTestCase(TestCase):
    def setUp(self):
        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            state=ECCServer.IDLE,
            is_online=False
        )

    def test_check_ecc_server_online(self, mock_worker_interface):
        wi = mock_worker_interface.return_value
        wi_context_mgr = wi.__enter__.return_value
        wi_context_mgr.check_ecc_server_status.return_value = True

        check_ecc_server_online_task(self.ecc.pk)

        wi_context_mgr.check_ecc_server_status.assert_called_once_with()

        self.ecc.refresh_from_db()
        self.assertTrue(self.ecc.is_online)

    def test_with_invalid_ecc_pk(self, _):
        with self.assertLogs(level=logging.ERROR):
            check_ecc_server_online_task(self.ecc.pk + 10)

    def test_raised_exception(self, mock_worker_interface):
        wi = mock_worker_interface.return_value
        wi_context_mgr = wi.__enter__.return_value
        wi_context_mgr.check_ecc_server_status.side_effect = ValueError

        with self.assertLogs(level=logging.ERROR):
            check_ecc_server_online_task(self.ecc.pk)

    def test_soft_time_limit_exceeded(self, mock_worker_interface):
        wi = mock_worker_interface.return_value
        wi_context_mgr = wi.__enter__.return_value
        wi_context_mgr.check_ecc_server_status.side_effect = SoftTimeLimitExceeded

        with self.assertLogs(level=logging.ERROR) as cm:
            check_ecc_server_online_task(self.ecc.pk)
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], r'Time limit')


@patch('attpcdaq.daq.tasks.WorkerInterface')
class OrganizeFilesTaskTestCase(TestCase):
    def setUp(self):
        self.data_router = DataRouter.objects.create(
            name='DataRouter',
            ip_address='123.456.789.0',
        )
        self.experiment_name = 'Test experiment'
        self.run_num = 10

    def test_organize_files(self, mock_worker_interface):
        wi = mock_worker_interface.return_value
        wi_context_manager = wi.__enter__.return_value

        self.data_router.staging_directory_is_clean = False
        self.data_router.save()

        organize_files_task(self.data_router.pk, self.experiment_name, self.run_num)

        mock_worker_interface.assert_called_once_with(self.data_router.ip_address)
        wi_context_manager.organize_files.assert_called_once_with(self.experiment_name, self.run_num)

        self.data_router.refresh_from_db()

        self.assertTrue(self.data_router.staging_directory_is_clean)

    def test_with_invalid_data_router_pk(self, _):
        with self.assertLogs(level=logging.ERROR):
            organize_files_task(self.data_router.pk + 10, self.experiment_name, self.run_num)

    def test_raised_exception(self, mock_worker_interface):
        wi = mock_worker_interface.return_value
        wi_context_manager = wi.__enter__.return_value
        wi_context_manager.organize_files.side_effect = ValueError

        with self.assertLogs(level=logging.ERROR):
            organize_files_task(self.data_router.pk, self.experiment_name, self.run_num)

    def test_soft_time_limit_exceeded(self, mock_worker_interface):
        wi = mock_worker_interface.return_value
        wi_context_manager = wi.__enter__.return_value
        wi_context_manager.organize_files.side_effect = SoftTimeLimitExceeded

        with self.assertLogs(level=logging.ERROR) as cm:
            organize_files_task(self.data_router.pk, self.experiment_name, self.run_num)
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], r'Time limit')

