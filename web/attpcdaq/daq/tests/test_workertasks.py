from unittest import TestCase
from unittest.mock import patch, MagicMock, call
import os
from itertools import chain
from io import BytesIO

from ..workertasks import WorkerInterface, mkdir_recursive


class MkdirRecursiveTestCase(TestCase):
    def test_dir_already_exists(self):
        target_path = '/some/path'
        mock = MagicMock()
        mkdir_recursive(mock, target_path)

        mock.chdir.assert_called_once_with(target_path)
        mock.mkdir.assert_not_called()

    def test_basedir_exists(self):
        target_path = '/some/path'
        mock = MagicMock()

        good_dirs = ['/some']

        def chdir_side_effect(arg):
            if arg not in good_dirs:
                raise FileNotFoundError()

        mock.chdir.side_effect = chdir_side_effect
        mock.mkdir.side_effect = lambda x: good_dirs.append(x)

        mkdir_recursive(mock, target_path)

        expect = [call(target_path), call(os.path.dirname(target_path)), call(os.path.basename(target_path))]
        self.assertEqual(mock.chdir.call_args_list, expect)
        mock.mkdir.assert_called_once_with(os.path.basename(target_path))

    def test_make_two_levels(self):
        target_path = '/some/long/path'
        mock = MagicMock()

        good_dirs = ['/some']

        def chdir_side_effect(arg):
            if arg not in good_dirs:
                raise FileNotFoundError()

        mock.chdir.side_effect = chdir_side_effect
        mock.mkdir.side_effect = lambda x: good_dirs.append(x)

        mkdir_recursive(mock, target_path)

        mkdir_calls = [call('long'), call('path')]
        self.assertEqual(mock.mkdir.call_args_list, mkdir_calls)

        chdir_calls = [
            call('/some/long/path'),
            call('/some/long'),
            call('/some'),
            call('long'),
            call('path'),
        ]
        self.assertEqual(mock.chdir.call_args_list, chdir_calls)

    def test_root_path(self):
        target_path = '/'
        mock = MagicMock()

        mkdir_recursive(mock, target_path)

        mock.chdir.assert_called_once_with(target_path)
        mock.mkdir.assert_not_called()

    def test_empty_path(self):
        target_path = ''
        mock = MagicMock()

        mkdir_recursive(mock, target_path)

        mock.chdir.assert_not_called()
        mock.mkdir.assert_not_called()

    def test_tilde_in_path(self):
        target_path = '~/some/path'
        mock = MagicMock()

        with self.assertRaisesRegex(ValueError, r'Cannot handle'):
            mkdir_recursive(mock, target_path)

        mock.mkdir.assert_not_called()
        mock.chdir.assert_not_called()


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

    def _check_process_impl(self, client, ecc_server_running=True, data_router_running=True):
        if ecc_server_running:
            ecc_line = ' 1234 ??         0:01.23 /path/to/getEccSoapServer --args something\n'
        else:
            ecc_line = ''

        if data_router_running:
            data_router_line = ' 1235 ??         0:03.45 /path/to/dataRouter --args 123.345.567.789\n'
        else:
            data_router_line = ''

        client.exec_command.return_value = ([], (ecc_line, data_router_line), [])

        with WorkerInterface(self.hostname) as wint:
            ecc_server_running_res, data_router_running_res = wint.check_process_status()

        self.assertIs(ecc_server_running_res, ecc_server_running)
        self.assertIs(data_router_running_res, data_router_running)

    def _check_ecc_running_impl(self, mock_client, is_running):
        if is_running:
            ecc_line = ' 1234 ??         0:01.23 /path/to/getEccSoapServer --args something\n'
        else:
            ecc_line = ''

        client = mock_client.return_value
        client.exec_command.return_value = ([], (ecc_line,), [])

        with WorkerInterface(self.hostname) as wint:
            ecc_server_running_res = wint.check_ecc_server_status()

        self.assertIs(ecc_server_running_res, is_running)

    def test_check_ecc_running_when_true(self, mock_client, mock_config):
        self._check_ecc_running_impl(mock_client, True)

    def test_check_ecc_running_when_false(self, mock_client, mock_config):
        self._check_ecc_running_impl(mock_client, False)

    def _check_data_router_running_impl(self, mock_client, is_running):
        if is_running:
            dr_line = ' 1234 ??         0:01.23 /path/to/dataRouter --args something\n'
        else:
            dr_line = ''

        client = mock_client.return_value
        client.exec_command.return_value = ([], [dr_line], [])

        with WorkerInterface(self.hostname) as wint:
            dr_status_result = wint.check_data_router_status()

        self.assertIs(dr_status_result, is_running)

    def test_check_data_router_running_when_true(self, mock_client, mock_config):
        self._check_data_router_running_impl(mock_client, True)

    def test_check_data_router_running_when_false(self, mock_client, mock_config):
        self._check_data_router_running_impl(mock_client, False)

    @patch('attpcdaq.daq.workertasks.WorkerInterface.find_data_router')
    def test_get_graw_list(self, mock_find_data_router, mock_client, mock_config):
        mock_open_sftp = mock_client.return_value.open_sftp
        mock_sftp = mock_open_sftp.return_value.__enter__.return_value

        mock_find_data_router.return_value = self.router_path

        file_list = ['file1.graw', 'file2.graw', 'file3.graw', 'file4.txt', 'file5.html']
        mock_sftp.listdir.return_value = file_list

        with WorkerInterface(self.hostname) as wint:
            result = wint.get_graw_list()

        mock_find_data_router.assert_called_once_with()
        mock_open_sftp.assert_called_once_with()
        mock_sftp.listdir.assert_called_once_with(self.router_path)

        expect = [os.path.join(self.router_path, f) for f in file_list[:3]]
        self.assertEqual(result, expect)

    @patch('attpcdaq.daq.workertasks.mkdir_recursive')
    @patch('attpcdaq.daq.workertasks.WorkerInterface.get_graw_list')
    @patch('attpcdaq.daq.workertasks.WorkerInterface.find_data_router')
    def test_organize_files(self, mock_find_data_router, mock_get_graw_list, mock_mkdir, mock_client, mock_config):
        # Shortcuts to mocks
        mock_sftp = mock_client.return_value.open_sftp.return_value.__enter__.return_value

        # Experiment info
        exp_name = 'experiment name'
        run_number = 1

        # Build file paths
        full_src_graws = [os.path.join(self.router_path, g) for g in self.graw_list]
        dest_dir = os.path.join(self.router_path, exp_name, 'run_{:04d}'.format(run_number))
        full_dest_graws = [os.path.join(dest_dir, g) for g in self.graw_list]

        # Set side effects
        mock_find_data_router.return_value = self.router_path
        mock_get_graw_list.return_value = full_src_graws

        # Call method
        with WorkerInterface(self.hostname) as wint:
            wint.organize_files(exp_name, run_number)

        # Check calls
        mock_find_data_router.assert_called_once_with()
        mock_get_graw_list.assert_called_once_with()

        expected_calls = [call(s, d) for s, d in zip(full_src_graws, full_dest_graws)]
        self.assertEqual(mock_sftp.rename.call_args_list, expected_calls)

    @patch('attpcdaq.daq.workertasks.mkdir_recursive')
    @patch('attpcdaq.daq.workertasks.WorkerInterface.get_graw_list')
    @patch('attpcdaq.daq.workertasks.WorkerInterface.find_data_router')
    def test_organize_files_failure(self, mock_find_data_router, mock_get_graw_list, mock_mkdir, mock_client, mock_config):
        # Shortcuts to mocks
        mock_sftp = mock_client.return_value.open_sftp.return_value.__enter__.return_value

        # Experiment info
        exp_name = 'experiment name'
        run_number = 1

        # Set side effects
        mock_get_graw_list.return_value = self.graw_list  # Not full paths, but that's not important here
        mock_sftp.rename.side_effect = FileNotFoundError('Something happened')
        mock_find_data_router.return_value = self.router_path

        # Call method
        with self.assertRaises(FileNotFoundError):
            with WorkerInterface(self.hostname) as wint:
                wint.organize_files(exp_name, run_number)

    @patch('attpcdaq.daq.workertasks.WorkerInterface.find_data_router')
    def test_build_run_dir_path(self, mock_find_data_router, mock_client, mock_config):
        mock_find_data_router.return_value = self.router_path

        exp_name = 'experiment'
        run_num = 1
        run_name = 'run_{:04d}'.format(run_num)

        expect = os.path.join(self.router_path, exp_name, run_name)

        with WorkerInterface(self.hostname) as wint:
            result = wint.build_run_dir_path(exp_name, run_num)

        self.assertEqual(result, expect)
        mock_find_data_router.assert_called_once_with()

    @patch('attpcdaq.daq.workertasks.mkdir_recursive')
    def test_backup_config_files(self, mock_mkdir, mock_client, mock_config):
        mock_sftp = mock_client.return_value.open_sftp.return_value.__enter__.return_value

        dest_root = '/backup/destination'

        exp_name = 'experiment'
        run_num = 1
        run_name = 'run_{:04d}'.format(run_num)

        backup_dest = os.path.join(dest_root, exp_name, run_name)

        src_paths = ['/some/config/file1.xcfg', '/some/config/file2.xcfg']
        dest_paths = [os.path.join(backup_dest, os.path.basename(s)) for s in src_paths]

        mock_file = mock_sftp.open.return_value.__enter__.return_value
        sample_contents = b'Some file contents'
        mock_file.read.return_value = sample_contents

        with WorkerInterface(self.hostname) as wint:
            wint.backup_config_files(exp_name, run_num, src_paths, dest_root)

        mock_mkdir.assert_called_once_with(mock_sftp, backup_dest)

        expected_calls = list(chain.from_iterable(zip(
            (call(f, 'r') for f in src_paths),
            (call(f, 'w') for f in dest_paths)
        )))

        self.assertEqual(mock_sftp.open.call_args_list, expected_calls)
        self.assertEqual(mock_file.read.call_count, len(src_paths))
        self.assertEqual(mock_file.write.call_args_list, [call(sample_contents)] * len(dest_paths))

    def test_tail_file(self, mock_client, mock_config):
        path = '/path/to/file'
        contents = 'Sample\nfile\ncontents\nwith\nfive\nlines'
        num_lines = 3
        buffer = BytesIO(bytes(contents, 'ascii'))

        mock_sftp = mock_client.return_value.open_sftp.return_value.__enter__.return_value
        mock_file = mock_sftp.open.return_value.__enter__.return_value

        mock_file.seek.side_effect = buffer.seek
        mock_file.read.side_effect = buffer.read
        mock_file.tell.side_effect = buffer.tell

        with WorkerInterface(self.hostname) as wint:
            result = wint.tail_file(path, num_lines=num_lines)

        expect = '\n'.join(contents.splitlines()[-3:])
        self.assertEqual(result, expect)

        mock_sftp.open.assert_called_once_with(path, 'r')

