# This file is part of Compute
#
# Compute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Compute is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Compute.  If not, see <http://www.gnu.org/licenses/>.

"""Command line interface."""

import argparse
import json
import logging
import os
import re
import shlex
import string
import sys
import uuid

import libvirt
import yaml
from pydantic import ValidationError

from compute import __version__
from compute.exceptions import ComputeError, GuestAgentTimeoutError
from compute.instance import GuestAgent, Instance, InstanceSchema
from compute.instance.devices import DiskConfig, DiskDriver
from compute.session import Session
from compute.utils import dictutil, ids


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


def _init_instance(session: Session, args: argparse.Namespace) -> None:
    try:
        data = yaml.load(args.file.read(), Loader=yaml.SafeLoader)
        log.debug('Read from file: %s', data)
    except yaml.YAMLError as e:
        sys.exit(f'error: cannot parse YAML: {e}')
    capabilities = session.get_capabilities()
    node_info = session.get_node_info()
    base_instance_config = {
        'name': str(uuid.uuid4()),
        'title': None,
        'description': None,
        'arch': capabilities.arch,
        'machine': capabilities.machine,
        'emulator': capabilities.emulator,
        'max_vcpus': node_info.cpus,
        'max_memory': node_info.memory,
        'cpu': {
            'emulation_mode': 'host-passthrough',
            'model': None,
            'vendor': None,
            'topology': None,
            'features': None,
        },
        'network_interfaces': [
            {
                'source': 'default',
                'mac': ids.random_mac(),
            },
        ],
        'boot': {'order': ['cdrom', 'hd']},
    }
    data = dictutil.override(base_instance_config, data)
    volumes = []
    for volume in data['volumes']:
        base_disk_config = {
            'bus': 'virtio',
            'is_readonly': False,
            'driver': {
                'name': 'qemu',
                'type': 'qcow2',
                'cache': 'writethrough',
            },
        }
        base_cdrom_config = {
            'bus': 'ide',
            'target': 'hda',
            'is_readonly': True,
            'driver': {
                'name': 'qemu',
                'type': 'raw',
                'cache': 'writethrough',
            },
        }
        if volume.get('device') is None:
            volume['device'] = 'disk'
        if volume['device'] == 'disk':
            volumes.append(dictutil.override(base_disk_config, volume))
        if volume['device'] == 'cdrom':
            volumes.append(dictutil.override(base_cdrom_config, volume))
    data['volumes'] = volumes
    try:
        log.debug('Input data: %s', data)
        if args.test:
            _ = InstanceSchema(**data)
            print(json.dumps(dict(data), indent=4, sort_keys=True))
            sys.exit()
        instance = session.create_instance(**data)
        print(f'initialised: {instance.name}')
        if args.start:
            instance.start()
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


def _confirm(message: str, *, default: bool | None = None) -> None:
    while True:
        match default:
            case True:
                prompt = 'default: yes'
            case False:
                prompt = 'default: no'
            case _:
                prompt = 'no default'
        try:
            answer = input(f'{message} ({prompt}) ')
        except KeyboardInterrupt:
            sys.exit('aborted')
        if not answer and isinstance(default, bool):
            return default
        if re.match(r'^y(es)?$', answer, re.I):
            return True
        if re.match(r'^no?$', answer, re.I):
            return False
        print("Please respond 'yes' or 'no'")


def _delete_instance(session: Session, args: argparse.Namespace) -> None:
    if args.yes is True or _confirm(
        'this action is irreversible, continue?',
        default=False,
    ):
        instance = session.get_instance(args.instance)
        if args.save_volumes is False:
            instance.delete(with_volumes=True)
        else:
            instance.delete()
    else:
        print('aborted')
        sys.exit()


def _get_disk_target(instance: Instance, prefix: str = 'hd') -> str:
    disks_live = instance.list_disks(persistent=False)
    disks_inactive = instance.list_disks(persistent=True)
    disks = [d for d in disks_inactive if d not in disks_live]
    devs = [d.target[-1] for d in disks if d.target.startswith(prefix)]
    return prefix + [x for x in string.ascii_lowercase if x not in devs][0]  # noqa: RUF015


def _manage_cdrom(session: Session, args: argparse.Namespace) -> None:
    instance = session.get_instance(args.instance)
    if args.detach:
        for disk in instance.list_disks(persistent=True):
            if disk.device == 'cdrom' and disk.source == args.source:
                instance.detach_disk(disk.target, live=False)
                print(
                    f"disk '{disk.target}' detached, "
                    'perform power reset to apply changes'
                )
        return
    target = _get_disk_target(instance, 'hd')
    cdrom = DiskConfig(
        type='file',
        device='cdrom',
        source=args.source,
        target=target,
        is_readonly=True,
        bus='ide',
        driver=DiskDriver('qemu', 'raw', 'writethrough'),
    )
    instance.attach_device(cdrom, live=False)
    print(
        f"CDROM attached as disk '{target}', "
        'perform power reset to apply changes'
    )


def main(session: Session, args: argparse.Namespace) -> None:
    """Perform actions."""
    match args.command:
        case 'init':
            _init_instance(session, args)
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
        case 'setcdrom':
            _manage_cdrom(session, args)
        case 'delete':
            _delete_instance(session, args)


def get_parser() -> argparse.ArgumentParser:  # noqa: PLR0915
    """Return command line arguments parser."""
    root = argparse.ArgumentParser(
        prog='compute',
        description='Manage compute instances.',
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
    init.add_argument(
        '-s',
        '--start',
        action='store_true',
        default=False,
        help='start instance after init',
    )
    init.add_argument(
        '-t',
        '--test',
        action='store_true',
        default=False,
        help='just print resulting instance config as JSON and exit',
    )

    # exec subcommand
    execute = subparsers.add_parser(
        'exec',
        help='execute command in guest via guest agent',
        description=(
            'Execute command in guest via guest agent. '
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

    # setcdrom subcommand
    setcdrom = subparsers.add_parser('setcdrom', help='manage CDROM devices')
    setcdrom.add_argument('instance')
    setcdrom.add_argument('source', help='source for CDROM')
    setcdrom.add_argument(
        '-d',
        '--detach',
        action='store_true',
        default=False,
        help='detach CDROM device',
    )

    # delete subcommand
    delete = subparsers.add_parser(
        'delete',
        help='delete instance',
    )
    delete.add_argument('instance')
    delete.add_argument(
        '-y',
        '--yes',
        action='store_true',
        default=False,
        help='automatic yes to prompt',
    )
    delete.add_argument(
        '--save-volumes',
        action='store_true',
        default=False,
        help='do not delete local storage volumes',
    )

    return root


def cli() -> None:
    """Run arguments parser."""
    root = get_parser()
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


if __name__ == '__main__':
    cli()
