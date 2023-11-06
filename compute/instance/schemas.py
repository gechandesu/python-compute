"""Compute instance related objects schemas."""

import re
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, validator

from compute.utils.units import DataUnit


class CPUEmulationMode(StrEnum):
    """CPU emulation mode enumerated."""

    HOST_PASSTHROUGH = 'host-passthrough'
    HOST_MODEL = 'host-model'
    CUSTOM = 'custom'
    MAXIMUM = 'maximum'


class CPUTopologySchema(BaseModel):
    """CPU topology model."""

    sockets: int
    cores: int
    threads: int
    dies: int = 1


class CPUFeaturesSchema(BaseModel):
    """CPU features model."""

    require: list[str]
    disable: list[str]


class CPUSchema(BaseModel):
    """CPU model."""

    emulation_mode: CPUEmulationMode
    model: str
    vendor: str
    topology: CPUTopologySchema
    features: CPUFeaturesSchema


class VolumeType(StrEnum):
    """Storage volume types enumeration."""

    FILE = 'file'
    NETWORK = 'network'


class VolumeCapacitySchema(BaseModel):
    """Storage volume capacity field model."""

    value: int
    unit: DataUnit


class VolumeSchema(BaseModel):
    """Storage volume model."""

    type: VolumeType  # noqa: A003
    source: Path
    target: str
    capacity: VolumeCapacitySchema
    readonly: bool = False
    is_system: bool = False


class NetworkInterfaceSchema(BaseModel):
    """Network inerface model."""

    source: str
    mac: str


class BootOptionsSchema(BaseModel):
    """Instance boot settings."""

    order: tuple


class InstanceSchema(BaseModel):
    """Compute instance model."""

    name: str
    title: str
    description: str
    memory: int
    max_memory: int
    vcpus: int
    max_vcpus: int
    cpu: CPUSchema
    machine: str
    emulator: Path
    arch: str
    image: str
    boot: BootOptionsSchema
    volumes: list[VolumeSchema]
    network_interfaces: list[NetworkInterfaceSchema]

    @validator('name')
    def _check_name(cls, value: str) -> str:  # noqa: N805
        if not re.match(r'^[a-z0-9_]+$', value):
            msg = (
                'Name can contain only lowercase letters, numbers '
                'and underscore.'
            )
            raise ValueError(msg)
        return value

    @validator('volumes')
    def _check_volumes(cls, value: list) -> list:  # noqa: N805
        if len([v for v in value if v.is_system is True]) != 1:
            msg = 'Volumes list must contain one system volume'
            raise ValueError(msg)
        return value

    @validator('network_interfaces')
    def _check_network_interfaces(cls, value: list) -> list:  # noqa: N805
        if not value:
            msg = 'Network interfaces list must contain at least one element'
            raise ValueError(msg)
        return value
