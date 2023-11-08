from collections import UserDict
from typing import Any

class _NotPresent:
    """
    Type for representing non-existent dictionary keys.

    See :class:`_FillableDict`
    """

class _FillableDict(UserDict):
    """Use :method:`fill` to add key if not present."""

    def __init__(self, data: dict):
        self.data = data

    def fill(self, key: str, value: Any) -> None:
        if self.data.get(key, _NotPresent) is _NotPresent:
            self.data[key] = value

d = _FillableDict({'a': None, 'b': 'BBBB'})
d.fill('c', 'CCCCCCCCC')
d.fill('a', 'CCCCCCCCC')
d['a'].fill('gg', 'AAAAAAAA')
print(d)
