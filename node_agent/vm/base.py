import libvirt

from .exceptions import VMError


class VirtualMachineBase:

    def __init__(self, domain: libvirt.virDomain):
        self.domain = domain
        self.domain_name = self._get_domain_name()
        self.domain_info = self._get_domain_info()

    def _get_domain_name(self):
        try:
            return self.domain.name()
        except libvirt.libvirtError as err:
            raise VMError(f'Cannot get domain name: {err}') from err

    def _get_domain_info(self):
        try:
            info = self.domain.info()
            return {
                'state': info[0],
                'max_memory': info[1],
                'memory': info[2],
                'nproc': info[3],
                'cputime': info[4]
            }
        except libvirt.libvirtError as err:
            raise VMError(f'Cannot get domain info: {err}') from err
