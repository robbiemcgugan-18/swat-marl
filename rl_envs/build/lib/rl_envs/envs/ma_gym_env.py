from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController, RemoteController

from .topo import SwatTopo
from .run import SwatS1CPS

from .sa_gym_env import SingleAgentSwatEnv

import gymnasium as gym
from ray.rllib.env.multi_agent_env import MultiAgentEnv
from mininet.cli import CLI

import sys
import subprocess

class MultiAgentSwatEnv(MultiAgentEnv):

    def __init__(self):
        super().__init__()

        print("STARTING MULTI AGENT SWAT ENVIRONMENT")
        self.controller = RemoteController(name='ryu', ip='127.0.0.1', port=5555)

        # Initialize the Mininet network
        TOPO = SwatTopo()
        NET = Mininet(topo=TOPO, controller=self.controller)
        self.swat_s1_cps = SwatS1CPS(name='swat_s1', net=NET)

        self.agents = [SingleAgentSwatEnv(self.swat_s1_cps, i) for i in range(1,4)]

        self._agent_ids = set(range(3))
        self.dones = set()
        self.last_obs = {}
        self.last_rew = {}
        self.last_done = {}
        self.last_info = {}
        self.i = 0
        self.num = 3
        self.observation_space = gym.spaces.Discrete(10)
        self.action_space = gym.spaces.Discrete(2)

    def reset(self, *, seed=None, options=None):
        self.swat_s1_cps.net.stop()
        TOPO =SwatTopo()
        NET = Mininet(topo=TOPO, controller=self.controller)
        self.swat_s1_cps = SwatS1CPS(name='swat_s1', net=NET)
        
        self.dones = set()
        self.last_obs = {}
        self.last_rew = {}
        self.last_done = {}
        self.last_info = {}

        self.i = 0
        for i, a in enumerate(self.agents):
            self.last_obs[i] = a.reset()
            self.last_rew[i] = 0
            self.last_done[i] = False
            self.last_info[i] = {}

        obs_dict = {self.i: self.last_obs[self.i]}
        self.i = (self.i + 1) % len(self.agents)
        return obs_dict

    def step(self, action_dict):
        assert len(self.dones) != len(self.agents)
        for i, action in action_dict.items():
            (
                self.last_obs[i],
                self.last_rew[i],
                self.last_done[i],
                self.last_info[i],
            ) = self.agents[i].step(action)

        obs = {self.i: self.last_obs[self.i]}
        rew = {self.i: self.last_rew[self.i]}
        done = {self.i: self.last_done[self.i]}
        info = {self.i: self.last_info[self.i]}

        if done[self.i]:
            rew[self.i] = 0
            self.dones.add(self.i)
        self.i = (self.i + 1) % self.num
        done["__all__"] = len(self.dones) == len(self.agents)
        return obs, rew, done, info
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.swat_s1_cps.net)