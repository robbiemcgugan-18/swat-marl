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

class SwatEnv(gym.Env):

    def __init__(self):

        print("STARTING SWAT ENVIRONMENT")
        self.controller = RemoteController(name='ryu', ip='127.0.0.1', port=6633)

        # Initialize the Mininet network
        TOPO =SwatTopo()
        NET = Mininet(topo=TOPO, controller=self.controller)
        self.swat_s1_cps = SwatS1CPS(name='swat_s1', net=NET)

        # Define your observation space and action space
        self.observation_space = gym.spaces.Discrete(2)
        self.action_space = gym.spaces.Discrete(3)

        # Other initialization code

    def reset(self, *, seed=None, options=None):
        print("RESETTING SWAT ENVIRONMENT")
        # Reset the Mininet network and return the initial observation
        self.swat_s1_cps.net.stop()
        TOPO =SwatTopo()
        NET = Mininet(topo=TOPO, controller=self.controller)
        self.swat_s1_cps = SwatS1CPS(name='swat_s1', net=NET)
        # Other reset code
        return 1, {}

    def step(self, action):
        # Execute the given action in the Mininet network and return the next observation, reward, done flag, and additional info
        # Other step code
        return (0, 1, False, False, {})
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.swat_s1_cps.net)

    


