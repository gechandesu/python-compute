import libvirt

from .vm import VirtualMachine


class NodeAgent:
    def __init__(self, conn: libvirt.virConnect, config: dict):
        self.vm = VirtualMachine(conn, config)
