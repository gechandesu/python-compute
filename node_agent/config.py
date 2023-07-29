import os
import tomllib
from pathlib import Path
from collections import UserDict


NODEAGENT_CONFIG_FILE = os.getenv('NODEAGENT_CONFIG_FILE')
NODEAGENT_DEFAULT_CONFIG_FILE = '/etc/node-agent/config.toml'


class ConfigLoadError(Exception):
    """Bad config file syntax, unreachable file or bad data."""


class ConfigLoader(UserDict):
    def __init__(self, file: Path | None = None):
        if file is None:
            file = NODEAGENT_CONFIG_FILE or NODEAGENT_DEFAULT_CONFIG_FILE
        self.file = Path(file)
        self.data = self._load()
        # todo: load deafult configuration

    def _load(self):
        try:
            with open(self.file, 'rb') as config:
                return tomllib.load(config)
                # todo: config schema validation
        except tomllib.TOMLDecodeError as tomlerr:
            raise ConfigLoadError(f'Bad TOML syntax in config file: {self.file}: {tomlerr}') from tomlerr
        except (OSError, ValueError) as readerr:
            raise ConfigLoadError(f'Cannot read config file: {self.file}: {readerr}') from readerr
