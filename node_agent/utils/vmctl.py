"""
Manage virtual machines.

Usage:  na-vmctl [options] status <machine>
        na-vmctl [options] is-running <machine>
        na-vmctl [options] start <machine>
        na-vmctl [options] shutdown <machine> [-f|--force] [-9|--sigkill]

Options:
    -c, --config <file>  Config file [default: /etc/node-agent/config.yaml]
    -l, --loglvl <lvl>   Logging level [default: INFO]
    -f, --force          Force action. On shutdown calls graceful destroy()
    -9, --sigkill        Send SIGKILL to QEMU process. Not affects without --force
"""

import sys
import pathlib
import logging

from docopt import docopt

sys.path.append('/home/ge/Code/node-agent')
from node_agent import LibvirtSession, VirtualMachine, VMError, VMNotFound


logger = logging.getLogger(__name__)
levels = logging.getLevelNamesMapping()


class Color:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    NONE = '\033[0m'


def cli():
    args = docopt(__doc__)
    config = pathlib.Path(args['--config']) or None
    loglvl = args['--loglvl'].upper()

    if loglvl in levels:
        logging.basicConfig(level=levels[loglvl])

    with LibvirtSession(config) as session:
        try:
            vm = VirtualMachine(session, args['<machine>'])
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
            sys.exit(f'{Color.RED}VM {args["<machine>"]} not found.{Color.NONE}')
        except VMError as vmerr:
            sys.exit(f'{Color.RED}{vmerr}{Color.NONE}')


if __name__ == '__main__':
    cli()
