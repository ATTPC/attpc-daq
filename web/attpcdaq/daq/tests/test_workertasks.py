from unittest import TestCase
from unittest.mock import patch, MagicMock, call
import os

from ..workertasks import WorkerInterface

@patch('attpcdaq.daq.workertasks.SSHConfig')
@patch('attpcdaq.daq.workertasks.SSHClient')
class WorkerInterfaceTestCase(TestCase):

    def setUp(self):
        self.hostname = 'hostname'
        self.full_hostname = 'full_hostname'
        self.user = 'username'
        self.router_path = '/path/to/router'
        self.graw_list = ['test1.graw', 'test2.graw']

    def test_initialize_loads_host_keys(self, mock_client, mock_config):
        wint = WorkerInterface(self.hostname)
        client = mock_client.return_value
        client.load_system_host_keys.assert_called_once_with()

    @patch('attpcdaq.daq.workertasks.open')
    def test_initialize_finds_default_ssh_config_path(self, mock_open, mock_client, mock_config):
        wint = WorkerInterface(self.hostname)
        exp_path = os.path.expanduser('~/.ssh/config')
        mock_open.assert_called_once_with(exp_path)

    @patch('attpcdaq.daq.workertasks.open')
    def test_initialize_with_config_path(self, mock_open, mock_client, mock_config):
        path = '/path/to/file'
        wint = WorkerInterface(self.hostname, config_path=path)
        mock_open.assert_called_once_with(path)

    def test_hostname_lookup(self, mock_client, mock_config):
        mock_host_cfg = MagicMock(spec=dict)
        mock_host_cfg.get.side_effect = {'hostname': self.full_hostname,
                                         'user': self.user}.get

        config = mock_config.return_value
        config.lookup.return_value = mock_host_cfg
        config.get_hostnames.return_value = [self.hostname]

        wint = WorkerInterface(self.hostname)

        expected_get_calls = [call('hostname', self.hostname), call('user', None)]
        self.assertEqual(mock_host_cfg.get.call_args_list, expected_get_calls)

        client = mock_client.return_value
        client.connect.assert_called_once_with(self.full_hostname, 22, username=self.user)

    def test_exit_closes_connection(self, mock_client, mock_config):
        client = mock_client.return_value

        with WorkerInterface(self.hostname) as wint:
            pass

        client.close.assert_called_once_with()

    def test_find_data_router(self, mock_client, mock_config):
        true_drpath = '/path/to/router'
        client = mock_client.return_value
        fake_lsof_return = ('p1234\n', 'cdataRouter\n', 'n{}\n'.format(true_drpath))
        client.exec_command.return_value = ([], fake_lsof_return, [])

        with WorkerInterface(self.hostname) as wint:
            drpath = wint.find_data_router()

        self.assertEqual(drpath, true_drpath)

    def test_find_data_router_not_running(self, mock_client, mock_config):
        client = mock_client.return_value
        client.exec_command.return_value = ([], [], [])

        with WorkerInterface(self.hostname) as wint:
            self.assertRaisesRegex(RuntimeError, r"lsof didn't find dataRouter",
                                   wint.find_data_router)

    def test_find_data_router_gets_junk(self, mock_client, mock_config):
        client = mock_client.return_value

        fake_lsof_return = ('p1234\n', 'csomeProgram\n', 'n/some/path\n')
        client.exec_command.return_value = ([], fake_lsof_return, [])

        with WorkerInterface(self.hostname) as wint:
            self.assertRaisesRegex(RuntimeError, r"lsof found .* instead of dataRouter",
                                   wint.find_data_router)

    @patch('attpcdaq.daq.workertasks.WorkerInterface.get_graw_list')
    @patch('attpcdaq.daq.workertasks.WorkerInterface.find_data_router')
    def test_organize_files(self, mock_find_data_router, mock_get_graw_list, mock_client, mock_config):
        mock_find_data_router.return_value = self.router_path
        mock_get_graw_list.return_value = self.graw_list

        exp_name = 'experiment_name'
        run_number = 1

        with WorkerInterface(self.hostname) as wint:
            wint.organize_files(exp_name, run_number)

        mock_find_data_router.assert_called_once_with()
        mock_get_graw_list.assert_called_once_with()

        mkdir_call = call('mkdir -p /path/to/router/experiment_name/run_0001')
        mv_call = call('mv test1.graw test2.graw /path/to/router/experiment_name/run_0001')
        client = mock_client.return_value
        self.assertEqual(client.exec_command.call_args_list, [mkdir_call, mv_call])

    @patch('attpcdaq.daq.workertasks.WorkerInterface.get_graw_list')
    @patch('attpcdaq.daq.workertasks.WorkerInterface.find_data_router')
    def test_organize_files_spaces_escaped(self, mock_find_data_router, mock_get_graw_list,
                                           mock_client, mock_config):
        mock_find_data_router.return_value = self.router_path
        mock_get_graw_list.return_value = self.graw_list

        exp_name = 'name with spaces'
        run_number = 1

        with WorkerInterface(self.hostname) as wint:
            wint.organize_files(exp_name, run_number)

        mock_find_data_router.assert_called_once_with()
        mock_get_graw_list.assert_called_once_with()

        mkdir_call = call(r"mkdir -p '/path/to/router/name with spaces/run_0001'")
        mv_call = call(r"mv test1.graw test2.graw '/path/to/router/name with spaces/run_0001'")
        client = mock_client.return_value
        self.assertEqual(client.exec_command.call_args_list, [mkdir_call, mv_call])







