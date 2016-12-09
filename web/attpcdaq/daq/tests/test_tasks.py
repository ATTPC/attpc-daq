"""Unit tests for Celery tasks"""

from django.test import TestCase
from unittest.mock import patch, MagicMock, call
import logging
from celery.exceptions import SoftTimeLimitExceeded

from ..tasks import organize_files_task, eccserver_refresh_state_task, eccserver_change_state_task
from ..tasks import check_ecc_server_online_task, check_data_router_status_task, organize_files_all_task
from ..tasks import eccserver_refresh_all_task, check_ecc_server_online_all_task, check_data_router_status_all_task
from ..models import ECCServer, DataRouter


class TaskTestCaseBase(TestCase):
    def setUp(self):
        self.mock = MagicMock()
        self.patcher = patch(self.patch_target, new=self.mock)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def get_callable(self, *args, **kwargs):
        return self.mock

    def set_mock_effect(self, effect, side_effect=False, *args, **kwargs):
        mock_callable = self.get_callable(*args, **kwargs)
        if side_effect:
            mock_callable.side_effect = effect
        else:
            mock_callable.return_value = effect

    def call_task(self, *args, **kwargs):
        raise NotImplementedError()


class AllTaskTestCaseBase(TaskTestCaseBase):
    def setUp(self):
        self.subtask_mock = MagicMock()
        self.subtask_patcher = patch(self.subtask_patch_target, new=self.subtask_mock)
        self.subtask_patcher.start()
        self.addCleanup(self.subtask_patcher.stop)

        self.group_mock = MagicMock()
        self.group_patcher = patch('attpcdaq.daq.tasks.group', new=self.group_mock)
        self.group_patcher.start()
        self.addCleanup(self.group_patcher.stop)

    def get_callable(self, which='group'):
        if which == 'group':
            return self.group_mock
        elif which == 'subtask':
            return self.subtask_mock.s
        else:
            raise ValueError('Invalid callable {} requested'.format(which))

    def get_queryset(self):
        raise NotImplementedError()

    def get_expected_subtask_calls(self, *subtask_args):
        return [call(x.pk, *subtask_args) for x in self.get_queryset()]


class TestCalledForAllMixin(object):
    def test_called_for_all(self: AllTaskTestCaseBase):
        self.call_task()
        task_calls = self.get_expected_subtask_calls()

        self.get_callable('subtask').assert_has_calls(task_calls)

        gp = self.get_callable('group')
        self.assertEqual(gp.call_count, 1)         # Check group object was constructed
        gp.return_value.assert_called_once_with()  # Check group object was called


class ExceptionHandlingTestMixin(object):
    def test_raised_exception(self: TaskTestCaseBase):
        self.set_mock_effect(ValueError, side_effect=True)
        with self.assertLogs(level=logging.ERROR):
            self.call_task()

    def test_soft_time_limit_exceeded(self: TaskTestCaseBase):
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


class EccServerRefreshAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin, AllTaskTestCaseBase):
    def setUp(self):
        self.subtask_patch_target = 'attpcdaq.daq.tasks.eccserver_refresh_state_task'
        super().setUp()

        for i in range(10):
            ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address='123.123.123.123',
            )

    def call_task(self):
        return eccserver_refresh_all_task()

    def get_queryset(self):
        return ECCServer.objects.all()


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


class CheckEccServerOnlineAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin, AllTaskTestCaseBase):
    def setUp(self):
        self.subtask_patch_target = 'attpcdaq.daq.tasks.check_ecc_server_online_task'
        super().setUp()

        for i in range(10):
            ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address='123.123.123.123',
            )

    def call_task(self):
        return check_ecc_server_online_all_task()

    def get_queryset(self):
        return ECCServer.objects.all()


class CheckDataRouterStatusTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        self.patch_target = 'attpcdaq.daq.tasks.WorkerInterface'
        super().setUp()

        self.data_router = DataRouter.objects.create(
            name='DataRouter',
            ip_address='123.123.123.123',
        )

    def get_callable(self, which='status'):
        cm = self.mock.return_value.__enter__.return_value
        if which == 'status':
            return cm.check_data_router_status
        elif which == 'clean':
            return cm.working_dir_is_clean
        else:
            raise ValueError('Unknown method {} requested'.format(which))

    def call_task(self, pk=None):
        if pk is None:
            pk = self.data_router.pk
        check_data_router_status_task(pk)

    def test_check_data_router_status(self):
        self.data_router.is_online = False
        self.data_router.staging_directory_is_clean = False
        self.data_router.save()

        self.set_mock_effect(True, which='status')
        self.set_mock_effect(True, which='clean')

        self.call_task()

        self.mock.assert_called_once_with(self.data_router.ip_address)
        self.get_callable(which='status').assert_called_once_with()
        self.get_callable(which='clean').assert_called_once_with()

        self.data_router.refresh_from_db()
        self.assertTrue(self.data_router.is_online)
        self.assertTrue(self.data_router.staging_directory_is_clean)

    def test_with_invalid_data_router_pk(self):
        with self.assertLogs(level=logging.ERROR) as cm:
            self.call_task(self.data_router.pk + 10)

    def test_does_not_check_if_clean_if_not_online(self):
        self.set_mock_effect(False, which='status')
        self.call_task()

        self.mock.assert_called_once_with(self.data_router.ip_address)
        self.get_callable(which='status').assert_called_once_with()
        self.get_callable(which='clean').assert_not_called()


class CheckDataRouterStatusAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin, AllTaskTestCaseBase):
    def setUp(self):
        self.subtask_patch_target = 'attpcdaq.daq.tasks.check_data_router_status_task'
        super().setUp()

        for i in range(10):
            DataRouter.objects.create(
                name='DataRouter{}'.format(i),
                ip_address='123.123.123.123',
            )

    def get_queryset(self):
        return DataRouter.objects.all()

    def call_task(self):
        return check_data_router_status_all_task()


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


class OrganizeFilesAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin, AllTaskTestCaseBase):
    def setUp(self):
        self.subtask_patch_target = 'attpcdaq.daq.tasks.organize_files_task'
        super().setUp()

        for i in range(10):
            DataRouter.objects.create(
                name='DataRouter{}'.format(i),
                ip_address='123.123.123.123',
            )

        self.experiment_name = 'Test experiment'
        self.run_number = 1

    def get_queryset(self):
        return DataRouter.objects.all()

    def call_task(self):
        return organize_files_all_task(self.experiment_name, self.run_number)

    def get_expected_subtask_calls(self):
        return super().get_expected_subtask_calls(self.experiment_name, self.run_number)
