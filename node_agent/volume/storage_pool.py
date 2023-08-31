import libvirt

from .volume import Volume, VolumeInfo


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

    def create_volume(self, vol_info: VolumeInfo) -> None:
        # todo: return Volume object?
        self.pool.createXML(
            vol_info.to_xml(),
            flags=libvirt.VIR_STORAGE_VOL_CREATE_PREALLOC_METADATA)

    def get_volume(self, name: str) -> Volume:
        vol = self.pool.storageVolLookupByName(name)
        return Volume(self.pool, vol)

    def list_volumes(self) -> list[Volume]:
        return [Volume(self.pool, vol) for vol in self.pool.listAllVolumes()]
