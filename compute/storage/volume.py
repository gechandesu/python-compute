"""Manage storage volumes."""

from dataclasses import dataclass
from pathlib import Path
from time import time

import libvirt
from lxml import etree
from lxml.builder import E

from compute.utils import units


@dataclass
class VolumeConfig:
    """
    Storage volume config builder.

    Generate XML config for creating a volume in a libvirt
    storage pool.
    """

    name: str
    path: str
    capacity: int

    def to_xml(self) -> str:
        """Return XML config for libvirt."""
        unixtime = str(int(time()))
        xml = E.volume(type='file')
        xml.append(E.name(self.name))
        xml.append(E.key(self.path))
        xml.append(E.source())
        xml.append(E.capacity(str(self.capacity), unit='bytes'))
        xml.append(E.allocation('0'))
        xml.append(
            E.target(
                E.path(self.path),
                E.format(type='qcow2'),
                E.timestamps(
                    E.atime(unixtime), E.mtime(unixtime), E.ctime(unixtime)
                ),
                E.compat('1.1'),
                E.features(E.lazy_refcounts()),
            )
        )
        return etree.tostring(xml, encoding='unicode', pretty_print=True)


@dataclass
class DiskConfig:
    """
    Disk config builder.

    Generate XML config for attaching or detaching storage volumes
    to compute instances.
    """

    target: str
    path: str
    readonly: bool = False

    def to_xml(self) -> str:
        """Return XML config for libvirt."""
        xml = E.disk(type='file', device='disk')
        xml.append(E.driver(name='qemu', type='qcow2', cache='writethrough'))
        xml.append(E.source(file=self.path))
        xml.append(E.target(dev=self.target, bus='virtio'))
        if self.readonly:
            xml.append(E.readonly())
        return etree.tostring(xml, encoding='unicode', pretty_print=True)


class Volume:
    """Storage volume manipulating class."""

    def __init__(
        self, pool: libvirt.virStoragePool, vol: libvirt.virStorageVol
    ):
        """
        Initialise Volume.

        :param pool: libvirt virStoragePool object
        :param vol: libvirt virStorageVol object
        """
        self.pool = pool
        self.pool_name = pool.name()
        self.vol = vol
        self.name = vol.name()
        self.path = Path(vol.path())

    def dump_xml(self) -> str:
        """Return volume XML description as string."""
        return self.vol.XMLDesc()

    def clone(self, vol_conf: VolumeConfig) -> None:
        """
        Make a copy of volume to the same storage pool.

        :param vol_info VolumeInfo: New storage volume dataclass object
        """
        self.pool.createXMLFrom(
            vol_conf.to_xml(),
            self.vol,
            flags=libvirt.VIR_STORAGE_VOL_CREATE_PREALLOC_METADATA,
        )

    def resize(self, capacity: int, unit: units.DataUnit) -> None:
        """
        Resize volume.

        :param capacity int: Volume new capacity.
        :param unit DataUnit: Data unit. Internally converts into bytes.
        """
        # TODO @ge: Check actual volume size before resize
        self.vol.resize(units.to_bytes(capacity, unit=unit))

    def delete(self) -> None:
        """Delete volume from storage pool."""
        self.vol.delete()
