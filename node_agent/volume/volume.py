from dataclasses import dataclass
from time import time

import libvirt
from lxml.builder import E
from lxml.etree import tostring


@dataclass
class VolumeInfo:
    name: str
    path: str
    capacity: int

    def to_xml(self) -> str:
        unixtime = str(int(time()))
        xml = E.volume(type='file')
        xml.append(E.name(self.name))
        xml.append(E.key(self.path))
        xml.append(E.source())
        xml.append(E.capacity(str(self.capacity * 1024 * 1024), unit='bytes'))
        xml.append(E.allocation('0'))
        xml.append(E.target(
            E.path(self.path),
            E.format(type='qcow2'),
            E.timestamps(
                E.atime(unixtime),
                E.mtime(unixtime),
                E.ctime(unixtime)),
            E.compat('1.1'),
            E.features(E.lazy_refcounts())
        ))
        return tostring(xml, encoding='unicode', pretty_print=True)


class Volume:
    def __init__(self, pool: libvirt.virStoragePool,
                 vol: libvirt.virStorageVol):
        self.pool = pool
        self.vol = vol

    @property
    def name(self) -> str:
        return self.vol.name()

    @property
    def path(self) -> str:
        return self.vol.path()

    def dump_xml(self) -> str:
        return self.vol.XMLDesc()

    def clone(self, vol_info: VolumeInfo) -> None:
        self.pool.createXMLFrom(
            vol_info.to_xml(),
            self.vol,
            flags=libvirt.VIR_STORAGE_VOL_CREATE_PREALLOC_METADATA)

    def resize(self, capacity: int):
        """Resize volume to `capacity`. Unit is mebibyte."""
        self.vol.resize(capacity * 1024 * 1024)

    def delete(self) -> None:
        self.vol.delete()
