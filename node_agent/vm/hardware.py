import textwrap
from enum import Enum
from collections import UserDict

import libvirt
from lxml.etree import SubElement, fromstring, tostring


class Boot(Enum):
    BIOS = 'bios'
    UEFI = 'uefi'


class vCPUMode(Enum):
    HOST_MODEL = 'host-model'
    HOST_PASSTHROUGTH = 'host-passthrougth'
    CUSTOM = 'custom'
    MAXIMUM = 'maximum'


class DomainCapabilities:

    def __init__(self, session: libvirt.virConnect):
        self.session = session
        self.domcaps = fromstring(
            self.session.getDomainCapabilities())

    @property
    def arch(self):
        return self.domcaps.xpath('/domainCapabilities/arch')[0].text

    @property
    def virttype(self):
        return self.domcaps.xpath('/domainCapabilities/domain')[0].text

    @property
    def emulator(self):
        return self.domcaps.xpath('/domainCapabilities/path')[0].text

    @property
    def machine(self):
        return self.domcaps.xpath('/domainCapabilities/machine')[0].text

    def best_cpu(self, mode: vCPUMode) -> str:
        """
        See https://libvirt.org/html/libvirt-libvirt-host.html
        #virConnectBaselineHypervisorCPU
        """
        cpus = self.domcaps.xpath(
            f'/domainCapabilities/cpu/mode[@name="{mode}"]')[0]
        cpus.tag = 'cpu'
        for attr in cpus.attrib.keys():
            del cpus.attrib[attr]
        arch = SubElement(cpus, 'arch')
        arch.text = self.arch
        xmlcpus = tostring(cpus, encoding='unicode', pretty_print=True)
        xml = self.session.baselineHypervisorCPU(self.emulator,
            self.arch, self.machine, self.virttype, [xmlcpus])
        return textwrap.indent(xml, ' ' * 2)


class vCPUTopology(UserDict):
    """
    CPU topology schema ``{'sockets': 1, 'cores': 4, 'threads': 1}``::

        <topology sockets='1' dies='1' cores='4' threads='1'/>
    """

    def __init__(self, topology: dict):
        super().__init__(self._validate(topology))

    def _validate(self, topology: dict):
        if isinstance(topology, dict):
            if ['sockets', 'cores', 'threads'] != list(topology.keys()):
                raise ValueError("Topology must have 'sockets', 'cores' "
                                 "and 'threads' keys.")
            for key in topology.keys():
                if not isinstance(topology[key], int):
                    raise TypeError(f"Key '{key}' must be 'int'")
            return topology
        raise TypeError("Topology must be a 'dict'")
