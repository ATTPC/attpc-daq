"""Tasks to be performed on the DAQ workers, where the data router and ECC server run.

This module uses the Paramiko SSH library to connect to the nodes running the data router to,
for example, organize files at the end of a run.

"""

from paramiko.client import SSHClient
from paramiko.config import SSHConfig
from paramiko import WarningPolicy
import os
import re


class WorkerInterface(object):
    """An interface to perform tasks on the DAQ worker nodes.

    This is used perform tasks on the computers running the data router and the ECC server. This includes things
    like cleaning up the data files at the end of each run.

    The connection is made using SSH, and the SSH config file at `config_path` is honored in making the connection.
    Additionally, the server *must* accept connections authenticated using a public key, and this public key must
    be available in your `.ssh` directory.

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
        The path to the SSH config file. The default is `~/.ssh/config`.

    """
    def __init__(self, hostname, port=22, username=None, config_path=None):
        self.hostname = hostname
        self.client = SSHClient()

        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(WarningPolicy())

        if config_path is None:
            config_path = os.path.join(os.path.expanduser('~'), '.ssh', 'config')
        self.config = SSHConfig()
        self.config.parse(config_path)

        if hostname in self.config.get_hostnames():
            host_cfg = self.config.lookup(hostname)
            full_hostname = host_cfg.get('hostname', default=hostname)
            if username is None:
                username = host_cfg.get('user', default=None)  # If none, it will try the user running the server.
        else:
            full_hostname = hostname

        self.client.connect(full_hostname, port, username=username)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def find_data_router(self):
        """Find the working directory of the data router process.

        The directory is found using `lsof`, which must be available on the remote system.

        Returns
        -------
        str
            The directory where the data router is running, and therefore writing data.

        Raises
        ------
        RuntimeError
            If `lsof` finds something strange instead of a process called `dataRouter`.

        """
        stdin, stdout, stderr = self.client.exec_command('lsof -a -d cwd -c dataRouter -Fcn')
        for line in stdout:
            if line[0] == 'c' and not re.match('cdataRouter', line):
                raise RuntimeError("lsof didn't find dataRouter. Process name found was {}".format(line[1:]))
            elif line[0] == 'n':
                return line[1:].strip()

    def get_graw_list(self):
        """Get a list of GRAW files in the data router's working directory.

        Returns
        -------
        list[str]
            A list of the file names.

        """
        pwd = self.find_data_router()

        _, stdout, _ = self.client.exec_command('ls -1 {}'.format(os.path.join(pwd, '*.graw')))

        graws = []
        for line in stdout:
            line = line.strip()
            if re.search(r'\.graw$', line):
                graws.append(line)

        return graws

    def organize_files(self, experiment_name, run_number):
        """Organize the GRAW files at the end of a run.

        This will get a list of the files written in the working directory of the data router and move them to
        the directory `./experiment_name/run_name`, which will be created if necessary. For example, if
        the `experiment_name` is "test" and the `run_number` is 4, the files will be placed in `./test/run_0004`.

        Parameters
        ----------
        experiment_name : str
            A name for the experiment directory.
        run_number : int
            The current run number.

        """
        pwd = self.find_data_router()
        run_name = 'run_{:04d}'.format(run_number)  # run_0001, run_0002, etc.
        run_dir = os.path.join(pwd, experiment_name, run_name)

        graws = self.get_graw_list()

        self.client.exec_command('mkdir -p {}'.format(run_dir))

        self.client.exec_command('mv {} {}'.format(' '.join(graws), run_dir))
