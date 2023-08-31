from lxml.builder import E
from lxml.etree import Element, QName, SubElement, fromstring, tostring


class Constructor:
    """
    The XML constructor. This class builds XML configs for libvirt.
    """

    def gen_domain_xml(self, name: str, title: str, desc: str, memory: int,
                       vcpus: int, domain_type: str, machine: str, arch: str,
                       boot_order: tuple, cpu: str, mac: str) -> str:
        """
        Return basic libvirt domain configuration.
        """
        domain = E.domain(
            E.name(name),
            E.title(title),
            E.description(desc),
            E.metadata(),
            E.memory(str(memory), unit='MB'),
            E.currentMemory(str(memory), unit='MB'),
            E.vcpu(str(vcpus), placement='static'),
            type='kvm'
        )
        os = E.os(E.type(domain_type, machine=machine, arch=arch))
        for dev in boot_order:
            os.append(E.boot(dev=dev))
        domain.append(os)
        domain.append(E.features(E.acpi(), E.apic()))
        domain.append(fromstring(cpu))
        domain.append(E.on_poweroff('destroy'))
        domain.append(E.on_reboot('restart'))
        domain.append(E.on_crash('restart'))
        domain.append(E.pm(
            E('suspend-to-mem', enabled='no'),
            E('suspend-to-disk', enabled='no'))
        )
        devices = E.devices()
        devices.append(E.emulator('/usr/bin/qemu-system-x86_64'))
        devices.append(E.interface(
            E.source(network='default'),
            E.mac(address=mac),
            type='network')
        )
        devices.append(E.graphics(type='vnc', port='-1', autoport='yes'))
        devices.append(E.input(type='tablet', bus='usb'))
        devices.append(E.channel(
            E.source(mode='bind'),
            E.target(type='virtio', name='org.qemu.guest_agent.0'),
            E.address(type='virtio-serial', controller='0', bus='0', port='1'),
            type='unix')
        )
        devices.append(E.console(
            E.target(type='serial', port='0'),
            type='pty')
        )
        devices.append(E.video(
            E.model(type='vga', vram='16384', heads='1', primary='yes'))
        )
        domain.append(devices)
        return tostring(domain, encoding='unicode', pretty_print=True).strip()

    def gen_volume_xml(self, dev: str, mode: str, path: str) -> str:
        """
        Todo: No hardcode
        https://libvirt.org/formatdomain.html#hard-drives-floppy-disks-cdroms
        """
        volume = E.disk(type='file', device='disk')
        volume.append(
            E.driver(
                name='qemu',
                type='qcow2',
                cache='writethrough'))
        volume.append(E.source(file=path))
        volume.append(E.target(dev=dev, bus='virtio'))
        if mode.lower() == 'ro':
            volume.append(E.readonly())
        return tostring(volume, encoding='unicode', pretty_print=True).strip()

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

    def add_meta(self, xml: Element, data: dict,
                 namespace: str, nsprefix: str) -> None:
        """
        Add metadata to domain. See:
        https://libvirt.org/formatdomain.html#general-metadata
        """
        metadata = metadata_old = xml.xpath('/domain/metadata')[0]
        metadata.append(
            self.construct_xml(
                data,
                namespace=namespace,
                nsprefix=nsprefix,
            ))
        xml.replace(metadata_old, metadata)
