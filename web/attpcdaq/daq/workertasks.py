"""Tasks to be performed on the DAQ workers, where the data router and ECC server run.

This module uses the Paramiko SSH library to connect to the nodes running the data router to,
for example, organize files at the end of a run.

"""

from paramiko.client import SSHClient
from paramiko.config import SSHConfig
from paramiko.sftp_file import SFTPFile
from paramiko import AutoAddPolicy
import os
import re


def mkdir_recursive(sftp, path):
    """Recursively create the directory tree given by ``path``.

    This emulates ``mkdir -p`` on the remote system.

    Parameters
    ----------
    sftp : paramiko.sftp_client.SFTPClient
        The SFTP client object. This should be connected to the remote host.
    path : str
        The path that needs to be created.

    Raises
    ------
    ValueError
        If the path contains a '~'. Home directory expansion is not currently supported on the remote host.

    """
    # Based on http://stackoverflow.com/a/14819803/3820658
    if '~' in path:
        raise ValueError('Cannot handle ~ in remote directory.')

    if path == '':
        return
    elif path == '/':
        sftp.chdir(path)
        return

    try:
        sftp.chdir(path)
    except IOError:
        head, tail = os.path.split(path.rstrip('/'))
        mkdir_recursive(sftp, head)
        sftp.mkdir(tail)
        sftp.chdir(tail)
        return


class WorkerInterface(object):
    """An interface to perform tasks on the DAQ worker nodes.

    This is used perform tasks on the computers running the data router and the ECC server. This includes things
    like cleaning up the data files at the end of each run.

    The connection is made using SSH, and the SSH config file at ``config_path`` is honored in making the connection.
    Additionally, the server *must* accept connections authenticated using a public key, and this public key must
    be available in your ``.ssh`` directory.

    Parameters
    ----------
    hostname : str
        The hostname to connect to.
    port : int, optional
        The port that the SSH server is listening on. The default is 22.
    username : str, optional
        The username to use. If it isn't provided, a username will be read from the SSH config file. If no username
        is listed there, the name of the user running the code will be used.
    config_path : str, optional
        The path to the SSH config file. The default is ``~/.ssh/config``.

    """
    def __init__(self, hostname, port=22, username=None, config_path=None):
        self.hostname = hostname
        self.client = SSHClient()

        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(AutoAddPolicy())

        if config_path is None:
            config_path = os.path.join(os.path.expanduser('~'), '.ssh', 'config')
        self.config = SSHConfig()
        with open(config_path) as config_file:
            self.config.parse(config_file)

        if hostname in self.config.get_hostnames():
            host_cfg = self.config.lookup(hostname)
            full_hostname = host_cfg.get('hostname', hostname)
            if username is None:
                username = host_cfg.get('user', None)  # If none, it will try the user running the server.
        else:
            full_hostname = hostname

        self.client.connect(full_hostname, port, username=username)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def find_data_router(self):
        """Find the working directory of the data router process.

        The directory is found using ``lsof``, which must be available on the remote system.

        Returns
        -------
        str
            The directory where the data router is running, and therefore writing data.

        Raises
        ------
        RuntimeError
            If ``lsof`` finds something strange instead of a process called ``dataRouter``.

        """
        stdin, stdout, stderr = self.client.exec_command('lsof -a -d cwd -c dataRouter -Fcn')
        for line in stdout:
            if line[0] == 'c' and not re.match('cdataRouter', line):
                raise RuntimeError("lsof found {} instead of dataRouter".format(line[1:].strip()))
            elif line[0] == 'n':
                return line[1:].strip()
        else:
            raise RuntimeError("lsof didn't find dataRouter")

    def get_graw_list(self):
        """Get a list of GRAW files in the data router's working directory.

        Returns
        -------
        list[str]
            A list of the full paths to the GRAW files.

        """
        data_dir = self.find_data_router()

        with self.client.open_sftp() as sftp:
            full_list = sftp.listdir(data_dir)

        graws = filter(lambda s: re.match(r'.*\.graw$', s), full_list)
        full_graw_paths = (os.path.join(data_dir, filename) for filename in graws)

        return list(full_graw_paths)

    def working_dir_is_clean(self):
        """Check if there are GRAW files in the data router's working directory.

        Returns
        -------
        bool
            True if there are files in the working directory, False otherwise.
        """
        return len(self.get_graw_list()) == 0

    def _check_process_status(self, process_name):
        """Checks if the given process is running.

        Parameters
        ----------
        process_name : str
            The name of the process to look for

        Returns
        -------
        bool
            True if the process is running.
        """

        _, stdout, _ = self.client.exec_command('ps -e')

        for line in stdout:
            if re.search(process_name, line):
                return True
        else:
            return False

    def check_ecc_server_status(self):
        """Checks if the ECC server is running.

        Returns
        -------
        bool
            True if ``getEccSoapServer`` is running.
        """
        return self._check_process_status(r'getEccSoapServer')

    def check_data_router_status(self):
        """Checks if the data router is running.

        Returns
        -------
        bool
            True if ``dataRouter`` is running.
        """
        return self._check_process_status(r'dataRouter')

    def build_run_dir_path(self, experiment_name, run_number):
        """Get the path to the directory for a given run.

        This returns a path of the format ``experiment_name/run_name`` under the directory where the data router
        is running. The ``run_name``, in this case, has the format ``run_NNNN``.

        Parameters
        ----------
        experiment_name : str
            The name of the experiment directory.
        run_number : int
            The run number.

        Returns
        -------
        run_dir : str
            The full path to the run directory. *This should be escaped before passing it to a shell command.*

        """
        pwd = self.find_data_router()
        run_name = 'run_{:04d}'.format(run_number)  # run_0001, run_0002, etc.
        run_dir = os.path.join(pwd, experiment_name, run_name)
        return run_dir

    def organize_files(self, experiment_name, run_number):
        """Organize the GRAW files at the end of a run.

        This will get a list of the files written in the working directory of the data router and move them to
        the directory ``./experiment_name/run_name``, which will be created if necessary. For example, if
        the ``experiment_name`` is "test" and the ``run_number`` is 4, the files will be placed in ``./test/run_0004``.

        Parameters
        ----------
        experiment_name : str
            A name for the experiment directory.
        run_number : int
            The current run number.

        """
        run_dir = self.build_run_dir_path(experiment_name, run_number)

        graws = self.get_graw_list()

        with self.client.open_sftp() as sftp:
            mkdir_recursive(sftp, run_dir)
            for srcpath in graws:
                _, srcfile = os.path.split(srcpath)
                destpath = os.path.join(run_dir, srcfile)
                sftp.rename(srcpath, destpath)

    def backup_config_files(self, experiment_name, run_number, file_paths, backup_root):
        """Makes a copy of the config files on the remote computer.

        The files are copied to a subdirectory ``experiment_name/run_name`` of ``backup_root``.

        Parameters
        ----------
        experiment_name : str
            The name of the experiment.
        run_number : int
            The run number.
        file_paths : iterable of str
            The *full* paths to the config files.
        backup_root : str
            Where the backups should be written.

        """
        run_name = 'run_{:04d}'.format(run_number)
        backup_dest = os.path.join(backup_root, experiment_name, run_name)

        with self.client.open_sftp() as sftp:
            mkdir_recursive(sftp, backup_dest)
            for source_path in file_paths:
                dest_path = os.path.join(backup_dest, os.path.basename(source_path))
                with sftp.open(source_path, 'r') as src, sftp.open(dest_path, 'w') as dest:
                    buffer = src.read()
                    dest.write(buffer)

    def tail_file(self, path, num_lines=50):
        """Retrieve the tail of a text file on the remote host.

        Note that this assumes the file is ASCII-encoded plain text.

        Parameters
        ----------
        path : str
            Path to the file.
        num_lines : int
            The number of lines to include.

        Returns
        -------
        str
            The tail of the file's contents.
        """
        # Based on https://gist.github.com/volker48/3437288
        with self.client.open_sftp() as sftp:
            with sftp.open(path, 'r') as f:
                f.seek(-1, SFTPFile.SEEK_END)
                lines = 0
                while lines < num_lines and f.tell() > 0:
                    char = f.read(1)
                    if char == b'\n':
                        lines += 1
                        if lines == num_lines:
                            break
                    f.seek(-2, SFTPFile.SEEK_CUR)

                return f.read().decode('ascii')
