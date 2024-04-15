from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController, RemoteController

from .topo import SwatTopo
from .run import SwatS1CPS

import gymnasium as gym
from mininet.cli import CLI

import sys
import subprocess

import numpy as np
import requests
import json

class SwatEnv(gym.Env):

    def __init__(self, episode_length, epsilon_start=1.0, epsilon_decay=0.99, epsilon_min=0.01):

        print("STARTING SWAT ENVIRONMENT")
        self.controller = RemoteController(name='ryu', ip='127.0.0.1', port=5555)

        # Initialize the Mininet network
        TOPO =SwatTopo()
        NET = Mininet(topo=TOPO, controller=self.controller)
        self.swat_s1_cps = SwatS1CPS(name='swat_s1', net=NET)

        # Define the observation space with an arbitrary high and low limit for simplicity
        low_limits = np.full((17,), -np.inf)  # Assuming negative values are not expected, but setting to -inf for generalization
        high_limits = np.full((17,), np.inf)  # Setting to inf to not limit the range artificially

        self.observation_space = gym.spaces.Box(low=low_limits, high=high_limits, dtype=np.float32)
        self.action_space = gym.spaces.Discrete(4)
        self.attacked = False
        self.episode_length = episode_length
        self.i = 0
        self.epsilon = epsilon_start
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        self.setup_traffic()
        self.reset()

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

        response = requests.get(f'http://localhost:5000/network/global_stats')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        observation = self.flatten_observation(data)

        return observation, self.info

    def step(self, action):
        if np.random.rand() < 0.2:
            action = self.action_space.sample()

        self.i += 1
        # Execute the given action in the Mininet network and return the next observation, reward, done flag, and additional info
        # Other step code
        if action == 0:
            pass
        elif action == 1:
            self.rateLimitICMP(f'plc1')
            self.rateLimitICMP(f'plc2')
            self.rateLimitICMP(f'plc3')

        elif action == 2:
            self.rateLimitSYN(f'plc1')
            self.rateLimitSYN(f'plc2')
            self.rateLimitSYN(f'plc3')

        elif action == 3:
            self.rateLimitUDP(f'plc1')
            self.rateLimitUDP(f'plc2')
            self.rateLimitUDP(f'plc3')

        response = requests.get(f'http://localhost:5000/network/global_stats')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        self.info["msg"] = "This is the info message"

        observation = self.flatten_observation(data)


        self.reward = self.calculate_reward(data)

        if self.is_attack_time():
            self.generate_dos_attack('sources', 'plc1')
            self.generate_dos_attack('sources', 'plc2')
            self.generate_dos_attack('sources', 'plc3')


        if self.i >= self.episode_length:
            self.truncated = True
            self.done = True

        return observation, self.reward, self.i >= self.episode_length, self.i >= self.episode_length, self.info
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.swat_s1_cps.net)


    def calculate_reward(self, observation):
        # Thresholds and penalty weights
        LATENCY_THRESHOLD = 50  # ms
        RESOURCE_USAGE_PENALTY_WEIGHT = 0.0001
        PACKET_COUNT_PENALTY_WEIGHT = 0.05
        ERROR_PENALTY = -25  # Penalty for global errors
        TABLE_LOOKUP_THRESHOLD = 10000000
        TABLE_LOOKUP_PENALTY_WEIGHT = 0.00001

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
        agents_numbers = [1,2,3]
        number1 = np.random.choice(agents_numbers)
        agents_numbers.remove(number1)
        number2 = np.random.choice(agents_numbers)
        host1 = self.swat_s1_cps.net.get(f'plc{number1}')
        host2 = self.swat_s1_cps.net.get(f'plc{number2}')
        result = self.swat_s1_cps.net.ping([host1, host2])
        current_latency = result  # Simulated function
        latency_penalty = -100 if current_latency > LATENCY_THRESHOLD else 0

        # Table lookup efficiency
        lookup_count_penalty = 0
        if global_stats['tables']['lookup_count'] > TABLE_LOOKUP_THRESHOLD:
            excess_lookups = global_stats['tables']['lookup_count'] - TABLE_LOOKUP_THRESHOLD
            lookup_count_penalty = excess_lookups * TABLE_LOOKUP_PENALTY_WEIGHT

        # Total reward calculation
        reward = 300 - byte_count_penalty - packet_count_penalty - error_penalty - lookup_count_penalty - latency_penalty
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
    
    def rateLimitICMP(self, host_name):
        host = self.swat_s1_cps.net.get(host_name)
        """ Limit ICMP traffic to 100kbps with bursts up to 200kbps """
        host.cmd('tc class add dev %s-eth0 parent 1: classid 1:1 htb rate 100kbps ceil 200kbps' % host.name)
        host.cmd('tc filter add dev %s-eth0 protocol ip parent 1:0 prio 1 u32 match ip protocol 1 0xff flowid 1:1' % host.name)

    def rateLimitSYN(self, host_name):
        host = self.swat_s1_cps.net.get(host_name)
        """ Limit SYN packets to 50kbps with bursts up to 100kbps """
        host.cmd('tc class add dev %s-eth0 parent 1: classid 1:2 htb rate 50kbps ceil 100kbps' % host.name)
        host.cmd('tc filter add dev %s-eth0 protocol ip parent 1:0 prio 1 u32 match ip protocol 6 0xff match u8 0x02 0x02 at 33 flowid 1:2' % host.name)

    def rateLimitUDP(self, host_name):
        host = self.swat_s1_cps.net.get(host_name)
        """ Limit UDP traffic to 100kbps with bursts up to 150kbps """
        host.cmd('tc class add dev %s-eth0 parent 1: classid 1:3 htb rate 100kbps ceil 150kbps' % host.name)
        host.cmd('tc filter add dev %s-eth0 protocol ip parent 1:0 prio 1 u32 match ip protocol 17 0xff flowid 1:3' % host.name)

    def is_attack_time(self):
        self.operation_count += 1
        if self.operation_count >= 200 and not self.attacked:
            self.attacked = True
            return True
        return False
    
    def generate_tcp_traffic(self, source_host, target_ip):
        """Generate continuous normal TCP traffic from a source host to a target IP."""
        source = self.swat_s1_cps.net.get(source_host)
        # Run hping3 command in the background to generate continuous TCP traffic
        # Removing the '-c' option sends packets indefinitely
        source.cmd(f'hping3 {target_ip} > /tmp/{source_host}_hping3.log 2>&1 &')
        print(f'Continuous TCP traffic generation started from {source_host} to {target_ip}')

    def generate_dos_attack(self, source_host, target_ip):
        """Generate continuous high TCP traffic from a source host to a target IP."""
        source = self.swat_s1_cps.net.get(source_host)
        # Run hping3 command in the background to generate continuous TCP traffic
        # The --flood option sends packets as fast as possible
        # The --rand-source option uses random source addresses
        source.cmd(f'hping3 -1 --flood --rand-source -q --interval u10000 {target_ip} > /tmp/{source_host}_hping3.log 2>&1 &')
        print(f'High TCP traffic generation started from {source_host} to {target_ip}')

    def stop_dos_attack(self, source_host):
        """Stop the DoS attack from a source host."""
        source = self.swat_s1_cps.net.get(source_host)
        # Kill the hping3 command running in the background
        source.cmd('pkill hping3')
        print(f'DoS attack stopped from {source_host}')

    def setup_traffic(self):
        # Example setup calls
        plc1_ip = self.swat_s1_cps.net.get('plc1').IP()  # Assuming plc1 is a host in the network
        plc2_ip = self.swat_s1_cps.net.get('plc2').IP()
        plc3_ip = self.swat_s1_cps.net.get('plc3').IP()

        self.generate_tcp_traffic('sources', plc1_ip)
        self.generate_tcp_traffic('sources', plc2_ip)
        self.generate_tcp_traffic('sources', plc3_ip)

    


