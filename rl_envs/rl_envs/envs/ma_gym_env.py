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

import numpy as np


class MultiAgentSwatEnv(MultiAgentEnv):

    def __init__(self):
        super().__init__()

        self.controller = RemoteController(name='ryu', ip='127.0.0.1', port=5555)

        # Initialize the Mininet network
        self.TOPO = SwatTopo()
        net = Mininet(topo=self.TOPO, controller=self.controller)

        print("STARTING MULTI AGENT SWAT ENVIRONMENT")
        self.swat_s1_cps = SwatS1CPS(name='swat_s1', net=net)

        self.agents = [SingleAgentSwatEnv(self.swat_s1_cps, i, 30) for i in range(1,4)]

        self._agent_ids = set(range(3))
        self.terminateds = set()
        self.truncateds = set()
        self.resetted = False
        self.operation_count = 0
        self.attacked = False

        # Define the observation space with an arbitrary high and low limit for simplicity
        low_limits = np.full((31,), -np.inf)  # Assuming negative values are not expected, but setting to -inf for generalization
        high_limits = np.full((31,), np.inf)  # Setting to inf to not limit the range artificially

        self.observation_space = gym.spaces.Box(low=low_limits, high=high_limits, dtype=np.float32)
        self.action_space = gym.spaces.Discrete(4)

        self.setup_traffic()

    def reset(self, *, seed=None, options=None):
        
        if self.attacked:
            self.stop_dos_attack('attacker')
        self.resetted = True
        self.terminateds = set()
        self.truncateds = set()
        self.info_dict = {}
        self.operation_count = 0
        self.attacked = False
        return {i: a.reset() for i, a in enumerate(self.agents)}, self.info_dict

    def step(self, action_dict):
        obs, rew, terminated, trunc, info = {}, {}, {}, {}, {}

        if self.is_attack_time():
            self.generate_dos_attack('sources', 'plc1')
            self.generate_dos_attack('sources', 'plc2')
            self.generate_dos_attack('sources', 'plc3')

        for i, action in action_dict.items():
            obs[i], rew[i], terminated[i], trunc[i], info[i] = self.agents[i].step(action)
            if terminated[i]:
                self.terminateds.add(i)

            if trunc[i]:
                self.truncateds.add(i)

        terminated["__all__"] = len(self.terminateds) == len(self.agents)
        trunc["__all__"] = len(self.truncateds) == len(self.agents)

        return obs, rew, terminated, trunc, info
    
    def render(self, mode='human'):
        print('Rendering the environment')

    def cli(self):
        CLI(self.swat_s1_cps.net)

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


    metadata = {
        "render.modes": ["rgb_array"],
    }


    