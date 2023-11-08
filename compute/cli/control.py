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
from compute.exceptions import (
    ComputeServiceError,
    GuestAgentTimeoutExceededError,
)
from compute.instance import GuestAgent
from compute.session import Session
from compute.utils import ids


log = logging.getLogger(__name__)
log_levels = logging.getLevelNamesMapping()

env_log_level = os.getenv('CMP_LOG')

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
    if len(arguments) > 1:
        arguments = [shlex.join(arguments)]
    if not args.no_cmd_string:
        arguments.insert(0, '-c')
    stdin = None
    if not sys.stdin.isatty():
        stdin = sys.stdin.read()
    try:
        output = ga.guest_exec(
            path=args.shell,
            args=arguments,
            env=args.env,
            stdin=stdin,
            capture_output=True,
            decode_output=True,
            poll=True,
        )
    except GuestAgentTimeoutExceededError as e:
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


def main(session: Session, args: argparse.Namespace) -> None:
    """Perform actions."""
    match args.command:
        case 'create':
            _create_instance(session, args.file)
        case 'exec':
            _exec_guest_agent_command(session, args)
        case 'ls':
            _list_instances(session)
        case 'start':
            instance = session.get_instance(args.instance)
            instance.start()
        case 'shutdown':
            instance = session.get_instance(args.instance)
            instance.shutdown(args.method)
        case 'reboot':
            instance = session.get_instance(args.instance)
            instance.reboot()
        case 'reset':
            instance = session.get_instance(args.instance)
            instance.reset()
        case 'status':
            instance = session.get_instance(args.instance)
            print(instance.status)
        case 'setvcpus':
            instance = session.get_instance(args.instance)
            instance.set_vcpus(args.nvcpus, live=True)


def cli() -> None:  # noqa: PLR0915
    """Parse command line arguments."""
    root = argparse.ArgumentParser(
        prog='compute',
        description='manage compute instances and storage volumes.',
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
        default='qemu:///system',
        help='libvirt connection URI',
    )
    root.add_argument(
        '-l',
        '--log-level',
        metavar='LEVEL',
        choices=log_levels,
        help='log level [envvar: CMP_LOG]',
    )
    root.add_argument(
        '-V',
        '--version',
        action='version',
        version=__version__,
    )
    subparsers = root.add_subparsers(dest='command', metavar='COMMAND')

    # create command
    create = subparsers.add_parser(
        'create', help='create new instance from YAML config file'
    )
    create.add_argument(
        'file',
        type=argparse.FileType('r', encoding='UTF-8'),
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
            'in guest, 60 sec by default'
        ),
    )
    execute.add_argument(
        '-s',
        '--shell',
        default='/bin/sh',
        help='path to executable in guest, /bin/sh by default',
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
        '--no-cmd-string',
        action='store_true',
        default=False,
        help=(
            "do not append '-c' option to arguments list, suitable "
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
    shutdown.add_argument(
        '-m',
        '--method',
        choices=['soft', 'normal', 'hard', 'unsafe'],
        default='normal',
        help='use shutdown method',
    )

    # reboot subcommand
    reboot = subparsers.add_parser('reboot', help='reboot instance')
    reboot.add_argument('instance')

    # reset subcommand
    reset = subparsers.add_parser('reset', help='reset instance')
    reset.add_argument('instance')

    # status subcommand
    status = subparsers.add_parser('status', help='display instance status')
    status.add_argument('instance')

    # setvcpus subcommand
    setvcpus = subparsers.add_parser('setvcpus', help='set vCPU number')
    setvcpus.add_argument('instance')
    setvcpus.add_argument('nvcpus', type=int)

    # Run parser
    args = root.parse_args()
    if args.command is None:
        root.print_help()
        sys.exit()

    # Set logging level
    log_level = args.log_level or env_log_level
    if log_level in log_levels:
        logging.basicConfig(level=log_levels[log_level])

    log.debug('CLI started with args: %s', args)
    # Perform actions
    try:
        with Session(args.connect) as session:
            main(session, args)
    except ComputeServiceError as e:
        sys.exit(f'error: {e}')
    except KeyboardInterrupt:
        sys.exit()
    except SystemExit as e:
        sys.exit(e)
    except Exception as e:  # noqa: BLE001
        sys.exit(f'unexpected error {type(e)}: {e}')


if __name__ == '__main__':
    cli()
