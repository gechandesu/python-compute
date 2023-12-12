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

"""Auxiliary functions for working with disks."""

import string


def get_disk_target(
    disks: list[str], prefix: str, *, from_end: bool = False
) -> str:
    """
    Return free disk name.

    .. code-block:: shell-session

       >>> get_disk_target(['vda', 'vdb'], 'vd')
       'vdc'
       >>> get_disk_target(['vda', 'vdc'], 'vd')
       'vdb'
       >>> get_disk_target(['vda', 'vdd'], 'vd', from_end=True)
       'vdz'
       >>> get_disk_target(['vda', 'hda'], 'hd')
       'hdb'

    :param disks: List of attached disk names.
    :param prefix: Disk name prefix.
    :param from_end: If True select a drive letter starting from the
        end of the alphabet.
    """
    index = -1 if from_end else 0
    devs = [d[-1] for d in disks if d.startswith(prefix)]
    return prefix + [x for x in string.ascii_lowercase if x not in devs][index]
