from pathlib import Path

from lxml import etree

from compute.storage import DiskConfig



with Path('./dom.xml').open('r') as f:
    xml = etree.fromstring(f.read())



def get_disk_by_target(name):
    disk_tgt = xml.xpath('/domain/devices/disk/target[@dev="vda"]')



def get_disks(xml: etree.Element) -> list[etree.Element]:
    xmldisks = xml.findall('devices/disk')
    for xmldisk in xmldisks:
        disk_config = DiskConfig(
            type=xmldisk.get('type'),
            device=xmldisk.get('device'),
            target=xmldisk.find('target').get('dev'),
            path=xmldisk.find('source').get('file'),
        )



