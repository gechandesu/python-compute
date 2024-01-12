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
from collections import Counter
from enum import StrEnum
from pathlib import Path

from pydantic import validator

from compute.abstract import EntityModel
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


class DiskCache(StrEnum):
    """Possible disk cache mechanisms enumeration."""

    NONE = 'none'
    WRITETHROUGH = 'writethrough'
    WRITEBACK = 'writeback'
    DIRECTSYNC = 'directsync'
    UNSAFE = 'unsafe'


class DiskDriverSchema(EntityModel):
    """Virtual disk driver model."""

    name: str
    type: str  # noqa: A003
    cache: DiskCache = DiskCache.WRITETHROUGH


class DiskBus(StrEnum):
    """Possible disk buses enumeration."""

    VIRTIO = 'virtio'
    IDE = 'ide'
    SATA = 'sata'


class VolumeSchema(EntityModel):
    """Storage volume model."""

    type: VolumeType  # noqa: A003
    target: str
    driver: DiskDriverSchema
    capacity: VolumeCapacitySchema | None
    source: str | None = None
    is_readonly: bool = False
    is_system: bool = False
    bus: DiskBus = DiskBus.VIRTIO
    device: str = 'disk'


class NetworkAdapterModel(StrEnum):
    """Network adapter models."""

    VIRTIO = 'virtio'
    E1000 = 'e1000'
    RTL8139 = 'rtl8139'


class NetworkInterfaceSchema(EntityModel):
    """Network inerface model."""

    source: str
    mac: str
    model: NetworkAdapterModel


class NetworkSchema(EntityModel):
    """Network configuration schema."""

    interfaces: list[NetworkInterfaceSchema]


class BootOptionsSchema(EntityModel):
    """Instance boot settings."""

    order: tuple


class CloudInitSchema(EntityModel):
    """Cloud-init config model."""

    user_data: str | None = None
    meta_data: str | None = None
    vendor_data: str | None = None
    network_config: str | None = None


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
    network: NetworkSchema | None | bool
    image: str | None = None
    cloud_init: CloudInitSchema | None = None

    @validator('name')
    def _check_name(cls, value: str) -> str:  # noqa: N805
        if not re.match(r'^[a-z0-9_-]+$', value):
            msg = (
                'Name must contain only lowercase letters, numbers, '
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
        index = 0
        for volume in volumes:
            index += 1
            if volume.source is None and volume.capacity is None:
                msg = f"{index}: capacity is required if 'source' is unset"
                raise ValueError(msg)
            if volume.is_system is True and volume.is_readonly is True:
                msg = 'volume marked as system cannot be readonly'
                raise ValueError(msg)
        sources = [v.source for v in volumes if v.source is not None]
        targets = [v.target for v in volumes]
        for item in [sources, targets]:
            duplicates = Counter(item) - Counter(set(item))
            if duplicates:
                msg = f'find duplicate values: {list(duplicates)}'
                raise ValueError(msg)
        return volumes

    @validator('network')
    def _check_network(
        cls,  # noqa: N805
        network: NetworkSchema | None | bool,
    ) -> NetworkSchema | None | bool:
        if network is True:
            msg = (
                "'network' cannot be True, set it to False "
                'or provide network configuration'
            )
            raise ValueError(msg)
        return network
