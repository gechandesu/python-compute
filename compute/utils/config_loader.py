"""Configuration loader."""

import tomllib
from collections import UserDict
from pathlib import Path

from compute.exceptions import ConfigLoaderError


DEFAULT_CONFIGURATION = {}
DEFAULT_CONFIG_FILE = '/etc/computed/computed.toml'


class ConfigLoader(UserDict):
    """UserDict for storing configuration."""

    def __init__(self, file: Path | None = None):
        """
        Initialise ConfigLoader.

        :param file: Path to configuration file. If `file` is None
            use default path from DEFAULT_CONFIG_FILE constant.
        """
        # TODO @ge: load deafult configuration
        self.file = Path(file) if file else Path(DEFAULT_CONFIG_FILE)
        super().__init__(self.load())

    def load(self) -> dict:
        """Load confguration object from TOML file."""
        try:
            with Path(self.file).open('rb') as configfile:
                return tomllib.load(configfile)
                # TODO @ge: add config schema validation
        except tomllib.TOMLDecodeError as tomlerr:
            raise ConfigLoaderError(
                f'Bad TOML syntax in config file: {self.file}: {tomlerr}'
            ) from tomlerr
        except (OSError, ValueError) as readerr:
            raise ConfigLoaderError(
                f'Cannot read config file: {self.file}: {readerr}'
            ) from readerr
