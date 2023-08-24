"""
Execute shell commands on guest via guest agent.

Usage:  na-vmexec [options] <machine> <command>

Options:
    -c, --config <file>  Config file [default: /etc/node-agent/config.yaml]
    -l, --loglvl <lvl>   Logging level
    -s, --shell <shell>  Guest shell [default: /bin/sh]
    -t, --timeout <sec>  QEMU timeout in seconds to stop polling command status [default: 60]
"""

import logging
import pathlib
import sys

from docopt import docopt

from ..session import LibvirtSession
from ..vm import QemuAgent, QemuAgentError, VMNotFound


logger = logging.getLogger(__name__)
levels = logging.getLevelNamesMapping()


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

    with LibvirtSession(config) as session:
        shell = args['--shell']
        cmd = args['<command>']

        try:
            ga = QemuAgent(session, machine)
            exited, exitcode, stdout, stderr = ga.shellexec(
                cmd, executable=shell, capture_output=True, decode_output=True,
                timeout=int(args['--timeout']))
        except QemuAgentError as qemuerr:
            errmsg = f'{Color.RED}{qemuerr}{Color.NONE}'
            if str(qemuerr).startswith('Polling command pid='):
                errmsg = (errmsg + Color.YELLOW +
                          '\n[NOTE: command may still running]' + Color.NONE)
            sys.exit(errmsg)
        except VMNotFound as err:
            sys.exit(f'{Color.RED}VM {machine} not found{Color.NONE}')

    if not exited:
        print(Color.YELLOW + '[NOTE: command may still running]' + Color.NONE,
              file=sys.stderr)
    else:
        if exitcode == 0:
            exitcolor = Color.GREEN
        else:
            exitcolor = Color.RED
        print(exitcolor + f'[command exited with exit code {exitcode}]' +
              Color.NONE,
              file=sys.stderr)

    if stderr:
        print(Color.RED + stderr.strip() + Color.NONE, file=sys.stderr)
    if stdout:
        print(Color.GREEN + stdout.strip() + Color.NONE, file=sys.stdout)
    sys.exit(exitcode)


if __name__ == '__main__':
    cli()
