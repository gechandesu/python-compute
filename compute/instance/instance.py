# This file is part of Compute
#
# Compute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Compute is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Compute.  If not, see <http://www.gnu.org/licenses/>.

"""Manage compute instances."""

__all__ = ['Instance', 'InstanceConfig', 'InstanceInfo']

import logging
import time
from typing import NamedTuple
from uuid import UUID

import libvirt
from lxml import etree
from lxml.builder import E

from compute.abstract import DeviceConfig, EntityConfig
from compute.exceptions import (
    GuestAgentCommandNotSupportedError,
    InstanceError,
)
from compute.utils import units

from .devices import DiskConfig
from .guest_agent import GuestAgent
from .schemas import (
    CPUEmulationMode,
    CPUSchema,
    InstanceSchema,
    NetworkInterfaceSchema,
)


log = logging.getLogger(__name__)


class InstanceConfig(EntityConfig):
    """Compute instance XML config builder."""

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
        self.network = schema.network

    def _gen_cpu_xml(self, cpu: CPUSchema) -> etree.Element:
        options = {
            'mode': cpu.emulation_mode,
            'match': 'exact',
            'check': 'partial',
        }
        if cpu.emulation_mode == CPUEmulationMode.HOST_PASSTHROUGH:
            options['check'] = 'none'
            options['migratable'] = 'on'
        xml = E.cpu(**options)
        if cpu.model:
            xml.append(E.model(cpu.model, fallback='forbid'))
        if cpu.vendor:
            xml.append(E.vendor(cpu.vendor))
        if cpu.topology:
            xml.append(
                E.topology(
                    sockets=str(cpu.topology.sockets),
                    dies=str(cpu.topology.dies),
                    cores=str(cpu.topology.cores),
                    threads=str(cpu.topology.threads),
                )
            )
        if cpu.features:
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
            E.model(type=interface.model),
            type='network',
        )

    def to_xml(self) -> str:
        """Return XML config for libvirt."""
        xml = E.domain(type='kvm')
        xml.append(E.name(self.name))
        if self.title:
            xml.append(E.title(self.title))
        if self.description:
            xml.append(E.description(self.description))
        xml.append(E.metadata())
        xml.append(E.memory(str(self.max_memory * 1024), unit='KiB'))
        xml.append(E.currentMemory(str(self.memory * 1024), unit='KiB'))
        xml.append(
            E.vcpu(
                str(self.max_vcpus),
                placement='static',
                current=str(self.vcpus),
            )
        )
        xml.append(self._gen_cpu_xml(self.cpu))
        xml.append(
            E.clock(
                E.timer(name='rtc', tickpolicy='catchup'),
                E.timer(name='pit', tickpolicy='delay'),
                E.timer(name='hpet', present='no'),
                offset='utc',
            )
        )
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
        if self.network:
            for interface in self.network.interfaces:
                devices.append(self._gen_network_interface_xml(interface))
        devices.append(E.graphics(type='vnc', autoport='yes'))
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
        devices.append(E.serial(E.target(port='0'), type='pty'))
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


class InstanceInfo(NamedTuple):
    """
    Store compute instance info.

    Reference:
    https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainInfo
    """

    state: str
    max_memory: int
    memory: int
    nproc: int
    cputime: int


class Instance:
    """Manage compute instances."""

    def __init__(self, domain: libvirt.virDomain):
        """
        Initialise Compute Instance object.

        :param domain: libvirt domain object
        """
        self._domain = domain
        self._connection = domain.connect()
        self._name = domain.name()
        self._uuid = domain.UUID()
        self._guest_agent = GuestAgent(domain)

    @property
    def connection(self) -> libvirt.virConnect:
        """Libvirt connection object."""
        return self._connection

    @property
    def domain(self) -> libvirt.virDomain:
        """Libvirt domain object."""
        return self._domain

    @property
    def name(self) -> str:
        """Instance name."""
        return self._name

    @property
    def uuid(self) -> UUID:
        """Instance UUID."""
        return UUID(bytes=self._uuid)

    @property
    def guest_agent(self) -> GuestAgent:
        """:class:`GuestAgent` object."""
        return self._guest_agent

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

    def get_info(self) -> InstanceInfo:
        """Return instance info."""
        info = self.domain.info()
        return InstanceInfo(
            state=self._expand_instance_state(info[0]),
            max_memory=info[1],
            memory=info[2],
            nproc=info[3],
            cputime=info[4],
        )

    def get_status(self) -> str:
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

    def is_running(self) -> bool:
        """Return True if instance is running, else return False."""
        if self.domain.isActive() == 1:
            return True
        return False

    def is_autostart(self) -> bool:
        """Return True if instance autostart is enabled, else return False."""
        try:
            return bool(self.domain.autostart())
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot get autostart status for '
                f'instance={self.name}: {e}'
            ) from e

    def get_max_memory(self) -> int:
        """Maximum memory value for domain in KiB."""
        return self.domain.maxMemory()

    def get_max_vcpus(self) -> int:
        """Maximum vCPUs number for domain."""
        if not self.is_running():
            xml = etree.fromstring(self.dump_xml(inactive=True))
            return int(xml.xpath('/domain/vcpu/text()')[0])
        return self.domain.maxVcpus()

    def start(self) -> None:
        """Start defined instance."""
        log.info("Starting instance '%s'", self.name)
        if self.is_running():
            log.warning(
                "Instance '%s' is already started, nothing to do", self.name
            )
            return
        try:
            self.domain.create()
        except libvirt.libvirtError as e:
            raise InstanceError(
                f"Cannot start instance '{self.name}': {e}"
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

        DESTROY
            Forced shutdown. Internally send SIGKILL to instance process.
            There is high data corruption risk!

        If method is None NORMAL method will used.

        :param method: Method used to shutdown instance
        """
        if not self.is_running():
            return
        methods = {
            'SOFT': libvirt.VIR_DOMAIN_SHUTDOWN_GUEST_AGENT,
            'NORMAL': libvirt.VIR_DOMAIN_SHUTDOWN_DEFAULT,
            'HARD': libvirt.VIR_DOMAIN_DESTROY_GRACEFUL,
            'DESTROY': libvirt.VIR_DOMAIN_DESTROY_DEFAULT,
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
        if method == 'SOFT' and self.guest_agent.is_available() is False:
            method = 'NORMAL'
        log.info("Performing instance shutdown with method '%s'", method)
        try:
            if method in ['SOFT', 'NORMAL']:
                self.domain.shutdownFlags(flags=methods[method])
            elif method in ['HARD', 'DESTROY']:
                self.domain.destroyFlags(flags=methods[method])
        except libvirt.libvirtError as e:
            raise InstanceError(
                f"Cannot shutdown instance '{self.name}' with '{method=}': {e}"
            ) from e

    def reboot(self) -> None:
        """Send ACPI signal to guest OS to reboot. OS may ignore this."""
        try:
            self.domain.reboot()
        except libvirt.libvirtError as e:
            raise InstanceError(
                f'Cannot reboot instance={self.name}: {e}'
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
                f"Cannot reset instance '{self.name}': {e}"
            ) from e

    def power_reset(self) -> None:
        """
        Shutdown instance and start.

        By analogy with real hardware, this is a normal server shutdown,
        and then turning off from the power supply and turning it on again.

        This method is applicable in cases where there has been a
        configuration change in libvirt and you need to restart the
        instance to apply the new configuration.
        """
        log.debug("Performing power reset for instance '%s'", self.name)
        self.shutdown('NORMAL')
        time.sleep(3)
        # TODO @ge: do safe shutdown insted of this shit
        if self.is_running():
            self.shutdown('HARD')
        time.sleep(1)
        self.start()

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
                f"Cannot set {autostart=} flag for instance '{self.name}': {e}"
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
        if nvcpus <= 0:
            raise InstanceError('Cannot set zero vCPUs')
        if nvcpus > self.get_max_vcpus():
            raise InstanceError('vCPUs count is greather than max_vcpus')
        if nvcpus == self.get_info().nproc:
            log.warning(
                "Instance '%s' already have %s vCPUs, nothing to do",
                self.name,
                nvcpus,
            )
            return
        try:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
            self.domain.setVcpusFlags(nvcpus, flags=flags)
            if live is True:
                if not self.is_running():
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
                            "'guest-set-vcpus' command is not supported, '"
                            'you may need to enable CPUs in guest manually.'
                        )
                else:
                    log.warning(
                        'Guest agent is not installed or not connected, '
                        'you may need to enable CPUs in guest manually.'
                    )
        except libvirt.libvirtError as e:
            raise InstanceError(
                f"Cannot set vCPUs for instance '{self.name}': {e}"
            ) from e

    def set_memory(self, memory: int, *, live: bool = False) -> None:
        """
        Set memory.

        If `live` is True and instance is not currently running set memory
        in config and will applied when instance boot.

        :param memory: Memory value in mebibytes
        :param live: Affect a running instance
        """
        if memory <= 0:
            raise InstanceError('Cannot set zero memory')
        if (memory * 1024) > self.get_max_memory():
            raise InstanceError('Memory is greather than max_memory')
        if (memory * 1024) == self.get_info().memory:
            log.warning(
                "Instance '%s' already have %s memory, nothing to do",
                self.name,
                memory,
            )
            return
        if live and self.is_running():
            flags = (
                libvirt.VIR_DOMAIN_AFFECT_LIVE
                | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            )
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        try:
            self.domain.setMemoryFlags(memory * 1024, flags=flags)
        except libvirt.libvirtError as e:
            msg = f'Cannot set memory for instance={self.name} {memory=}: {e}'
            raise InstanceError(msg) from e

    def attach_device(
        self, device: DeviceConfig, *, live: bool = False
    ) -> None:
        """
        Attach device to compute instance.

        :param device: Object with device description e.g. DiskConfig
        :param live: Affect a running instance
        """
        if live and self.is_running():
            flags = (
                libvirt.VIR_DOMAIN_AFFECT_LIVE
                | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            )
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        if isinstance(device, DiskConfig):  # noqa: SIM102
            if self.get_disk(device.target):
                log.warning(
                    "Volume with target '%s' is already attached",
                    device.target,
                )
                return
        self.domain.attachDeviceFlags(device.to_xml(), flags=flags)

    def detach_device(
        self, device: DeviceConfig, *, live: bool = False
    ) -> None:
        """
        Dettach device from compute instance.

        :param device: Object with device description e.g. DiskConfig
        :param live: Affect a running instance
        """
        if live and self.is_running():
            flags = (
                libvirt.VIR_DOMAIN_AFFECT_LIVE
                | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            )
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        if isinstance(device, DiskConfig):  # noqa: SIM102
            if self.get_disk(device.target) is None:
                log.warning(
                    "Volume with target '%s' is already detached",
                    device.target,
                )
                return
        self.domain.detachDeviceFlags(device.to_xml(), flags=flags)

    def get_disk(
        self, name: str, *, persistent: bool = False
    ) -> DiskConfig | None:
        """
        Return :class:`DiskConfig` by disk target name.

        Return None if disk with specified target not found.

        :param name: Disk name e.g. `vda`, `sda`, etc. This name may
            not match the name of the disk inside the guest OS.
        :param persistent: If True get only persistent volumes described
            in instance XML config.
        """
        xml = etree.fromstring(self.dump_xml(inactive=persistent))
        child = xml.xpath(f'/domain/devices/disk/target[@dev="{name}"]')
        if len(child) == 0:
            return None
        return DiskConfig.from_xml(child[0].getparent())

    def list_disks(self, *, persistent: bool = False) -> list[DiskConfig]:
        """
        Return list of attached disk devices.

        :param persistent: If True list only persistent volumes described
            in instance XML config.
        """
        xml = etree.fromstring(self.dump_xml(inactive=persistent))
        disks = xml.xpath('/domain/devices/disk')
        return [DiskConfig.from_xml(disk) for disk in disks]

    def detach_disk(self, name: str, *, live: bool = False) -> None:
        """
        Detach disk device by target name.

        There is no ``attach_disk()`` method. Use :func:`attach_device`
        with :class:`DiskConfig` as argument.

        :param name: Disk name e.g. `vda`, `sda`, etc. This name may
            not match the name of the disk inside the guest OS.
        :param live: Affect a running instance. Not supported for CDROM
            devices.
        """
        disk = self.get_disk(name, persistent=live)
        if disk is None:
            log.warning(
                "Volume with target '%s' is already detached",
                name,
            )
            return
        self.detach_device(disk, live=live)

    def resize_disk(
        self, name: str, capacity: int, unit: units.DataUnit
    ) -> None:
        """
        Resize attached block device.

        :param name: Disk name e.g. `vda`, `sda`, etc. This name may
            not match the name of the disk inside the guest OS.
        :param capacity: New capacity.
        :param unit: Capacity unit.
        """
        # TODO @ge: check actual size before making changes
        self.domain.blockResize(
            name,
            units.to_bytes(capacity, unit=unit),
            flags=libvirt.VIR_DOMAIN_BLOCK_RESIZE_BYTES,
        )

    def pause(self) -> None:
        """Pause instance."""
        if not self.is_running():
            raise InstanceError('Cannot pause inactive instance')
        self.domain.suspend()

    def resume(self) -> None:
        """Resume paused instance."""
        self.domain.resume()

    def list_ssh_keys(self, user: str) -> list[str]:
        """
        Return list of authorized SSH keys in guest for specific user.

        :param user: Username.
        """
        self.guest_agent.raise_for_commands(['guest-ssh-get-authorized-keys'])
        exc = self.guest_agent.guest_exec(
            path='/bin/sh',
            args=[
                '-c',
                (
                    'su -c "'
                    'if ! [ -f ~/.ssh/authorized_keys ]; then '
                    'mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys; '
                    'fi" '
                    f'{user}'
                ),
            ],
            capture_output=True,
            decode_output=True,
            poll=True,
        )
        log.debug(exc)
        try:
            return self.domain.authorizedSSHKeysGet(user)
        except libvirt.libvirtError as e:
            raise InstanceError(e) from e

    def set_ssh_keys(
        self,
        user: str,
        keys: list[str],
        *,
        remove: bool = False,
        append: bool = False,
    ) -> None:
        """
        Add authorized SSH keys to guest for specific user.

        :param user: Username.
        :param keys: List of authorized SSH keys.
        :param append: Append keys to authorized SSH keys instead of
            overriding authorized_keys file.
        :param remove: Remove authorized keys listed in `keys` parameter.
        """
        qemu_ga_commands = ['guest-ssh-add-authorized-keys']
        if remove and append:
            raise InstanceError(
                "'append' and 'remove' parameters are mutually exclusive"
            )
        if not self.is_running():
            raise InstanceError(
                'Cannot add authorized SSH keys to inactive instance'
            )
        if append:
            flags = libvirt.VIR_DOMAIN_AUTHORIZED_SSH_KEYS_SET_APPEND
        elif remove:
            flags = libvirt.VIR_DOMAIN_AUTHORIZED_SSH_KEYS_SET_REMOVE
            qemu_ga_commands = ['guest-ssh-remove-authorized-keys']
        else:
            flags = 0
        if keys.sort() == self.list_ssh_keys().sort():
            return
        self.guest_agent.raise_for_commands(qemu_ga_commands)
        try:
            self.domain.authorizedSSHKeysSet(user, keys, flags=flags)
        except libvirt.libvirtError as e:
            raise InstanceError(e) from e

    def set_user_password(
        self, user: str, password: str, *, encrypted: bool = False
    ) -> None:
        """
        Set new user password in guest OS.

        This action is performed by guest agent inside the guest.

        :param user: Username.
        :param password: Password.
        :param encrypted: Set it to True if password is already encrypted.
            Right encryption method depends on guest OS.
        """
        self.guest_agent.raise_for_commands(['guest-set-user-password'])
        flags = libvirt.VIR_DOMAIN_PASSWORD_ENCRYPTED if encrypted else 0
        log.debug("Setting up password for user '%s'", user)
        self.domain.setUserPassword(user, password, flags=flags)

    def dump_xml(self, *, inactive: bool = False) -> str:
        """Return instance XML description."""
        flags = libvirt.VIR_DOMAIN_XML_INACTIVE if inactive else 0
        return self.domain.XMLDesc(flags)

    def delete(self, *, with_volumes: bool = False) -> None:
        """
        Delete instance with local volumes.

        :param with_volumes: If True delete local volumes with instance.
        """
        log.info("Shutdown instance '%s'", self.name)
        self.shutdown(method='HARD')
        disks = self.list_disks(persistent=True)
        log.debug('Disks list: %s', disks)
        for disk in disks:
            if with_volumes and disk.type == 'file':
                try:
                    volume = self.connection.storageVolLookupByPath(
                        disk.source
                    )
                except libvirt.libvirtError as e:
                    if e.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_VOL:
                        log.warning(
                            "Volume '%s' not found, skipped",
                            disk.source,
                        )
                    continue
                log.info('Delete volume: %s', volume.path())
                volume.delete()
        log.info('Undefine instance')
        self.domain.undefine()
