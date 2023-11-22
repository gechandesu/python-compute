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

"""Tools for data units convertion."""

from enum import StrEnum


class DataUnit(StrEnum):
    """Data units enumerated."""

    BYTES = 'bytes'
    KIB = 'KiB'
    MIB = 'MiB'
    GIB = 'GiB'
    TIB = 'TiB'


class InvalidDataUnitError(ValueError):
    """Data unit is not valid."""

    def __init__(self, msg: str):
        """Initialise InvalidDataUnitError."""
        super().__init__(
            f'{msg}, valid units are: {", ".join(list(DataUnit))}'
        )


def to_bytes(value: int, unit: DataUnit = DataUnit.BYTES) -> int:
    """Convert value to bytes. See :class:`DataUnit`."""
    try:
        _ = DataUnit(unit)
    except ValueError as e:
        raise InvalidDataUnitError(e) from e
    powers = {
        DataUnit.BYTES: 0,
        DataUnit.KIB: 1,
        DataUnit.MIB: 2,
        DataUnit.GIB: 3,
        DataUnit.TIB: 4,
    }
    return value * pow(1024, powers[unit])
