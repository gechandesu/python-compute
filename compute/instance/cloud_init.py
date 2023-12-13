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

# ruff: noqa: S603

"""
`Cloud-init`_ integration for bootstraping compute instances.

.. _Cloud-init: https://cloudinit.readthedocs.io
"""

import logging
import subprocess
import tempfile
from pathlib import Path

from compute.exceptions import InstanceError

from .devices import DiskConfig, DiskDriver
from .instance import Instance


log = logging.getLogger(__name__)


class CloudInit:
    """
    Cloud-init integration.

    :ivar str user_data: user-data.
    :ivar str vendor_data: vendor-data.
    :ivar str network_config: network-config.
    :ivar str meta_data: meta-data.
    """

    def __init__(self):
        """Initialise :class:`CloudInit`."""
        self.user_data = None
        self.vendor_data = None
        self.network_config = None
        self.meta_data = None

    def __repr__(self) -> str:
        """Represent :class:`CloudInit` object."""
        return (
            self.__class__.__name__
            + '('
            + ', '.join(
                [
                    f'{self.user_data=}',
                    f'{self.vendor_data=}',
                    f'{self.network_config=}',
                    f'{self.meta_data=}',
                ]
            )
            + ')'
        ).replace('self.', '')

    def _write_to_disk(
        self,
        disk: str,
        filename: str,
        data: str | None,
        *,
        force_file_create: bool = False,
        delete_existing_file: bool = False,
        default_data: str | None = None,
    ) -> None:
        data = data or default_data
        log.debug('Input data %s: %r', filename, data)
        if isinstance(data, str):
            data = data.encode()
        if data is None and force_file_create is False:
            return
        with tempfile.NamedTemporaryFile() as data_file:
            if data is not None:
                data_file.write(data)
            data_file.flush()
            if delete_existing_file:
                log.debug('Deleting existing file')
                filelist = subprocess.run(
                    ['/usr/bin/mdir', '-i', disk, '-b'],
                    capture_output=True,
                    check=True,
                )
                files = [
                    f.replace('::/', '')
                    for f in filelist.stdout.decode().splitlines()
                ]
                log.debug('Files on disk: %s', files)
                log.debug("Removing '%s'", filename)
                if filename in files:
                    subprocess.run(
                        ['/usr/bin/mdel', '-i', disk, f'::{filename}'],
                        check=True,
                    )
            log.debug("Writing file '%s'", filename)
            subprocess.run(
                [
                    '/usr/bin/mcopy',
                    '-i',
                    disk,
                    data_file.name,
                    f'::{filename}',
                ],
                check=True,
            )

    def create_disk(self, disk: Path, *, force: bool = False) -> None:
        """
        Create disk with cloud-init config files.

        :param path: Disk path.
        :param force: Replace existing disk.
        """
        if not isinstance(disk, Path):
            disk = Path(disk)
        if disk.exists():
            if disk.is_file() is False:
                raise InstanceError('Cloud-init disk must be regular file')
            if force:
                disk.unlink()
            else:
                raise InstanceError('File already exists')
        subprocess.run(
            ['/usr/sbin/mkfs.vfat', '-n', 'CIDATA', '-C', str(disk), '1024'],
            check=True,
            stderr=subprocess.DEVNULL,
        )
        self._write_to_disk(
            disk=disk,
            filename='user-data',
            data=self.user_data,
            force_file_create=True,
            default_data='#cloud-config',
        )
        self._write_to_disk(
            disk=disk,
            filename='vendor-data',
            data=self.vendor_data,
        )
        self._write_to_disk(
            disk=disk,
            filename='network-config',
            data=self.network_config,
        )
        self._write_to_disk(
            disk=disk,
            filename='meta-data',
            data=self.meta_data,
            force_file_create=True,
        )

    def update_disk(self, disk: Path) -> None:
        """Update files on existing disk."""
        if not isinstance(disk, Path):
            disk = Path(disk)
        if not disk.exists():
            raise InstanceError(f"File '{disk}' does not exists")
        if self.user_data:
            self._write_to_disk(
                disk=disk,
                filename='user-data',
                data=self.user_data,
                force_file_create=True,
                default_data='#cloud-config',
                delete_existing_file=True,
            )
        if self.vendor_data:
            self._write_to_disk(
                disk=disk,
                filename='vendor-data',
                data=self.vendor_data,
                delete_existing_file=True,
            )
        if self.network_config:
            self._write_to_disk(
                disk=disk,
                filename='network-config',
                data=self.network_config,
                delete_existing_file=True,
            )
        if self.meta_data:
            self._write_to_disk(
                disk=disk,
                filename='meta-data',
                data=self.meta_data,
                force_file_create=True,
                delete_existing_file=True,
            )

    def attach_disk(self, disk: Path, target: str, instance: Instance) -> None:
        """
        Attach cloud-init disk to instance.

        :param disk: Path to disk.
        :param target: Disk target name e.g. `vda`.
        :param instance: Compute instance object.
        """
        instance.attach_device(
            DiskConfig(
                type='file',
                device='disk',
                source=disk,
                target=target,
                is_readonly=True,
                bus='virtio',
                driver=DiskDriver('qemu', 'raw'),
            )
        )
