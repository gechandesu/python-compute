import libvirt


class VolumeInfo:
    """
    Volume info schema
    {'type': 'local', 'system': True, 'size': 102400, 'mode': 'rw'}
    """
    pass


class Volume:
    def __init__(self, pool: libvirt.virStorageVol):
        self.pool = pool

    def lookup_by_path(self):
        pass

    def generate_xml(self):
        pass

    def create(self):
        pass
