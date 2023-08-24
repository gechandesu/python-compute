import random


def random_mac() -> str:
    """Retrun random MAC address."""
    mac = [0x00, 0x16, 0x3e,
           random.randint(0x00, 0x7f),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def unique_mac() -> str:
    """Return non-conflicting MAC address."""
    # todo: see virtinst.DeviceInterface.generate_mac
    raise NotImplementedError()
