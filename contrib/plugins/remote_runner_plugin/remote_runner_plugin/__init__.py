# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import socket

import paramiko
from oslo_config import cfg as config
from oslo_log import log as logging

import cfg

CONF = config.CONF

LOG = logging.getLogger(__name__)


class RemoteRunner(object):
    FILE = 'rrscript'
    ROOT = 'root'

    def __init__(self, host, user, timeout, sudo):
        """ Shell script runner on a remote host.

        :param host: the remote host to execute a shell script
        :param user: ssh user to connect to remote host
        :param timeout: command timeout
        :param sudo: execute a command as root
        """
        LOG.info('Host = {host}'.format(host=host))
        LOG.info('User = {user}'.format(user=user))
        LOG.info('Timeout = {timeout}'.format(timeout=timeout))
        LOG.info('Sudo = {sudo}'.format(sudo=sudo))
        LOG.info('Key file name = {key_filename}'.format(
            key_filename=CONF.remote_runner.key_filename))

        self.host = host
        self.user = user
        self.timeout = timeout
        self.sudo = sudo
        self.key_filename = CONF.remote_runner.key_filename

    @classmethod
    def init_plugin(cls):
        LOG.info('Initializing remote runner...')
        cls.CONF = cfg.init_config(CONF)

    def run(self, script, **kwargs):
        if kwargs:
            script = script.format(**kwargs)

        with paramiko.SSHClient() as ssh:
            try:
                # connect to remote machine
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.host, username=self.user,
                            key_filename=self.key_filename,
                            timeout=self.timeout)

                # create a shell file
                with ssh.open_sftp() as sftp:
                    with sftp.file('{file}.sh'.format(file=self.FILE), 'w', -1) as f:
                        f.write('#!/bin/bash\n')
                        for line in script.splitlines():
                            f.write(line)
                            f.write('\n')
                        f.flush()

                cmd = 'chmod +x {file}.sh && ./{file}.sh'.format(file=self.FILE)
                # add sudo if it is required
                if self.sudo and self.user != self.ROOT:
                    cmd = 'sudo bash -c \'{cmd}\''.format(cmd=cmd)

                # execute a command
                _, stdout, stderr = ssh.exec_command(cmd)
                if stdout:
                    LOG.info('Executing the command \"{cmd}\" ...'.format(cmd=cmd))
                    for out in stdout:
                        LOG.info('{out}'.format(out=out.strip()))
                if stderr:
                    for err in stderr:
                        LOG.error('{err}'.format(err=err.strip()))
            except (socket.error, paramiko.SSHException) as e:
                LOG.error(e.message)
                raise
