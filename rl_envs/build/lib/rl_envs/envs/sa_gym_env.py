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
import subprocess

import requests
import json

class SingleAgentSwatEnv(gym.Env):

    def __init__(self, swat_s1_cps, agent_id, episode_length, epsilon_start=1.0, epsilon_decay=0.99, epsilon_min=0.01):

        # self.swat_s1_cps = net
        self.agent_id = agent_id
        self.swat_s1_cps = swat_s1_cps
        print("STARTING SWAT ENVIRONMENT " + str(agent_id))

        # Define the observation space with an arbitrary high and low limit for simplicity
        low_limits = np.full((31,), -np.inf)  # Assuming negative values are not expected, but setting to -inf for generalization
        high_limits = np.full((31,), np.inf)  # Setting to inf to not limit the range artificially


        self.observation_space = gym.spaces.Box(low=low_limits, high=high_limits, dtype=np.float32)

        self.action_space = gym.spaces.Discrete(4)

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

        if np.random.rand() < 0.2:
            action = self.action_space.sample()

        self.i += 1
        # Execute the given action in the Mininet network and return the next observation, reward, done flag, and additional info
        # Other step code
        if action == 0:
            pass
        elif action == 1:
            self.rateLimitICMP(f'plc{self.agent_id}')
        elif action == 2:
            self.rateLimitSYN(f'plc{self.agent_id}')
        elif action == 3:
            self.rateLimitUDP(f'plc{self.agent_id}')

        response = requests.get(f'http://localhost:5000/network/stats/{self.agent_id}')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        self.info["msg"] = "This is the info message"

        observation = self.flatten_observation(data)


        self.reward = self.calculate_reward(data)


        if self.i >= self.episode_length:
            self.truncated = True
            self.done = True

        return observation, self.reward, self.i >= self.episode_length, self.i >= self.episode_length, self.info
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.swat_s1_cps.net)

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
        ERROR_PENALTY = -25  # Penalty for global errors
        LOCAL_ERROR_PENALTY = -50  # Higher penalty for local errors
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

        # Latency check
        agents_numbers = [1,2,3]
        agents_numbers.remove(self.agent_id)
        host1 = self.swat_s1_cps.net.get(f'plc{self.agent_id}')
        host2 = self.swat_s1_cps.net.get(f'plc{np.random.choice(agents_numbers)}')
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