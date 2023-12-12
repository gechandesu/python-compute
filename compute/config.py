# This file is part of Compute
#
# Compute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Compute is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Compute.  If not, see <http://www.gnu.org/licenses/>.

"""Configuration loader."""

__all__ = ['Config', 'ConfigSchema']

import os
import tomllib
from collections import UserDict
from pathlib import Path
from typing import ClassVar

from .abstract import EntityModel
from .exceptions import ConfigLoaderError
from .utils import dictutil


class LibvirtConfigSchema(EntityModel):
    """Schema for libvirt config."""

    uri: str


class LogConfigSchema(EntityModel):
    """Logger congif schema."""

    level: str | None = None
    file: str | None = None


class StorageConfigSchema(EntityModel):
    """Storage config schema."""

    volumes: str
    images: str


class ConfigSchema(EntityModel):
    """Configuration file schema."""

    libvirt: LibvirtConfigSchema | None
    log: LogConfigSchema | None
    storage: StorageConfigSchema


class Config(UserDict):
    """
    UserDict for storing configuration.

    Environment variables prefix is ``CMP_``. Environment variables
    have higher proirity then configuration file.

    :cvar str IMAGES_POOL: images storage pool name taken from env
    :cvar str VOLUMES_POOL: volumes storage pool name taken from env
    :cvar Path DEFAULT_CONFIG_FILE: :file:`/etc/computed/computed.toml`
    :cvar dict DEFAULT_CONFIGURATION:
    """

    LIBVIRT_URI = os.getenv('CMP_LIBVIRT_URI')
    IMAGES_POOL = os.getenv('CMP_IMAGES_POOL')
    VOLUMES_POOL = os.getenv('CMP_VOLUMES_POOL')

    DEFAULT_CONFIG_FILE = Path('/etc/compute/computed.toml')
    DEFAULT_CONFIGURATION: ClassVar[dict] = {
        'libvirt': {
            'uri': 'qemu:///system',
        },
        'log': {
            'level': None,
            'file': None,
        },
        'storage': {
            'images': 'images',
            'volumes': 'volumes',
        },
    }

    def __init__(self, file: Path | None = None):
        """
        Initialise Config.

        :param file: Path to configuration file. If `file` is None
            use default path from :var:`Config.DEFAULT_CONFIG_FILE`.
        """
        self.file = Path(file) if file else self.DEFAULT_CONFIG_FILE
        try:
            if self.file.exists():
                with self.file.open('rb') as configfile:
                    loaded = tomllib.load(configfile)
            else:
                loaded = {}
        except tomllib.TOMLDecodeError as etoml:
            raise ConfigLoaderError(
                f'Bad TOML syntax: {self.file}: {etoml}'
            ) from etoml
        except (OSError, ValueError) as eread:
            raise ConfigLoaderError(
                f'Config read error: {self.file}: {eread}'
            ) from eread
        config = dictutil.override(self.DEFAULT_CONFIGURATION, loaded)
        if self.LIBVIRT_URI:
            config['libvirt']['uri'] = self.LIBVIRT_URI
        if self.VOLUMES_POOL:
            config['storage']['volumes'] = self.VOLUMES_POOL
        if self.IMAGES_POOL:
            config['storage']['images'] = self.IMAGES_POOL
        ConfigSchema(**config)
        super().__init__(config)
