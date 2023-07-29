import json
import logging
from time import time, sleep
from base64 import standard_b64encode, b64decode

import libvirt
import libvirt_qemu

from ..main import LibvirtSession
from ..exceptions import QemuAgentError
from .base import VirtualMachineBase


logger = logging.getLogger(__name__)


QEMU_TIMEOUT = 60  # seconds
POLL_INTERVAL = 0.3  # also seconds


class QemuAgent(VirtualMachineBase):
    """
    Interacting with QEMU guest agent. Methods:

    execute()
        Low-level method for executing QEMU command as dict. Command dict
        internally converts to JSON. See method docstring for more info.
    shellexec()
        High-level method for executing shell commands on guest. Command
        must be passed as string. Wraps execute() method.
    _execute()
        Just executes QEMU command. Wraps libvirt_qemu.qemuAgentCommand()
    _get_cmd_result()
        Intended for long-time commands. This function loops and every
        POLL_INTERVAL calls 'guest-exec-status' for specified guest PID.
        Polling ends if command exited or on timeout.
    _return_tuple()
        This method transforms JSON command output to tuple and decode
        base64 encoded strings optionally.
    """

    def __init__(self,
        session: LibvirtSession,
        name: str,
        timeout: int | None = None,
        flags: int | None = None
    ):
        super().__init__(session, name)
        self.timeout = timeout or QEMU_TIMEOUT  # timeout for guest agent
        self.flags = flags or libvirt_qemu.VIR_DOMAIN_QEMU_MONITOR_COMMAND_DEFAULT

    def execute(
        self,
        command: dict,
        stdin: str | None = None,
        capture_output: bool = False,
        decode_output: bool = False,
        wait: bool = True,
        timeout: int = QEMU_TIMEOUT,
    ):
        """
        Execute command on guest and return output if capture_output is True.
        See https://wiki.qemu.org/Documentation/QMP for QEMU commands reference.
        Return values:
            tuple(
                exited: bool | None,
                exitcode: int | None,
                stdout: str | None,
                stderr: str | None
            )
        stdout and stderr are base64 encoded strings or None.
        """
        # todo command dict schema validation
        if capture_output:
            command['arguments']['capture-output'] = True
        if isinstance(stdin, str):
            command['arguments']['input-data'] = standard_b64encode(
                stdin.encode('utf-8')
            ).decode('utf-8')

        # Execute command on guest
        cmd_out = self._execute(command)

        if capture_output:
            cmd_pid = json.loads(cmd_out)['return']['pid']
            return self._get_cmd_result(
                cmd_pid,
                decode_output=decode_output,
                wait=wait,
                timeout=timeout,
            )
        return None, None, None, None

    def shellexec(
        self,
        command: str,
        stdin: str | None = None,
        executable: str = '/bin/sh',
        capture_output: bool = False,
        decode_output: bool = False,
        wait: bool = True,
        timeout: int = QEMU_TIMEOUT,
    ):
        """
        Execute command on guest with selected shell. /bin/sh by default.
        Otherwise of execute() this function brings command as string.
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


    def _execute(self, command: dict):
        logging.debug('Execute command: vm=%s cmd=%s', self.domname, command)
        try:
            return libvirt_qemu.qemuAgentCommand(
                self.domain,  # virDomain object
                json.dumps(command),
                self.timeout,
                self.flags,
            )
        except libvirt.libvirtError as err:
            raise QemuAgentError(err) from err

    def _get_cmd_result(
        self,
        pid: int,
        decode_output: bool = False,
        wait: bool = True,
        timeout: int = QEMU_TIMEOUT,
    ):
        """Get executed command result. See GuestAgent.execute() for info."""
        exited = exitcode = stdout = stderr = None

        cmd = {
            'execute': 'guest-exec-status',
            'arguments': {'pid': pid},
        }

        if not wait:
            output = json.loads(self._execute(cmd))
            return self._return_tuple(output, decode=decode_output)

        logger.debug('Start polling command pid=%s', pid)
        start_time = time()
        while True:
            output = json.loads(self._execute(cmd))
            if output['return']['exited']:
                break
            sleep(POLL_INTERVAL)
            now = time()
            if now - start_time > timeout:
                raise QemuAgentError(
                    f'Polling command pid={pid} took longer than {timeout} seconds.'
                )
        logger.debug(
            'Polling command pid=%s finished, time taken: %s seconds',
            pid, int(time()-start_time)
        )
        return self._return_tuple(output, decode=decode_output)

    def _return_tuple(self, cmd_output: dict, decode: bool = False):
        exited = cmd_output['return']['exited']
        exitcode = cmd_output['return']['exitcode']

        try:
            stdout = cmd_output['return']['out-data']
            if decode and stdout:
                stdout = b64decode(stdout).decode('utf-8')
        except KeyError:
            stdout = None

        try:
            stderr = cmd_output['return']['err-data']
            if decode and stderr:
                stderr = b64decode(stderr).decode('utf-8')
        except KeyError:
            stderr = None

        return exited, exitcode, stdout, stderr
