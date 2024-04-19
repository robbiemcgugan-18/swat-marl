from ray.rllib.algorithms.algorithm import Algorithm
from rl_envs.envs.ma_gym_env import MultiAgentSwatEnv
from rl_envs.envs.gym_env import SwatEnv
from ray.tune.registry import register_env
import gymnasium as gym
import os
import ray
from ray.rllib.algorithms.dqn.dqn import DQNConfig
import shutil
from ray import tune
from swat.run import SwatS1CPS
import numpy as np

def create_env(env_config={}):
    env = SwatS1CPS('swat_s1')
    return MultiAgentSwatEnv(env, evaluate=True)

def create_single_env(env_config={}):
    return SwatEnv(10)

ray.init(ignore_reinit_error=True)
tune.register_env("swat_env-v0", create_env)

# Use the Algorithm's `from_checkpoint` utility to get a new algo instance
# that has the exact same state as the old one, from which the checkpoint was
# created in the first place:
PATH = '/home/robbiemcgugan/DQN_swat_env-v0_32b6f_00000_0_num_atoms=1_2024-04-17_21-29-32/checkpoint_000000'
dqn_alg = Algorithm.from_checkpoint(PATH)

# Optionally configure evaluation settings if they were not set during training
dqn_alg.config["evaluation_interval"] = 3
dqn_alg.config["evaluation_num_episodes"] = 100
dqn_alg.config["evaluation_config"] = {
    # You can adjust settings that are specific to evaluation here
    "explore": False  # For example, turn off exploration during evaluation
}

# Number of evaluations
num_evaluations = 5

# Store the rewards for each evaluation
rewards = []

for i in range(num_evaluations):
    print("Evaluation Number:", i)
    # Evaluate the algorithm
    evaluation_results = dqn_alg.evaluate()

    # Get the reward from the evaluation results
    reward = evaluation_results['evaluation']['sampler_results']['episode_reward_mean']

    # Add the reward to the list
    rewards.append(reward)

# Calculate the average reward
average_reward = np.mean(rewards)

# Calculate the standard deviation of the rewards
reward_std = np.std(rewards)

# Print the average reward and standard deviation
print("Average Reward:", average_reward)
print("Reward Standard Deviation:", reward_std)

# Shutdown Ray
ray.shutdown()