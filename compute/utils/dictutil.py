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

"""Dict tools."""

from compute.exceptions import DictMergeConflictError


def merge(a: dict, b: dict, path: list[str] | None = None) -> dict:
    """
    Merge `b` into `a`. Return modified `a`.

    :raise: :class:`DictMergeConflictError`
    """
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], [*path, str(key)])
            elif a[key] != b[key]:
                raise DictMergeConflictError('.'.join([*path, str(key)]))
        else:
            a[key] = b[key]
    return a


def override(a: dict, b: dict) -> dict:
    """
    Override dict `a` by `b` values.

    Keys that not exists in `a`, but exists in `b` will be
    appended to `a`.

    .. code-block:: shell-session

       >>> from compute.utils import dictutil
       >>> default = {
       ...     'bus': 'virtio',
       ...     'driver': {'name': 'qemu', 'type': 'qcow2'}
       ... }
       >>> user = {
       ...     'bus': 'ide',
       ...     'target': 'vda',
       ...     'driver': {'type': 'raw'}
       ... }
       >>> dictutil.override(default, user)
       {'bus': 'ide', 'driver': {'name': 'qemu', 'type': 'raw'},
       'target': 'vda'}

    NOTE: merging dicts contained in lists is not supported.

    :param a: Dict to be overwritten.
    :param b: A dict whose values will be used to rewrite dict `a`.
    :return: Modified `a` dict.
    """
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                override(a[key], b[key])
            else:
                a[key] = b[key]  # replace existing key's values
        else:
            a[key] = b[key]
    return a
