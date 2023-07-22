import libvirt

from ..main import LibvirtSession
from ..exceptions import VMNotFound


class VMBase:
    def __init__(self, session: LibvirtSession, name: str):
        self.domname = name
        self.session = session.session  # virConnect object
        self.config = session.config  # ConfigLoader object
        self.domain = self._get_domain(name)

    def _get_domain(self, name: str) -> libvirt.virDomain:
        """Get virDomain object by name to manipulate with domain."""
        try:
            domain = self.session.lookupByName(name)
            if domain is not None:
                return domain
            raise VMNotFound(name)
        except libvirt.libvirtError as err:
            raise VMNotFound(err) from err
