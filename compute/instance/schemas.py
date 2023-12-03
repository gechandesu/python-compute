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

"""Compute instance related objects schemas."""

import re
from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError, validator
from pydantic.error_wrappers import ErrorWrapper

from compute.common import EntityModel
from compute.utils.units import DataUnit


class CPUEmulationMode(StrEnum):
    """CPU emulation mode enumerated."""

    HOST_PASSTHROUGH = 'host-passthrough'
    HOST_MODEL = 'host-model'
    CUSTOM = 'custom'
    MAXIMUM = 'maximum'


class CPUTopologySchema(EntityModel):
    """CPU topology model."""

    sockets: int
    cores: int
    threads: int
    dies: int = 1


class CPUFeaturesSchema(EntityModel):
    """CPU features model."""

    require: list[str]
    disable: list[str]


class CPUSchema(EntityModel):
    """CPU model."""

    emulation_mode: CPUEmulationMode
    model: str | None
    vendor: str | None
    topology: CPUTopologySchema | None
    features: CPUFeaturesSchema | None


class VolumeType(StrEnum):
    """Storage volume types enumeration."""

    FILE = 'file'


class VolumeCapacitySchema(EntityModel):
    """Storage volume capacity field model."""

    value: int
    unit: DataUnit


class DiskDriverSchema(EntityModel):
    """Virtual disk driver model."""

    name: str
    type: str  # noqa: A003
    cache: str = 'writethrough'


class VolumeSchema(EntityModel):
    """Storage volume model."""

    type: VolumeType  # noqa: A003
    target: str
    driver: DiskDriverSchema
    capacity: VolumeCapacitySchema | None
    source: str | None = None
    is_readonly: bool = False
    is_system: bool = False
    bus: str = 'virtio'
    device: str = 'disk'


class NetworkInterfaceSchema(EntityModel):
    """Network inerface model."""

    source: str
    mac: str


class BootOptionsSchema(EntityModel):
    """Instance boot settings."""

    order: tuple


class InstanceSchema(EntityModel):
    """Compute instance model."""

    name: str
    title: str | None
    description: str | None
    memory: int
    max_memory: int
    vcpus: int
    max_vcpus: int
    cpu: CPUSchema
    machine: str
    emulator: Path
    arch: str
    boot: BootOptionsSchema
    volumes: list[VolumeSchema]
    network_interfaces: list[NetworkInterfaceSchema]
    image: str | None = None

    @validator('name')
    def _check_name(cls, value: str) -> str:  # noqa: N805
        if not re.match(r'^[a-z0-9_-]+$', value):
            msg = (
                'Name can contain only lowercase letters, numbers, '
                'minus sign and underscore.'
            )
            raise ValueError(msg)
        return value

    @validator('cpu')
    def _check_topology(cls, cpu: int, values: dict) -> CPUSchema:  # noqa: N805
        topo = cpu.topology
        max_vcpus = values['max_vcpus']
        if topo and topo.sockets * topo.cores * topo.threads != max_vcpus:
            msg = f'CPU topology does not match with {max_vcpus=}'
            raise ValueError(msg)
        return cpu

    @validator('volumes')
    def _check_volumes(cls, volumes: list) -> list:  # noqa: N805
        if len([v for v in volumes if v.is_system is True]) != 1:
            msg = 'volumes list must contain one system volume'
            raise ValueError(msg)
        for vol in volumes:
            if vol.source is None and vol.capacity is None:
                raise ValidationError(
                    [
                        ErrorWrapper(
                            Exception(
                                "capacity is required if 'source' is unset"
                            ),
                            loc='X.capacity',
                        )
                    ],
                    model=VolumeSchema,
                )
            if vol.is_system is True and vol.is_readonly is True:
                msg = 'volume marked as system cannot be readonly'
                raise ValueError(msg)
        return volumes

    @validator('network_interfaces')
    def _check_network_interfaces(cls, value: list) -> list:  # noqa: N805
        if not value:
            msg = 'Network interfaces list must contain at least one element'
            raise ValueError(msg)
        return value
