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

"""Common symbols."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Extra


class EntityModel(BaseModel):
    """Basic entity model."""

    class Config:
        """Do not allow extra fields."""

        extra = Extra.forbid


class EntityConfig(ABC):
    """An abstract entity XML config builder class."""

    @abstractmethod
    def to_xml(self) -> str:
        """Return entity XML config."""
        raise NotImplementedError


class DeviceConfig(EntityConfig):
    """An abstract device XML config."""
