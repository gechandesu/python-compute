import libvirt


class NodeAgentBase:
    def __init__(self, conn: libvirt.virConnect, config: dict):
        self.config = config
        self.conn = conn
