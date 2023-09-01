import json
import logging
from base64 import b64decode, standard_b64encode
from time import sleep, time

import libvirt
import libvirt_qemu

from ..exceptions import GuestAgentError
from .base import VirtualMachineBase


logger = logging.getLogger(__name__)

QEMU_TIMEOUT = 60  # in seconds
POLL_INTERVAL = 0.3  # also in seconds


class GuestAgent(VirtualMachineBase):
    """
    Interacting with QEMU guest agent. Methods:

    execute()
        Low-level method for executing QEMU command as dict. Command dict
        internally converts to JSON. See method docstring for more info.
    shellexec()
        High-level method for executing shell commands on guest. Command
        must be passed as string. Wraps execute() method.
    """

    def __init__(self, domain: libvirt.virDomain, timeout: int | None = None,
                 flags: int | None = None):
        super().__init__(domain)
        self.timeout = timeout or QEMU_TIMEOUT  # timeout for guest agent
        self.flags = flags or libvirt_qemu.VIR_DOMAIN_QEMU_MONITOR_COMMAND_DEFAULT
        self.last_pid = None

    def execute(self,
                command: dict,
                stdin: str | None = None,
                capture_output: bool = False,
                decode_output: bool = False,
                wait: bool = True,
                timeout: int = QEMU_TIMEOUT
                ) -> tuple[bool | None, int | None, str | None, str | None]:
        """
        Execute command on guest and return output if `capture_output` is True.
        See https://wiki.qemu.org/Documentation/QMP for QEMU commands reference.
        If `wait` is True poll guest command output with POLL_INTERVAL. Raise
        GuestAgentError on `timeout` reached (in seconds).
        Return values:
            tuple(
                exited: bool | None,
                exitcode: int | None,
                stdout: str | None,
                stderr: str | None
            )
        stdout and stderr are base64 encoded strings or None. stderr and stdout
        will be decoded if `decode_output` is True.
        """
        # todo command dict schema validation
        if capture_output:
            command['arguments']['capture-output'] = True
        if isinstance(stdin, str):
            command['arguments']['input-data'] = standard_b64encode(
                stdin.encode('utf-8')).decode('utf-8')

        # Execute command on guest
        cmd_out = self._execute(command)

        if capture_output:
            self.last_pid = json.loads(cmd_out)['return']['pid']
            return self._get_cmd_result(
                self.last_pid,
                decode_output=decode_output,
                wait=wait,
                timeout=timeout,
            )
        return None, None, None, None

    def shellexec(self,
                  command: str,
                  stdin: str | None = None,
                  executable: str = '/bin/sh',
                  capture_output: bool = False,
                  decode_output: bool = False,
                  wait: bool = True,
                  timeout: int = QEMU_TIMEOUT
                  ) -> tuple[bool | None, int | None, str | None, str | None]:
        """
        Execute command on guest with selected shell. /bin/sh by default.
        Otherwise of execute() this function brings shell command as string.
        """
        cmd = {
            'execute': 'guest-exec',
            'arguments': {
                'path': executable,
                'arg': ['-c', command],
            }
        }
        return self.execute(
            cmd,
            stdin=stdin,
            capture_output=capture_output,
            decode_output=decode_output,
            wait=wait,
            timeout=timeout,
        )

    def poll_pid(self, pid: int):
        # Нужно цепляться к PID и вывести результат
        pass

    def _execute(self, command: dict):
        logging.debug('Execute command: vm=%s cmd=%s', self.domain_name,
                      command)
        if self.domain_info['state'] != libvirt.VIR_DOMAIN_RUNNING:
            raise GuestAgentError(
                f'Cannot execute command: vm={self.domain_name} is not running')
        try:
            return libvirt_qemu.qemuAgentCommand(
                self.domain,  # virDomain object
                json.dumps(command),
                self.timeout,
                self.flags,
            )
        except libvirt.libvirtError as err:
            raise GuestAgentError(
                f'Cannot execute command on vm={self.domain_name}: {err}'
            ) from err

    def _get_cmd_result(
            self, pid: int, decode_output: bool = False, wait: bool = True,
            timeout: int = QEMU_TIMEOUT):
        """Get executed command result. See GuestAgent.execute() for info."""
        cmd = {'execute': 'guest-exec-status', 'arguments': {'pid': pid}}

        if not wait:
            output = json.loads(self._execute(cmd))
            return self._return_tuple(output, decode=decode_output)

        logger.debug('Start polling command pid=%s on vm=%s', pid,
                     self.domain_name)
        start_time = time()
        while True:
            output = json.loads(self._execute(cmd))
            if output['return']['exited']:
                break
            sleep(POLL_INTERVAL)
            now = time()
            if now - start_time > timeout:
                raise GuestAgentError(
                    f'Polling command pid={pid} on vm={self.domain_name} '
                    f'took longer than {timeout} seconds.'
                )
        logger.debug('Polling command pid=%s on vm=%s finished, '
                     'time taken: %s seconds',
                     pid, self.domain_name, int(time() - start_time))
        return self._return_tuple(output, decode=decode_output)

    def _return_tuple(self, output: dict, decode: bool = False):
        output = output['return']
        exited = output['exited']
        exitcode = output['exitcode']
        stdout = stderr = None

        if 'out-data' in output.keys():
            stdout = output['out-data']
        if 'err-data' in output.keys():
            stderr = output['err-data']

        if decode:
            stdout = b64decode(stdout).decode('utf-8') if stdout else None
            stderr = b64decode(stderr).decode('utf-8') if stderr else None

        return exited, exitcode, stdout, stderr
