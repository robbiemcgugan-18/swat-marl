from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController, RemoteController

from .topo import SwatTopo
from .run import SwatS1CPS

import gymnasium as gym
from gymnasium.utils import seeding
from gymnasium.spaces import Dict, Discrete, Box
from ray.rllib.env.multi_agent_env import MultiAgentEnv
from mininet.cli import CLI
import numpy as np

import sys
import os
import subprocess

import requests
import json

class SingleAgentSwatEnv(gym.Env):

    def __init__(self, env, agent_id, episode_length, epsilon_start=1.0, epsilon_decay=0.9, epsilon_min=0.01):

        # self.env = net
        self.agent_id = agent_id
        self.env = env
        print("STARTING SWAT ENVIRONMENT " + str(agent_id))

        # Define the observation space with an arbitrary high and low limit for simplicity
        low_limits = np.full((31,), -np.inf)  # Assuming negative values are not expected, but setting to -inf for generalization
        high_limits = np.full((31,), np.inf)  # Setting to inf to not limit the range artificially


        self.observation_space = gym.spaces.Box(low=low_limits, high=high_limits, dtype=np.float32)

        self.action_space = gym.spaces.Discrete(21)

        self.episode_length = episode_length
        self.i = 0
        self.epsilon = epsilon_start
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        self.seed()
        self.reset()


    def reset(self, *, seed=None, options=None):


        self.reward = 0
        self.done = False
        self.truncated = False
        self.info = {}
        self.i = 0

        response = requests.get(f'http://localhost:5000/network/stats/{self.agent_id}')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        observation = self.flatten_observation(data)

        return observation

    def step(self, action):

        if np.random.rand() < self.epsilon:
            print("Taking random action")
            action = self.action_space.sample()

        print(f"Taking action {action}")

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

        response = requests.get(f'http://localhost:5000/network/stats/{self.agent_id}')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        self.info["msg"] = "This is the info message"

        observation = self.flatten_observation(data)


        self.reward = self.calculate_reward(data)


        if self.i >= self.episode_length:
            self.truncated = True
            self.done = True

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        if self.i >= self.episode_length:
            print(f"Episode finished after {self.i} steps with total reward: {self.reward}")
        return observation, self.reward, self.i >= self.episode_length, self.i >= self.episode_length, self.info
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.env.net)

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]
    
    def close(self):
        pass

    def calculate_reward(self, observation):
        # Thresholds and penalty weights
        LATENCY_THRESHOLD = 50  # ms
        GLOBAL_RESOURCE_USAGE_PENALTY_WEIGHT = 0.0001
        LOCAL_RESOURCE_USAGE_PENALTY_WEIGHT = 0.0002  # Higher penalty for local resources
        PACKET_COUNT_PENALTY_WEIGHT = 0.05
        LOCAL_PACKET_COUNT_PENALTY_WEIGHT = 0.1  # Higher penalty for local packets
        ERROR_PENALTY = 2.5  # Penalty for global errors
        LOCAL_ERROR_PENALTY = 5  # Higher penalty for local errors
        TABLE_LOOKUP_THRESHOLD = 10000000
        TABLE_LOOKUP_PENALTY_WEIGHT = 0.00001

        # Extract metrics
        global_stats = observation['global']
        local_stats = observation['local']

        # Resource usage penalties
        global_byte_count = global_stats['flow']['byte_count']
        local_byte_count = local_stats['flow']['byte_count']
        byte_count_penalty = (global_byte_count * GLOBAL_RESOURCE_USAGE_PENALTY_WEIGHT +
                            local_byte_count * LOCAL_RESOURCE_USAGE_PENALTY_WEIGHT)

        global_packet_count = global_stats['flow']['packet_count']
        local_packet_count = local_stats['flow']['packet_count']
        packet_count_penalty = (global_packet_count * PACKET_COUNT_PENALTY_WEIGHT +
                                local_packet_count * LOCAL_PACKET_COUNT_PENALTY_WEIGHT)

        # Error penalties
        error_penalty = 0
        if global_stats['port']['rx_errors'] > 0 or global_stats['port']['tx_errors'] > 0:
            error_penalty += ERROR_PENALTY
        if local_stats['port']['rx_errors'] > 0 or local_stats['port']['tx_errors'] > 0:
            error_penalty += LOCAL_ERROR_PENALTY

        latency_penalty = 0
        # Latency check
        agents_numbers = [1,2,3]
        agents_numbers.remove(self.agent_id)
        host1 = self.env.net.get(f'plc{self.agent_id}')
        host2 = self.env.net.get(f'plc{np.random.choice(agents_numbers)}')
        result = self.env.net.ping([host1, host2], timeout="0.1")
        current_latency = result  # Simulated function
        if current_latency > LATENCY_THRESHOLD:          
            latency_penalty += 50 
        else:
            latency_penalty -= 5

        # Table lookup efficiency
        # lookup_count_penalty = 0
        # if global_stats['tables']['lookup_count'] > TABLE_LOOKUP_THRESHOLD:
        #     excess_lookups = global_stats['tables']['lookup_count'] - TABLE_LOOKUP_THRESHOLD
        #     lookup_count_penalty = excess_lookups * TABLE_LOOKUP_PENALTY_WEIGHT

        # Total reward calculation
        print(byte_count_penalty, packet_count_penalty, error_penalty, latency_penalty)
        reward = 100 - byte_count_penalty - packet_count_penalty - error_penalty - latency_penalty
        return reward

    def flatten_observation(self, obs_dict):
        # Initialize a list to hold the flattened observation
        flat_obs = []
        
        # Iterate over the 'global' and 'local' keys
        for key in ['global', 'local']:
            if key in obs_dict:
                # Flatten each sub-key such as 'port', 'flow', 'tables', and 'window'
                for subkey in ['port', 'flow', 'tables', 'window']:
                    if subkey in obs_dict[key]:
                        stats = obs_dict[key][subkey]
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
