import os
import tomllib
from collections import UserDict
from pathlib import Path


NODEAGENT_CONFIG_FILE = os.getenv('NODEAGENT_CONFIG_FILE')
NODEAGENT_DEFAULT_CONFIG_FILE = '/etc/node-agent/config.toml'


class ConfigLoaderError(Exception):
    """Bad config file syntax, unreachable file or bad config schema."""


class ConfigLoader(UserDict):

    def __init__(self, file: Path | None = None):
        if file is None:
            file = NODEAGENT_CONFIG_FILE or NODEAGENT_DEFAULT_CONFIG_FILE
        self.file = Path(file)
        super().__init__(self._load())
        # todo: load deafult configuration

    def _load(self) -> dict:
        try:
            with open(self.file, 'rb') as config:
                return tomllib.load(config)
                # todo: config schema validation
        except tomllib.TOMLDecodeError as tomlerr:
            raise ConfigLoaderError(
                f'Bad TOML syntax in config file: {self.file}: {tomlerr}'
            ) from tomlerr
        except (OSError, ValueError) as readerr:
            raise ConfigLoaderError(
                f'Cannot read config file: {self.file}: {readerr}') from readerr

    def reload(self) -> None:
        self.data = self._load()
