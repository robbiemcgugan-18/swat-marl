from mininet.net import Mininet
from mininet.cli import CLI
from minicps.mcps import MiniCPS
from mininet.node import OVSController, RemoteController

from swat.topo import SwatTopo
from swat.run import SwatS1CPS

from .sa_gym_env import SingleAgentSwatEnv

import gymnasium as gym
from gymnasium.spaces import Dict, Discrete, Box
from ray.rllib.env.multi_agent_env import MultiAgentEnv
from mininet.cli import CLI

import sys
import subprocess

import numpy as np

class MultiAgentSwatEnv(MultiAgentEnv):

    def __init__(self, env, evaluate=False):
        super().__init__()


        print("STARTING MULTI AGENT SWAT ENVIRONMENT")
        self.env = env #SwatS1CPS(name='swat_s1')

        self.agents = [SingleAgentSwatEnv(self.env, i, 30) for i in range(1,3)]

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
        self.action_space = gym.spaces.Discrete(21)

        self.setup_traffic()

        if evaluate:
            print("Evaluating the environment")
            self.generate_dos_attack('attacker', 'plc1')
            self.generate_dos_attack('attacker', 'plc2')
            # self.generate_dos_attack('attacker', 'plc3')

    def reset(self, *, seed=None, options=None):
        
        if self.attacked:
            self.stop_dos_attack('attacker')
        self.resetted = True
        self.terminateds = set()
        self.truncateds = set()
        self.info_dict = {}
        self.operation_count = 0
        self.attacked = False

        s1 = self.env.net.get('s1')
        s1.dpctl('del-flows')

        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=1,actions=output:2,3,4,5')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=2,actions=output:1,3,4,5')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=3,actions=output:1,2,4,5')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=4,actions=output:1,2,3,5')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=5,actions=output:1,2,3,4')

        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=1,actions=output:2,3,4,5')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=2,actions=output:1,3,4,5')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=3,actions=output:1,2,4,5')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=4,actions=output:1,2,3,5')
        # s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=5,actions=output:1,2,3,4')

        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=1,actions=output:2,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=2,actions=output:1,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=3,actions=output:1,2,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,ip,in_port=4,actions=output:1,2,3')

        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=1,actions=output:2,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=2,actions=output:1,3,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=3,actions=output:1,2,4')
        s1.cmd('ovs-ofctl --protocols=OpenFlow13 add-flow s1 priority=10,arp,in_port=4,actions=output:1,2,3')

        return {i: a.reset() for i, a in enumerate(self.agents)}, self.info_dict

    def step(self, action_dict):
        obs, rew, terminated, trunc, info = {}, {}, {}, {}, {}

        if self.is_attack_time():
            self.generate_dos_attack('attacker', 'plc1')
            self.generate_dos_attack('attacker', 'plc2')
            # self.generate_dos_attack('attacker', 'plc3')

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
        CLI(self.env.net)

    def is_attack_time(self):
        self.operation_count += 1
        if self.operation_count >= 5 and not self.attacked:
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
        target_ip = self.env.net.get(target).IP()
        # source.cmd(sys.executable + ' -u ' + f'rl_envs/rl_envs/envs/dos.py {target_ip} &')
        source.cmd(f'hping3 -2 --flood --rand-source -q --interval u1000 {target_ip} > /tmp/{source_host}_hping3.log 2>&1 &')
        print(f'High TCP traffic generation started from {source_host} to {target_ip}')


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
        # plc3_ip = self.env.net.get('plc3').IP()

        self.generate_tcp_traffic('sources', plc1_ip)
        self.generate_tcp_traffic('sources', plc2_ip)
        # self.generate_tcp_traffic('sources', plc3_ip)


    metadata = {
        "render.modes": ["rgb_array"],
    }


    