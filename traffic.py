from scapy.all import *
from random import choice

def send_dummy_traffic(switch, interfaces):
    for interface in interfaces:
        ip = IP(dst=switch)
        tcp = TCP(dport=80)  # You can change the destination port
        packet = ip/tcp
        send(packet, iface=interface)

switch = 's1'
interfaces = ['s1-eth1', 's1-eth2', 's1-eth3']
send_dummy_traffic(switch, choice(interfaces))