from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController, RemoteController

from swat.topo import SwatTopo
from swat.run import SwatS1CPS
from physical.topo import PhysicalTopo
from physical.run import PhysicalTestbed

import gymnasium as gym
from mininet.cli import CLI

import sys
import subprocess

import numpy as np
import requests
import json

class SwatEnv(gym.Env):

    def __init__(self, episode_length, epsilon_start=1.0, epsilon_decay=0.99, epsilon_min=0.01, evaluate=False):

        print("STARTING SWAT ENVIRONMENT")

        self.env = PhysicalTestbed(name='physical')

        # Define the observation space with an arbitrary high and low limit for simplicity
        low_limits = np.full((17,), -np.inf)  # Assuming negative values are not expected, but setting to -inf for generalization
        high_limits = np.full((17,), np.inf)  # Setting to inf to not limit the range artificially

        self.observation_space = gym.spaces.Box(low=low_limits, high=high_limits, dtype=np.float32)
        self.action_space = gym.spaces.Discrete(21)
        self.attacked = False
        self.episode_length = episode_length
        self.i = 0
        self.epsilon = epsilon_start
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        self.setup_traffic()
        self.reset()

        if evaluate:
            self.generate_dos_attack('attacker', 'plc1')
            self.generate_dos_attack('attacker', 'plc2')
            self.generate_dos_attack('attacker', 'plc3')

    def reset(self, *, seed=None, options=None):
        if self.attacked:
            self.stop_dos_attack('attacker')

        self.reward = 0
        self.done = False
        self.truncated = False
        self.info = {}
        self.attacked = False
        self.operation_count = 0
        self.i = 0

        s1 = self.env.net.get('s1')
        s1.dpctl('del-flows')

        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=1,actions=output:2,3,4,5')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=2,actions=output:1,3,4,5')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=3,actions=output:1,2,4,5')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=4,actions=output:1,2,3,5')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=5,actions=output:1,2,3,4')

        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=1,actions=output:2,3,4,5')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=2,actions=output:1,3,4,5')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=3,actions=output:1,2,4,5')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=4,actions=output:1,2,3,5')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=5,actions=output:1,2,3,4')

        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=1,actions=output:2,3,4')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=2,actions=output:1,3,4')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=3,actions=output:1,2,4')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=4,actions=output:1,2,3')

        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=1,actions=output:2,3,4')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=2,actions=output:1,3,4')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=3,actions=output:1,2,4')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=4,actions=output:1,2,3')

        response = requests.get(f'http://localhost:5000/network/global_stats')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        host1 = self.env.net.get(f'plc1')
        host2 = self.env.net.get(f'plc2')
        result = self.env.net.ping([host1, host2], timeout='0.1')
        data["latency"] = result 

        observation = self.flatten_observation(data)

        return observation, self.info

    def step(self, action):
        if np.random.rand() < self.epsilon:
            action = self.action_space.sample()

        self.i += 1
        # Execute the given action in the Mininet network and return the next observation, reward, done flag, and additional info
        # Other step code
        if action == 0:
            self.blockICMP()
        elif action == 1:
            self.unblockICMP()
        elif action == 2:
            self.blockModbus()
        elif action == 3:
            self.unblockModbus()
        elif action == 4:
            self.blockUDP()
        elif action == 5:
            self.unblockUDP()
        elif action == 6:
            self.set_rate_icmp(100)
        elif action == 7:
            self.set_rate_icmp(750)
        elif action == 8:
            self.set_rate_icmp(1500)
        elif action == 9:
            self.set_rate_udp(100)
        elif action == 10:
            self.set_rate_udp(750)
        elif action == 11:
            self.set_rate_udp(1500)
        elif action == 12:
            self.set_rate_modbus(100)
        elif action == 13:
            self.set_rate_modbus(750)
        elif action == 14:
            self.set_rate_modbus(1500)
        elif action == 15:
            self.limit_new_connections(10, 60)
        elif action == 16:
            self.limit_new_connections(20, 120)
        elif action == 17:
            self.limit_new_connections(30, 180)
        elif action == 18:
            self.prioritize_udp()
        elif action == 19:
            self.prioritize_tcp()
        elif action == 20:
            self.prioritize_modbus_tcp()
        elif action == 21:
            pass

        response = requests.get(f'http://localhost:5000/network/global_stats')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        host1 = self.env.net.get(f'plc1')
        host2 = self.env.net.get(f'plc2')
        result = self.env.net.ping([host1, host2], timeout='0.1')
        data["latency"] = result 

        self.info["msg"] = "This is the info message"

        observation = self.flatten_observation(data)


        self.reward = self.calculate_reward(data)

        # if self.is_attack_time():
        #     self.generate_dos_attack('attacker', 'plc1')
        #     self.generate_dos_attack('attacker', 'plc2')
            # self.generate_dos_attack('attacker', 'plc3')


        if self.i >= self.episode_length:
            self.truncated = True
            self.done = True

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        return observation, self.reward, self.i >= self.episode_length, self.i >= self.episode_length, self.info
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.env.net)


    def calculate_reward(self, observation):
        # Thresholds and penalty weights
        LATENCY_THRESHOLD = 50  # ms
        RESOURCE_USAGE_PENALTY_WEIGHT = 0.0001
        PACKET_COUNT_PENALTY_WEIGHT = 0.05
        ERROR_PENALTY = 2.5  # Penalty for global errors
        TABLE_LOOKUP_THRESHOLD = 10000000
        TABLE_LOOKUP_PENALTY_WEIGHT = 0.00001
        QUEUE_BYTE_COUNT_THRESHOLD = 10000000
        QUEUE_BYTE_COUNT_PENALTY_WEIGHT = 0.00001
        WINDOW_AVERAGE_THRESHOLD = 100
        WINDOW_AVERAGE_PENALTY_WEIGHT = 0.01

        # Extract metrics
        global_stats = observation

        # Resource usage penalties
        byte_count = global_stats['flow']['byte_count']
        byte_count_penalty = byte_count * RESOURCE_USAGE_PENALTY_WEIGHT

        packet_count = global_stats['flow']['packet_count']
        packet_count_penalty = packet_count * PACKET_COUNT_PENALTY_WEIGHT

        # Error penalties
        error_penalty = 0
        if global_stats['port']['rx_errors'] > 0 or global_stats['port']['tx_errors'] > 0:
            error_penalty += ERROR_PENALTY

        # Latency check
        agents_numbers = [1,2]
        number1 = np.random.choice(agents_numbers)
        agents_numbers.remove(number1)
        number2 = np.random.choice(agents_numbers)
        host1 = self.env.net.get(f'plc{number1}')
        host2 = self.env.net.get(f'plc{number2}')
        result = self.env.net.ping([host1, host2], timeout='0.1')
        current_latency = result  # Simulated function

        latency_penalty = 0
        latency_penalty += 50 if current_latency > LATENCY_THRESHOLD else -5

        # Table lookup efficiency
        lookup_count_penalty = 0
        if global_stats['tables']['lookup_count'] > TABLE_LOOKUP_THRESHOLD:
            excess_lookups = global_stats['tables']['lookup_count'] - TABLE_LOOKUP_THRESHOLD
            lookup_count_penalty = excess_lookups * TABLE_LOOKUP_PENALTY_WEIGHT

        # Queue byte count penalty
        queue_byte_count_penalty = 0
        if global_stats['queue']['byte_count'] > QUEUE_BYTE_COUNT_THRESHOLD:
            excess_queue_byte_count = global_stats['queue']['byte_count'] - QUEUE_BYTE_COUNT_THRESHOLD
            queue_byte_count_penalty = excess_queue_byte_count * QUEUE_BYTE_COUNT_PENALTY_WEIGHT

        # Window average penalty
        window_average_penalty = 0
        if global_stats['window']['average'] < WINDOW_AVERAGE_THRESHOLD:
            window_average_deficit = WINDOW_AVERAGE_THRESHOLD - global_stats['window']['average']
            window_average_penalty = window_average_deficit * WINDOW_AVERAGE_PENALTY_WEIGHT

        # Total reward calculation
        print(byte_count_penalty, packet_count_penalty, error_penalty, latency_penalty)
        reward = 100 - byte_count_penalty - packet_count_penalty - error_penalty - latency_penalty - lookup_count_penalty - queue_byte_count_penalty - window_average_penalty
        return reward

    def flatten_observation(self, obs_dict):
        # Initialize a list to hold the flattened observation
        flat_obs = []
        
        # Iterate over the 'global' key
        for key in ['flow', 'port', 'tables', 'window']:
            if key in obs_dict:
                stats = obs_dict[key]
                # Flatten each stat and add to the flat_obs list
                for value in stats.values():
                    if isinstance(value, (int, float)):  # Directly append integers and floats
                        flat_obs.append(value)
                    elif isinstance(value, np.ndarray):  # Flatten arrays and append
                        flat_obs.extend(value.flatten())
                    else:
                        raise TypeError(f"Unsupported data type {type(value)}")
        return np.array(flat_obs, dtype=np.float32)  # Convert list to a NumPy array for consistency
    
    def blockICMP(self):
        s1 = self.env.net.get('s1')

        s1.cmd('ovs-ofctl add-flow s1 priority=400,in_port=1,dl_type=0x0800,nw_proto=1,actions=normal')
        s1.cmd('ovs-ofctl add-flow s1 priority=400,in_port=2,dl_type=0x0800,nw_proto=1,actions=normal')
        s1.cmd('ovs-ofctl add-flow s1 priority=400,in_port=3,dl_type=0x0800,nw_proto=1,actions=normal')

        s1.cmd('ovs-ofctl add-flow s1 priority=300,dl_type=0x0800,nw_proto=1,actions=drop')
        
    def unblockICMP(self):
        s1 = self.env.net.get('s1')

        # Removing the drop rule for ICMP traffic
        s1.cmd('ovs-ofctl del-flows s1 dl_type=0x0800,nw_proto=1')


    def blockModbus(self):
        s1 = self.env.net.get('s1')

        s1.cmd('ovs-ofctl add-flow s1 priority=500,in_port=1,dl_type=0x0800,nw_proto=6,tp_dst=502,actions=normal')
        s1.cmd('ovs-ofctl add-flow s1 priority=500,in_port=2,dl_type=0x0800,nw_proto=6,tp_dst=502,actions=normal')
        s1.cmd('ovs-ofctl add-flow s1 priority=500,in_port=3,dl_type=0x0800,nw_proto=6,tp_dst=502,actions=normal')
        
        # New rule to block all Modbus TCP traffic
        s1.cmd('ovs-ofctl add-flow s1 priority=300,dl_type=0x0800,nw_proto=6,tp_dst=502,actions=drop')

    def unblockModbus(self):
        s1 = self.env.net.get('s1')

        # Removing the drop rule for Modbus TCP traffic
        s1.cmd('ovs-ofctl del-flows s1 dl_type=0x0800,nw_proto=6,tp_dst=502')


    def blockUDP(self):
        s1 = self.env.net.get('s1')
        
        s1.cmd('ovs-ofctl add-flow s1 priority=500,in_port=1,dl_type=0x0800,nw_proto=17,actions=normal')
        s1.cmd('ovs-ofctl add-flow s1 priority=500,in_port=2,dl_type=0x0800,nw_proto=17,actions=normal')
        s1.cmd('ovs-ofctl add-flow s1 priority=500,in_port=3,dl_type=0x0800,nw_proto=17,actions=normal')

        # New rule to block all UDP traffic
        s1.cmd('ovs-ofctl add-flow s1 priority=300,dl_type=0x0800,nw_proto=17,actions=drop')

    def unblockUDP(self):
        s1 = self.env.net.get('s1')

        # Removing the drop rule for UDP traffic
        s1.cmd('ovs-ofctl del-flows s1 dl_type=0x0800,nw_proto=17')

    def cleanup_icmp(self):
        s1 = self.env.net.get('s1')

        # Assuming meter ids 1, 2, and 3 are used for ICMP rate limiting
        for meter_id in [1, 2, 3]:
            s1.cmd(f'ovs-ofctl -O Openflow13 del-meter s1 meter={meter_id}')

    def set_rate_icmp(self, rate_kbps):
        self.cleanup_icmp()
        s1 = self.env.net.get('s1')
        s1.cmd(f'ovs-ofctl -O Openflow13 add-meter s1 meter=1,kbps,band=type=drop,rate={rate_kbps}')
        s1.cmd('ovs-ofctl add-flow s1 priority=500,dl_type=0x0800,nw_proto=1,actions=meter:1')

    def cleanup_udp(self):
        s1 = self.env.net.get('s1')
        for meter_id in [4, 5, 6]:  # Assuming meter ids 4, 5, and 6 are used for UDP rate limiting
            s1.cmd(f'ovs-ofctl -O Openflow13 del-meter s1 meter={meter_id}')

    def set_rate_udp(self, rate_kbps):
        self.cleanup_udp()
        s1 = self.env.net.get('s1')
        s1.cmd(f'ovs-ofctl -O Openflow13 add-meter s1 meter=2,kbps,band=type=drop,rate={rate_kbps}')
        s1.cmd('ovs-ofctl add-flow s1 priority=500,dl_type=0x0800,nw_proto=17,actions=meter:2')

    def cleanup_modbus(self):
        s1 = self.env.net.get('s1')
        for meter_id in [7, 8, 9]:  # Assuming meter ids 7, 8, and 9 are used for Modbus rate limiting
            s1.cmd(f'ovs-ofctl -O Openflow13 del-meter s1 meter={meter_id}')

    def set_rate_modbus(self, rate_kbps):
        self.cleanup_modbus()
        s1 = self.env.net.get('s1')
        s1.cmd(f'ovs-ofctl -O Openflow13 add-meter s1 meter=3,kbps,band=type=drop,rate={rate_kbps}')
        s1.cmd('ovs-ofctl add-flow s1 priority=500,dl_type=0x0800,nw_proto=6,tp_dst=502,actions=meter:3')

    def limit_new_connections(self, max_connections, time_window):
        s1 = self.env.net.get('s1')
        s1.cmd('ovs-ofctl del-flows s1 dl_type=0x0800,nw_proto=6,tcp_flags=0x002')

        conjunction_id = hash(f"{max_connections}_{time_window}") % 10000

        # Adding flows to implement the new connection limit settings
        s1.cmd(f'ovs-ofctl -O OpenFlow13 add-flow s1 priority=700,dl_type=0x0800,nw_proto=6,tcp_flags=0x002,actions=conjunction({conjunction_id},1/2)')
        s1.cmd(f'ovs-ofctl -O OpenFlow13 add-flow s1 priority=700,conjunction_id={conjunction_id},action=drop')
        s1.cmd(f'ovs-ofctl -O OpenFlow13 add-flow s1 priority=700,conjunction_id={conjunction_id},action=normal')

    def prioritize_udp(self):
        s1 = self.env.net.get('s1')
        # Prioritize UDP traffic to a specific service port
        s1.cmd('ovs-ofctl add-flow s1 priority=900,dl_type=0x0800,nw_proto=17,actions=normal')

    def prioritize_tcp(self):
        s1 = self.env.net.get('s1')
        # Prioritize TCP traffic to a specific service port
        s1.cmd('ovs-ofctl add-flow s1 priority=900,dl_type=0x0800,nw_proto=6,actions=normal')

    def prioritize_modbus_tcp(self):
        s1 = self.env.net.get('s1')
        # Modbus TCP typically uses port 502, specify if different
        modbus_port = 502
        # Prioritize Modbus TCP traffic
        s1.cmd('ovs-ofctl add-flow s1 priority=900,dl_type=0x0800,nw_proto=6,tp_dst={modbus_port},actions=normal'.format(modbus_port=modbus_port))

    def is_attack_time(self):
        self.operation_count += 1
        if self.operation_count >= 200 and not self.attacked:
            self.attacked = True
            return True
        return False
    
    def is_attack_time(self):
        self.operation_count += 1
        if self.operation_count >= 20 and not self.attacked:
            self.attacked = True
            return True
        return False
    
    def generate_tcp_traffic(self, source_host, target_ip):
        """Generate continuous normal TCP traffic from a source host to a target IP."""
        source = self.env.net.get(source_host)
        # Run hping3 command in the background to generate continuous TCP traffic
        # Removing the '-c' option sends packets indefinitely
        source.cmd(sys.executable + ' -u ' + f'rl_envs/rl_envs/envs/traffic.py {target_ip} &')
        print(f'Continuous TCP traffic generation started from {source_host} to {target_ip}')

    def generate_dos_attack(self, source_host, target):
        """Generate continuous high TCP traffic from a source host to a target IP."""
        source = self.env.net.get(source_host)
        target_ip_1 = self.env.net.get(target[0]).IP()
        target_ip_2 = self.env.net.get(target[1]).IP()
        target_ip_3 = self.env.net.get(target[2]).IP()

        source.cmd(sys.executable + ' -u ' + f'rl_envs/rl_envs/envs/dos.py {target_ip_1} &')
        source.cmd(f'hping3 -2 --flood --rand-source -q --interval u1000 {target_ip_2} > /tmp/{source_host}_hping3.log 2>&1 &')
        source.cmd(f'hping3 -1 --flood --rand-source -q --interval u1000 {target_ip_3} > /tmp/{source_host}_hping3.log 2>&1 &')

        # Evaluation
        # source.cmd(f'hping3 -2 --flood --rand-source -q --interval u1000 {target_ip} > /tmp/{source_host}_hping3.log 2>&1 &')
        print(f'High TCP traffic generation started from {source_host} to {target_ip_1}, {target_ip_2}, {target_ip_3}')


    def stop_dos_attack(self, source_host):
        """Stop the DoS attack from a source host."""
        source = self.env.net.get(source_host)
        # Kill the Python command running the dos.py script in the background
        source.cmd('pkill -f "python.*dos.py"')
        source.cmd('pkill -f "hping3.*"')
        print(f'DoS attack stopped from {source_host}')

    def setup_traffic(self):
        # Example setup calls
        plc1_ip = self.env.net.get('plc1').IP()  # Assuming plc1 is a host in the network
        plc2_ip = self.env.net.get('plc2').IP()
        plc3_ip = self.env.net.get('plc3').IP()

        self.generate_tcp_traffic('sources', plc1_ip)
        self.generate_tcp_traffic('sources', plc2_ip)
        self.generate_tcp_traffic('sources', plc3_ip)

    


