from contextlib import AbstractContextManager

import libvirt

from .vm import GuestAgent, VirtualMachine, VMNotFound
from .volume import StoragePool


class LibvirtSessionError(Exception):
    """Something went wrong while connecting to libvirtd."""


class LibvirtSession(AbstractContextManager):

    def __init__(self, uri: str = 'qemu:///system'):
        self.connection = self._connect(uri)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()

    def _connect(self, connection_uri: str) -> libvirt.virConnect:
        try:
            return libvirt.open(connection_uri)
        except libvirt.libvirtError as err:
            raise LibvirtSessionError(
                f'Failed to open connection to the hypervisor: {err}') from err

    def _get_domain(self, name: str) -> libvirt.virDomain:
        try:
            return self.connection.lookupByName(name)
        except libvirt.libvirtError as err:
            if err.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise VMNotFound(name) from err
            raise LibvirtSessionError(err) from err

    def _list_all_domains(self) -> list[libvirt.virDomain]:
        try:
            return self.connection.listAllDomains()
        except libvirt.libvirtError as err:
            raise LibvirtSessionError(err) from err

    def _get_storage_pool(self, name: str) -> libvirt.virStoragePool:
        try:
            return self.connection.storagePoolLookupByName(name)
        except libvirt.libvirtError as err:
            raise LibvirtSessionError(err) from err

    def get_machine(self, name: str) -> VirtualMachine:
        return VirtualMachine(self._get_domain(name))

    def list_machines(self) -> list[VirtualMachine]:
        return [VirtualMachine(dom) for dom in self._list_all_domains()]

    def get_guest_agent(self, name: str, timeout: int | None = None,
                        flags: int | None = None) -> GuestAgent:
        return GuestAgent(self._get_domain(name), timeout, flags)

    def get_storage_pool(self, name: str) -> StoragePool:
        return StoragePool(self._get_storage_pool(name))

    def list_storage_pools(self):
        return [StoragePool(p) for p in self.connection.listStoragePools()]

    def close(self) -> None:
        self.connection.close()
