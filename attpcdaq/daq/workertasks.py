from paramiko.client import SSHClient
from paramiko import WarningPolicy
import os
import re


class WorkerInterface(object):
    def __init__(self, address, port=22, username=None):
        self.address = address
        self.client = SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(WarningPolicy())
        self.client.connect(address, port, username=username)

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
        run_dir = os.path.join(pwd, experiment_name, run_number)

        graws = self.get_graw_list()

        self.client.exec_command('mkdir -p {}'.format(run_dir))

        self.client.exec_command('mv {} {}'.format(' '.join(graws), run_dir))
