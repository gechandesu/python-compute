"""Exceptions."""


class ComputeServiceError(Exception):
    """Basic exception class for Compute."""


class ConfigLoaderError(ComputeServiceError):
    """Something went wrong when loading configuration."""


class SessionError(ComputeServiceError):
    """Something went wrong while connecting to libvirtd."""


class GuestAgentError(ComputeServiceError):
    """Something went wring when QEMU Guest Agent call."""


class GuestAgentUnavailableError(GuestAgentError):
    """Guest agent is not connected or is unavailable."""


class GuestAgentTimeoutExceededError(GuestAgentError):
    """QEMU timeout exceeded."""

    def __init__(self, msg: int):
        """Initialise GuestAgentTimeoutExceededError."""
        super().__init__(f'QEMU timeout ({msg} sec) exceeded')


class GuestAgentCommandNotSupportedError(GuestAgentError):
    """Guest agent command is not supported or blacklisted on guest."""


class StoragePoolError(ComputeServiceError):
    """Something went wrong when operating with storage pool."""


class StoragePoolNotFoundError(StoragePoolError):
    """Storage pool not found."""

    def __init__(self, msg: str):
        """Initialise StoragePoolNotFoundError."""
        super().__init__(f"storage pool named '{msg}' not found")


class VolumeNotFoundError(StoragePoolError):
    """Storage volume not found."""

    def __init__(self, msg: str):
        """Initialise VolumeNotFoundError."""
        super().__init__(f"storage volume '{msg}' not found")


class InstanceError(ComputeServiceError):
    """Something went wrong while interacting with the domain."""


class InstanceNotFoundError(InstanceError):
    """Virtual machine or container not found on compute node."""

    def __init__(self, msg: str):
        """Initialise InstanceNotFoundError."""
        super().__init__(f"compute instance '{msg}' not found")
