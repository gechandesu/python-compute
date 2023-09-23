class ConfigLoaderError(Exception):
    """Bad config file syntax, unreachable file or bad config schema."""


class LibvirtSessionError(Exception):
    """Something went wrong while connecting to libvirtd."""


class VMError(Exception):
    """Something went wrong while interacting with the domain."""


class VMNotFound(VMError):
    """Virtual machine not found on node."""


class GuestAgentError(Exception):
    """Mostly QEMU Guest Agent is not responding."""


class StoragePoolError(Exception):
    """Something went wrong when operating with storage pool."""
