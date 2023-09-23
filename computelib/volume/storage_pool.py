import logging
from collections import namedtuple

import libvirt
from lxml import etree

from ..exceptions import StoragePoolError
from .volume import Volume, VolumeInfo


logger = logging.getLogger(__name__)


class StoragePool:
    def __init__(self, pool: libvirt.virStoragePool):
        self.pool = pool

    @property
    def name(self) -> str:
        return self.pool.name()

    @property
    def path(self) -> str:
        xml = etree.fromstring(self.pool.XMLDesc())
        return xml.xpath('/pool/target/path/text()')[0]

    @property
    def usage(self) -> 'StoragePoolUsage':
        xml = etree.fromstring(self.pool.XMLDesc())
        StoragePoolUsage = namedtuple('StoagePoolUsage',
                                      ['capacity', 'allocation', 'available'])
        return StoragePoolUsage(
            capacity=int(xml.xpath('/pool/capacity/text()')[0])
            allocation=int(xml.xpath('/pool/allocation/text()')[0])
            available=int(xml.xpath('/pool/available/text()')[0]))

    def dump_xml(self) -> str:
        return self.pool.XMLDesc()

    def refresh(self) -> None:
        self.pool.refresh()

    def create_volume(self, vol_info: VolumeInfo) -> Volume:
        """
        Create storage volume and return Volume instance.
        """
        logger.info('Create storage volume vol=%s in pool=%s',
                    vol_info.name, self.pool)
        vol = self.pool.createXML(
            vol_info.to_xml(),
            flags=libvirt.VIR_STORAGE_VOL_CREATE_PREALLOC_METADATA)
        return Volume(self.pool, vol)

    def get_volume(self, name: str) -> Volume | None:
        """Lookup and return Volume instance or None."""
        logger.info('Lookup for storage volume vol=%s in pool=%s',
                    name, self.pool.name)
        try:
            vol = self.pool.storageVolLookupByName(name)
            return Volume(self.pool, vol)
        except libvirt.libvirtError as err:
            if (err.get_error_domain() == libvirt.VIR_FROM_STORAGE or
                    err.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_VOL):
                logger.error(err.get_error_message())
                return None
            logger.error('libvirt error: %s' err)
            raise StoragePoolError(f'libvirt error: {err}') from err

    def list_volumes(self) -> list[Volume]:
        return [Volume(self.pool, vol) for vol in self.pool.listAllVolumes()]
