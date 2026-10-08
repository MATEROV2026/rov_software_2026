"""Correction step for localization.py: an extended Kalman filter (EKF).

Dead reckoning (motion_model with the commanded control) drifts. The EKF
also predicts with motion_model, then corrects with the noisy landmark
range/bearing readings from get_observation(), so the estimate stays near
the true path. It reuses localization.py's models and noise levels as is.

    python localization/ekf.py                 # one run, plot in localization/runs/
    python localization/ekf.py --runs 200      # statistics over 200 random worlds
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Ellipse  # noqa: E402

from localization import generate_environment, get_observation, motion_model  # noqa: E402

SIGMA_R, SIGMA_PHI = 0.1, 0.05      # get_observation()'s sensor noise
SIGMA_V, SIGMA_OMEGA = 0.05, 0.02   # main()'s control noise on the true path
OUT = Path(__file__).resolve().parent / 'runs'


def wrap(angle):
    return (angle + np.pi) % (2 * np.pi) - np.pi


class EKF:
    """State [x, y, theta]; unicycle motion; range/bearing to known landmarks."""

    def __init__(self, state, landmarks, covariance):
        self.x = np.array(state, dtype=float)
        self.P = np.array(covariance, dtype=float)
        self.landmarks = np.asarray(landmarks, dtype=float)
        n = len(self.landmarks)
        self.R = np.diag([SIGMA_R ** 2] * n + [SIGMA_PHI ** 2] * n)  # same order as get_observation

    def predict(self, control, dt):
        v = control[0]
        theta = self.x[2]
        F = np.array([[1.0, 0.0, -v * np.sin(theta) * dt],   # d(motion) / d(state)
                      [0.0, 1.0, v * np.cos(theta) * dt],
                      [0.0, 0.0, 1.0]])
        G = np.array([[np.cos(theta) * dt, 0.0],             # d(motion) / d(control)
                      [np.sin(theta) * dt, 0.0],
                      [0.0, dt]])
        self.x = motion_model(self.x, control, dt)
        self.P = F @ self.P @ F.T + G @ np.diag([SIGMA_V ** 2, SIGMA_OMEGA ** 2]) @ G.T

    def expected(self, x):
        """What get_observation() would return, noise-free, if the robot were at x."""
        d = self.landmarks - x[:2]
        r = np.hypot(d[:, 0], d[:, 1])
        return np.concatenate((r, wrap(np.arctan2(d[:, 1], d[:, 0]) - x[2]))), d, r

    def jacobian(self, x):
        _, d, r = self.expected(x)
        n = len(self.landmarks)
        H = np.zeros((2 * n, len(x)))
        H[:n, 0], H[:n, 1] = -d[:, 0] / r, -d[:, 1] / r                       # ranges
        H[n:, 0], H[n:, 1], H[n:, 2] = d[:, 1] / r ** 2, -d[:, 0] / r ** 2, -1.0  # bearings
        return H

    def update(self, z):
        z_hat, _, _ = self.expected(self.x)
        n = len(self.landmarks)
        H = self.jacobian(self.x)
        innovation = z - z_hat
        innovation[n:] = wrap(innovation[n:])  # 179° vs -179° is a 2° error, not 358°
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ innovation
        self.x[2] = wrap(self.x[2])
        I_KH = np.eye(len(self.x)) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ self.R @ K.T  # Joseph form keeps P symmetric


class BiasEKF(EKF):
    """Also estimates a constant speed / turn-rate offset, which is what
    main() simulates: state [x, y, theta, speed offset, turn-rate offset]."""

    def __init__(self, state, landmarks, covariance, offset_sigma=(0.15, 0.06)):
        super().__init__(state, landmarks, covariance)
        self.x = np.concatenate((self.x, [0.0, 0.0]))
        P = np.zeros((5, 5))
        P[:3, :3] = self.P
        P[3, 3], P[4, 4] = np.square(offset_sigma)
        self.P = P

    def predict(self, control, dt):
        v, omega = control[0] + self.x[3], control[1] + self.x[4]
        theta = self.x[2]
        F = np.eye(5)
        F[0, 2], F[1, 2] = -v * np.sin(theta) * dt, v * np.cos(theta) * dt
        F[0, 3], F[1, 3], F[2, 4] = np.cos(theta) * dt, np.sin(theta) * dt, dt
        G = np.array([[np.cos(theta) * dt, 0.0], [np.sin(theta) * dt, 0.0], [0.0, dt], [0, 0], [0, 0]])
        Q = G @ np.diag([SIGMA_V ** 2, SIGMA_OMEGA ** 2]) @ G.T + np.diag([0, 0, 0, 1e-6, 1e-6])
        self.x[:3] = motion_model(self.x[:3], (v, omega), dt)
        self.P = F @ self.P @ F.T + Q


def run(seed, steps=100, dt=0.1, observe_every=1, initial_error=(0.0, 0.0, 0.0), random_walk=False,
        estimate_offset=False):
    """One simulation shaped like localization.main(): true path, dead reckoning, EKF."""
    np.random.seed(seed)
    start, landmarks = generate_environment(10, 2)
    control = np.array([1.0, 0.2])
    bias = control + np.random.normal(0, [SIGMA_V, SIGMA_OMEGA])  # main(): drawn once
    guess = start + np.array(initial_error)
    spread = np.maximum(np.abs(initial_error), 0.1)
    ekf = (BiasEKF if estimate_offset else EKF)(guess, landmarks, np.diag(spread ** 2))
    true, dead = start.copy(), guess.copy()
    log = {k: [] for k in ('true', 'dead', 'ekf', 'P')}
    for step in range(steps):
        actual = control + np.random.normal(0, [SIGMA_V, SIGMA_OMEGA]) if random_walk else bias
        true = motion_model(true, actual, dt)
        dead = motion_model(dead, control, dt)
        ekf.predict(control, dt)
        if step % observe_every == 0:
            ekf.update(get_observation(true, landmarks))
        for key, value in (('true', true), ('dead', dead), ('ekf', ekf.x[:3].copy()), ('P', ekf.P[:3, :3].copy())):
            log[key].append(value)
    out = {k: np.array(v) for k, v in log.items()}
    out.update(start=start, landmarks=landmarks)
    return out


def position_error(result, key):
    return np.hypot(*(result[key][:, :2] - result['true'][:, :2]).T)


def inside_2_sigma(result):
    """Share of steps where the truth lies inside the EKF's 2-sigma ellipse (ideal ~86%)."""
    hits = 0
    for est, true, P in zip(result['ekf'], result['true'], result['P']):
        e = true[:2] - est[:2]
        hits += e @ np.linalg.inv(P[:2, :2]) @ e <= 4.0
    return hits / len(result['ekf'])


def plot(result, path):
    fig, (ax, ax_err) = plt.subplots(1, 2, figsize=(12, 5))
    ax.plot(*result['landmarks'].T, 'bx', markersize=10, mew=2, label='landmarks')
    ax.plot(*result['start'][:2], 'ro', label='start')
    ax.plot(*result['true'][:, :2].T, 'k-', lw=2, label='true path')
    ax.plot(*result['dead'][:, :2].T, '--', color='#e67e22', lw=2, label='dead reckoning (current code)')
    ax.plot(*result['ekf'][:, :2].T, '-', color='#2e86c1', lw=1.5, label='EKF estimate')
    for est, P in zip(result['ekf'][::10], result['P'][::10]):
        values, vectors = np.linalg.eigh(P[:2, :2])
        angle = np.degrees(np.arctan2(vectors[1, 1], vectors[0, 1]))
        ax.add_patch(Ellipse(est[:2], 4 * np.sqrt(values[1]), 4 * np.sqrt(values[0]), angle=angle,
                             fill=False, color='#2e86c1', alpha=0.6))
    ax.set_aspect('equal')
    ax.grid(True)
    ax.legend(loc='best', fontsize=9)
    ax.set_title('Paths (ellipses: EKF 2σ uncertainty, every 1 s)')
    t = np.arange(1, len(result['true']) + 1) * 0.1
    ax_err.plot(t, position_error(result, 'dead'), '--', color='#e67e22', lw=2, label='dead reckoning')
    ax_err.plot(t, position_error(result, 'ekf'), color='#2e86c1', lw=2, label='EKF')
    bound = 2 * np.sqrt(result['P'][:, 0, 0] + result['P'][:, 1, 1])
    ax_err.fill_between(t, 0, bound, color='#2e86c1', alpha=0.12, label='EKF 2σ bound')
    ax_err.set_xlabel('time (s)')
    ax_err.set_ylabel('position error (m)')
    ax_err.grid(True)
    ax_err.legend(fontsize=9)
    ax_err.set_title('Position error')
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--runs', type=int, default=0, help='statistics over this many seeds')
    parser.add_argument('--offset', action='store_true', help='single run with the offset-estimating EKF')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if not args.runs:
        result = run(args.seed, estimate_offset=args.offset)
        name = OUT / f"ekf{'_offset' if args.offset else ''}_seed{args.seed}.png"
        plot(result, name)
        print(f"final error: dead reckoning {position_error(result, 'dead')[-1]:.2f} m, "
              f"EKF {position_error(result, 'ekf')[-1]:.2f} m  ->  {name}")
        return
    cases = [
        ("as in main() (constant drift, sighting every step)", {}),
        ('  + estimate the offset', {'estimate_offset': True}),
        ('start 1 m and 17° off', {'initial_error': (1.0, -1.0, 0.3)}),
        ('  + estimate the offset', {'initial_error': (1.0, -1.0, 0.3), 'estimate_offset': True}),
        ('sightings once per second', {'observe_every': 10}),
        ('  + estimate the offset', {'observe_every': 10, 'estimate_offset': True}),
        ('random (not constant) control noise', {'random_walk': True}),
        ('  + estimate the offset', {'random_walk': True, 'estimate_offset': True}),
    ]
    print(f"{'case':<52}{'dead reckoning':>16}{'EKF':>14}{'truth in 2σ':>14}")
    print(f"{'':<52}{'RMS / worst (m)':>16}{'RMS / worst':>14}{'(ideal 86%)':>14}")
    for name, kwargs in cases:
        stats = {'dead': [], 'ekf': [], 'cover': []}
        for seed in range(args.runs):
            result = run(seed, **kwargs)
            stats['dead'].append(position_error(result, 'dead'))
            stats['ekf'].append(position_error(result, 'ekf'))
            stats['cover'].append(inside_2_sigma(result))
        d, e = np.concatenate(stats['dead']), np.concatenate(stats['ekf'])
        print(f"{name:<52}{np.sqrt(np.mean(d ** 2)):>8.2f} / {d.max():<5.2f}"
              f"{np.sqrt(np.mean(e ** 2)):>7.2f} / {e.max():<5.2f}{np.mean(stats['cover']):>10.0%}")


if __name__ == '__main__':
    main()
