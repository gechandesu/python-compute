import logging

import libvirt

from ..exceptions import VMError
from .base import VirtualMachineBase


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
            raise VMError(f'Cannot fetch VM status vm={self.domname}: {err}') from err
        match state:
            case libvirt.VIR_DOMAIN_NOSTATE:
                return 'nostate'
            case libvirt.VIR_DOMAIN_RUNNING:
                return 'running'
            case libvirt.VIR_DOMAIN_BLOCKED:
                return 'blocked'
            case libvirt.VIR_DOMAIN_PAUSED:
                return 'paused'
            case libvirt.VIR_DOMAIN_SHUTDOWN:
                return 'shutdown'
            case libvirt.VIR_DOMAIN_SHUTOFF:
                return 'shutoff'
            case libvirt.VIR_DOMAIN_CRASHED:
                return 'crashed'
            case libvirt.VIR_DOMAIN_PMSUSPENDED:
                return 'pmsuspended'

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
            raise VMError(f'Cannot get autostart status vm={self.domname}: {err}') from err

    def start(self) -> None:
        """Start defined VM."""
        logger.info('Starting VM: vm=%s', self.domname)
        if self.is_running:
            logger.debug('VM vm=%s is already started, nothing to do', self.domname)
            return
        try:
            ret = self.domain.create()
        except libvirt.libvirtError as err:
            raise VMError(f'Cannot start vm={self.domname}: {err}') from err

    def shutdown(self, force=False, sigkill=False) -> None:
        """
        Send ACPI signal to guest OS to shutdown. OS may ignore this.
        Use `force=True` for graceful VM destroy. Add `sigkill=True`
        to hard shutdown (may corrupt guest data!).
        """
        if sigkill:
            flags = libvirt.VIR_DOMAIN_DESTROY_DEFAULT
        else:
            flags = libvirt.VIR_DOMAIN_DESTROY_GRACEFUL
        try:
            if force:
                self.domain.destroyFlags(flags=flags)
            else:
                # Normal VM shutdown via ACPI signal, OS may ignore this.
                self.domain.shutdown()
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot shutdown vm={self.domname} '
                f'force={force} sigkill={sigkill}: {err}'
            ) from err

    def reset(self):
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

    def autostart(self, enabled: bool) -> None:
        """
        Configure VM to be automatically started when the host machine boots.
        """
        if enabled:
            autostart_flag = 1
        else:
            autostart_flag = 0
        try:
            self.domain.setAutostart(autostart_flag)
        except libvirt.libvirtError as err:
            raise VMError(
                f'Cannot set autostart vm={self.domname} '
                f'autostart={autostart_flag}: {err}'
            ) from err

    def vcpu_set(self, count: int):
        pass

    def vram_set(self, count: int):
        pass

    def ssh_keys_list(self, user: str):
        pass

    def ssh_keys_add(self, user: str):
        pass

    def ssh_keys_remove(self, user: str):
        pass

    def set_user_password(self, user: str):
        pass
