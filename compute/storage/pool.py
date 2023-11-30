# This file is part of Compute
#
# Compute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

"""Manage storage pools."""

import logging
from pathlib import Path
from typing import NamedTuple

import libvirt
from lxml import etree

from compute.exceptions import StoragePoolError, VolumeNotFoundError

from .volume import Volume, VolumeConfig


log = logging.getLogger(__name__)


class StoragePoolUsageInfo(NamedTuple):
    """Storage pool usage info."""

    capacity: int
    allocation: int
    available: int


class StoragePool:
    """Storage pool manipulating class."""

    def __init__(self, pool: libvirt.virStoragePool):
        """Initislise StoragePool."""
        self.pool = pool
        self.name = pool.name()
        self.path = self._get_path()

    def _get_path(self) -> Path:
        """Return storage pool path."""
        xml = etree.fromstring(self.pool.XMLDesc())
        return Path(xml.xpath('/pool/target/path/text()')[0])

    def get_usage_info(self) -> StoragePoolUsageInfo:
        """Return info about storage pool usage."""
        xml = etree.fromstring(self.pool.XMLDesc())
        return StoragePoolUsageInfo(
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
            'Create storage volume vol=%s in pool=%s', vol_conf.name, self.name
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
            if e.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_VOL:
                raise VolumeNotFoundError(name) from e
            log.exception('unexpected error from libvirt')
            raise StoragePoolError(e) from e

    def list_volumes(self) -> list[Volume]:
        """Return list of volumes in storage pool."""
        return [Volume(self.pool, vol) for vol in self.pool.listAllVolumes()]
