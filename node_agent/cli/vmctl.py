"""
Manage virtual machines.

Usage:  na-vmctl [options] status <machine>
        na-vmctl [options] is-running <machine>
        na-vmctl [options] start <machine>
        na-vmctl [options] shutdown <machine> [-f|--force] [-9|--sigkill]
        na-vmctl [options] set-vcpus <machine> <nvcpus>
        na-vmctl [options] set-memory <machine> <memory>
        na-vmctl [options] list [-a|--all]

Options:
    -c, --config <file>  Config file [default: /etc/node-agent/config.yaml]
    -l, --loglvl <lvl>   Logging level
    -a, --all            List all machines including inactive
    -f, --force          Force action. On shutdown calls graceful destroy()
    -9, --sigkill        Send SIGKILL to QEMU process. Not affects without --force
"""

import logging
import pathlib
import sys

import libvirt
from docopt import docopt

from ..session import LibvirtSession
from ..vm import VirtualMachine, VMError, VMNotFound


logger = logging.getLogger(__name__)
levels = logging.getLevelNamesMapping()


class Color:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    NONE = '\033[0m'


class Table:
    """Print table. Example::

        t = Table()
        t.header(['KEY', 'VALUE'])  # header is optional
        t.row(['key 1', 'value 1'])
        t.row(['key 2', 'value 2'])
        t.rows(
            [
                ['key 3', 'value 3'],
                ['key 4', 'value 4']
            ]
        )
        t.print()

    """

    def __init__(self, whitespace: str = '\t'):
        self.__rows = []
        self.__whitespace = whitespace

    def header(self, columns: list):
        self.__rows.insert(0, [str(col) for col in columns])

    def row(self, row: list):
        self.__rows.append([str(col) for col in row])

    def rows(self, rows: list):
        for row in rows:
            self.row(row)

    def print(self):
        widths = [max(map(len, col)) for col in zip(*self.__rows)]
        for row in self.__rows:
            print(self.__whitespace.join(
                (val.ljust(width) for val, width in zip(row, widths))))


def cli():
    args = docopt(__doc__)
    config = pathlib.Path(args['--config']) or None
    loglvl = None
    machine = args['<machine>']

    if args['--loglvl']:
        loglvl = args['--loglvl'].upper()

    if loglvl in levels:
        logging.basicConfig(level=levels[loglvl])

    with LibvirtSession(config) as session:
        try:
            if args['list']:
                vms = session.list_domains()
                table = Table()
                table.header(['NAME', 'STATE', 'AUTOSTART'])
                for vm_ in vms:
                    vm_ = VirtualMachine(vm_)
                    table.row([vm_.name, vm_.status, vm_.is_autostart])
                table.print()
                sys.exit()

            vm = VirtualMachine(session, machine)
            if args['status']:
                print(vm.status)
            if args['is-running']:
                if vm.is_running:
                    print('running')
                else:
                    sys.exit(vm.status)
            if args['start']:
                vm.start()
                print(f'{vm.name} started')
            if args['shutdown']:
                vm.shutdown(force=args['--force'], sigkill=args['sigkill'])
        except VMNotFound as nferr:
            sys.exit(f'{Color.RED}VM {machine} not found.{Color.NONE}')
        except VMError as vmerr:
            sys.exit(f'{Color.RED}{vmerr}{Color.NONE}')


if __name__ == '__main__':
    cli()
