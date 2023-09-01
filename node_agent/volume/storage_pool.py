import logging

import libvirt

from ..exceptions import StoragePoolError
from .volume import Volume, VolumeInfo


logger = logging.getLogger(__name__)


class StoragePool:
    def __init__(self, pool: libvirt.virStoragePool):
        self.pool = pool

    @property
    def name(self) -> str:
        return self.pool.name()

    def dump_xml(self) -> str:
        return self.pool.XMLDesc()

    def create(self):
        pass

    def delete(self):
        pass

    def refresh(self) -> None:
        self.pool.refresh()

    def create_volume(self, vol_info: VolumeInfo) -> Volume:
        """
        Create storage volume and return Volume instance.
        """
        logger.info(f'Create storage volume vol={vol_info.name} '
                    f'in pool={self.pool}')
        vol = self.pool.createXML(
            vol_info.to_xml(),
            flags=libvirt.VIR_STORAGE_VOL_CREATE_PREALLOC_METADATA)
        return Volume(self.pool, vol)

    def get_volume(self, name: str) -> Volume | None:
        """
        Lookup and return Volume instance or None.
        """
        logger.info(f'Lookup for storage volume vol={name} '
                    f'in pool={self.pool.name}')
        try:
            vol = self.pool.storageVolLookupByName(name)
            return Volume(self.pool, vol)
        except libvirt.libvirtError as err:
            if (err.get_error_domain() == libvirt.VIR_FROM_STORAGE
                err.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_VOL):
                logger.error(err.get_error_message())
                return None
            else:
                logger.error(f'libvirt error: {err}')
                raise StoragePoolError(f'libvirt error: {err}') from err

    def list_volumes(self) -> list[Volume]:
        return [Volume(self.pool, vol) for vol in self.pool.listAllVolumes()]
