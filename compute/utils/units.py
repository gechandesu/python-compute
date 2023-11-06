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
