class QemuAgentError(Exception):
    """Mostly QEMU Guest Agent is not responding."""


class VMError(Exception):
    """Something went wrong while interacting with the domain."""


class VMNotFound(Exception):
    def __init__(self, domain, message='VM not found: {domain}'):
        self.domain = domain
        self.message = message.format(domain=domain)
        super().__init__(self.message)
