from contextlib import AbstractContextManager

import libvirt

from .exceptions import LibvirtSessionError, VMNotFound
from .vm import GuestAgent, VirtualMachine
from .volume import StoragePool


class LibvirtSession(AbstractContextManager):

    def __init__(self, uri: str = 'qemu:///system'):
        try:
            self.connection = libvirt.open(uri)
        except libvirt.libvirtError as err:
            raise LibvirtSessionError(err) from err

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()

    def get_machine(self, name: str) -> VirtualMachine:
        try:
            return VirtualMachine(self.connection.lookupByName(name))
        except libvirt.libvirtError as err:
            if err.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise VMNotFound(name) from err
            raise LibvirtSessionError(err) from err

    def list_machines(self) -> list[VirtualMachine]:
        return [VirtualMachine(dom) for dom in
                self.connection.listAllDomains()]

    def get_guest_agent(self, name: str,
                        timeout: int | None = None) -> GuestAgent:
        try:
            return GuestAgent(self.connection.lookupByName(name), timeout)
        except libvirt.libvirtError as err:
            if err.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise VMNotFound(name) from err
            raise LibvirtSessionError(err) from err

    def get_storage_pool(self, name: str) -> StoragePool:
        return StoragePool(self.connection.storagePoolLookupByName(name))

    def list_storage_pools(self) -> list[StoragePool]:
        return [StoragePool(p) for p in self.connection.listStoragePools()]

    def close(self) -> None:
        self.connection.close()
