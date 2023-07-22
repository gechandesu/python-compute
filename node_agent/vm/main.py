import logging

import libvirt

from ..exceptions import VMError
from .base import VMBase


logger = logging.getLogger(__name__)


class VirtualMachine(VMBase):

    @property
    def name(self):
        return self.domain.name()

    @property
    def status(self) -> str:
        """
        Return VM state: 'running', 'shutoff', etc. Reference:
        https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainState
        """
        state = self.domain.info()[0]
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

    def start(self) -> None:
        """Start defined VM."""
        logger.info('Starting VM: vm=%s', self.domname)
        if self.is_running:
            logger.debug('VM vm=%s is already started, nothing to do', self.domname)
            return
        try:
            ret = self.domain.create()
        except libvirt.libvirtError as err:
            raise VMError(err) from err
        if ret != 0:
            raise VMError('Cannot start VM: vm=%s exit_code=%s', self.domname, ret)

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
        if force:
            ret = self.domain.destroyFlags(flags=flags)
        else:
            # Normal VM shutdown via ACPI signal, OS may ignore this.
            ret = self.domain.shutdown()
        if ret != 0:
            raise VMError(
                f'Cannot shutdown VM, try force or sigkill: %s', self.domname
            )

    def reset(self):
        """
        Copypaste from libvirt doc::

            Reset a domain immediately without any guest OS shutdown.
            Reset emulates the power reset button on a machine, where all
            hardware sees the RST line set and reinitializes internal state.

            Note that there is a risk of data loss caused by reset without any
            guest OS shutdown.
        """
        ret = self.domian.reset()
        if ret != 0:
            raise VMError('Cannot reset VM: %s', self.domname)

    def reboot(self) -> None:
        """Send ACPI signal to guest OS to reboot. OS may ignore this."""
        ret = self.domain.reboot()
        if ret != 0:
            raise VMError('Cannot reboot: %s', self.domname)

    def set_autostart(self) -> None:
        ret = self.domain.autostart()
        if ret != 0:
            raise VMError('Cannot set : %s', self.domname)

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
