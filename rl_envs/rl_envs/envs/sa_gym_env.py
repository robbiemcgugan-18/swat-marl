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

import sys
import subprocess

import requests
import json

class SingleAgentSwatEnv(gym.Env):

    def __init__(self, net, agent_id):

        self.swat_s1_cps = net
        self.agent_id = agent_id
        print("STARTING SWAT ENVIRONMENT " + str(agent_id))

        # Define your observation space and action space
        self.observation_space = Dict({
            'local': Dict({
                'port': Dict({
                    'rx_packets': Discrete(1000),  # assuming max 1000 packets
                    'tx_packets': Discrete(1000),
                    'rx_bytes': Box(low=0, high=1e6, shape=(1,)),  # assuming max 1e6 bytes
                    'tx_bytes': Box(low=0, high=1e6, shape=(1,)),
                    'rx_errors': Discrete(100),
                    'tx_errors': Discrete(100),
                    'rx_dropped': Discrete(100),
                    'tx_dropped': Discrete(100),
                    'collisions': Discrete(10),
                }),
                'flow': Dict({
                    'byte_count': Box(low=0, high=1e6, shape=(1,)),
                    'packet_count': Discrete(1000),
                    'duration_sec': Box(low=0, high=1000, shape=(1,)),
                    'duration_nsec': Box(low=0, high=1e9, shape=(1,)),
                }),
                'table': Dict({
                    'active_count': Discrete(10),
                    'lookup_count': Discrete(1000),
                    'matched_count': Discrete(1000),
                }),
                'window': Dict({
                    'average': Box(low=0, high=1000, shape=(1,)),
                    'max': Box(low=0, high=1000, shape=(1,)),
                    'min': Box(low=0, high=1000, shape=(1,)),
                }),
            }),
            'global': Dict({
                'port': Dict({
                    'rx_packets': Discrete(1000),
                    'tx_packets': Discrete(1000),
                    'rx_bytes': Box(low=0, high=1e6, shape=(1,)),
                    'tx_bytes': Box(low=0, high=1e6, shape=(1,)),
                    'rx_errors': Discrete(100),
                    'tx_errors': Discrete(100),
                    'rx_dropped': Discrete(100),
                    'tx_dropped': Discrete(100),
                    'collisions': Discrete(10),
                }),
                'flow': Dict({
                    'byte_count': Box(low=0, high=1e6, shape=(1,)),
                    'packet_count': Discrete(1000),
                    'duration_sec': Box(low=0, high=1000, shape=(1,)),
                    'duration_nsec': Box(low=0, high=1e9, shape=(1,)),
                }),
                'table': Dict({
                    'active_count': Discrete(10),
                    'lookup_count': Discrete(1000),
                    'matched_count': Discrete(1000),
                }),
                'window': Dict({
                    'average': Box(low=0, high=1000, shape=(1,)),
                    'max': Box(low=0, high=1000, shape=(1,)),
                    'min': Box(low=0, high=1000, shape=(1,)),
                }),
            }),
        })

        self.action_space = gym.spaces.Discrete(2)

        self.seed()
        self.reset()


    def reset(self, *, seed=None, options=None):
        print("RESETTING SWAT ENVIRONMENT")

        self.reward = 0
        self.done = False
        self.info = {}

        response = requests.get(f'http://localhost:5000/network/stats/{self.agent_id}')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        return data, self.info

    def step(self, action):
        # Execute the given action in the Mininet network and return the next observation, reward, done flag, and additional info
        # Other step code
        if action == 0:
            self.reward += 5
        elif action == 1:
            self.reward -= 5


        if self.reward >= 100:
            self.done = True

        response = requests.get(f'http://localhost:5000/network/stats/{self.agent_id}')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        self.info["msg"] = "This is the info message"

        return (data, self.action_space, self.done, False, self.info)
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.swat_s1_cps.net)

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]
    
    def close(self):
        pass