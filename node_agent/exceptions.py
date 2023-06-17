class VMNotFound(Exception):
    def __init__(self, domain, message='VM not found: {domain}'):
        self.domain = domain
        self.message = message.format(domain=domain)
        super().__init__(self.message)


class VMStartError(Exception):
    def __init__(self, domain, message='VM start error: {domain}'):
        self.domain = domain
        self.message = message.format(domain=domain)
        super().__init__(self.message)


class VMShutdownError(Exception):
    def __init__(
            self,
            domain,
            message="VM '{domain}' cannot shutdown, try with hard=True"
        ):
        self.domain = domain
        self.message = message.format(domain=domain)
        super().__init__(self.message)


class VMRebootError(Exception):
    def __init__(
            self,
            domain,
            message="VM '{domain}' reboot, try with hard=True",
        ):
        self.domain = domain
        self.message = message.format(domain=domain)
        super().__init__(self.message)
