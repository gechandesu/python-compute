"""
Manage virtual machines.

Usage:  na-vmctl [options] status <machine>
        na-vmctl [options] is-running <machine>
        na-vmctl [options] start <machine>
        na-vmctl [options] shutdown <machine>
        na-vmctl [options] set-vcpus <machine> <nvcpus>
        na-vmctl [options] set-memory <machine> <memory>
        na-vmctl [options] list [-a|--all]

Options:
    -c, --config <file>  config file [default: /etc/node-agent/config.yaml]
    -l, --loglvl <lvl>   logging level
    -a, --all            list all machines including inactive
"""

import logging
import pathlib
import sys

import libvirt
from docopt import docopt

from ..session import LibvirtSession
from ..vm import VirtualMachine
from ..exceptions import VMError, VMNotFound


logger = logging.getLogger(__name__)
levels = logging.getLevelNamesMapping()

libvirt.registerErrorHandler(lambda userdata, err: None, ctx=None)


class Color:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    NONE = '\033[0m'


class Table:

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

    with LibvirtSession() as session:
        try:
            if args['list']:
                table = Table()
                table.header(['NAME', 'STATE', 'AUTOSTART'])
                for vm_ in session.list_machines():
                    table.row([vm_.name, vm_.status, vm_.is_autostart])
                table.print()
                sys.exit()

            vm = session.get_machine(machine)
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
                vm.shutdown('NORMAL')
        except VMNotFound as nferr:
            sys.exit(f'{Color.RED}VM {machine} not found.{Color.NONE}')
        except VMError as vmerr:
            sys.exit(f'{Color.RED}{vmerr}{Color.NONE}')


if __name__ == '__main__':
    cli()
