from pathlib import Path

from lxml.builder import E
from lxml.etree import Element, QName, SubElement, tostring, fromstring


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

    def gen_volume_xml(self, dev: str, mode: str) -> str:
        """
        Todo: No hardcode
        https://libvirt.org/formatdomain.html#hard-drives-floppy-disks-cdroms
        """
        volume = E.disk(type='file', device='disk')
        volume.append(E.driver(name='qemu', type='qcow2', cache='writethrough'))
        volume.append(E.source(file=path))
        volume.append(E.target(dev=dev, bus='virtio'))
        if mode.lower() == 'ro':
            volume.append(E.readonly())
        return tostring(volume, encoding='unicode', pretty_print=True).strip()
