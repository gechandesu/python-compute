"""
Execute shell commands on guest via guest agent.

Usage:  na-vmexec [options] <machine> <command>

Options:
    -c, --config <file>  Config file [default: /etc/node-agent/config.yaml]
    -l, --loglvl <lvl>   Logging level [default: INFO]
    -s, --shell <shell>  Guest shell [default: /bin/sh]
    -t, --timeout <sec>  QEMU timeout in seconds to stop polling command status [default: 60]
"""

import sys
import pathlib
import logging

from docopt import docopt

sys.path.append('/home/ge/Code/node-agent')
from node_agent import LibvirtSession, VMNotFound, QemuAgent, QemuAgentError


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
        shell = args['--shell']
        cmd = args['<command>']

        try:
            ga = QemuAgent(session, args['<machine>'])
            exited, exitcode, stdout, stderr = ga.shellexec(
                cmd,
                executable=shell,
                capture_output=True,
                decode_output=True,
                timeout=int(args['--timeout']),
            )
        except QemuAgentError as qemuerr:
            errmsg = f'{Color.RED}{err}{Color.NONE}'
            if str(err).startswith('Polling command pid='):
                errmsg = (
                    errmsg + Color.YELLOW
                    + '\n[NOTE: command may still running]'
                    + Color.NONE
                )
            sys.exit(errmsg)
        except VMNotFound as err:
            sys.exit(
                f'{Color.RED}VM {args["<machine>"]} not found.{Color.NONE}'
            )

    if not exited:
        print(
            Color.YELLOW
            +'[NOTE: command may still running]'
            + Color.NONE
        )
    else:
        if exitcode == 0:
            exitcolor = Color.GREEN
        else:
            exitcolor = Color.RED
        print(
            exitcolor
            + f'[command exited with exit code {exitcode}]'
            + Color.NONE
        )

    if stderr:
        print(Color.RED + stderr.strip() + Color.NONE)
    if stdout:
        print(Color.GREEN + stdout.strip() + Color.NONE)

if __name__ == '__main__':
    cli()
