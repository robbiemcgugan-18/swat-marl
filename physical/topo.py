"""
swat-s1 topology
"""

from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import Intf


IP = {
    'plc1': '192.168.1.10',
    'plc2': '192.168.1.20',
    'attacker': '192.168.1.77',
    'sources': '192.168.1.86'
}

NETMASK = '/24'

MAC = {
    'plc1': '00:1D:9C:C7:B0:70',
    'plc2': '00:1D:9C:C8:BC:46',
    'attacker': 'AA:AA:AA:AA:AA:AA',
    'sources': 'AA:AA:AA:AA:AA:AB'
}


class PhysicalTopo(Topo):

    def build(self):

        switch = self.addSwitch('s1')

        attacker = self.addHost(
            'attacker',
            ip=IP['attacker'] + NETMASK,
            mac=MAC['attacker'])
        self.addLink(attacker, switch)

        sources = self.addHost(
            'sources',
            ip=IP['sources'] + NETMASK,
            mac=MAC['sources'])
        self.addLink(sources, switch)

        intfName = 'br0'
        intf = Intf(intfName, node=switch)
