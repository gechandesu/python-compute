import libvirt


class StoragePool:
    def __init__(self, pool: libvirt.virStoragePool):
        self.pool = pool

    def create_volume(self):
        pass
