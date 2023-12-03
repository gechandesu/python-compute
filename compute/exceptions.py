# This file is part of Compute
#
# Compute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Compute is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Compute.  If not, see <http://www.gnu.org/licenses/>.

"""Exceptions."""


class ComputeError(Exception):
    """Basic exception class."""


class ConfigLoaderError(ComputeError):
    """Something went wrong when loading configuration."""


class SessionError(ComputeError):
    """Something went wrong while connecting to libvirtd."""


class GuestAgentError(ComputeError):
    """Something went wring when QEMU Guest Agent call."""


class GuestAgentUnavailableError(GuestAgentError):
    """Guest agent is not connected or is unavailable."""


class GuestAgentTimeoutError(GuestAgentError):
    """QEMU timeout exceeded."""

    def __init__(self, seconds: int):
        """Initialise GuestAgentTimeoutExceededError."""
        super().__init__(f'QEMU timeout ({seconds} sec) exceeded')


class GuestAgentCommandNotSupportedError(GuestAgentError):
    """Guest agent command is not supported or blacklisted on guest."""


class StoragePoolError(ComputeError):
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


class InstanceError(ComputeError):
    """Something went wrong while interacting with the domain."""


class InstanceNotFoundError(InstanceError):
    """Virtual machine or container not found on compute node."""

    def __init__(self, msg: str):
        """Initialise InstanceNotFoundError."""
        super().__init__(f"compute instance '{msg}' not found")


class InvalidDeviceConfigError(ComputeError):
    """
    Invalid device XML description.

    :class:`DeviceCoonfig` instance cannot be created because
    device config in libvirt XML config is not valid.
    """

    def __init__(self, msg: str, xml: str):
        """Initialise InvalidDeviceConfigError."""
        self.msg = f'Invalid device XML config: {msg}'
        self.loc = f'    {xml}'
        super().__init__(f'{self.msg}\n:{self.loc}')


class InvalidDataUnitError(ValueError, ComputeError):
    """Data unit is not valid."""

    def __init__(self, msg: str, units: list):
        """Initialise InvalidDataUnitError."""
        super().__init__(f'{msg}, valid units are: {", ".join(units)}')


class DictMergeConflictError(ComputeError):
    """Conflict when merging dicts."""

    def __init__(self, key: str):
        """Initialise DictMergeConflictError."""
        super().__init__(f'Conflicting key: {key}')
