"""
swat-s1 run.py
"""

from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController

from .topo import SwatTopo


import sys


class SwatS1CPS(MiniCPS):

    """Main container used to run the simulation."""

    def __init__(self, name, net):

        self.name = name
        self.net = net

        net.start()

        # net.pingAll()

        # start devices
        plc1, plc2, plc3, s1 = self.net.get(
            'plc1', 'plc2', 'plc3', 's1')

        # SPHINX_SWAT_TUTORIAL RUN(
        plc2.cmd(sys.executable + ' -u ' +' plc2.py &> logs/plc2.log &')
        plc3.cmd(sys.executable + ' -u ' + ' plc3.py  &> logs/plc3.log &')
        plc1.cmd(sys.executable + ' -u ' + ' plc1.py  &> logs/plc1.log &')
        s1.cmd(sys.executable + ' -u ' + ' physical_process.py  &> logs/process.log &')
        # SPHINX_SWAT_TUTORIAL RUN)
        # CLI(self.net)

        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=1,actions=output:2,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=2,actions=output:1,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=3,actions=output:1,2,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=4,actions=output:1,2,3')

        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=1,actions=output:2,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=2,actions=output:1,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=3,actions=output:1,2,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=4,actions=output:1,2,3')

    def adjust_bandwidth(self, host_name, interface_name, bandwidth):
        """Adjust the bandwidth of a specific interface on a specific host."""
        host = self.net.get(host_name)
        host.cmd('tc qdisc add dev {} root tbf rate {}mbit burst 32kbit latency 400ms'.format(interface_name, bandwidth))
        print('tc qdisc add dev {} root tbf rate {}mbit burst 32kbit latency 400ms'.format(interface_name, bandwidth))

    def adjust_latency(self, host_name, interface_name, latency):
        """Adjust the latency of a specific interface on a specific host."""
        host = self.net.get(host_name)
        host.cmd('tc qdisc add dev {} root netem delay {}ms'.format(interface_name, latency))
        result = host.cmd('ping plc2')
        print(result)

    def adjust_packet_loss(self, host_name, interface_name, loss_rate):
        """Adjust the packet loss rate of a specific interface on a specific host."""
        host = self.net.get(host_name)
        host.cmd('tc qdisc add dev {} root netem loss {}%'.format(interface_name, loss_rate))

