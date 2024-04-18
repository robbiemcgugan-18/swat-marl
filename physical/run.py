"""
swat-s1 run.py
"""

from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController, RemoteController

from physical.topo import PhysicalTopo


import sys


class PhysicalTestbed:

    """Main container used to run the simulation."""

    def __init__(self, name):

        self.controller = RemoteController(name='ryu', ip='127.0.0.1', port=5555)

        # Initialize the Mininet network
        self.TOPO = PhysicalTopo()
        net = Mininet(topo=self.TOPO, controller=self.controller)

        self.name = name
        self.net = net

        net.start()

        # net.pingAll()

        # start devices
        plc1, plc2, s1, attacker = self.net.get(
            'plc1', 'plc2', 's1', 'attacker')

        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=1,actions=output:2,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=2,actions=output:1,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=3,actions=output:1,2,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=4,actions=output:1,2,3')

        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=1,actions=output:2,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=2,actions=output:1,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=3,actions=output:1,2,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=4,actions=output:1,2,3')


    def reset(self):
        self.net.stop()

        self.net = Mininet(topo=self.TOPO, controller=self.controller)

        self.net.start()

