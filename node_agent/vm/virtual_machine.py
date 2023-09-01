import logging

import libvirt

from ..exceptions import VMError
from ..volume import VolumeInfo
from .base import VirtualMachineBase


logger = logging.getLogger(__name__)


class VirtualMachine(VirtualMachineBase):

    @property
    def name(self):
        return self.domain_name

    @property
    def status(self) -> str:
        """
        Return VM state: 'running', 'shutoff', etc. Reference:
        https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainState
        """
        try:
            # libvirt returns list [state: int, reason: int]
            # https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainGetState
            state = self.domain.state()[0]
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot fetch VM status vm={self.domain_name}: {err}') from err
        STATES = {
            libvirt.VIR_DOMAIN_NOSTATE: 'nostate',
            libvirt.VIR_DOMAIN_RUNNING: 'running',
            libvirt.VIR_DOMAIN_BLOCKED: 'blocked',
            libvirt.VIR_DOMAIN_PAUSED: 'paused',
            libvirt.VIR_DOMAIN_SHUTDOWN: 'shutdown',
            libvirt.VIR_DOMAIN_SHUTOFF: 'shutoff',
            libvirt.VIR_DOMAIN_CRASHED: 'crashed',
            libvirt.VIR_DOMAIN_PMSUSPENDED: 'pmsuspended',
        }
        return STATES.get(state)

    @property
    def is_running(self) -> bool:
        """Return True if VM is running, else return False."""
        if self.domain.isActive() != 1:
            # inactive (0) or error (-1)
            return False
        return True

    @property
    def is_autostart(self) -> bool:
        """Return True if VM autostart is enabled, else return False."""
        try:
            if self.domain.autostart() == 1:
                return True
            return False
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot get autostart status vm={self.domain_name}: {err}'
            ) from err

    def start(self) -> None:
        """Start defined VM."""
        logger.info('Starting VM: vm=%s', self.domain_name)
        if self.is_running:
            logger.warning('VM vm=%s is already started, nothing to do',
                           self.domain_name)
            return
        try:
            self.domain.create()
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot start vm={self.domain_name}: {err}') from err

    def shutdown(self, method: str | None = None) -> None:
        """
        Send signal to guest OS to shutdown. Supports several modes:
        * GUEST_AGENT - use guest agent
        * NORMAL - use method choosen by hypervisor to shutdown machine
        * SIGTERM - send SIGTERM to QEMU process, destroy machine gracefully
        * SIGKILL - send SIGKILL to QEMU process. May corrupt guest data!
        If mode is not passed use 'NORMAL' mode.
        """
        METHODS = {
            'GUEST_AGENT': libvirt.VIR_DOMAIN_SHUTDOWN_GUEST_AGENT,
            'NORMAL': libvirt.VIR_DOMAIN_SHUTDOWN_DEFAULT,
            'SIGTERM': libvirt.VIR_DOMAIN_DESTROY_GRACEFUL,
            'SIGKILL': libvirt.VIR_DOMAIN_DESTROY_DEFAULT
        }
        if method is None:
            method = 'NORMAL'
        if not isinstance(method, str):
            raise ValueError(f"Mode must be a 'str', not {type(method)}")
        if method.upper() not in METHODS:
            raise ValueError(f"Unsupported mode: '{method}'")
        try:
            if method in ['GUEST_AGENT', 'NORMAL']:
                self.domain.shutdownFlags(flags=METHODS.get(method))
            elif method in ['SIGTERM', 'SIGKILL']:
                self.domain.destroyFlags(flags=METHODS.get(method))
        except libvirt.libvirtError as err:
            raise VMError(f'Cannot shutdown vm={self.domain_name} with '
                          f'method={method}: {err}') from err

    def reset(self) -> None:
        """
        Copypaste from libvirt doc:

        Reset a domain immediately without any guest OS shutdown.
        Reset emulates the power reset button on a machine, where all
        hardware sees the RST line set and reinitializes internal state.

        Note that there is a risk of data loss caused by reset without any
        guest OS shutdown.
        """
        try:
            self.domain.reset()
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot reset vm={self.domain_name}: {err}') from err

    def reboot(self) -> None:
        """Send ACPI signal to guest OS to reboot. OS may ignore this."""
        try:
            self.domain.reboot()
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot reboot vm={self.domain_name}: {err}') from err

    def set_autostart(self, enable: bool) -> None:
        """
        Configure VM to be automatically started when the host machine boots.
        """
        if enable:
            autostart_flag = 1
        else:
            autostart_flag = 0
        try:
            self.domain.setAutostart(autostart_flag)
        except libvirt.libvirtError as err:
            raise VMError(f'Cannot set autostart vm={self.domain_name} '
                          f'autostart={autostart_flag}: {err}') from err

    def set_vcpus(self, nvcpus: int, hotplug: bool = False):
        """
        Set vCPUs for VM. If `hotplug` is True set vCPUs on running VM.
        If VM is not running set `hotplug` to False. If `hotplug` is True
        and VM is not currently running vCPUs will set in config and will
        applied when machine boot.

        NB: Note that if this call is executed before the guest has
        finished booting, the guest may fail to process the change.
        """
        if nvcpus == 0:
            raise VMError(f'Cannot set zero vCPUs vm={self.domain_name}')
        if hotplug and self.domain_info['state'] == libvirt.VIR_DOMAIN_RUNNING:
            flags = (libvirt.VIR_DOMAIN_AFFECT_LIVE +
                     libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        try:
            self.domain.setVcpusFlags(nvcpus, flags=flags)
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot set vCPUs for vm={self.domain_name}: {err}') from err

    def set_memory(self, memory: int, hotplug: bool = False):
        """
        Set momory for VM. `memory` must be passed in mebibytes. Internally
        converted to kibibytes. If `hotplug` is True set memory for running
        VM, else set memory in config and will applied when machine boot.
        If `hotplug` is True and machine is not currently running set memory
        in config.
        """
        if memory == 0:
            raise VMError(f'Cannot set zero memory vm={self.domain_name}')
        if hotplug and self.domain_info['state'] == libvirt.VIR_DOMAIN_RUNNING:
            flags = (libvirt.VIR_DOMAIN_AFFECT_LIVE +
                     libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        try:
            self.domain.setVcpusFlags(memory * 1024, flags=flags)
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot set memory for vm={self.domain_name}: {err}') from err

    def attach_device(self, dev_xml: str, hotplug: bool = False):
        if hotplug and self.domain_info['state'] == libvirt.VIR_DOMAIN_RUNNING:
            flags = (libvirt.VIR_DOMAIN_AFFECT_LIVE +
                     libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        self.domain.attachDeviceFlags(dev_xml, flags=flags)

    def detach_device(self, dev_xml: str, hotplug: bool = False):
        if hotplug and self.domain_info['state'] == libvirt.VIR_DOMAIN_RUNNING:
            flags = (libvirt.VIR_DOMAIN_AFFECT_LIVE +
                     libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        else:
            flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
        self.domain.detachDeviceFlags(dev_xml, flags=flags)

    def resize_volume(self, vol_info: VolumeInfo, online: bool = False):
        # Этот метод должен принимать описание волюма и в зависимости от
        # флага online вызывать virStorageVolResize или virDomainBlockResize
        # https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainBlockResize
        pass

    def list_ssh_keys(self, user: str):
        pass

    def set_ssh_keys(self, user: str):
        pass

    def remove_ssh_keys(self, user: str):
        pass

    def set_user_password(self, user: str, password: str):
        self.domain.setUserPassword(user, password)

    def dump_xml(self) -> str:
        return self.domain.XMLDesc()

    def delete(self, delete_volumes: bool = False):
        """Undefine VM."""
        self.shutdown(method='SIGTERM')
        self.domain.undefine()
