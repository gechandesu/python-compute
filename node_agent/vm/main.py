import logging

import libvirt

from .base import VirtualMachineBase
from .exceptions import VMError


logger = logging.getLogger(__name__)


class VirtualMachine(VirtualMachineBase):

    @property
    def name(self):
        return self.domname

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
                f'Cannot fetch VM status vm={self.domname}: {err}') from err
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
                f'Cannot get autostart status vm={self.domname}: {err}'
            ) from err

    def start(self) -> None:
        """Start defined VM."""
        logger.info('Starting VM: vm=%s', self.domname)
        if self.is_running:
            logger.debug('VM vm=%s is already started, nothing to do',
                         self.domname)
            return
        try:
            self.domain.create()
        except libvirt.libvirtError as err:
            raise VMError(f'Cannot start vm={self.domname}: {err}') from err

    def shutdown(self, mode: str | None = None) -> None:
        """
        Send signal to guest OS to shutdown. Supports several modes:
        * GUEST_AGENT - use guest agent
        * NORMAL - use method choosen by hypervisor to shutdown machine
        * SIGTERM - send SIGTERM to QEMU process, destroy machine gracefully
        * SIGKILL - send SIGKILL, this option may corrupt guest data!
        If mode is not passed use 'NORMAL' mode.
        """
        MODES = {
            'GUEST_AGENT': libvirt.VIR_DOMAIN_SHUTDOWN_GUEST_AGENT,
            'NORMAL': libvirt.VIR_DOMAIN_SHUTDOWN_DEFAULT,
            'SIGTERM': libvirt.VIR_DOMAIN_DESTROY_GRACEFUL,
            'SIGKILL': libvirt.VIR_DOMAIN_DESTROY_DEFAULT
        }
        if mode is None:
            mode = 'NORMAL'
        if not isinstance(mode, str):
            raise ValueError(f'Mode must be a string, not {type(mode)}')
        if mode.upper() not in MODES:
            raise ValueError(f"Unsupported mode: '{mode}'")
        try:
            if mode in ['GUEST_AGENT', 'NORMAL']:
                self.domain.shutdownFlags(flags=MODES.get(mode))
            elif mode in ['SIGTERM', 'SIGKILL']:
                self.domain.destroyFlags(flags=MODES.get(mode))
        except libvirt.libvirtError as err:
            raise VMError(f'Cannot shutdown vm={self.domname} with '
                          f'mode={mode}: {err}') from err

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
            raise VMError(f'Cannot reset vm={self.domname}: {err}') from err

    def reboot(self) -> None:
        """Send ACPI signal to guest OS to reboot. OS may ignore this."""
        try:
            self.domain.reboot()
        except libvirt.libvirtError as err:
            raise VMError(f'Cannot reboot vm={self.domname}: {err}') from err

    def autostart(self, enable: bool) -> None:
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
            raise VMError(f'Cannot set autostart vm={self.domname} '
                          f'autostart={autostart_flag}: {err}') from err

    def set_vcpus(self, count: int):
        pass

    def set_ram(self, count: int):
        pass

    def list_ssh_keys(self, user: str):
        pass

    def set_ssh_keys(self, user: str):
        pass

    def remove_ssh_keys(self, user: str):
        pass

    def set_user_password(self, user: str):
        pass
