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

"""Tools for data units convertion."""

from collections.abc import Callable
from enum import StrEnum

from compute.exceptions import InvalidDataUnitError


class DataUnit(StrEnum):
    """Data units enumeration."""

    BYTES = 'bytes'
    KIB = 'KiB'
    MIB = 'MiB'
    GIB = 'GiB'
    TIB = 'TiB'
    KB = 'kb'
    MB = 'Mb'
    GB = 'Gb'
    TB = 'Tb'
    KBIT = 'kbit'
    MBIT = 'Mbit'
    GBIT = 'Gbit'
    TBIT = 'Tbit'

    @classmethod
    def _missing_(cls, name: str) -> 'DataUnit':
        for member in cls:
            if member.name.lower() == name.lower():
                return member
        return None


def validate_input(*args: str) -> Callable:
    """Validate data units in functions input."""
    to_validate = args

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: float | str, **kwargs: str) -> Callable:
            try:
                if kwargs:
                    for arg in to_validate:
                        unit = kwargs[arg]
                        DataUnit(unit)
                else:
                    for arg in args[1:]:
                        unit = arg
                        DataUnit(unit)
            except ValueError as e:
                raise InvalidDataUnitError(e, list(DataUnit)) from e
            return func(*args, **kwargs)

        return wrapper

    return decorator


@validate_input('unit')
def to_bytes(value: float, unit: DataUnit = DataUnit.BYTES) -> float:
    """Convert value to bytes."""
    unit = DataUnit(unit)
    basis = 2 if unit.endswith('iB') else 10
    factor = 125 if unit.endswith('bit') else 1
    power = {
        DataUnit.BYTES: 0,
        DataUnit.KIB: 10,
        DataUnit.MIB: 20,
        DataUnit.GIB: 30,
        DataUnit.TIB: 40,
        DataUnit.KB: 3,
        DataUnit.MB: 6,
        DataUnit.GB: 9,
        DataUnit.TB: 12,
        DataUnit.KBIT: 0,
        DataUnit.MBIT: 3,
        DataUnit.GBIT: 6,
        DataUnit.TBIT: 9,
    }
    return value * factor * pow(basis, power[unit])


@validate_input('from_unit', 'to_unit')
def convert(value: float, from_unit: DataUnit, to_unit: DataUnit) -> float:
    """Convert units."""
    value_in_bits = to_bytes(value, from_unit) * 8
    to_unit = DataUnit(to_unit)
    basis = 2 if to_unit.endswith('iB') else 10
    divisor = 1 if to_unit.endswith('bit') else 8
    power = {
        DataUnit.BYTES: 0,
        DataUnit.KIB: 10,
        DataUnit.MIB: 20,
        DataUnit.GIB: 30,
        DataUnit.TIB: 40,
        DataUnit.KB: 3,
        DataUnit.MB: 6,
        DataUnit.GB: 9,
        DataUnit.TB: 12,
        DataUnit.KBIT: 3,
        DataUnit.MBIT: 6,
        DataUnit.GBIT: 9,
        DataUnit.TBIT: 12,
    }
    return value_in_bits / divisor / pow(basis, power[to_unit])
