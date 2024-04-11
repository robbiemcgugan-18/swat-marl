from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController, RemoteController

from .topo import SwatTopo
from .run import SwatS1CPS

from .sa_gym_env import SingleAgentSwatEnv

import gymnasium as gym
from gymnasium.spaces import Dict, Discrete, Box
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
        self.terminateds = set()
        self.truncateds = set()
        self.last_obs = {}
        self.last_rew = {}
        self.last_terminated = {}
        self.last_info = {}
        self.i = 0
        self.num = 3
        self.observation_space = Dict({
            'local': Dict({
                'port': Dict({
                    'rx_packets': Discrete(1000),  # assuming max 1000 packets
                    'tx_packets': Discrete(1000),
                    'rx_bytes': Box(low=0, high=1e6, shape=(1,)),  # assuming max 1e6 bytes
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

    def reset(self, *, seed=None, options=None):
        self.swat_s1_cps.net.stop()
        TOPO =SwatTopo()
        NET = Mininet(topo=TOPO, controller=self.controller)
        self.swat_s1_cps = SwatS1CPS(name='swat_s1', net=NET)
        
        self.terminateds = set()
        self.truncateds = set()
        self.last_obs = {}
        self.last_rew = {}
        self.last_terminated = {}
        self.last_info = {}

        self.i = 0
        for i, a in enumerate(self.agents):
            self.last_obs[i] = a.reset()
            self.last_rew[i] = 0
            self.last_terminated[i] = False
            self.last_info[i] = {}

        obs_dict = {self.i: self.last_obs[self.i]}
        info_dict = {self.i: self.last_info[self.i]}
        self.i = (self.i + 1) % len(self.agents)
        return obs_dict, info_dict

    def step(self, action_dict):
        assert len(self.terminateds) != len(self.agents)
        for i, action in action_dict.items():
            (
                self.last_obs[i],
                self.last_rew[i],
                self.last_terminated[i],
                self.last_info[i],
            ) = self.agents[i].step(action)

        obs = {self.i: self.last_obs[self.i]}
        rew = {self.i: self.last_rew[self.i]}
        terminated = {self.i: self.last_terminated[self.i]}
        truncated = {self.i: False}
        info = {self.i: self.last_info[self.i]}

        if terminated[self.i]:
            rew[self.i] = 1
            self.terminateds.add(self.i)
        self.i = (self.i + 1) % self.num
        terminated["__all__"] = len(self.terminateds) == len(self.agents)
        truncated["__all__"] = len(self.truncateds) == len(self.agents)
        return obs, rew, terminated, truncated, info
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.swat_s1_cps.net)