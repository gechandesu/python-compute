"""
Execute shell commands on guest via guest agent.

Usage:  na-vmexec [options] <machine> <command>

Options:
    -c, --config <file>  config file [default: /etc/node-agent/config.yaml]
    -l, --loglvl <lvl>   logging level
    -s, --shell <shell>  guest shell [default: /bin/sh]
    -t, --timeout <sec>  QEMU timeout in seconds to stop polling command status [default: 60]
    -p, --pid <PID>      PID on guest to poll output
"""

import logging
import pathlib
import sys

import libvirt
from docopt import docopt

from ..session import LibvirtSession
from ..vm import GuestAgent
from ..exceptions import GuestAgentError, VMNotFound


logger = logging.getLogger(__name__)
levels = logging.getLevelNamesMapping()

libvirt.registerErrorHandler(lambda userdata, err: None, ctx=None)


class Color:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    NONE = '\033[0m'

# TODO: Add STDIN support e.g.: cat something.sh | na-vmexec vmname bash


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
        shell = args['--shell']
        cmd = args['<command>']

        try:
            ga = session.get_guest_agent(machine)
            exited, exitcode, stdout, stderr = ga.shellexec(
                cmd, executable=shell, capture_output=True, decode_output=True,
                timeout=int(args['--timeout']))
        except GuestAgentError as gaerr:
            errmsg = f'{Color.RED}{gaerr}{Color.NONE}'
            if str(gaerr).startswith('Polling command pid='):
                errmsg = (errmsg + Color.YELLOW +
                          '\n[NOTE: command may still running on guest '
                          'pid={ga.last_pid}]' + Color.NONE)
            sys.exit(errmsg)
        except VMNotFound as err:
            sys.exit(f'{Color.RED}VM {machine} not found{Color.NONE}')

    if not exited:
        print(Color.YELLOW +
              '[NOTE: command may still running on guest pid={ga.last_pid}]' +
              Color.NONE, file=sys.stderr)
    if stderr:
        print(stderr.strip(), file=sys.stderr)
    if stdout:
        print(stdout.strip(), file=sys.stdout)
    sys.exit(exitcode)


if __name__ == '__main__':
    cli()
