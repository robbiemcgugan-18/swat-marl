import gymnasium as gym
import rl_envs

def run_one_episode(env, verbose=False):
    env.reset()
    sum_reward = 0

    for i in range(10):
        action = env.action_space.sample()

        if verbose:
            print(f"Step {i}: {action}")

        state, reward, done, info = env.step(action)
        sum_reward += reward

        if verbose:
            env.render()

        if done:
            if verbose:
                print(f"Episode finished after {i} steps")

            break

    if verbose:
        print(f"Total reward: {sum_reward}")

    return sum_reward

def main():
    env = gym.make("mininet_env-v0")
    sum_reward = run_one_episode(env, verbose=True)

    history = []

    for _ in range(1000):
        sum_reward = run_one_episode(env)
        history.append(sum_reward)

    avg_reward = sum(history) / len(history)
    print(f"Average reward: {avg_reward}")


if __name__ == "__main__":
    main()