import libvirt

from .base import NodeAgentBase
from .exceptions import (
    VMNotFound,
    VMStartError,
    VMRebootError,
    VMShutdownError,
)


class VirtualMachine(NodeAgentBase):

    def _dom(self, domain: str) -> libvirt.virDomain:
        """Get virDomain object to manipulate with domain."""
        try:
            ret = self.conn.lookupByName(domain)
            if ret is not None:
                return ret
            raise VMNotFound(domain)
        except libvirt.libvirtError as err:
            raise VMNotFound(err) from err

    def create(
        self,
        name: str,
        volumes: list[dict],
        vcpus: int,
        vram: int,
        image: dict,
        cdrom: dict | None = None,
    ):
        # TODO
        pass

    def delete(self, name: str, delete_volumes=False):
        pass

    def status(self, name: str) -> str:
        """
        Return VM state: 'running', 'shutoff', etc. Ref:
        https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainState
        """
        state = self._dom(name).info()[0]
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

    def is_running(self, name: str) -> bool:
        """Return True if VM is running, else return False."""
        if self._dom(name).isActive() != 1:
            return False  # inactive (0) or error (-1)
        return True

    def start(self, name: str) -> None:
        """Start VM."""
        if not self.is_running(name):
            ret = self._dom(name).create()
        else:
            return
        if ret != 0:
            raise VMStartError(name)

    def shutdown(self, name: str, hard=False) -> None:
        """Shutdown VM. Use hard=True to force shutdown."""
        if hard:
            # Destroy VM gracefully (no SIGKILL)
            ret = self._dom(name).destroyFlags(flags=libvirt.VIR_DOMAIN_DESTROY_GRACEFUL)
        else:
            # Normal VM shutdown, OS may ignore this.
            ret = self._dom(name).shutdown()
        if ret != 0:
            raise VMShutdownError(name)

    def reboot(self, name: str, hard=False) -> None:
        """
        Reboot VM. Use hard=True to force reboot. With forced reboot
        VM will shutdown via self.shutdown() (no forced) and started.
        """
        if hard:
            # Forced "reboot"
            self.shutdown(name)
            self.start(name)
        else:
            # Normal reboot.
            ret = self._dom(name).reboot()
        if ret != 0:
            raise VMRebootError(name)

    def vcpu_set(self, name: str, count: int):
        pass

    def vram_set(self, name: str, count: int):
        pass

    def ssh_keys_list(self, name: str, user: str):
        pass

    def ssh_keys_add(self, name: str, user: str):
        pass

    def ssh_keys_remove(self, name: str, user: str):
        pass

    def set_user_password(self, name: str, user: str):
        pass
