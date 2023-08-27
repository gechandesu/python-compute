from contextlib import AbstractContextManager
from pathlib import Path

import libvirt

from .config import ConfigLoader


class LibvirtSessionError(Exception):
    """Something went wrong while connecting to libvirtd."""


class LibvirtSession(AbstractContextManager):

    def __init__(self, config: Path | None = None):
        self.config = ConfigLoader(config)
        self.session = self._connect(self.config['libvirt']['uri'])

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()

    def _connect(self, connection_uri: str):
        try:
            return libvirt.open(connection_uri)
        except libvirt.libvirtError as err:
            raise LibvirtSessionError(
                f'Failed to open connection to the hypervisor: {err}') from err

    def close(self) -> None:
        self.session.close()

    def list_domains(self):
        return self.session.listAllDomains()

    def get_domain(self, name: str) -> libvirt.virDomain:
        try:
            return self.session.lookupByName(name)
        except libvirt.libvirtError as err:
            if err.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise VMNotFound(name)
            else:
                raise LibvirtSessionError(err)

    def get_storage_pool(self, name: str) -> libvirt.virStoragePool:
        try:
            return self.session.storagePoolLookupByName(name)
        except libvirt.libvirtError as err:
            raise LibvirtSessionError(err)