"""Unit tests for Celery tasks"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
import logging
from celery.exceptions import SoftTimeLimitExceeded

from ..tasks import organize_files_task, eccserver_refresh_state_task, eccserver_change_state_task
from ..tasks import check_ecc_server_online_task
from ..models import ECCServer, DataRouter, DataSource, Experiment


class TaskTestCaseBase(TestCase):
    def setUp(self):
        self.mock = MagicMock()
        self.patcher = patch(self.patch_target, new=self.mock)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def get_callable(self):
        return self.mock

    def set_mock_effect(self, effect, side_effect=False):
        mock_callable = self.get_callable()
        if side_effect:
            mock_callable.side_effect = effect
        else:
            mock_callable.return_value = effect

    def call_task(self, *args, **kwargs):
        raise NotImplementedError()


class ExceptionHandlingTestMixin(object):
    def test_raised_exception(self):
        self.set_mock_effect(ValueError, side_effect=True)
        with self.assertLogs(level=logging.ERROR):
            self.call_task()

    def test_soft_time_limit_exceeded(self):
        self.set_mock_effect(SoftTimeLimitExceeded, side_effect=True)
        with self.assertLogs(level=logging.ERROR) as cm:
            self.call_task()
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], r'Time limit')


class EccServerRefreshStateTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        self.patch_target = 'attpcdaq.daq.tasks.ECCServer.refresh_state'
        super().setUp()

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
        )

    def call_task(self, pk=None):
        if pk is None:
            pk = self.ecc.pk
        eccserver_refresh_state_task(pk)

    def test_refresh_state(self):
        self.call_task()
        self.get_callable().assert_called_once_with()

    def test_with_invalid_ecc_pk(self):
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.ecc.pk + 10)


class EccServerChangeStateTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        self.patch_target = 'attpcdaq.daq.tasks.ECCServer.change_state'
        super().setUp()

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            state=ECCServer.IDLE,
        )
        self.target_state = ECCServer.DESCRIBED

    def call_task(self, pk=None):
        if pk is None:
            pk = self.ecc.pk
        eccserver_change_state_task(pk, self.target_state)

    def test_change_state(self):
        self.call_task()
        self.get_callable().assert_called_once_with(self.target_state)

    def test_with_invalid_ecc_pk(self):
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.ecc.pk + 10)


class CheckEccServerOnlineTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        self.patch_target = 'attpcdaq.daq.tasks.WorkerInterface'
        super().setUp()

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            state=ECCServer.IDLE,
            is_online=False
        )

    def get_callable(self):
        return self.mock.return_value.__enter__.return_value.check_ecc_server_status

    def call_task(self, pk=None):
        if pk is None:
            pk = self.ecc.pk
        check_ecc_server_online_task(pk)

    def test_check_ecc_server_online(self):
        self.set_mock_effect(True)

        self.call_task()
        self.get_callable().assert_called_once_with()

        self.ecc.refresh_from_db()
        self.assertTrue(self.ecc.is_online)

    def test_with_invalid_ecc_pk(self):
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.ecc.pk + 10)


class OrganizeFilesTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        self.patch_target = 'attpcdaq.daq.tasks.WorkerInterface'
        super().setUp()

        self.data_router = DataRouter.objects.create(
            name='DataRouter',
            ip_address='123.456.789.0',
        )
        self.experiment_name = 'Test experiment'
        self.run_num = 10

    def get_callable(self):
        return self.mock.return_value.__enter__.return_value.organize_files

    def call_task(self, pk=None):
        if pk is None:
            pk = self.data_router.pk
        organize_files_task(pk, self.experiment_name, self.run_num)

    def test_organize_files(self):
        self.data_router.staging_directory_is_clean = False
        self.data_router.save()

        self.call_task()

        self.mock.assert_called_once_with(self.data_router.ip_address)
        self.get_callable().assert_called_once_with(self.experiment_name, self.run_num)

        self.data_router.refresh_from_db()
        self.assertTrue(self.data_router.staging_directory_is_clean)

    def test_with_invalid_data_router_pk(self):
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.data_router.pk + 10)
