"""Unit tests for Celery tasks"""

from django.test import TestCase
from unittest.mock import patch, MagicMock, call
import logging
from celery.exceptions import SoftTimeLimitExceeded

from ..tasks import organize_files_task, eccserver_refresh_state_task, eccserver_change_state_task
from ..tasks import check_ecc_server_online_task, check_data_router_status_task, organize_files_all_task
from ..tasks import eccserver_refresh_all_task, check_ecc_server_online_all_task, check_data_router_status_all_task
from ..tasks import backup_config_files_task, backup_config_files_all_task
from ..models import ECCServer, DataRouter, ConfigId, Experiment, RunMetadata


class TaskTestCaseBase(TestCase):
    """An abstract base for testing the Celery tasks.

    This implements an abstract interface that makes it easier to test certain aspects of the
    tasks that are present in each one. This allows the testing code to be re-used for each
    task without repeating it over and over.

    This is an abstract class. Subclasses must override the methods :meth:`get_patch_target` and :meth:`call_task`
    for this to work. You will also likely want to override :meth:`get_callable`.

    """
    def setUp(self):
        self.mock = MagicMock()
        self.patcher = patch(self.get_patch_target(), new=self.mock)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def get_callable(self, *args, **kwargs):
        """Return the mock object that will be called when the task executes.

        This should return the mock that you would want to check the calls on.

        """
        return self.mock

    def get_patch_target(self):
        """Should return the dotted path to the object to be patched in the main code."""
        raise NotImplementedError()

    def set_mock_effect(self, effect, side_effect=False, *args, **kwargs):
        """Set a return value or side effect for the mock object.

        The mock to set up is found using :meth:`get_callable`. Any extra arguments are passed on to this method.

        Parameters
        ----------
        effect : object
            The effect to be assigned. This could be anything that the :mod:`unittest.mock` library supports.
        side_effect : bool
            If true, the ``effect`` will be assigned to the ``side_effect`` attribute of the mock. If False,
            it will be assigned to the ``return_value`` instead.

        """
        mock_callable = self.get_callable(*args, **kwargs)
        if side_effect:
            mock_callable.side_effect = effect
        else:
            mock_callable.return_value = effect

    def call_task(self, *args, **kwargs):
        """Should call the task to be tested.

        Arguments can be passed on to the task, if desired.

        """
        raise NotImplementedError()


class AllTaskTestCaseBase(TaskTestCaseBase):
    """An abstract base for the tasks that do something for all of the instances of an object.

    This is like :class:`TaskTestCaseBase`, but it also mocks out the Celery ``group`` function.

    """
    def setUp(self):
        self.subtask_mock = MagicMock()
        self.subtask_patcher = patch(self.get_patch_target(), new=self.subtask_mock)
        self.subtask_patcher.start()
        self.addCleanup(self.subtask_patcher.stop)

        self.group_mock = MagicMock()
        self.group_patcher = patch('attpcdaq.daq.tasks.group', new=self.group_mock)
        self.group_patcher.start()
        self.addCleanup(self.group_patcher.stop)

    def get_callable(self, which='group'):
        """Get the mock object.

        Parameters
        ----------
        which : str
            If 'group', return the mock Celery ``group`` function. If 'subtask', return the mock
            version of the subtask under test.

        Returns
        -------
        MagicMock
            The mock object.

        """
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
    """A mixin with tests for the 'all' tasks."""

    def test_called_for_all(self: AllTaskTestCaseBase):
        """Test that the task is called for all relevant instances of the relevant model."""
        self.call_task()
        task_calls = self.get_expected_subtask_calls()

        subtask = self.get_callable('subtask')
        self.assertEqual(subtask.call_args_list, task_calls)

        gp = self.get_callable('group')
        self.assertEqual(gp.call_count, 1)         # Check group object was constructed
        gp.return_value.assert_called_once_with()  # Check group object was called


class TestOkWithoutActiveExperimentMixin(object):
    """Tests for tasks that depend on an active experiment."""

    def test_noop_if_no_active_experiment(self: AllTaskTestCaseBase):
        """Tests that nothing happens if there's no active experiment."""
        Experiment.objects.all().update(is_active=False)

        with patch('attpcdaq.daq.tasks.logger', autospec=True) as mock_logger:
            self.call_task()

            gp = self.get_callable('group')
            gp.return_value.assert_not_called()

            mock_logger.exception.assert_not_called()


class ExceptionHandlingTestMixin(object):
    """A mixin with tests for task exception handling."""

    def test_raised_exception(self: TaskTestCaseBase):
        """Test that a raised exception is caught and logged."""
        self.set_mock_effect(ValueError, side_effect=True)
        with self.assertLogs(level=logging.ERROR):
            self.call_task()

    def test_soft_time_limit_exceeded(self: TaskTestCaseBase):
        """Test that a message is logged and the task returns if the time limit is exceeded."""
        self.set_mock_effect(SoftTimeLimitExceeded, side_effect=True)
        with self.assertLogs(level=logging.ERROR) as cm:
            self.call_task()
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], r'Time limit')


class EccServerRefreshStateTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
        )

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.ECCServer.refresh_state'

    def call_task(self, pk=None):
        if pk is None:
            pk = self.ecc.pk
        eccserver_refresh_state_task(pk)

    def test_refresh_state(self):
        """Test that the task works."""
        self.call_task()
        self.get_callable().assert_called_once_with()

    def test_with_invalid_ecc_pk(self):
        """Test that the task logs an error if the pk is invalid."""
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.ecc.pk + 10)


class EccServerRefreshAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin,
                                      TestOkWithoutActiveExperimentMixin, AllTaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
            is_active=True,
        )
        for i in range(10):
            ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address='123.123.123.123',
                experiment=self.experiment,
            )

        self.other_experiment = Experiment.objects.create(
            name='other experiment',
            is_active=False
        )
        ECCServer.objects.create(
            name='Other ECC',
            ip_address='123.123.123.123',
            experiment=self.other_experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.eccserver_refresh_state_task'

    def call_task(self):
        return eccserver_refresh_all_task()

    def get_queryset(self):
        return ECCServer.objects.filter(experiment=self.experiment)


class EccServerChangeStateTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
        )

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            state=ECCServer.IDLE,
            experiment=self.experiment,
        )
        self.target_state = ECCServer.DESCRIBED

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.ECCServer.change_state'

    def call_task(self, pk=None):
        if pk is None:
            pk = self.ecc.pk
        eccserver_change_state_task(pk, self.target_state)

    def test_change_state(self):
        """Test that the task works."""
        self.call_task()
        self.get_callable().assert_called_once_with(self.target_state)

    def test_with_invalid_ecc_pk(self):
        """Test that the task logs an error if the pk is invalid."""
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.ecc.pk + 10)


class CheckEccServerOnlineTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
        )

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            state=ECCServer.IDLE,
            is_online=False,
            experiment=self.experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.WorkerInterface'

    def get_callable(self):
        return self.mock.return_value.__enter__.return_value.check_ecc_server_status

    def call_task(self, pk=None):
        if pk is None:
            pk = self.ecc.pk
        check_ecc_server_online_task(pk)

    def test_check_ecc_server_online(self):
        """Test that the task works."""
        self.set_mock_effect(True)

        self.call_task()
        self.get_callable().assert_called_once_with()

        self.ecc.refresh_from_db()
        self.assertTrue(self.ecc.is_online)

    def test_with_invalid_ecc_pk(self):
        """Test that the task logs an error if the pk is invalid."""
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.ecc.pk + 10)


class CheckEccServerOnlineAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin,
                                          TestOkWithoutActiveExperimentMixin, AllTaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
            is_active=True,
        )

        for i in range(10):
            ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address='123.123.123.123',
                experiment=self.experiment,
            )

        self.other_experiment = Experiment.objects.create(
            name='other experiment',
            is_active=False
        )
        ECCServer.objects.create(
            name='Other ECC',
            ip_address='123.123.123.123',
            experiment=self.other_experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.check_ecc_server_online_task'

    def call_task(self):
        return check_ecc_server_online_all_task()

    def get_queryset(self):
        return ECCServer.objects.filter(experiment=self.experiment)


class CheckDataRouterStatusTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
        )

        self.data_router = DataRouter.objects.create(
            name='DataRouter',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.WorkerInterface'

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
        """Test that the task works."""
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
        """Test that the task logs an error if the pk is invalid."""
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.data_router.pk + 10)

    def test_does_not_check_if_clean_if_not_online(self):
        """Test that the staging directory status is not checked if the server is not online."""
        self.set_mock_effect(False, which='status')
        self.call_task()

        self.mock.assert_called_once_with(self.data_router.ip_address)
        self.get_callable(which='status').assert_called_once_with()
        self.get_callable(which='clean').assert_not_called()


class CheckDataRouterStatusAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin,
                                           TestOkWithoutActiveExperimentMixin, AllTaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
            is_active=True,
        )

        for i in range(10):
            DataRouter.objects.create(
                name='DataRouter{}'.format(i),
                ip_address='123.123.123.123',
                experiment=self.experiment,
            )

        self.other_experiment = Experiment.objects.create(
            name='other experiment',
            is_active=False
        )
        DataRouter.objects.create(
            name='Other router',
            ip_address='123.123.123.123',
            experiment=self.other_experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.check_data_router_status_task'

    def get_queryset(self):
        return DataRouter.objects.filter(experiment=self.experiment)

    def call_task(self):
        return check_data_router_status_all_task()


class OrganizeFilesTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
        )

        self.data_router = DataRouter.objects.create(
            name='DataRouter',
            ip_address='123.456.789.0',
            experiment=self.experiment
        )
        self.run = RunMetadata.objects.create(
            run_number=10,
            experiment=self.experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.WorkerInterface'

    def get_callable(self):
        return self.mock.return_value.__enter__.return_value.organize_files

    def call_task(self, pk=None):
        if pk is None:
            pk = self.data_router.pk
        organize_files_task(pk, self.experiment.pk, self.run.pk)

    def test_organize_files(self):
        """Test that the task works."""
        self.data_router.staging_directory_is_clean = False
        self.data_router.save()

        self.call_task()

        self.mock.assert_called_once_with(self.data_router.ip_address)
        self.get_callable().assert_called_once_with(self.experiment.name, self.run.run_number)

        self.data_router.refresh_from_db()
        self.assertTrue(self.data_router.staging_directory_is_clean)

    def test_with_invalid_data_router_pk(self):
        """Test that the task logs an error if the pk is invalid."""
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.data_router.pk + 10)


class OrganizeFilesAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin, AllTaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
            is_active=True,
        )

        for i in range(10):
            DataRouter.objects.create(
                name='DataRouter{}'.format(i),
                ip_address='123.123.123.123',
                experiment=self.experiment,
            )

        self.other_experiment = Experiment.objects.create(
            name='other experiment',
            is_active=False
        )
        DataRouter.objects.create(
            name='Other router',
            ip_address='123.123.123.123',
            experiment=self.other_experiment,
        )

        self.run = RunMetadata.objects.create(
            run_number=1,
            experiment=self.experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.organize_files_task'

    def get_queryset(self):
        return DataRouter.objects.filter(experiment=self.experiment)

    def call_task(self):
        return organize_files_all_task(self.experiment.pk, self.run.pk)

    def get_expected_subtask_calls(self):
        return super().get_expected_subtask_calls(self.experiment.pk, self.run.pk)


class BackupConfigFilesTaskTestCase(ExceptionHandlingTestMixin, TaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
        )

        self.ecc = ECCServer.objects.create(
            name='ECC',
            ip_address='123.123.123.123',
            experiment=self.experiment,
        )

        self.config = ConfigId.objects.create(
            describe='describe',
            prepare='prepare',
            configure='configure',
            ecc_server=self.ecc,
        )

        self.ecc.selected_config = self.config
        self.ecc.save()

        self.run = RunMetadata.objects.create(
            run_number=1,
            experiment=self.experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.WorkerInterface'

    def get_callable(self):
        return self.mock.return_value.__enter__.return_value.backup_config_files

    def call_task(self, pk=None):
        if pk is None:
            pk = self.ecc.pk
        return backup_config_files_task(pk, self.experiment.pk, self.run.pk)

    def test_backup_files(self):
        """Test that the task works with valid parameters."""
        self.call_task()

        self.mock.assert_called_once_with(self.ecc.ip_address)
        self.get_callable().assert_called_once_with(self.experiment.name, self.run.run_number,
                                                    self.ecc.config_file_paths(), self.ecc.config_backup_root)

    def test_with_invalid_ecc_pk(self):
        """Test that the task logs an error if the pk is invalid."""
        with self.assertLogs(level=logging.ERROR):
            self.call_task(self.ecc.pk + 10)


class BackupConfigFilesAllTaskTestCase(ExceptionHandlingTestMixin, TestCalledForAllMixin, AllTaskTestCaseBase):
    def setUp(self):
        super().setUp()

        self.experiment = Experiment.objects.create(
            name='Test',
            is_active=True,
        )

        for i in range(10):
            ecc = ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address='123.123.123.123',
                experiment=self.experiment,
            )

            config = ConfigId.objects.create(
                describe='describe',
                prepare='prepare',
                configure='configure',
                ecc_server=ecc,
            )

            ecc.selected_config = config
            ecc.save()

        self.other_experiment = Experiment.objects.create(
            name='other experiment',
            is_active=False
        )
        ECCServer.objects.create(
            name='Other ECC',
            ip_address='123.123.123.123',
            experiment=self.other_experiment,
        )

        self.run = RunMetadata.objects.create(
            run_number=1,
            experiment=self.experiment,
        )

    def get_patch_target(self):
        return 'attpcdaq.daq.tasks.backup_config_files_task'

    def get_queryset(self):
        return ECCServer.objects.filter(experiment=self.experiment)

    def call_task(self):
        return backup_config_files_all_task(self.experiment.pk, self.run.pk)

    def get_expected_subtask_calls(self):
        return super().get_expected_subtask_calls(self.experiment.pk, self.run.pk)
