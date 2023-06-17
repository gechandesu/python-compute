import os
import sys
import pathlib
import tomllib


NODEAGENT_CONFIG_FILE = \
    os.getenv('NODEAGENT_CONFIG_FILE') or '/etc/nodeagent/configuration.toml'


def load_config(config: pathlib.Path):
    try:
        with open(config, 'rb') as conf:
            return tomllib.load(conf)
    except (OSError, ValueError) as readerr:
        sys.exit(f'Error: Cannot read configuration file: {readerr}')
    except tomllib.TOMLDecodeError as tomlerr:
        sys.exit(f'Error: Bad TOML syntax in configuration file: {tomlerr}')


config = load_config(pathlib.Path(NODEAGENT_CONFIG_FILE))
