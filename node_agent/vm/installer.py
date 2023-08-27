import re

import libvirt

from ..utils.xml import Constructor
from ..utils.mac import random_mac
from .hardware import DomainCapabilities, vCPUMode, vCPUTopology, Boot


class vCPUInfo:
    pass

class ImageVolume:
    pass

class CloudInitConfig:
    pass

class BootOrder:
    pass

class VirtualMachineInstaller:
    def __init__(self, session: libvirt.virConnect):
        self.session = session
        self.info = {}

    def install(
        self,
        name: str | None = None,
        title: str | None = None,
        description: str = '',
        os: str | None = None,
        image: ImageVolume | None = None,
        volumes: list['VolumeInfo'] | None = None,
        vcpus: int = 0,
        vcpu_info: vCPUInfo | None = None,
        vcpu_mode: vCPUMode | None = None,
        vcpu_topology: vCPUTopology | None = None,
        memory: int = 0,
        boot: Boot = Boot.BIOS,
        boot_menu: bool = False,
        boot_order: BootOrder = ('cdrom', 'hd'),
        cloud_init: CloudInitConfig | None = None):
        """
        Install virtual machine with passed parameters.
        """
        domcaps = DomainCapabilities(self.session.session)
        name = self._validate_name(name)
        if vcpu_topology is None:
            vcpu_topology = vCPUTopology(
                {'sockets': 1, 'cores': vcpus, 'threads': 1})
        self._validate_topology(vcpus, vcpu_topology)
        if vcpu_info is None:
            if not vcpu_mode:
                vcpu_mode = vCPUMode.CUSTOM.value
            xml_cpu = domcaps.best_cpu(vcpu_mode)
        else:
            raise NotImplementedError('Custom CPU not implemented')
        xml_domain = Constructor().gen_domain_xml(
            name=name,
            title=title if title else name,
            desc=description if description else '',
            vcpus=vcpus,
            memory=memory,
            domain_type='hvm',
            machine=domcaps.machine,
            arch=domcaps.arch,
            boot_order=('cdrom', 'hd'),
            cpu=xml_cpu,
            mac=random_mac()
        )
        return xml_domain

    def _validate_name(self, name):
        if name is None:
            raise ValueError("'name' cannot be empty")
        if isinstance(name, str):
            if not re.match(r"^[a-z0-9_]+$", name, re.I):
                raise ValueError(
                    "'name' can contain only letters, numbers "
                    "and underscore.")
            return name.lower()
        raise TypeError(f"'name' must be 'str', not {type(name)}")

    def _validate_topology(self, vcpus, topology):
        sockets = topology['sockets']
        cores = topology['cores']
        threads = topology['threads']
        if sockets * cores * threads == vcpus:
            return
        raise ValueError("CPU topology must match the number of 'vcpus'")

    def _define(self, xml: str):
        self.session.defineXML(xml)
