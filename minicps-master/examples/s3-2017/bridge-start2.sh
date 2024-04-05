#!/bin/bash

#################################
# Set up Ethernet bridge on Linux
# Requires: bridge-utils
#################################

# Define Bridge Interface
br="br1"

# Define list of TAP interfaces to be bridged,
# for example tap="tap0 tap1 tap2".
tap="tap1"

# Define physical ethernet interface to be bridged
# with TAP interface(s) above.
eth="attacker2-eth0"
# eth_ip="192.168.1.78"
# eth_netmask="255.255.255.0"
# eth_broadcast="192.168.1.255"

for t in $tap; do
    openvpn --mktun --dev $t
done

brctl addbr $br
brctl addif $br $eth

for t in $tap; do
    brctl addif $br $t
done

for t in $tap; do
    ifconfig $t 0.0.0.0 promisc up
done

ifconfig $eth 0.0.0.0 promisc up

# ifconfig $br $eth_ip netmask $eth_netmask broadcast $eth_broadcast
ifconfig $br up
