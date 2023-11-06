"""Random identificators."""

# ruff: noqa: S311, C417

import random


def random_mac() -> str:
    """Retrun random MAC address."""
    mac = [
        0x00,
        0x16,
        0x3E,
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
    ]
    return ':'.join(map(lambda x: '%02x' % x, mac))
