"""Manage QEMU guest agent."""

import json
import logging
from base64 import b64decode, standard_b64encode
from time import sleep, time
from typing import NamedTuple

import libvirt
import libvirt_qemu

from compute.exceptions import (
    GuestAgentCommandNotSupportedError,
    GuestAgentError,
    GuestAgentTimeoutExceededError,
    GuestAgentUnavailableError,
)


log = logging.getLogger(__name__)

QEMU_TIMEOUT = 60
POLL_INTERVAL = 0.3


class GuestExecOutput(NamedTuple):
    """QEMU guest-exec command output."""

    exited: bool | None = None
    exitcode: int | None = None
    stdout: str | None = None
    stderr: str | None = None


class GuestAgent:
    """Class for interacting with QEMU guest agent."""

    def __init__(self, domain: libvirt.virDomain, timeout: int | None = None):
        """
        Initialise GuestAgent.

        :param domain: Libvirt domain object
        :param timeout: QEMU timeout
        """
        self.domain = domain
        self.timeout = timeout or QEMU_TIMEOUT
        self.flags = libvirt_qemu.VIR_DOMAIN_QEMU_MONITOR_COMMAND_DEFAULT
        self.last_pid = None

    def execute(self, command: dict) -> dict:
        """
        Execute QEMU guest agent command.

        See: https://qemu-project.gitlab.io/qemu/interop/qemu-ga-ref.html

        :param command: QEMU guest agent command as dict
        :return: Command output
        :rtype: dict
        """
        log.debug(command)
        try:
            output = libvirt_qemu.qemuAgentCommand(
                self.domain, json.dumps(command), self.timeout, self.flags
            )
            return json.loads(output)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_AGENT_UNRESPONSIVE:
                log.exception(
                    'Guest agent is unavailable on instanse=%s', self.name
                )
                raise GuestAgentUnavailableError(e) from e
            raise GuestAgentError(e) from e

    def is_available(self) -> bool:
        """
        Execute guest-ping.

        :return: True or False if guest agent is unreachable.
        :rtype: bool
        """
        try:
            if self.execute({'execute': 'guest-ping', 'arguments': {}}):
                return True
        except GuestAgentError:
            return False

    def available_commands(self) -> set[str]:
        """Return set of available guest agent commands."""
        output = self.execute({'execute': 'guest-info', 'arguments': {}})
        return {
            cmd['name']
            for cmd in output['return']['supported_commands']
            if cmd['enabled'] is True
        }

    def raise_for_commands(self, commands: list[str]) -> None:
        """
        Check QEMU guest agent command availability.

        Raise exception if command is not available.

        :param commands: List of required commands
        :raise: GuestAgentCommandNotSupportedError
        """
        for command in commands:
            if command not in self.available_commands():
                raise GuestAgentCommandNotSupportedError(command)

    def guest_exec(  # noqa: PLR0913
        self,
        path: str,
        args: list[str] | None = None,
        env: list[str] | None = None,
        stdin: str | None = None,
        *,
        capture_output: bool = False,
        decode_output: bool = False,
        poll: bool = False,
    ) -> GuestExecOutput:
        """
        Execute qemu-exec command and return output.

        :param path: Path ot executable on guest.
        :param arg: List of arguments to pass to executable.
        :param env: List of environment variables to pass to executable.
            For example: ``['LANG=C', 'TERM=xterm']``
        :param stdin: Data to pass to executable STDIN.
        :param capture_output: Capture command output.
        :param decode_output: Use base64_decode() to decode command output.
            Affects only if `capture_output` is True.
        :param poll: Poll command output. Uses `self.timeout` and
            POLL_INTERVAL constant.
        :return: Command output
        :rtype: GuestExecOutput
        """
        self.raise_for_commands(['guest-exec', 'guest-exec-status'])
        command = {
            'execute': 'guest-exec',
            'arguments': {
                'path': path,
                **({'arg': args} if args else {}),
                **({'env': env} if env else {}),
                **(
                    {
                        'input-data': standard_b64encode(
                            stdin.encode('utf-8')
                        ).decode('utf-8')
                    }
                    if stdin
                    else {}
                ),
                'capture-output': capture_output,
            },
        }
        output = self.execute(command)
        self.last_pid = pid = output['return']['pid']
        command_status = self.guest_exec_status(pid, poll=poll)['return']
        exited = command_status['exited']
        exitcode = command_status['exitcode']
        stdout = command_status.get('out-data', None)
        stderr = command_status.get('err-data', None)
        if decode_output:
            stdout = b64decode(stdout or '').decode('utf-8')
            stderr = b64decode(stderr or '').decode('utf-8')
        return GuestExecOutput(exited, exitcode, stdout, stderr)

    def guest_exec_status(self, pid: int, *, poll: bool = False) -> dict:
        """
        Execute guest-exec-status and return output.

        :param pid: PID in guest
        :param poll: If True poll command status with POLL_INTERVAL
        :return: Command output
        :rtype: dict
        """
        self.raise_for_commands(['guest-exec-status'])
        command = {
            'execute': 'guest-exec-status',
            'arguments': {'pid': pid},
        }
        if not poll:
            return self.execute(command)
        start_time = time()
        while True:
            command_status = self.execute(command)
            if command_status['return']['exited']:
                break
            sleep(POLL_INTERVAL)
            now = time()
            if now - start_time > self.timeout:
                raise GuestAgentTimeoutExceededError(self.timeout)
        log.debug(
            'Polling command pid=%s finished, time taken: %s seconds',
            pid,
            int(time() - start_time),
        )
        return command_status
