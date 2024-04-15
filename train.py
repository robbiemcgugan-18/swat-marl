from rl_envs.envs.ma_gym_env import MultiAgentSwatEnv
from rl_envs.envs.gym_env import SwatEnv
from ray.tune.registry import register_env
import gymnasium as gym
import os
import ray
from ray.rllib.algorithms.dqn.dqn import DQNConfig
import shutil
from ray import tune, air

def create_env(env_config={}):
    return MultiAgentSwatEnv()

def create_single_env(env_config={}):
    return SwatEnv(30)

def main():
    # env = create_single_env()

    # env.cli()
    checkpoint_root = "tmp/ppo/mininet_env"
    shutil.rmtree(checkpoint_root, ignore_errors=True, onerror=None)

    ray_results = "{}/Documents/Y5/new/ray_results/".format(os.getenv("HOME"))
    shutil.rmtree(ray_results, ignore_errors=True, onerror=None)

    ray.init(ignore_reinit_error=True)
    tune.register_env("swat_env-v0", create_single_env)

    config = DQNConfig()
    config = config.training(num_atoms=tune.grid_search([1,]))
    config = config.environment("swat_env-v0")

    tune.Tuner("DQN", run_config=air.RunConfig(stop={"training_iteration": 20}), param_space=config.to_dict(), ).fit()

    # tune.run("PPO", config={"env": "mininet_env-v0"}, stop={"training_iteration": 10})
    # select_env = "mininet_env-v0"
    # register_env(select_env, create_env)

    # config = ppo.DEFAULT_CONFIG.copy()
    # config["log_level"] = "WARN"
    # agent = ppo.PPOTrainer(config, env=select_env)

    # status = "{:2d} reward {:6.2f}/{:6.2f}/{:6.2f} len {:4.2f} saved {}"
    # n_iter = 5

    # for n in range(n_iter):
    #     result = agent.train()
    #     checkpoint_file = agent.save(checkpoint_root)

    #     print(status.format(
    #         n + 1,
    #         result["episode_reward_min"],
    #         result["episode_reward_mean"],
    #         result["episode_reward_max"],
    #         result["episode_len_mean"],
    #         checkpoint_file
    #     ))

    # policy = agent.get_policy()
    # model = policy.model
    # print(model.base_model.summary())

    # agent.restore(checkpoint_file)
    # env = gym.make(select_env)

    # state = env.reset()
    # sum_reward = 0
    # n_step = 20

    # for step in range(n_step):
    #     action = agent.compute_action(state)
    #     state, reward, done, info = env.step(action)
    #     sum_reward += reward

    #     env.render()

    #     if done == 1:
    #         print("cumulative reward", sum_reward)
    #         state = env.reset()
    #         sum_reward = 0

if __name__ == "__main__":
    main()

