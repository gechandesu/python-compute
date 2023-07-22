import pathlib

from lxml import etree
from lxml.builder import E


class NewXML:
    def __init__(
        self,
        name: str,
        title: str,
        memory: int,
        vcpus: int,
        cpu_vendor: str,
        cpu_model: str,
        volume_path: str,

        desc: str | None = None,
        show_boot_menu: bool = False,
    ):
        """
        Initialise basic XML using lxml E-Factory. Ref:

            - https://lxml.de/tutorial.html#the-e-factory
            - https://libvirt.org/formatdomain.html
        """
        DOMAIN = E.domain
        NAME = E.name
        TITLE = E.title
        DESCRIPTION = E.description
        METADATA = E.metadata
        MEMORY = E.memory
        CURRENTMEMORY = E.currentMemory
        VCPU = E.vcpu
        OS = E.os
        OS_TYPE = E.type
        OS_BOOT = E.boot
        FEATURES = E.features
        ACPI = E.acpi
        APIC = E.apic
        CPU = E.cpu
        CPU_VENDOR = E.vendor
        CPU_MODEL = E.model
        ON_POWEROFF = E.on_poweroff
        ON_REBOOT = E.on_reboot
        ON_CRASH = E.on_crash
        DEVICES = E.devices
        EMULATOR = E.emulator
        DISK = E.disk
        DISK_DRIVER = E.driver
        DISK_SOURCE = E.source
        DISK_TARGET = E.target
        INTERFACE = E.interface
        GRAPHICS = E.graphics

        self.domain = DOMAIN(
            NAME(name),
            TITLE(title),
            DESCRIPTION(desc or ""),
            METADATA(),
            MEMORY(str(memory), unit='MB'),
            CURRENTMEMORY(str(memory), unit='MB'),
            VCPU(str(vcpus), placement='static'),
            OS(
                OS_TYPE('hvm', arch='x86_64'),
                OS_BOOT(dev='cdrom'),
                OS_BOOT(dev='hd'),
            ),
            FEATURES(
                ACPI(),
                APIC(),
            ),
            CPU(
                CPU_VENDOR(cpu_vendor),
                CPU_MODEL(cpu_model, fallback='forbid'),
                mode='custom',
                match='exact',
                check='partial',
            ),
            ON_POWEROFF('destroy'),
            ON_REBOOT('restart'),
            ON_CRASH('restart'),
            DEVICES(
                EMULATOR('/usr/bin/qemu-system-x86_64'),
                DISK(
                    DISK_DRIVER(name='qemu', type='qcow2', cache='writethrough'),
                    DISK_SOURCE(file=volume_path),
                    DISK_TARGET(dev='vda', bus='virtio'),
                    type='file',
                    device='disk',
                ),
            ),
            type='kvm',
        )

    def add_volume(self, options: dict, params: dict):
        """Add disk device to domain."""
        DISK = E.disk
        DISK_DRIVER = E.driver
        DISK_SOURCE = E.source
        DISK_TARGET = E.target

x = NewXML(
    name='1',
    title='first',
    memory=2048,
    vcpus=4,
    cpu_vendor='Intel',
    cpu_model='Broadwell',
    volume_path='/srv/vm-volumes/5031077f-f9ea-410b-8d84-ae6e79f8cde0.qcow2',
)

# x.add_volume()
# print(x.domain)
print(etree.tostring(x.domain, pretty_print=True).decode().strip())
