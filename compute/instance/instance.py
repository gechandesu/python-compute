"""Manage compute instances."""

__all__ = ['Instance', 'InstanceConfig']

import logging
from dataclasses import dataclass

import libvirt
from lxml import etree
from lxml.builder import E

from compute.exceptions import (
    GuestAgentCommandNotSupportedError,
    InstanceError,
)
from compute.utils import units

from .guest_agent import GuestAgent
from .schemas import CPUSchema, InstanceSchema, NetworkInterfaceSchema


log = logging.getLogger(__name__)


class InstanceConfig:
    """Compute instance description for libvirt."""

    def __init__(self, schema: InstanceSchema):
        """
        Initialise InstanceConfig.

        :param schema: InstanceSchema object
        """
        self.name = schema.name
        self.title = schema.title
        self.description = schema.description
        self.memory = schema.memory
        self.max_memory = schema.max_memory
        self.vcpus = schema.vcpus
        self.max_vcpus = schema.max_vcpus
        self.cpu = schema.cpu
        self.machine = schema.machine
        self.emulator = schema.emulator
        self.arch = schema.arch
        self.boot = schema.boot
        self.network_interfaces = schema.network_interfaces

    def _gen_cpu_xml(self, cpu: CPUSchema) -> etree.Element:
        xml = E.cpu(match='exact', mode=cpu.emulation_mode)
        xml.append(E.model(cpu.model, fallback='forbid'))
        xml.append(E.vendor(cpu.vendor))
        xml.append(
            E.topology(
                sockets=str(cpu.topology.sockets),
                dies=str(cpu.topology.dies),
                cores=str(cpu.topology.cores),
                threads=str(cpu.topology.threads),
            )
        )
        for feature in cpu.features.require:
            xml.append(E.feature(policy='require', name=feature))
        for feature in cpu.features.disable:
            xml.append(E.feature(policy='disable', name=feature))
        return xml

    def _gen_vcpus_xml(self, vcpus: int, max_vcpus: int) -> etree.Element:
        xml = E.vcpus()
        xml.append(E.vcpu(id='0', enabled='yes', hotpluggable='no', order='1'))
        for i in range(max_vcpus - 1):
            enabled = 'yes' if (i + 2) <= vcpus else 'no'
            xml.append(
                E.vcpu(
                    id=str(i + 1),
                    enabled=enabled,
                    hotpluggable='yes',
                    order=str(i + 2),
                )
            )
        return xml

    def _gen_network_interface_xml(
        self, interface: NetworkInterfaceSchema
    ) -> etree.Element:
        return E.interface(
            E.source(network=interface.source),
            E.mac(address=interface.mac),
            type='network',
        )

    def to_xml(self) -> str:
        """Return XML config for libvirt."""
        xml = E.domain(
            E.name(self.name),
            E.title(self.title),
            E.description(self.description),
            E.metadata(),
            E.memory(str(self.memory * 1024), unit='KiB'),
            E.currentMemory(str(self.memory * 1024), unit='KiB'),
            type='kvm',
        )
        xml.append(
            E.vcpu(
                str(self.max_vcpus),
                placement='static',
                current=str(self.vcpus),
            )
        )
        xml.append(self._gen_cpu_xml(self.cpu))
        os = E.os(E.type('hvm', machine=self.machine, arch=self.arch))
        for dev in self.boot.order:
            os.append(E.boot(dev=dev))
        xml.append(os)
        xml.append(E.features(E.acpi(), E.apic()))
        xml.append(E.on_poweroff('destroy'))
        xml.append(E.on_reboot('restart'))
        xml.append(E.on_crash('restart'))
        xml.append(
            E.pm(
                E('suspend-to-mem', enabled='no'),
                E('suspend-to-disk', enabled='no'),
            )
        )
        devices = E.devices()
        devices.append(E.emulator(str(self.emulator)))
        for interface in self.network_interfaces:
            devices.append(self._gen_network_interface_xml(interface))
        devices.append(E.graphics(type='vnc', port='-1', autoport='yes'))
        devices.append(E.input(type='tablet', bus='usb'))
        devices.append(
            E.channel(
                E.source(mode='bind'),
                E.target(type='virtio', name='org.qemu.guest_agent.0'),
                E.address(
                    type='virtio-serial', controller='0', bus='0', port='1'
                ),
                type='unix',
            )
        )
        devices.append(
            E.console(E.target(type='serial', port='0'), type='pty')
        )
        devices.append(
            E.video(
                E.model(type='vga', vram='16384', heads='1', primary='yes')
            )
        )
        xml.append(devices)
        return etree.tostring(xml, encoding='unicode', pretty_print=True)


@dataclass
class InstanceInfo:
    state: str
    max_memory: int
    memory: int
    nproc: int
    cputime: int


class DeviceConfig:
    """Abstract device description class."""


class Instance:
    """Manage compute instances."""

    def __init__(self, domain: libvirt.virDomain):
        """
        Initialise Instance.

        :ivar libvirt.virDomain domain: domain object
        :ivar libvirt.virConnect connection: connection object
        :ivar str name: domain name
        :ivar GuestAgent guest_agent: :class:`GuestAgent` object

        :param domain: libvirt domain object
        """
        self.domain = domain
        self.connection = domain.connect()
        self.name = domain.name()
        self.guest_agent = GuestAgent(domain)

    def _expand_instance_state(self, state: int) -> str:
        states = {
            libvirt.VIR_DOMAIN_NOSTATE: 'nostate',
            libvirt.VIR_DOMAIN_RUNNING: 'running',
            libvirt.VIR_DOMAIN_BLOCKED: 'blocked',
            libvirt.VIR_DOMAIN_PAUSED: 'paused',
            libvirt.VIR_DOMAIN_SHUTDOWN: 'shutdown',
            libvirt.VIR_DOMAIN_SHUTOFF: 'shutoff',
            libvirt.VIR_DOMAIN_CRASHED: 'crashed',
            libvirt.VIR_DOMAIN_PMSUSPENDED: 'pmsuspended',
        }
        return states[state]

    @property
    def info(self) -> InstanceInfo:
        """
        Return instance info.

        https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainInfo
        """
        _info = self.domain.info()
        return InstanceInfo(
            state=self._expand_instance_state(_info[0]),
            max_memory=_info[1],
            memory=_info[2],
            nproc=_info[3],
            cputime=_info[4],
        )

    @property
    def status(self) -> str:
        """
        Return instance state: 'running', 'shutoff', etc.

        Reference:
        https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainState
        """
        try:
            state, _ = self.domain.state()
        except libvirt.libvirtError as e:
            raise InstanceError(
                'Cannot fetch status of ' f'instance={self.name}: {e}'
            ) from e
        return self._expand_instance_state(state)

    @property
    def is_running(self) -> bool:
        """Return True if instance is running, else return False."""
        if self.domain.isActive() != 1:
            # 0 - is inactive, -1 - is error
            return False
        return True

    @property
    def is_autostart(self) -> bool:
        """Return True if instance autostart is enabled, else return False."""
        try:
            return bool(self.domain.autostart())
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot get autostart status for '
                f'instance={self.name}: {e}'
            ) from e

    def start(self) -> None:
        """Start defined instance."""
        log.info('Starting instnce=%s', self.name)
        if self.is_running:
            log.warning(
                'Already started, nothing to do instance=%s', self.name
            )
            return
        try:
            self.domain.create()
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot start instance={self.name}: {e}'
            ) from e

    def shutdown(self, method: str | None = None) -> None:
        """
        Shutdown instance.

        Shutdown methods:

        SOFT
            Use guest agent to shutdown. If guest agent is unavailable
            NORMAL method will be used.

        NORMAL
            Use method choosen by hypervisor to shutdown. Usually send ACPI
            signal to guest OS. OS may ignore ACPI e.g. if guest is hanged.

        HARD
            Shutdown instance without any guest OS shutdown. This is simular
            to unplugging machine from power. Internally send SIGTERM to
            instance process and destroy it gracefully.

        UNSAFE
            Force shutdown. Internally send SIGKILL to instance process.
            There is high data corruption risk!

        If method is None NORMAL method will used.

        :param method: Method used to shutdown instance
        """
        methods = {
            'SOFT': libvirt.VIR_DOMAIN_SHUTDOWN_GUEST_AGENT,
            'NORMAL': libvirt.VIR_DOMAIN_SHUTDOWN_DEFAULT,
            'HARD': libvirt.VIR_DOMAIN_DESTROY_GRACEFUL,
            'UNSAFE': libvirt.VIR_DOMAIN_DESTROY_DEFAULT,
        }
        if method is None:
            method = 'NORMAL'
        if not isinstance(method, str):
            raise TypeError(
                f"Shutdown method must be a 'str', not {type(method)}"
            )
        method = method.upper()
        if method not in methods:
            raise ValueError(f"Unsupported shutdown method: '{method}'")
        try:
            if method in ['SOFT', 'NORMAL']:
                self.domain.shutdownFlags(flags=methods[method])
            elif method in ['HARD', 'UNSAFE']:
                self.domain.destroyFlags(flags=methods[method])
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot shutdown instance={self.name} ' f'{method=}: {e}'
            ) from e

    def reset(self) -> None:
        """
        Reset instance.

        Copypaste from libvirt doc:

        Reset a domain immediately without any guest OS shutdown.
        Reset emulates the power reset button on a machine, where all
        hardware sees the RST line set and reinitializes internal state.

        Note that there is a risk of data loss caused by reset without any
        guest OS shutdown.
        """
        try:
            self.domain.reset()
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot reset instance={self.name}: {e}'
            ) from e

    def reboot(self) -> None:
        """Send ACPI signal to guest OS to reboot. OS may ignore this."""
        try:
            self.domain.reboot()
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot reboot instance={self.name}: {e}'
            ) from e

    def set_autostart(self, *, enabled: bool) -> None:
        """
        Set autostart flag for instance.

        :param enabled: Bool argument to set or unset autostart flag.
        """
        autostart = 1 if enabled else 0
        try:
            self.domain.setAutostart(autostart)
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot set autostart flag for instance={self.name} '
                f'{autostart=}: {e}'
            ) from e

    def set_vcpus(self, nvcpus: int, *, live: bool = False) -> None:
        """
        Set vCPU number.

        If `live` is True and instance is not currently running vCPUs
        will set in config and will applied when instance boot.

        NB: Note that if this call is executed before the guest has
        finished booting, the guest may fail to process the change.

        :param nvcpus: Number of vCPUs
        :param live: Affect a running instance
        """
        if nvcpus == 0:
            raise InstanceError(
                f'Cannot set zero vCPUs for instance={self.name}'
            )
        if nvcpus == self.info.nproc:
            log.warning(
                'Instance instance=%s already have %s vCPUs, nothing to do',
                self.name,
                nvcpus,
            )
            return
        try:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
            self.domain.setVcpusFlags(nvcpus, flags=flags)
            if live is True:
                if not self.is_running:
                    log.warning(
                        'Instance is not running, changes applied in '
                        'instance config.'
                    )
                    return
                flags = libvirt.VIR_DOMAIN_AFFECT_LIVE
                self.domain.setVcpusFlags(nvcpus, flags=flags)
                if self.guest_agent.is_available():
                    try:
                        self.guest_agent.raise_for_commands(
                            ['guest-set-vcpus']
                        )
                        flags = libvirt.VIR_DOMAIN_VCPU_GUEST
                        self.domain.setVcpusFlags(nvcpus, flags=flags)
                    except GuestAgentCommandNotSupportedError:
                        log.warning(
                            'Cannot set vCPUs in guest via agent, you may '
                            'need to apply changes in guest manually.'
                        )
                else:
                    log.warning(
                        'Cannot set vCPUs in guest OS on instance=%s. '
                        'You may need to apply CPUs in guest manually.',
                        self.name,
                    )
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot set vCPUs for instance={self.name}: {e}'
            ) from e

    def set_memory(self, memory: int, *, live: bool = False) -> None:
        """
        Set memory.

        If `live` is True and instance is not currently running set memory
        in config and will applied when instance boot.

        :param memory: Memory value in mebibytes
        :param live: Affect a running instance
        """
        if memory == 0:
            raise InstanceError(
                f'Cannot set zero memory for instance={self.name}'
            )
        if live and self.info()['state'] == libvirt.VIR_DOMAIN_RUNNING:
            flags = (
                libvirt.VIR_DOMAIN_AFFECT_LIVE
                | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            )
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        try:
            self.domain.setMemoryFlags(
                memory * 1024, flags=libvirt.VIR_DOMAIN_MEM_MAXIMUM
            )
            self.domain.setMemoryFlags(memory * 1024, flags=flags)
        except libvirt.libvirtError as e:
            msg = f'Cannot set memory for instance={self.name} {memory=}: {e}'
            raise InstanceError(msg) from e

    def attach_device(
        self, device: 'DeviceConfig', *, live: bool = False
    ) -> None:
        """
        Attach device to compute instance.

        :param device: Object with device description e.g. DiskConfig
        :param live: Affect a running instance
        """
        if live and self.is_running:
            flags = (
                libvirt.VIR_DOMAIN_AFFECT_LIVE
                | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            )
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        self.domain.attachDeviceFlags(device.to_xml(), flags=flags)

    def detach_device(
        self, device: 'DeviceConfig', *, live: bool = False
    ) -> None:
        """
        Dettach device from compute instance.

        :param device: Object with device description e.g. DiskConfig
        :param live: Affect a running instance
        """
        if live and self.is_running:
            flags = (
                libvirt.VIR_DOMAIN_AFFECT_LIVE
                | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            )
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        self.domain.detachDeviceFlags(device.to_xml(), flags=flags)

    def resize_volume(
        self, name: str, capacity: int, unit: units.DataUnit
    ) -> None:
        """
        Resize block device.

        :param name: Disk device name e.g. `vda`, `sda`, etc.
        :param capacity: Volume capacity in bytes.
        """
        self.domain.blockResize(
            name,
            units.to_bytes(capacity, unit=unit),
            flags=libvirt.VIR_DOMAIN_BLOCK_RESIZE_BYTES,
        )

    def pause(self) -> None:
        """Pause instance."""
        raise NotImplementedError

    def resume(self) -> None:
        """Resume paused instance."""
        raise NotImplementedError

    def list_ssh_keys(self, user: str) -> list[str]:
        """
        Get list of SSH keys on guest for specific user.

        :param user: Username.
        """
        raise NotImplementedError

    def set_ssh_keys(self, user: str, ssh_keys: list[str]) -> None:
        """
        Add SSH keys to guest for specific user.

        :param user: Username.
        :param ssh_keys: List of public SSH keys.
        """
        raise NotImplementedError

    def remove_ssh_keys(self, user: str, ssh_keys: list[str]) -> None:
        """
        Remove SSH keys from guest for specific user.

        :param user: Username.
        :param ssh_keys: List of public SSH keys.
        """
        raise NotImplementedError

    def set_user_password(self, user: str, password: str) -> None:
        """
        Set new user password in guest OS.

        This action performs by guest agent inside guest.

        :param user: Username.
        :param password: Password.
        """
        self.domain.setUserPassword(user, password)

    def dump_xml(self, *, inactive: bool = False) -> str:
        """Return instance XML description."""
        flags = libvirt.VIR_DOMAIN_XML_INACTIVE if inactive else 0
        return self.domain.XMLDesc(flags)

    def delete(self) -> None:
        """Undefine instance and delete local volumes."""
        self.shutdown(method='HARD')
        self.domain.undefine()
