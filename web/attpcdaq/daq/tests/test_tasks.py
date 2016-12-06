"""Unit tests for Celery tasks"""

from django.test import TestCase
from unittest.mock import patch

from ..tasks import organize_files_task, organize_files_all_task
from ..models import ECCServer, DataRouter, DataSource, Experiment


@patch('attpcdaq.daq.tasks.WorkerInterface')
class OrganizeFilesTestCase(TestCase):
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
