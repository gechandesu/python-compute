# This file is part of Compute
#
# Compute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

"""Command line interface."""

import argparse
import io
import logging
import os
import shlex
import sys
from collections import UserDict
from typing import Any
from uuid import uuid4

import libvirt
import yaml
from pydantic import ValidationError

from compute import __version__
from compute.exceptions import ComputeError, GuestAgentTimeoutError
from compute.instance import GuestAgent
from compute.session import Session
from compute.utils import ids


log = logging.getLogger(__name__)
log_levels = [lv.lower() for lv in logging.getLevelNamesMapping()]

libvirt.registerErrorHandler(
    lambda userdata, err: None,  # noqa: ARG005
    ctx=None,
)


class Table:
    """Minimalistic text table constructor."""

    def __init__(self, whitespace: str | None = None):
        """Initialise Table."""
        self.whitespace = whitespace or '\t'
        self.header = []
        self.rows = []
        self.table = ''

    def add_row(self, row: list) -> None:
        """Add table row."""
        self.rows.append([str(col) for col in row])

    def add_rows(self, rows: list[list]) -> None:
        """Add multiple rows."""
        for row in rows:
            self.add_row(row)

    def __str__(self) -> str:
        """Build table and return."""
        widths = [max(map(len, col)) for col in zip(*self.rows, strict=True)]
        self.rows.insert(0, [str(h).upper() for h in self.header])
        for row in self.rows:
            self.table += self.whitespace.join(
                (
                    val.ljust(width)
                    for val, width in zip(row, widths, strict=True)
                )
            )
            self.table += '\n'
        return self.table.strip()


def _list_instances(session: Session) -> None:
    table = Table()
    table.header = ['NAME', 'STATE']
    for instance in session.list_instances():
        table.add_row(
            [
                instance.name,
                instance.get_status(),
            ]
        )
    print(table)
    sys.exit()


def _exec_guest_agent_command(
    session: Session, args: argparse.Namespace
) -> None:
    instance = session.get_instance(args.instance)
    ga = GuestAgent(instance.domain, timeout=args.timeout)
    arguments = args.arguments.copy()
    if len(arguments) > 1 and not args.no_join_args:
        arguments = [shlex.join(arguments)]
    if not args.no_join_args:
        arguments.insert(0, '-c')
    stdin = None
    if not sys.stdin.isatty():
        stdin = sys.stdin.read()
    try:
        output = ga.guest_exec(
            path=args.executable,
            args=arguments,
            env=args.env,
            stdin=stdin,
            capture_output=True,
            decode_output=True,
            poll=True,
        )
    except GuestAgentTimeoutError as e:
        sys.exit(
            f'{e}. NOTE: command may still running in guest, '
            f'PID={ga.last_pid}'
        )
    if output.stderr:
        print(output.stderr.strip(), file=sys.stderr)
    if output.stdout:
        print(output.stdout.strip(), file=sys.stdout)
    sys.exit(output.exitcode)


class _NotPresent:
    """
    Type for representing non-existent dictionary keys.

    See :class:`_FillableDict`.
    """


class _FillableDict(UserDict):
    """Use :method:`fill` to add key if not present."""

    def __init__(self, data: dict):
        self.data = data

    def fill(self, key: str, value: Any) -> None:  # noqa: ANN401
        if self.data.get(key, _NotPresent) is _NotPresent:
            self.data[key] = value


def _merge_dicts(a: dict, b: dict, path: list[str] | None = None) -> dict:
    """Merge `b` into `a`. Return modified `a`."""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                _merge_dicts(a[key], b[key], [path + str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                a[key] = b[key]  # replace existing key's values
        else:
            a[key] = b[key]
    return a


def _create_instance(session: Session, file: io.TextIOWrapper) -> None:
    try:
        data = _FillableDict(yaml.load(file.read(), Loader=yaml.SafeLoader))
        log.debug('Read from file: %s', data)
    except yaml.YAMLError as e:
        sys.exit(f'error: cannot parse YAML: {e}')

    capabilities = session.get_capabilities()
    node_info = session.get_node_info()

    data.fill('name', uuid4().hex)
    data.fill('title', None)
    data.fill('description', None)
    data.fill('arch', capabilities.arch)
    data.fill('machine', capabilities.machine)
    data.fill('emulator', capabilities.emulator)
    data.fill('max_vcpus', node_info.cpus)
    data.fill('max_memory', node_info.memory)
    data.fill('cpu', {})
    cpu = {
        'emulation_mode': 'host-passthrough',
        'model': None,
        'vendor': None,
        'topology': None,
        'features': None,
    }
    data['cpu'] = _merge_dicts(data['cpu'], cpu)
    data.fill(
        'network_interfaces',
        [{'source': 'default', 'mac': ids.random_mac()}],
    )
    data.fill('boot', {'order': ['cdrom', 'hd']})

    try:
        log.debug('Input data: %s', data)
        session.create_instance(**data)
    except ValidationError as e:
        for error in e.errors():
            fields = '.'.join([str(lc) for lc in error['loc']])
            print(
                f"validation error: {fields}: {error['msg']}",
                file=sys.stderr,
            )
        sys.exit()


def _shutdown_instance(session: Session, args: argparse.Namespace) -> None:
    instance = session.get_instance(args.instance)
    if args.soft:
        method = 'SOFT'
    elif args.hard:
        method = 'HARD'
    elif args.unsafe:
        method = 'UNSAFE'
    else:
        method = 'NORMAL'
    instance.shutdown(method)


def main(session: Session, args: argparse.Namespace) -> None:
    """Perform actions."""
    match args.command:
        case 'init':
            _create_instance(session, args.file)
        case 'exec':
            _exec_guest_agent_command(session, args)
        case 'ls':
            _list_instances(session)
        case 'start':
            instance = session.get_instance(args.instance)
            instance.start()
        case 'shutdown':
            _shutdown_instance(session, args)
        case 'reboot':
            instance = session.get_instance(args.instance)
            instance.reboot()
        case 'reset':
            instance = session.get_instance(args.instance)
            instance.reset()
        case 'powrst':
            instance = session.get_instance(args.instance)
            instance.power_reset()
        case 'pause':
            instance = session.get_instance(args.instance)
            instance.pause()
        case 'resume':
            instance = session.get_instance(args.instance)
            instance.resume()
        case 'status':
            instance = session.get_instance(args.instance)
            print(instance.status)
        case 'setvcpus':
            instance = session.get_instance(args.instance)
            instance.set_vcpus(args.nvcpus, live=True)
        case 'setmem':
            instance = session.get_instance(args.instance)
            instance.set_memory(args.memory, live=True)
        case 'setpass':
            instance = session.get_instance(args.instance)
            instance.set_user_password(
                args.username,
                args.password,
                encrypted=args.encrypted,
            )


def cli() -> None:  # noqa: PLR0915
    """Return command line arguments parser."""
    root = argparse.ArgumentParser(
        prog='compute',
        description='manage compute instances',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    root.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help='enable verbose mode',
    )
    root.add_argument(
        '-c',
        '--connect',
        metavar='URI',
        help='libvirt connection URI',
    )
    root.add_argument(
        '-l',
        '--log-level',
        type=str.lower,
        metavar='LEVEL',
        choices=log_levels,
        help='log level',
    )
    root.add_argument(
        '-V',
        '--version',
        action='version',
        version=__version__,
    )
    subparsers = root.add_subparsers(dest='command', metavar='COMMAND')

    # init command
    init = subparsers.add_parser(
        'init', help='initialise instance using YAML config file'
    )
    init.add_argument(
        'file',
        type=argparse.FileType('r', encoding='UTF-8'),
        nargs='?',
        default='instance.yaml',
        help='instance config [default: instance.yaml]',
    )

    # exec subcommand
    execute = subparsers.add_parser(
        'exec',
        help='execute command in guest via guest agent',
        description=(
            'NOTE: any argument after instance name will be passed into '
            'guest as shell command.'
        ),
    )
    execute.add_argument('instance')
    execute.add_argument('arguments', nargs=argparse.REMAINDER)
    execute.add_argument(
        '-t',
        '--timeout',
        type=int,
        default=60,
        help=(
            'waiting time in seconds for a command to be executed '
            'in guest [default: 60]'
        ),
    )
    execute.add_argument(
        '-x',
        '--executable',
        default='/bin/sh',
        help='path to executable in guest [default: /bin/sh]',
    )
    execute.add_argument(
        '-e',
        '--env',
        type=str,
        nargs='?',
        action='append',
        help='environment variables to pass to executable in guest',
    )
    execute.add_argument(
        '-n',
        '--no-join-args',
        action='store_true',
        default=False,
        help=(
            "do not join arguments list and add '-c' option, suitable "
            'for non-shell executables and other specific cases.'
        ),
    )

    # ls subcommand
    listall = subparsers.add_parser('ls', help='list instances')
    listall.add_argument(
        '-a',
        '--all',
        action='store_true',
        default=False,
        help='list all instances including inactive',
    )

    # start subcommand
    start = subparsers.add_parser('start', help='start instance')
    start.add_argument('instance')

    # shutdown subcommand
    shutdown = subparsers.add_parser('shutdown', help='shutdown instance')
    shutdown.add_argument('instance')
    shutdown_opts = shutdown.add_mutually_exclusive_group()
    shutdown_opts.add_argument(
        '-s',
        '--soft',
        action='store_true',
        help='normal guest OS shutdown, guest agent is used',
    )
    shutdown_opts.add_argument(
        '-n',
        '--normal',
        action='store_true',
        help='shutdown with hypervisor selected method [default]',
    )
    shutdown_opts.add_argument(
        '-H',
        '--hard',
        action='store_true',
        help=(
            "gracefully destroy instance, it's like long "
            'pressing the power button'
        ),
    )
    shutdown_opts.add_argument(
        '-u',
        '--unsafe',
        action='store_true',
        help=(
            'destroy instance, this is similar to a power outage '
            'and may result in data loss or corruption'
        ),
    )

    # reboot subcommand
    reboot = subparsers.add_parser('reboot', help='reboot instance')
    reboot.add_argument('instance')

    # reset subcommand
    reset = subparsers.add_parser('reset', help='reset instance')
    reset.add_argument('instance')

    # powrst subcommand
    powrst = subparsers.add_parser('powrst', help='power reset instance')
    powrst.add_argument('instance')

    # pause subcommand
    pause = subparsers.add_parser('pause', help='pause instance')
    pause.add_argument('instance')

    # resume subcommand
    resume = subparsers.add_parser('resume', help='resume paused instance')
    resume.add_argument('instance')

    # status subcommand
    status = subparsers.add_parser('status', help='display instance status')
    status.add_argument('instance')

    # setvcpus subcommand
    setvcpus = subparsers.add_parser('setvcpus', help='set vCPU number')
    setvcpus.add_argument('instance')
    setvcpus.add_argument('nvcpus', type=int)

    # setmem subcommand
    setmem = subparsers.add_parser('setmem', help='set memory size')
    setmem.add_argument('instance')
    setmem.add_argument('memory', type=int, help='memory in MiB')

    # setpass subcommand
    setpass = subparsers.add_parser(
        'setpass',
        help='set user password in guest',
    )
    setpass.add_argument('instance')
    setpass.add_argument('username')
    setpass.add_argument('password')
    setpass.add_argument(
        '-e',
        '--encrypted',
        action='store_true',
        default=False,
        help='set it if password is already encrypted',
    )

    args = root.parse_args()
    if args.command is None:
        root.print_help()
        sys.exit()

    log_level = args.log_level or os.getenv('CMP_LOG')

    if isinstance(log_level, str) and log_level.lower() in log_levels:
        logging.basicConfig(
            level=logging.getLevelNamesMapping()[log_level.upper()]
        )

    log.debug('CLI started with args: %s', args)

    connect_uri = (
        args.connect
        or os.getenv('CMP_LIBVIRT_URI')
        or os.getenv('LIBVIRT_DEFAULT_URI')
        or 'qemu:///system'
    )

    try:
        with Session(connect_uri) as session:
            main(session, args)
    except ComputeError as e:
        sys.exit(f'error: {e}')
    except KeyboardInterrupt:
        sys.exit()
    except SystemExit as e:
        sys.exit(e)
    except Exception as e:  # noqa: BLE001
        sys.exit(f'unexpected error {type(e)}: {e}')


if __name__ == '__main__':
    cli()
