"""Hypervisor session manager."""

import logging
import os
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, NamedTuple
from uuid import uuid4

import libvirt
from lxml import etree

from .exceptions import InstanceNotFoundError, SessionError
from .instance import Instance, InstanceConfig, InstanceSchema
from .storage import DiskConfig, StoragePool, VolumeConfig
from .utils import units


log = logging.getLogger(__name__)


class Capabilities(NamedTuple):
    """Store domain capabilities info."""

    arch: str
    virt: str
    emulator: str
    machine: str


class Session(AbstractContextManager):
    """Hypervisor session manager."""

    def __init__(self, uri: str | None = None):
        """
        Initialise session with hypervisor.

        :param uri: libvirt connection URI.
        """
        self.IMAGES_POOL = os.getenv('CMP_IMAGES_POOL')
        self.VOLUMES_POOL = os.getenv('CMP_VOLUMES_POOL')
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

    def capabilities(self) -> Capabilities:
        """Return capabilities e.g. arch, virt, emulator, etc."""
        prefix = '/domainCapabilities'
        caps = etree.fromstring(self.connection.getDomainCapabilities())  # noqa: S320
        return Capabilities(
            arch=caps.xpath(f'{prefix}/arch/text()')[0],
            virt=caps.xpath(f'{prefix}/domain/text()')[0],
            emulator=caps.xpath(f'{prefix}/path/text()')[0],
            machine=caps.xpath(f'{prefix}/machine/text()')[0],
        )

    def create_instance(self, **kwargs: Any) -> Instance:
        """
        Create and return new compute instance.

        :param name str: Instance name.
        :param title str: Instance title for humans.
        :param description str: Some information about instance
        :param memory int: Memory in MiB.
        :param max_memory int: Maximum memory in MiB.
        """
        # TODO @ge: create instances in transaction
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
            # if not volume.source:
            # В случае если пользователь передаёт source для волюма, следует
            # в либвирте делать поиск волюма по пути, а не по имени
            #    gen_vol_name
            # TODO @ge: come up with something else
            vol_name = f'{config.name}-{volume.target}-{uuid4()}.qcow2'
            vol_conf = VolumeConfig(
                name=vol_name,
                path=str(volumes_pool.path.joinpath(vol_name)),
                capacity=capacity,
            )
            log.info('Volume configuration is:\n %s', vol_conf.to_xml())
            if volume.is_system is True:
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
                DiskConfig(path=vol_conf.path, target=volume.target)
            )
        return instance

    def get_instance(self, name: str) -> Instance:
        """Get compute instance by name."""
        try:
            return Instance(self.connection.lookupByName(name))
        except libvirt.libvirtError as err:
            if err.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise InstanceNotFoundError(name) from err
            raise SessionError(err) from err

    def list_instances(self) -> list[Instance]:
        """List all instances."""
        return [Instance(dom) for dom in self.connection.listAllDomains()]

    def get_storage_pool(self, name: str) -> StoragePool:
        """Get storage pool by name."""
        # TODO @ge: handle Storage pool not found error
        return StoragePool(self.connection.storagePoolLookupByName(name))

    def list_storage_pools(self) -> list[StoragePool]:
        """List all strage pools."""
        return [StoragePool(p) for p in self.connection.listStoragePools()]
