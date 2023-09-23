import textwrap
from dataclasses import dataclass
from enum import Enum

from lxml import etree
from lxml.builder import E

from ..utils import mac
from ..volume import DiskInfo, VolumeInfo


@dataclass
class VirtualMachineInfo:
    name: str
    title: str
    memory: int
    vcpus: int
    machine: str
    emulator: str
    arch: str
    cpu: str  # CPU full XML description
    mac: str
    description: str = ''
    boot_order: tuple = ('cdrom', 'hd')

    def to_xml(self) -> str:
        xml = E.domain(
            E.name(self.name),
            E.title(self.title),
            E.description(self.description),
            E.metadata(),
            E.memory(str(self.memory), unit='MB'),
            E.currentMemory(str(self.memory), unit='MB'),
            E.vcpu(str(self.vcpus), placement='static'),
            type='kvm')
        os = E.os(E.type('hvm', machine=self.machine, arch=self.arch))
        for dev in self.boot_order:
            os.append(E.boot(dev=dev))
        xml.append(os)
        xml.append(E.features(E.acpi(), E.apic()))
        xml.append(etree.fromstring(self.cpu))
        xml.append(E.on_poweroff('destroy'))
        xml.append(E.on_reboot('restart'))
        xml.append(E.on_crash('restart'))
        xml.append(E.pm(
            E('suspend-to-mem', enabled='no'),
            E('suspend-to-disk', enabled='no'))
        )
        devices = E.devices()
        devices.append(E.emulator(self.emulator))
        devices.append(E.interface(
            E.source(network='default'),
            E.mac(address=self.mac),
            type='network'))
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
        xml.append(devices)
        return etree.tostring(xml, encoding='unicode', pretty_print=True)


class CPUMode(Enum):
    HOST_MODEL = 'host-model'
    HOST_PASSTHROUGH = 'host-passthrough'
    CUSTOM = 'custom'
    MAXIMUM = 'maximum'

    @classmethod
    def default(cls):
        return cls.HOST_PASSTHROUGH


@dataclass
class CPUTopology:
    sockets: int
    cores: int
    threads: int

    def validate(self, vcpus: int) -> None:
        if self.sockets * self.cores * self.threads == vcpus:
            return
        raise ValueError("CPU topology must match the number of 'vcpus'")


class VirtualMachineInstaller:

    def __init__(self, session: 'LibvirtSession'):
        self.session = session
        self.connection = session.connection  # libvirt.virConnect object
        self.domcaps = etree.fromstring(
            self.connection.getDomainCapabilities())
        self.arch = self.domcaps.xpath('/domainCapabilities/arch/text()')[0]
        self.virttype = self.domcaps.xpath(
            '/domainCapabilities/domain/text()')[0]
        self.emulator = self.domcaps.xpath(
            '/domainCapabilities/path/text()')[0]
        self.machine = self.domcaps.xpath(
            '/domainCapabilities/machine/text()')[0]

    def install(self, data: 'VirtualMachineSchema'):
        xml_cpu = self._choose_best_cpu(CPUMode.default())
        xml_vm = VirtualMachineInfo(
            name=data['name'],
            title=data['title'],
            vcpus=data['vcpus'],
            memory=data['memory'],
            machine=self.machine,
            emulator=self.emulator,
            arch=self.arch,
            cpu=xml_cpu,
            mac=mac.random_mac()
        ).to_xml()
        self._define(xml_vm)
        storage_pool = self.session.get_storage_pool('default')
        etalon_vol = storage_pool.get_volume('bookworm.qcow2')
        new_vol = VolumeInfo(
            name=data['name'] +
            '_disk_some_pattern.qcow2',
            path=storage_pool.path +
            '/' +
            data['name'] +
            '_disk_some_pattern.qcow2',
            capacity=data['volume']['capacity'])
        etalon_vol.clone(new_vol)
        vm = self.session.get_machine(data['name'])
        vm.attach_device(DiskInfo(path=new_vol.path, target='vda'))
        vm.set_vcpus(data['vcpus'])
        vm.set_memory(data['memory'])
        vm.start()
        vm.set_autostart(enabled=True)

    def _choose_best_cpu(self, mode: CPUMode) -> str:
        if mode == 'host-passthrough':
            xml = '<cpu mode="host-passthrough" migratable="on"/>'
        elif mode == 'maximum':
            xml = '<cpu mode="maximum" migratable="on"/>'
        elif mode in ['host-model', 'custom']:
            cpus = self.domcaps.xpath(
                f'/domainCapabilities/cpu/mode[@name="{mode}"]')[0]
            cpus.tag = 'cpu'
            for attr in cpus.attrib.keys():
                del cpus.attrib[attr]
            arch = etree.SubElement(cpus, 'arch')
            arch.text = self.arch
            xmlcpus = etree.tostring(
                cpus, encoding='unicode', pretty_print=True)
            xml = self.connection.baselineHypervisorCPU(
                self.emulator, self.arch, self.machine, self.virttype, [xmlcpus])
        else:
            raise ValueError(
                f'CPU mode must be in {[v.value for v in CPUMode]}, '
                f"but passed '{mode}'")
        return textwrap.indent(xml, ' ' * 2)

    def _define(self, xml: str) -> None:
        self.connection.defineXML(xml)
