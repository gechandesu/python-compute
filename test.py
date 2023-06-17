import libvirt

from node_agent import NodeAgent
from node_agent.config import config


try:
    conn = libvirt.open(config['general']['connect_uri'])
except libvirt.libvirtError as err:
    sys.exit('Failed to open connection to the hypervisor: %s' % err)


node_agent = NodeAgent(conn, config)
s = node_agent.vm.status('debian12')
print(s)
conn.close()
