from gym.envs.registration import register

register(
    id='mininet_env-v0',
    entry_point='rl_envs.envs:MininetEnv',
)

register(
    id='swat_env-v0',
    entry_point='rl_envs.envs:SwatEnv',
)