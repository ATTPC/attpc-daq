from paramiko.client import SSHClient
from paramiko.config import SSHConfig
from paramiko import WarningPolicy
import os
import re


class WorkerInterface(object):
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
        stdin, stdout, stderr = self.client.exec_command('lsof -a -d cwd -c dataRouter -Fcn')
        for line in stdout:
            if line[0] == 'c' and not re.match('cdataRouter', line):
                raise RuntimeError("lsof didn't find dataRouter. Process name found was {}".format(line[1:]))
            elif line[0] == 'n':
                return line[1:].strip()

    def get_graw_list(self):
        pwd = self.find_data_router()

        _, stdout, _ = self.client.exec_command('ls -1 {}'.format(os.path.join(pwd, '*.graw')))

        graws = []
        for line in stdout:
            line = line.strip()
            if re.search(r'\.graw$', line):
                graws.append(line)

        return graws

    def organize_files(self, experiment_name, run_number):
        pwd = self.find_data_router()
        run_name = 'run_{:04d}'.format(run_number)  # run_0001, run_0002, etc.
        run_dir = os.path.join(pwd, experiment_name, run_name)

        graws = self.get_graw_list()

        self.client.exec_command('mkdir -p {}'.format(run_dir))

        self.client.exec_command('mv {} {}'.format(' '.join(graws), run_dir))
