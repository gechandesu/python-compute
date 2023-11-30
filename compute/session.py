# This file is part of Compute
#
# Compute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

"""Hypervisor session manager."""

import logging
import os
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, NamedTuple
from uuid import uuid4

import libvirt
from lxml import etree

from .exceptions import (
    InstanceNotFoundError,
    SessionError,
    StoragePoolNotFoundError,
)
from .instance import Instance, InstanceConfig, InstanceSchema
from .storage import DiskConfig, StoragePool, VolumeConfig
from .utils import units


log = logging.getLogger(__name__)


class Capabilities(NamedTuple):
    """Store domain capabilities info."""

    arch: str
    virt_type: str
    emulator: str
    machine: str
    max_vcpus: int
    cpu_vendor: str
    cpu_model: str
    cpu_features: dict
    usable_cpus: list[dict]


class NodeInfo(NamedTuple):
    """
    Store compute node info.

    See https://libvirt.org/html/libvirt-libvirt-host.html#virNodeInfo
    NOTE: memory unit in libvirt docs is wrong! Actual unit is MiB.
    """

    arch: str
    memory: int
    cpus: int
    mhz: int
    nodes: int
    sockets: int
    cores: int
    threads: int


class Session(AbstractContextManager):
    """
    Hypervisor session context manager.

    :cvar IMAGES_POOL: images storage pool name taken from env
    :cvar VOLUMES_POOL: volumes storage pool name taken from env
    """

    IMAGES_POOL = os.getenv('CMP_IMAGES_POOL')
    VOLUMES_POOL = os.getenv('CMP_VOLUMES_POOL')

    def __init__(self, uri: str | None = None):
        """
        Initialise session with hypervisor.

        :ivar str uri: libvirt connection URI.
        :ivar libvirt.virConnect connection: libvirt connection object.

        :param uri: libvirt connection URI.
        """
        self.uri = uri or 'qemu:///system'
        self.connection = libvirt.open(self.uri)

    def __enter__(self):
        """Return Session object."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ):
        """Close the connection when leaving the context."""
        self.close()

    def close(self) -> None:
        """Close connection to libvirt daemon."""
        self.connection.close()

    def get_node_info(self) -> NodeInfo:
        """Return information about compute node."""
        info = self.connection.getInfo()
        return NodeInfo(
            arch=info[0],
            memory=info[1],
            cpus=info[2],
            mhz=info[3],
            nodes=info[4],
            sockets=info[5],
            cores=info[6],
            threads=info[7],
        )

    def _cap_get_usable_cpus(self, xml: etree.Element) -> list[dict]:
        x = xml.xpath('/domainCapabilities/cpu/mode[@name="custom"]')[0]
        cpus = []
        for cpu in x.findall('model'):
            if cpu.get('usable') == 'yes':
                cpus.append(  # noqa: PERF401
                    {
                        'vendor': cpu.get('vendor'),
                        'model': cpu.text,
                    }
                )
        return cpus

    def _cap_get_cpu_features(self, xml: etree.Element) -> dict:
        x = xml.xpath('/domainCapabilities/cpu/mode[@name="host-model"]')[0]
        require = []
        disable = []
        for feature in x.findall('feature'):
            policy = feature.get('policy')
            name = feature.get('name')
            if policy == 'require':
                require.append(name)
            if policy == 'disable':
                disable.append(name)
        return {'require': require, 'disable': disable}

    def get_capabilities(self) -> Capabilities:
        """Return capabilities e.g. arch, virt, emulator, etc."""
        prefix = '/domainCapabilities'
        hprefix = f'{prefix}/cpu/mode[@name="host-model"]'
        caps = etree.fromstring(self.connection.getDomainCapabilities())
        return Capabilities(
            arch=caps.xpath(f'{prefix}/arch/text()')[0],
            virt_type=caps.xpath(f'{prefix}/domain/text()')[0],
            emulator=caps.xpath(f'{prefix}/path/text()')[0],
            machine=caps.xpath(f'{prefix}/machine/text()')[0],
            max_vcpus=int(caps.xpath(f'{prefix}/vcpu/@max')[0]),
            cpu_vendor=caps.xpath(f'{hprefix}/vendor/text()')[0],
            cpu_model=caps.xpath(f'{hprefix}/model/text()')[0],
            cpu_features=self._cap_get_cpu_features(caps),
            usable_cpus=self._cap_get_cpus(caps),
        )

    def create_instance(self, **kwargs: Any) -> Instance:
        """
        Create and return new compute instance.

        :param name: Instance name.
        :type name: str
        :param title: Instance title for humans.
        :type title: str
        :param description: Some information about instance.
        :type description: str
        :param memory: Memory in MiB.
        :type memory: int
        :param max_memory: Maximum memory in MiB.
        :type max_memory: int
        :param vcpus: Number of vCPUs.
        :type vcpus: int
        :param max_vcpus: Maximum vCPUs.
        :type max_vcpus: int
        :param cpu: CPU configuration. See :class:`CPUSchema` for info.
        :type cpu: dict
        :param machine: QEMU emulated machine.
        :type machine: str
        :param emulator: Path to emulator.
        :type emulator: str
        :param arch: CPU architecture to virtualization.
        :type arch: str
        :param boot: Boot settings. See :class:`BootOptionsSchema`.
        :type boot: dict
        :param image: Source disk image name for system disk.
        :type image: str
        :param volumes: List of storage volume configs. For more info
            see :class:`VolumeSchema`.
        :type volumes: list[dict]
        :param network_interfaces: List of virtual network interfaces
            configs. See :class:`NetworkInterfaceSchema` for more info.
        :type network_interfaces: list[dict]
        """
        data = InstanceSchema(**kwargs)
        config = InstanceConfig(data)
        log.info('Define XML...')
        log.info(config.to_xml())
        self.connection.defineXML(config.to_xml())
        log.info('Getting instance...')
        instance = self.get_instance(config.name)
        log.info('Creating volumes...')
        for volume in data.volumes:
            log.info('Creating volume=%s', volume)
            capacity = units.to_bytes(
                volume.capacity.value, volume.capacity.unit
            )
            log.info('Connecting to images pool...')
            images_pool = self.get_storage_pool(self.IMAGES_POOL)
            log.info('Connecting to volumes pool...')
            volumes_pool = self.get_storage_pool(self.VOLUMES_POOL)
            log.info('Building volume configuration...')
            if not volume.source:
                vol_name = f'{uuid4()}.qcow2'
            else:
                vol_name = volume.source
            vol_conf = VolumeConfig(
                name=vol_name,
                path=str(volumes_pool.path.joinpath(vol_name)),
                capacity=capacity,
            )
            log.info('Volume configuration is:\n %s', vol_conf.to_xml())
            if volume.is_system is True and data.image:
                log.info(
                    "Volume is marked as 'system', start cloning image..."
                )
                log.info('Get image %s', data.image)
                image = images_pool.get_volume(data.image)
                log.info('Cloning image into volumes pool...')
                vol = volumes_pool.clone_volume(image, vol_conf)
                log.info(
                    'Resize cloned volume to specified size: %s',
                    capacity,
                )
                vol.resize(capacity, unit=units.DataUnit.BYTES)
            else:
                log.info('Create volume...')
                volumes_pool.create_volume(vol_conf)
            log.info('Attaching volume to instance...')
            instance.attach_device(
                DiskConfig(
                    disk_type=volume.type,
                    source=vol_conf.path,
                    target=volume.target,
                    readonly=volume.is_readonly,
                )
            )
        return instance

    def get_instance(self, name: str) -> Instance:
        """Get compute instance by name."""
        try:
            return Instance(self.connection.lookupByName(name))
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise InstanceNotFoundError(name) from e
            raise SessionError(e) from e

    def list_instances(self) -> list[Instance]:
        """List all instances."""
        return [Instance(dom) for dom in self.connection.listAllDomains()]

    def get_storage_pool(self, name: str) -> StoragePool:
        """Get storage pool by name."""
        try:
            return StoragePool(self.connection.storagePoolLookupByName(name))
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_POOL:
                raise StoragePoolNotFoundError(name) from e
            raise SessionError(e) from e

    def list_storage_pools(self) -> list[StoragePool]:
        """List all strage pools."""
        return [StoragePool(p) for p in self.connection.listStoragePools()]
