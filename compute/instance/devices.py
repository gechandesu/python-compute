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

# ruff: noqa: SIM211, UP007, A003

"""Virtual devices configs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from lxml import etree
from lxml.builder import E

from compute.abstract import DeviceConfig
from compute.exceptions import InvalidDeviceConfigError


@dataclass
class DiskDriver:
    """Disk driver description for libvirt."""

    name: str = 'qemu'
    type: str = 'qcow2'
    cache: str = 'default'

    def __call__(self):
        """Return self."""
        return self


@dataclass
class DiskConfig(DeviceConfig):
    """
    Disk config builder.

    Generate XML config for attaching or detaching storage volumes
    to compute instances.
    """

    type: str
    source: str | Path
    target: str
    is_readonly: bool = False
    device: str = 'disk'
    bus: str = 'virtio'
    driver: DiskDriver = field(default_factory=DiskDriver())

    def to_xml(self) -> str:
        """Return XML config for libvirt."""
        xml = E.disk(type=self.type, device=self.device)
        xml.append(
            E.driver(
                name=self.driver.name,
                type=self.driver.type,
                cache=self.driver.cache,
            )
        )
        if self.source and self.type == 'file':
            xml.append(E.source(file=str(self.source)))
        xml.append(E.target(dev=self.target, bus=self.bus))
        if self.is_readonly:
            xml.append(E.readonly())
        return etree.tostring(xml, encoding='unicode', pretty_print=True)

    @classmethod
    def from_xml(cls, xml: Union[str, etree.Element]) -> 'DiskConfig':
        """
        Create :class:`DiskConfig` instance from XML config.

        :param xml: Disk device XML configuration as :class:`str` or lxml
            :class:`etree.Element` object.
        """
        if isinstance(xml, str):
            xml_str = xml
            xml = etree.fromstring(xml)
        else:
            xml_str = etree.tostring(
                xml,
                encoding='unicode',
                pretty_print=True,
            ).strip()
        driver = xml.find('driver')
        cachetype = driver.get('cache')
        disk_params = {
            'type': xml.get('type'),
            'device': xml.get('device'),
            'driver': DiskDriver(
                name=driver.get('name'),
                type=driver.get('type'),
                **({'cache': cachetype} if cachetype else {}),
            ),
            'source': xml.find('source').get('file'),
            'target': xml.find('target').get('dev'),
            'bus': xml.find('target').get('bus'),
            'is_readonly': False if xml.find('readonly') is None else True,
        }
        for param in disk_params:
            if disk_params[param] is None:
                msg = f"missing XML tag '{param}'"
                raise InvalidDeviceConfigError(msg, xml_str)
            if param == 'driver':
                driver = disk_params[param]
                for driver_param in [driver.name, driver.type, driver.cache]:
                    if driver_param is None:
                        msg = (
                            "'driver' tag must have "
                            "'name' and 'type' attributes"
                        )
                        raise InvalidDeviceConfigError(msg, xml_str)
        return cls(**disk_params)
