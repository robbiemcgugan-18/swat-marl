"""
swat-s1 topology
"""

from mininet.topo import Topo
from mininet.link import TCLink


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

        plc1 = self.addHost(
            'plc1',
            ip=IP['plc1'] + NETMASK,
            mac=MAC['plc1'])
        self.addLink(plc1, switch, cls=TCLink, bw=10)

        plc2 = self.addHost(
            'plc2',
            ip=IP['plc2'] + NETMASK,
            mac=MAC['plc2'])
        self.addLink(plc2, switch, cls=TCLink, bw=10)

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
