"""Manage storage pools."""

import logging
from pathlib import Path
from typing import NamedTuple

import libvirt
from lxml import etree

from compute.exceptions import StoragePoolError

from .volume import Volume, VolumeConfig


log = logging.getLogger(__name__)


class StoragePoolUsage(NamedTuple):
    """Storage pool usage info schema."""

    capacity: int
    allocation: int
    available: int


class StoragePool:
    """Storage pool manipulating class."""

    def __init__(self, pool: libvirt.virStoragePool):
        """Initislise StoragePool."""
        self.pool = pool
        self.name = pool.name()

    @property
    def path(self) -> Path:
        """Return storage pool path."""
        xml = etree.fromstring(self.pool.XMLDesc())  # noqa: S320
        return Path(xml.xpath('/pool/target/path/text()')[0])

    def usage(self) -> StoragePoolUsage:
        """Return info about storage pool usage."""
        xml = etree.fromstring(self.pool.XMLDesc())  # noqa: S320
        return StoragePoolUsage(
            capacity=int(xml.xpath('/pool/capacity/text()')[0]),
            allocation=int(xml.xpath('/pool/allocation/text()')[0]),
            available=int(xml.xpath('/pool/available/text()')[0]),
        )

    def dump_xml(self) -> str:
        """Return storage pool XML description as string."""
        return self.pool.XMLDesc()

    def refresh(self) -> None:
        """Refresh storage pool."""
        # TODO @ge: handle libvirt asynchronous job related exceptions
        self.pool.refresh()

    def create_volume(self, vol_conf: VolumeConfig) -> Volume:
        """Create storage volume and return Volume instance."""
        log.info(
            'Create storage volume vol=%s in pool=%s', vol_conf.name, self.pool
        )
        vol = self.pool.createXML(
            vol_conf.to_xml(),
            flags=libvirt.VIR_STORAGE_VOL_CREATE_PREALLOC_METADATA,
        )
        return Volume(self.pool, vol)

    def clone_volume(self, src: Volume, dst: VolumeConfig) -> Volume:
        """
        Make storage volume copy.

        :param src: Input volume
        :param dst: Output volume config
        """
        log.info(
            'Start volume cloning '
            'src_pool=%s src_vol=%s dst_pool=%s dst_vol=%s',
            src.pool_name,
            src.name,
            self.pool.name,
            dst.name,
        )
        vol = self.pool.createXMLFrom(
            dst.to_xml(),  # new volume XML description
            src.vol,  # source volume virStorageVol object
            flags=libvirt.VIR_STORAGE_VOL_CREATE_PREALLOC_METADATA,
        )
        if vol is None:
            raise StoragePoolError
        return Volume(self.pool, vol)

    def get_volume(self, name: str) -> Volume | None:
        """Lookup and return Volume instance or None."""
        log.info(
            'Lookup for storage volume vol=%s in pool=%s', name, self.pool.name
        )
        try:
            vol = self.pool.storageVolLookupByName(name)
            return Volume(self.pool, vol)
        except libvirt.libvirtError as e:
            # TODO @ge: Raise VolumeNotFoundError instead
            if (
                e.get_error_domain() == libvirt.VIR_FROM_STORAGE
                or e.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_VOL
            ):
                log.exception(e.get_error_message())
                return None
            log.exception('unexpected error from libvirt')
            raise StoragePoolError(e) from e

    def list_volumes(self) -> list[Volume]:
        """Return list of volumes in storage pool."""
        return [Volume(self.pool, vol) for vol in self.pool.listAllVolumes()]
