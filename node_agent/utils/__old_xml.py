from pathlib import Path

from lxml.builder import E
from lxml.etree import Element, QName, SubElement, tostring, fromstring


XPATH_DOM_NAME = '/domain/name'
XPATH_DOM_TITLE = '/domain/title'
XPATH_DOM_DESCRIPTION = '/domain/description'
XPATH_DOM_METADATA = '/domain/metadata'
XPATH_DOM_MEMORY = '/domain/memory'
XPATH_DOM_CURRENT_MEMORY = '/domain/currentMemory'
XPATH_DOM_VCPU = '/domain/vcpu'
XPATH_DOM_OS = '/domian/os'
XPATH_DOM_CPU = '/domain/cpu'


class Reader:

    def __init__(xml: str):
        self.xml = xml
        self.el = fromstring(self.xml)

    def get_domcaps_machine(self):
        return self.el.xpath('/domainCapabilities/machine')[0].text

    def get_domcaps_cpus(self):
        # mode can be: custom, host-model, host-passthrough
        return self.el.xpath('/domainCapabilities/cpu/mode[@name="custom"]')[0]


class Constructor:
    """
    The XML constructor. This class builds XML configs for libvirt.
    Features:
        - Generate basic virtual machine XML. See gen_domain_xml()
        - Generate virtual disk XML. See gen_volume_xml()
        - Add arbitrary metadata to XML from special structured dict
    """

    def __init__(self, xml: str | None = None):
        self.xml_string = xml
        self.xml = None

    @property
    def domain_xml(self):
        return self.xml

    def gen_domain_xml(self,
                       name: str,
                       title: str,
                       vcpus: int,
                       vcpu_vendor: str,
                       vcpu_model: str,
                       mac_addr: str,
                       memory: int,
                       volume: Path,
                       vcpu_features: dict | None = None,
                       desc: str = "") -> None:
        """
        Generate default domain XML configuration for virtual machines.
        See https://lxml.de/tutorial.html#the-e-factory for details.
        """
        domain_xml = E.domain(
            E.name(name),
            E.title(title),
            E.description(desc),
            E.metadata(),
            E.memory(str(memory), unit='MB'),
            E.currentMemory(str(memory), unit='MB'),
            E.vcpu(str(vcpus), placement='static'),
            E.os(
                E.type('hvm', arch='x86_64'),
                E.boot(dev='cdrom'),
                E.boot(dev='hd'),
            ),
            E.features(
                E.acpi(),
                E.apic(),
            ),
            E.cpu(
                E.vendor(vcpu_vendor),
                E.model(vcpu_model, fallback='forbid'),
                E.topology(sockets='1', dies='1', cores=str(vcpus),
                           threads='1'),
                mode='custom',
                match='exact',
                check='partial',
            ),
            E.on_poweroff('destroy'),
            E.on_reboot('restart'),
            E.on_crash('restart'),
            E.pm(
                E('suspend-to-mem', enabled='no'),
                E('suspend-to-disk', enabled='no'),
            ),
            E.devices(
                E.emulator('/usr/bin/qemu-system-x86_64'),
                E.disk(
                    E.driver(name='qemu', type='qcow2', cache='writethrough'),
                    E.source(file=volume),
                    E.target(dev='vda', bus='virtio'),
                    type='file',
                    device='disk',
                ),
                E.interface(
                    E.source(network='default'),
                    E.mac(address=mac_addr),
                    type='network',
                ),
                E.graphics(
                    E.listen(type='address'),
                    type='vnc', port='-1', autoport='yes'
                ),
                E.video(
                    E.model(type='vga', vram='16384', heads='1', primary='yes'),
                    E.address(type='pci', domain='0x0000', bus='0x00',
                              slot='0x02', function='0x0'),
                ),
            ),
            type='kvm',
        )
        return self.to_string(domain_xml)

    def gen_volume_xml(self,
                       device_name: str,
                       file: Path,
                       bus: str = 'virtio',
                       cache: str = 'writethrough',
                       disktype: str = 'file'):
        disk_xml = E.disk(E.driver(name='qemu', type='qcow2', cache=cache),
                      E.source(file=file),
                      E.target(dev=device_name, bus=bus),
                      type=disktype,
                      device='disk')
        return self.to_string(disk_xml)

    def add_volume(self):
        raise NotImplementedError()

    def add_meta(self, data: dict, namespace: str, nsprefix: str) -> None:
        """
        Add metadata to domain. See:
        https://libvirt.org/formatdomain.html#general-metadata
        """
        metadata = metadata_old = self.xml.xpath('/domain/metadata')[0]
        metadata.append(
            self.construct_xml(
                data,
                namespace=namespace,
                nsprefix=nsprefix,
            ))
        self.xml.replace(metadata_old, metadata)

    def remove_meta(self, namespace: str):
        """Remove metadata by namespace."""
        raise NotImplementedError()

    def construct_xml(self,
                      tag: dict,
                      namespace: str | None = None,
                      nsprefix: str | None = None,
                      root: Element = None) -> Element:
        """
        Shortly this recursive function transforms dictonary to XML.
        Return etree.Element built from dict with following structure::

            {
                'name': 'device',  # tag name
                'text': '',  # optional key
                'values': {  # optional key, must be a dict of key-value pairs
                    'type': 'disk'
                },
                children: []  # optional key, must be a list of dicts
            }

        Child elements must have the same structure. Infinite `children` nesting
        is allowed.
        """
        use_ns = False
        if isinstance(namespace, str) and isinstance(nsprefix, str):
            use_ns = True
        # Create element
        if root is None:
            if use_ns:
                element = Element(QName(namespace, tag['name']),
                                  nsmap={nsprefix: namespace})
            else:
                element = Element(tag['name'])
        else:
            if use_ns:
                element = SubElement(root, QName(namespace, tag['name']))
            else:
                element = SubElement(root, tag['name'])
        # Fill up element with content
        if 'text' in tag.keys():
            element.text = tag['text']
        if 'values' in tag.keys():
            for key in tag['values'].keys():
                element.set(str(key), str(tag['values'][key]))
        if 'children' in tag.keys():
            for child in tag['children']:
                element.append(
                    self.construct_xml(child,
                                       namespace=namespace,
                                       nsprefix=nsprefix,
                                       root=element))
        return element

    def to_string(self):
        return (tostring(self.xml, pretty_print=True,
                         encoding='utf-8').decode().strip())
