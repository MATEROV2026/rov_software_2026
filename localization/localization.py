import numpy as np
import matplotlib.pyplot as plt

def generate_environment(n, num_obstacles):
    state = np.array([
        np.random.uniform(0, n),
        np.random.uniform(0, n),
        np.random.uniform(-np.pi, np.pi),
    ])

    obstacles = np.array([
        np.array([
            np.random.randint(1, n),
            np.random.randint(1, n),
        ])
        for _ in range(num_obstacles)
    ])
    return state, obstacles

def plot_env(state, obstacles, trajectories=None):
    plt.plot(state[0], state[1], marker='o', color='r', label='state')
    plt.plot(obstacles[:, 0], obstacles[:, 1], marker='x', color='b', label='obstacles', linestyle='none')
    if trajectories is not None:
        colors = ['#000000', '#FFFF00']
        for idx, trajectory in enumerate(trajectories):
            plt.plot(trajectory[:, 0], trajectory[:, 1], marker='.', color=colors[idx % 2], label='trajectory')
    plt.xlim(0, 10)
    plt.ylim(0, 10)
    plt.grid(True)
    plt.show()

def get_observation(state, obstacles):
    sigma_r = 0.1
    sigma_phi = 0.05
    r_true = np.array([
        np.linalg.norm(state[0:2] - obstacles[i])
        for i in range(len(obstacles))
    ])
    phi_true = np.array([
        (np.arctan2(obstacles[i, 1] - state[1], obstacles[i, 0] - state[0]) - state[2] + np.pi)
        % (2 * np.pi) - np.pi
        for i in range(len(obstacles))
    ])
    r_measured = r_true + np.random.normal(0, sigma_r, size=len(r_true))
    phi_measured = phi_true + np.random.normal(0, sigma_phi, size=len(phi_true))
    return np.concatenate((r_measured, phi_measured))

def motion_model(state, control, dt):
    x, y, theta = state
    v, omega = control

    new_state = np.array([
        x + v * np.cos(theta) * dt,
        y + v * np.sin(theta) * dt,
        theta + omega * dt
    ])
    new_state[2] = (new_state[2] + np.pi) % (2 * np.pi) - np.pi
    return new_state

def main():
    init_state, obstacles = generate_environment(10, 2)
    control = np.array([1.0, 0.2])
    dt = 0.1
    true_trajectory = []
    estimated_trajectory = []
    true_state = init_state
    estimated_state = init_state
    true_control = control + np.random.normal(
        0,
        [0.05, 0.02]
    )

    for _ in range(100):
        true_state = motion_model(true_state, true_control, dt)
        estimated_state = motion_model(estimated_state, control, dt)
        true_trajectory.append(true_state)
        estimated_trajectory.append(estimated_state)
    trajectories = np.array([np.array(true_trajectory), np.array(estimated_trajectory)])
    plot_env(init_state, obstacles, trajectories)


if __name__ == '__main__':
    main()