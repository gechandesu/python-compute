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

"""Utils for creating terminal output and interface elements."""

import re
import sys


class Table:
    """Minimalistic text table constructor."""

    def __init__(self, whitespace: str | None = None):
        """Initialise Table."""
        self.whitespace = whitespace or '\t'
        self.header = []
        self.rows = []
        self.table = ''

    def add_row(self, row: list) -> None:
        """Add table row."""
        self.rows.append([str(col) for col in row])

    def add_rows(self, rows: list[list]) -> None:
        """Add multiple rows."""
        for row in rows:
            self.add_row(row)

    def __str__(self) -> str:
        """Return table."""
        widths = [max(map(len, col)) for col in zip(*self.rows, strict=True)]
        self.rows.insert(0, [str(h).upper() for h in self.header])
        for row in self.rows:
            widths = widths or [len(i) for i in row]
            self.table += self.whitespace.join(
                (
                    val.ljust(width)
                    for val, width in zip(row, widths, strict=True)
                )
            )
            self.table += '\n'
        return self.table.strip()


def confirm(message: str, *, default: bool | None = None) -> None:
    """Start yes/no interactive dialog."""
    while True:
        match default:
            case True:
                prompt = 'default: yes'
            case False:
                prompt = 'default: no'
            case _:
                prompt = 'no default'
        try:
            answer = input(f'{message} ({prompt}) ')
        except KeyboardInterrupt:
            sys.exit('aborted')
        if not answer and isinstance(default, bool):
            return default
        if re.match(r'^y(es)?$', answer, re.I):
            return True
        if re.match(r'^no?$', answer, re.I):
            return False
        print("Please respond 'yes' or 'no'")
