import re
import textwrap
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from uuid import UUID

from lxml.etree import SubElement, fromstring, tostring

from ..utils import mac, xml


class CPUMode(Enum):
    HOST_MODEL = 'host-model'
    HOST_PASSTHROUGH = 'host-passthrough'
    CUSTOM = 'custom'
    MAXIMUM = 'maximum'

    @classmethod
    def default(cls):
        return cls.HOST_MODEL


@dataclass
class CPUTopology:
    sockets: int
    cores: int
    threads: int

    def validate(self, vcpus: int) -> None:
        if self.sockets * self.cores * self.threads == vcpus:
            return
        raise ValueError("CPU topology must match the number of 'vcpus'")


@dataclass
class CPUInfo:
    vendor: str
    model: str
    required_features: list[str]
    disabled_features: list[str]


@dataclass
class VolumeInfo:
    name: str
    path: Path
    capacity: int


@dataclass
class CloudInitConfig:
    user_data: str = ''
    meta_data: str = ''


class Boot(Enum):
    BIOS = 'bios'
    UEFI = 'uefi'

    @classmethod
    def default(cls):
        return cls.BIOS


@dataclass
class BootMenu:
    enabled: bool = False
    timeout: int = 3000


class VirtualMachineInstaller:

    def __init__(self, session: 'LibvirtSession'):
        self.connection = session.connection  # libvirt.virConnect object
        self.domcaps = fromstring(
            self.connection.getDomainCapabilities())
        self.arch = self.domcaps.xpath('/domainCapabilities/arch/text()')[0]
        self.virttype = self.domcaps.xpath(
            '/domainCapabilities/domain/text()')[0]
        self.emulator = self.domcaps.xpath(
            '/domainCapabilities/path/text()')[0]
        self.machine = self.domcaps.xpath(
            '/domainCapabilities/machine/text()')[0]

    def install(
            self,
            name: str | None = None,
            title: str | None = None,
            description: str = '',
            os: str | None = None,
            image: UUID | None = None,
            volumes: list['VolumeInfo'] | None = None,
            vcpus: int = 0,
            vcpu_info: CPUInfo | None = None,
            vcpu_mode: CPUMode = CPUMode.default(),
            vcpu_topology: CPUTopology | None = None,
            memory: int = 0,
            boot: Boot = Boot.default(),
            boot_menu: BootMenu = BootMenu(),
            boot_order: tuple[str] = ('cdrom', 'hd'),
            cloud_init: CloudInitConfig | None = None):
        """
        Install virtual machine with passed parameters.

        If no `vcpu_info` is None select best CPU wich can be provided by
        hypervisor. Choosen CPU depends on `vcpu_mode`, default is 'custom'.
        See CPUMode for more info. Default `vcpu_topology` is: 1 socket,
        `vcpus` cores, 1 threads.

        `memory` must be integer value in mebibytes e.g. 4094 MiB = 4 GiB.

        Volumes must be passed as list of VolumeInfo objects. Minimum one
        volume is required.
        """
        name = self._validate_name(name)

        if vcpu_topology is None:
            vcpu_topology = CPUTopology(sockets=1, cores=vcpus, threads=1)
        vcpu_topology.validate(vcpus)

        if vcpu_info is None:
            if not vcpu_mode:
                vcpu_mode = CPUMode.CUSTOM.value
            xml_cpu = self._choose_best_cpu(vcpu_mode)
        else:
            raise NotImplementedError('Custom CPU not implemented')

        xml_domain = xml.Constructor().gen_domain_xml(
            name=name,
            title=title if title else name,
            desc=description if description else '',
            vcpus=vcpus,
            # vcpu_topology=vcpu_topology,
            # vcpu_info=vcpu_info,
            memory=memory,
            domain_type='hvm',
            machine=self.machine,
            arch=self.arch,
            # boot_menu=boot_menu,
            boot_order=boot_order,
            cpu=xml_cpu,
            mac=mac.random_mac()
        )
        xml_volume = xml.Constructor().gen_volume_xml(
            dev='vda', mode='rw', path='')

        virconn = self.connection

        virstor = virconn.storagePoolLookupByName('default')
        # Мб использовать storageVolLookupByPath вместо поиска по имени
        etalon_volume = virstor.storageVolLookupByName('debian_bookworm.qcow2')

        return xml_domain

    def _validate_name(self, name) -> str:
        if name is None:
            raise ValueError("'name' cannot be empty")
        if isinstance(name, str):
            if not re.match(r"^[a-z0-9_]+$", name, re.I):
                raise ValueError(
                    "'name' can contain only letters, numbers "
                    "and underscore.")
            return name.lower()
        raise TypeError(f"'name' must be 'str', not {type(name)}")

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
            arch = SubElement(cpus, 'arch')
            arch.text = self.arch
            xmlcpus = tostring(cpus, encoding='unicode', pretty_print=True)
            xml = self.connection.baselineHypervisorCPU(
                self.emulator, self.arch, self.machine, self.virttype, [xmlcpus])
        else:
            raise ValueError(
                f'CPU mode must be in {[v.value for v in CPUMode]}, '
                f"but passed '{mode}'")
        return textwrap.indent(xml, ' ' * 2)

    def _define(self, xml: str) -> None:
        self.connection.defineXML(xml)
