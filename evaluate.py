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

def create_env(env_config={}):
    env = SwatS1CPS('swat_s1')
    return MultiAgentSwatEnv(env, evaluate=True)

ray.init(ignore_reinit_error=True)
tune.register_env("swat_env-v0", create_env)

# Use the Algorithm's `from_checkpoint` utility to get a new algo instance
# that has the exact same state as the old one, from which the checkpoint was
# created in the first place:
dqn_alg = Algorithm.from_checkpoint('/home/robbiemcgugan/DQN_swat_env-v0_32b6f_00000_0_num_atoms=1_2024-04-17_21-29-32/checkpoint_000000')

# Optionally configure evaluation settings if they were not set during training
dqn_alg.config["evaluation_interval"] = 3
dqn_alg.config["evaluation_num_episodes"] = 100
dqn_alg.config["evaluation_config"] = {
    # You can adjust settings that are specific to evaluation here
    "explore": False  # For example, turn off exploration during evaluation
}

# Evaluate the algorithm
evaluation_results = dqn_alg.evaluate()

# Print the evaluation results
print("Evaluation Results:", evaluation_results)

# Shutdown Ray
ray.shutdown()

a = dqn_alg.evaluate()

print(a)