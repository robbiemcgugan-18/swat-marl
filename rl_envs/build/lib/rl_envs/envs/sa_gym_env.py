from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController, RemoteController

from .topo import SwatTopo
from .run import SwatS1CPS

import gymnasium as gym
from ray.rllib.env.multi_agent_env import MultiAgentEnv
from mininet.cli import CLI

import sys
import subprocess

import requests
import json

class SingleAgentSwatEnv(MultiAgentEnv):

    def __init__(self, net, agent_id):

        self.swat_s1_cps = net
        self.agent_id = agent_id
        print("STARTING SWAT ENVIRONMENT " + str(agent_id))

        # Define your observation space and action space
        self.observation_space = gym.spaces.Discrete(2)
        self.action_space = gym.spaces.Discrete(3)

        response = requests.get(f'http://localhost:5000/network/stats/{self.agent_id}')
        # # The response from the server is a string, so we need to convert it to a Python object
        data = json.loads(response.text)

        print(data)

    def reset(self, *, seed=None, options=None):
        print("RESETTING SWAT ENVIRONMENT")
        return 1, {}

    def step(self, action_dict):
        # Execute the given action in the Mininet network and return the next observation, reward, done flag, and additional info
        # Other step code
        return (0, 5, False, False, {})
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.swat_s1_cps.net)