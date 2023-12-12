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

"""Command line argument parser."""

import argparse
import logging
import os
import sys
import textwrap
from collections.abc import Callable
from typing import NamedTuple

from compute import Session, __version__
from compute.cli import commands
from compute.exceptions import ComputeError


log = logging.getLogger(__name__)
log_levels = [lv.lower() for lv in logging.getLevelNamesMapping()]


class Doc(NamedTuple):
    """Parsed docstring."""

    help: str  # noqa: A003
    desc: str


def get_doc(func: Callable) -> Doc:
    """Extract help message and description from function docstring."""
    doc = func.__doc__
    if isinstance(doc, str):
        doc = textwrap.dedent(doc).strip().split('\n\n')
        return Doc(doc[0][0].lower() + doc[0][1:], '\n\n'.join(doc))
    return Doc('', '')


def get_parser() -> argparse.ArgumentParser:
    """Return command line argument parser."""
    root = argparse.ArgumentParser(
        prog='compute',
        description='Manage compute instances.',
    )
    root.add_argument(
        '-V',
        '--version',
        action='version',
        version=__version__,
    )
    root.add_argument(
        '-c',
        '--connect',
        dest='root_connect',
        metavar='URI',
        help='libvirt connection URI',
    )
    root.add_argument(
        '-l',
        '--log-level',
        dest='root_log_level',
        type=str.lower,
        choices=log_levels,
        metavar='LEVEL',
        help='log level',
    )

    # common options
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        '-c',
        '--connect',
        metavar='URI',
        help='libvirt connection URI',
    )
    common.add_argument(
        '-l',
        '--log-level',
        type=str.lower,
        choices=log_levels,
        metavar='LEVEL',
        help='log level',
    )

    subparsers = root.add_subparsers(dest='command', metavar='COMMAND')

    # init command
    init = subparsers.add_parser(
        'init',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.init).help,
        description=get_doc(commands.init).desc,
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
    init.set_defaults(func=commands.init)

    # exec subcommand
    execute = subparsers.add_parser(
        'exec',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.exec_).help,
        description=get_doc(commands.exec_).desc,
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
    execute.set_defaults(func=commands.exec_)

    # ls subcommand
    ls = subparsers.add_parser(
        'ls',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.ls).help,
        description=get_doc(commands.ls).desc,
    )
    ls.set_defaults(func=commands.ls)

    # lsdisks subcommand
    lsdisks = subparsers.add_parser(
        'lsdisks',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.lsdisks).help,
        description=get_doc(commands.lsdisks).desc,
    )
    lsdisks.add_argument('instance')
    lsdisks.add_argument(
        '-p',
        '--persistent',
        action='store_true',
        default=False,
        help='display only persisnent devices',
    )
    lsdisks.set_defaults(func=commands.lsdisks)

    # start subcommand
    start = subparsers.add_parser(
        'start',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.start).help,
        description=get_doc(commands.start).desc,
    )
    start.add_argument('instance')
    start.set_defaults(func=commands.start)

    # shutdown subcommand
    shutdown = subparsers.add_parser(
        'shutdown',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.shutdown).help,
        description=get_doc(commands.shutdown).desc,
    )
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
    shutdown.set_defaults(func=commands.shutdown)

    # reboot subcommand
    reboot = subparsers.add_parser(
        'reboot',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.reboot).help,
        description=get_doc(commands.reboot).desc,
    )
    reboot.add_argument('instance')
    reboot.set_defaults(func=commands.reboot)

    # reset subcommand
    reset = subparsers.add_parser(
        'reset',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.reset).help,
        description=get_doc(commands.reset).desc,
    )
    reset.add_argument('instance')
    reset.set_defaults(func=commands.reset)

    # powrst subcommand
    powrst = subparsers.add_parser(
        'powrst',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.powrst).help,
        description=get_doc(commands.powrst).desc,
    )
    powrst.add_argument('instance')
    powrst.set_defaults(func=commands.powrst)

    # pause subcommand
    pause = subparsers.add_parser(
        'pause',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.pause).help,
        description=get_doc(commands.pause).desc,
    )
    pause.add_argument('instance')
    pause.set_defaults(func=commands.pause)

    # resume subcommand
    resume = subparsers.add_parser(
        'resume',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.resume).help,
        description=get_doc(commands.resume).desc,
    )
    resume.add_argument('instance')
    resume.set_defaults(func=commands.resume)

    # status subcommand
    status = subparsers.add_parser(
        'status',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.status).help,
        description=get_doc(commands.status).desc,
    )
    status.add_argument('instance')
    status.set_defaults(func=commands.status)

    # setvcpus subcommand
    setvcpus = subparsers.add_parser(
        'setvcpus',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.setvcpus).help,
        description=get_doc(commands.setvcpus).desc,
    )
    setvcpus.add_argument('instance')
    setvcpus.add_argument('nvcpus', type=int)
    setvcpus.set_defaults(func=commands.setvcpus)

    # setmem subcommand
    setmem = subparsers.add_parser(
        'setmem',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.setmem).help,
        description=get_doc(commands.setmem).desc,
    )
    setmem.add_argument('instance')
    setmem.add_argument('memory', type=int, help='memory in MiB')
    setmem.set_defaults(func=commands.setmem)

    # setpass subcommand
    setpass = subparsers.add_parser(
        'setpass',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.setpass).help,
        description=get_doc(commands.setpass).desc,
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
    setpass.set_defaults(func=commands.setpass)

    # setcdrom subcommand
    setcdrom = subparsers.add_parser(
        'setcdrom',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.setcdrom).help,
        description=get_doc(commands.setcdrom).desc,
    )
    setcdrom.add_argument('instance')
    setcdrom.add_argument('source', help='source for CDROM')
    setcdrom.add_argument(
        '-d',
        '--detach',
        action='store_true',
        default=False,
        help='detach CDROM device',
    )
    setcdrom.set_defaults(func=commands.setcdrom)

    # setcloudinit subcommand
    setcloudinit = subparsers.add_parser(
        'setcloudinit',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.setcloudinit).help,
        description=get_doc(commands.setcloudinit).desc,
    )
    setcloudinit.add_argument('instance')
    setcloudinit.add_argument(
        '--user-data',
        type=argparse.FileType('r'),
        help='user-data file',
    )
    setcloudinit.add_argument(
        '--vendor-data',
        type=argparse.FileType('r'),
        help='vendor-data file',
    )
    setcloudinit.add_argument(
        '--meta-data',
        type=argparse.FileType('r'),
        help='meta-data file',
    )
    setcloudinit.add_argument(
        '--network-config',
        type=argparse.FileType('r'),
        help='network-config file',
    )
    setcloudinit.set_defaults(func=commands.setcloudinit)

    # delete subcommand
    delete = subparsers.add_parser(
        'delete',
        parents=[common],
        formatter_class=argparse.RawTextHelpFormatter,
        help=get_doc(commands.delete).help,
        description=get_doc(commands.delete).desc,
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
    delete.set_defaults(func=commands.delete)

    return root


def run() -> None:
    """Run argument parser."""
    parser = get_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit()
    log_level = args.root_log_level or args.log_level or os.getenv('CMP_LOG')
    if isinstance(log_level, str) and log_level.lower() in log_levels:
        logging.basicConfig(
            level=logging.getLevelNamesMapping()[log_level.upper()]
        )
    log.debug('CLI started with args: %s', args)
    connect_uri = (
        args.root_connect
        or args.connect
        or os.getenv('CMP_LIBVIRT_URI')
        or os.getenv('LIBVIRT_DEFAULT_URI')
        or 'qemu:///system'
    )
    try:
        with Session(connect_uri) as session:
            # Invoke command
            args.func(session, args)
    except ComputeError as e:
        sys.exit(f'error: {e}')
    except KeyboardInterrupt:
        sys.exit()
