"""ROV-like localization: the EKF prototype reshaped for our vehicle.

Changes from localization.py's 2-D unicycle:
- surge, sway and heave: the vectored thrusters can strafe. These are
  commands; nothing on the ROV measures its speed.
- heading from the IMU's gyro, which has an unknown bias. The ICM-20649 has
  no magnetometer, so nothing else knows which way is north.
- depth measured directly by the pressure sensor.
- sightings from the ZED: the 3-D position of a known marker relative to
  the camera, only inside its field of view and range, noisier far away.
- or, with no markers, pose fixes from finding camera frames in a COLMAP map
  of the walls (MapCamera; colmap_map.py measures their error on real photos).
- a water current that pushes the ROV, as in 2026 task 1.3.

Anything constant that the ROV cannot measure is part of the state, so it
gets estimated: the current, the gyro bias, and how far the real surge/sway
speed is from the commanded speed. The ROV steers by its own estimate, so the
comparison that matters is where it really goes.

State: [x, y, depth, heading, current_x, current_y, gyro_bias, surge_scale, sway_scale]

    python localization/rov_ekf.py              # survey + station-keeping plot
    python localization/rov_ekf.py --runs 100   # statistics over random pools
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

DT = 0.1                          # 10 Hz, like the IMU and camera topics
POOL = (12.0, 8.0)                # m; east wall at x = 12, north wall at y = 8
CAMERA_HALF_FOV = np.radians(45)  # forward ZED, narrowed by water
CAMERA_HALF_VFOV = np.radians(35)
CAMERA_RANGE = 8.0                # m of usable pool visibility
SIGMA_DEPTH = 0.02                # m, pressure sensor
SIGMA_GYRO = 0.005                # rad/s
SIGMA_WATER = 0.02                # m/s of turbulence on top of the steady current
MAX_SPEED = 0.3                   # m/s
GATE = 11.34                      # chi-squared, 3 dof, 99%: reject wild sightings
MIN_WALL_IN_VIEW = 8              # 0.5 m squares of mapped wall a map fix needs (2 m²)
OUT = Path(__file__).resolve().parent / 'runs'


def wrap(angle):
    return (angle + np.pi) % (2 * np.pi) - np.pi


def rot(heading):
    c, s = np.cos(heading), np.sin(heading)
    return np.array([[c, -s], [s, c]])


def sighting_sigma(distance):
    """Stereo depth error grows with the square of the distance."""
    return 0.01 + 0.004 * distance ** 2


def relative(position, heading, marker):
    """Marker in the ROV frame: forward, left, deeper."""
    d = marker - position
    return np.concatenate((rot(heading).T @ d[:2], [d[2]]))


def visible(rel):
    """For one sighting (3,) or many (n, 3)."""
    forward, left, down = np.moveaxis(np.asarray(rel), -1, 0)
    return ((forward > 0) & (np.linalg.norm(rel, axis=-1) <= CAMERA_RANGE)
            & (np.abs(np.arctan2(left, forward)) <= CAMERA_HALF_FOV)
            & (np.abs(np.arctan2(down, np.hypot(forward, left))) <= CAMERA_HALF_VFOV))


# Mapped texture (tiles, props) on the east and north walls, one point per 0.5 m square.
WALL_TEXTURE = np.array([(POOL[0], y, z) for y in np.arange(0.25, POOL[1], 0.5) for z in np.arange(0.75, 4.5, 0.5)]
                        + [(x, POOL[1], z) for x in np.arange(0.25, POOL[0], 0.5) for z in np.arange(0.75, 4.5, 0.5)])
MAP_ORIGIN = np.array(POOL)       # the corner where the map is pinned to the pool


@dataclass
class MapCamera:
    """Pose fixes from finding camera frames in a COLMAP map of the walls
    (colmap_map.py). A fix needs enough mapped wall in view, and its error is
    a share of the distance to the wall: 0.12% per axis on the real photos
    (in air), rounded up here."""
    error: float = 0.002                    # per axis, share of the distance to the wall
    heading_error: float = np.radians(0.1)
    scale_error: float = 0.0                # map built this share too big: fixes stretch away from MAP_ORIGIN
    every: int = 5                          # one fix every 5 frames: 2 Hz

    def fix(self, position, heading, rng):
        """Measured (x, y, heading) and its covariance; None with too little mapped wall in view."""
        d = WALL_TEXTURE - position
        rel = np.column_stack((d[:, :2] @ rot(heading), d[:, 2]))
        seen = visible(rel)
        if seen.sum() < MIN_WALL_IN_VIEW:
            return None
        sigma = self.error * np.median(np.linalg.norm(rel[seen], axis=1))
        xy = MAP_ORIGIN + (1 + self.scale_error) * (position[:2] - MAP_ORIGIN) + rng.normal(0, sigma, 2)
        measured = np.array([*xy, wrap(heading + rng.normal(0, self.heading_error))])
        return measured, np.diag([sigma ** 2, sigma ** 2, self.heading_error ** 2])


@dataclass
class World:
    markers: np.ndarray   # (n, 3) known marker positions (z = depth)
    current: np.ndarray   # (2,) steady water current, world frame, m/s
    scale: np.ndarray     # (2,) real / commanded surge and sway speed
    gyro_bias: float      # rad/s


def make_world(rng, current_speed=0.15):
    east = [(POOL[0], y, z) for y in (1.5, 4.0, 6.5) for z in (1.5, 3.5)]
    north = [(x, POOL[1], 2.5) for x in (3.0, 6.0, 9.0)]
    angle = rng.uniform(-np.pi, np.pi)
    return World(np.array(east + north, dtype=float),
                 current_speed * np.array([np.cos(angle), np.sin(angle)]),
                 rng.uniform(0.8, 1.2, 2), rng.normal(0, 0.01))


class RovEKF:
    N = 9

    def __init__(self, position, heading):
        self.x = np.zeros(self.N)
        self.x[:3], self.x[3] = position, heading
        self.P = np.diag([0.1, 0.1, 0.05, 0.05, 0.2, 0.2, 0.02, 0.25, 0.25]) ** 2

    position = property(lambda self: self.x[:3])
    heading = property(lambda self: self.x[3])
    current = property(lambda self: self.x[4:6])

    def motion(self, x, command, gyro, dt):
        u, v, w = command
        new = x.copy()
        speed = np.array([u * (1 + x[7]), v * (1 + x[8])])
        new[:2] = x[:2] + (rot(x[3]) @ speed + x[4:6]) * dt
        new[2] = x[2] + w * dt
        new[3] = wrap(x[3] + (gyro - x[6]) * dt)
        return new

    def motion_jacobian(self, command, dt):
        u, v, _ = command
        psi, su, sv = self.x[3], 1 + self.x[7], 1 + self.x[8]
        c, s = np.cos(psi), np.sin(psi)
        F = np.eye(self.N)
        F[0, 3], F[1, 3] = (-su * u * s - sv * v * c) * dt, (su * u * c - sv * v * s) * dt
        F[0, 4] = F[1, 5] = dt
        F[3, 6] = -dt
        F[0, 7], F[1, 7] = c * u * dt, s * u * dt
        F[0, 8], F[1, 8] = -s * v * dt, c * v * dt
        return F

    def predict(self, command, gyro, dt):
        F = self.motion_jacobian(command, dt)
        Q = np.zeros((self.N, self.N))
        Q[:2, :2] = np.eye(2) * (SIGMA_WATER * dt) ** 2
        Q[2, 2] = (0.01 * dt) ** 2
        Q[3, 3] = (SIGMA_GYRO * dt) ** 2
        Q[4, 4] = Q[5, 5] = 0.003 ** 2 * dt    # the current changes slowly
        Q[6, 6] = 1e-4 ** 2 * dt               # the gyro bias, more slowly still
        Q[7, 7] = Q[8, 8] = 0.002 ** 2 * dt
        self.x = self.motion(self.x, command, gyro, dt)
        self.P = F @ self.P @ F.T + Q

    def marker_jacobian(self, x, marker):
        d = marker - x[:3]
        c, s = np.cos(x[3]), np.sin(x[3])
        forward, left = c * d[0] + s * d[1], -s * d[0] + c * d[1]
        H = np.zeros((3, self.N))
        H[0, 0], H[0, 1], H[0, 3] = -c, -s, left
        H[1, 0], H[1, 1], H[1, 3] = s, -c, -forward
        H[2, 2] = -1.0
        return H

    def _update(self, innovation, H, R, gate=None):
        S = H @ self.P @ H.T + R
        if gate is not None and innovation @ np.linalg.solve(S, innovation) > gate:
            return False
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ innovation
        self.x[3] = wrap(self.x[3])
        I_KH = np.eye(self.N) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T
        return True

    def update_depth(self, depth):
        H = np.zeros((1, self.N))
        H[0, 2] = 1.0
        self._update(np.array([depth - self.x[2]]), H, np.array([[SIGMA_DEPTH ** 2]]))

    def update_marker(self, marker, measured):
        expected = relative(self.x[:3], self.x[3], marker)
        R = np.eye(3) * sighting_sigma(np.linalg.norm(expected)) ** 2
        return self._update(measured - expected, self.marker_jacobian(self.x, marker), R, GATE)

    def update_fix(self, measured, R):
        """A pose fix from the map camera: x, y and heading. (The depth sensor beats its depth.)"""
        H = np.zeros((3, self.N))
        H[0, 0] = H[1, 1] = H[2, 3] = 1.0
        innovation = measured - self.x[[0, 1, 3]]
        innovation[2] = wrap(innovation[2])
        return self._update(innovation, H, R, GATE)


class DeadReckoning:
    """What the ROV knows without sightings: commands, gyro, depth sensor."""

    def __init__(self, position, heading):
        self.position, self.heading = np.array(position, dtype=float), heading
        self.current = np.zeros(2)

    def predict(self, command, gyro, dt):
        self.position[:2] += rot(self.heading) @ np.array(command[:2]) * dt
        self.heading = wrap(self.heading + gyro * dt)

    def update_depth(self, depth):
        self.position[2] = depth


def simulate(world, rng, waypoints, heading=0.0, hold_s=0.0, use_ekf=True, max_s=300.0, sight_every=1,
             camera=None):
    """Fly the waypoints (or hold the first one for hold_s) steering by the estimate.
    sight_every: camera updates every n steps (1 = 10 Hz).
    camera: a MapCamera, to correct with map fixes instead of marker sightings."""
    waypoints = np.asarray(waypoints, dtype=float)
    true_pos, true_heading = waypoints[0].copy(), heading
    est = RovEKF(true_pos, heading) if use_ekf else DeadReckoning(true_pos, heading)
    target = 0 if hold_s else 1
    log = {'t': [], 'true': [], 'est': [], 'current': [], 'seen': []}
    t = 0.0
    while t < (hold_s or max_s):
        wp = waypoints[target]
        # Guidance: head for the waypoint, cancelling the current we think there is.
        world_vel = 0.6 * (wp[:2] - est.position[:2]) - est.current
        if np.linalg.norm(world_vel) > MAX_SPEED:
            world_vel *= MAX_SPEED / np.linalg.norm(world_vel)
        surge, sway = rot(est.heading).T @ world_vel
        heave = np.clip(0.6 * (wp[2] - est.position[2]), -0.2, 0.2)
        turn = np.clip(1.0 * wrap(heading - est.heading), -0.3, 0.3)
        command = (surge, sway, heave)

        # The real ROV: the speed it actually gets, plus the current.
        true_pos[:2] += (rot(true_heading) @ (world.scale * np.array([surge, sway]))
                         + world.current + rng.normal(0, SIGMA_WATER, 2)) * DT
        true_pos[2] += heave * DT + rng.normal(0, 0.002)
        true_turn = turn + rng.normal(0, 0.002)
        true_heading = wrap(true_heading + true_turn * DT)

        est.predict(command, true_turn + world.gyro_bias + rng.normal(0, SIGMA_GYRO), DT)
        est.update_depth(true_pos[2] + rng.normal(0, SIGMA_DEPTH))
        seen = 0
        if use_ekf and camera is not None:
            fix = camera.fix(true_pos, true_heading, rng) if round(t / DT) % camera.every == 0 else None
            seen = int(fix is not None and est.update_fix(*fix))
        elif use_ekf and round(t / DT) % sight_every == 0:
            for marker in world.markers:
                rel = relative(true_pos, true_heading, marker)
                if visible(rel):
                    seen += est.update_marker(marker, rel + rng.normal(0, sighting_sigma(np.linalg.norm(rel)), 3))
        t += DT
        for key, value in (('t', t), ('true', true_pos.copy()), ('est', np.array(est.position).copy()),
                           ('current', np.array(est.current).copy()), ('seen', seen)):
            log[key].append(value)
        if not hold_s and np.linalg.norm(wp[:2] - est.position[:2]) < 0.25:
            target += 1
            if target == len(waypoints):
                break
    return {k: np.array(v) for k, v in log.items()}


# Lawnmower at 2.5 m depth: lanes from x = 5 to 10, alternating direction.
SURVEY = [(5.0, 1.5, 2.5), (10.0, 1.5, 2.5), (10.0, 3.0, 2.5), (5.0, 3.0, 2.5),
          (5.0, 4.5, 2.5), (10.0, 4.5, 2.5), (10.0, 6.0, 2.5), (5.0, 6.0, 2.5)]
STATION = [(8.0, 4.0, 2.5)]


def cross_track(points, plan):
    """Distance from each point to the planned path (a polyline)."""
    plan = np.asarray(plan)[:, :2]
    best = np.full(len(points), np.inf)
    for a, b in zip(plan[:-1], plan[1:]):
        ab = b - a
        t = np.clip(((points[:, :2] - a) @ ab) / (ab @ ab), 0, 1)
        best = np.minimum(best, np.linalg.norm(points[:, :2] - (a + t[:, None] * ab), axis=1))
    return best


# How the ROV works out where it is: name -> simulate() arguments.
SETUPS = {'dead reckoning': {'use_ekf': False},
          'EKF + 9 wall markers': {},
          'EKF + COLMAP map fixes': {'camera': MapCamera()},
          '  map fixes 10x worse': {'camera': MapCamera(error=0.02, heading_error=np.radians(1.0))},
          '  map 2% too big': {'camera': MapCamera(scale_error=0.02)}}


def plot(seed, path):
    fig, (ax_survey, ax_hold) = plt.subplots(1, 2, figsize=(13, 6.4))
    world = make_world(np.random.default_rng(seed))
    for ax in (ax_survey, ax_hold):
        ax.plot([0, POOL[0], POOL[0], 0, 0], [0, 0, POOL[1], POOL[1], 0], color='#7f8c8d', lw=1)
        ax.plot([POOL[0], POOL[0], 0], [0, POOL[1], POOL[1]], color='#27ae60', lw=7, alpha=0.25,
                solid_capstyle='butt', label='walls in the COLMAP map')
        ax.plot(*world.markers[:, :2].T, 'k^', markersize=8, label='ZED markers (walls)')
        ax.annotate('', xy=(2.0 + 6 * world.current[0], 1.0 + 6 * world.current[1]), xytext=(2.0, 1.0),
                    arrowprops={'arrowstyle': '->', 'color': '#16a085', 'lw': 2})
        ax.text(2.0, 0.4, f'current {np.linalg.norm(world.current):.2f} m/s', color='#16a085', fontsize=9)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.4)
    plan = np.array(SURVEY)
    ax_survey.plot(*plan[:, :2].T, '--', color='#95a5a6', lw=2, label='planned lanes')
    notes = {'survey': [], 'hold': []}
    for label, colour, style in (('dead reckoning', '#e67e22', '-'), ('EKF + 9 wall markers', '#2e86c1', '-'),
                                 ('EKF + COLMAP map fixes', '#27ae60', '--')):
        run = simulate(world, np.random.default_rng(seed + 1), SURVEY, **SETUPS[label])
        ax_survey.plot(*run['true'][:, :2].T, style, color=colour, lw=1.8, label=f'steering by {label} (true path)')
        notes['survey'].append(f'{label}: off the lanes by {np.sqrt(np.mean(cross_track(run["true"], SURVEY) ** 2)):.2f} m RMS')
        hold = simulate(world, np.random.default_rng(seed + 2), STATION, hold_s=40.0, **SETUPS[label])
        ax_hold.plot(*hold['true'][:, :2].T, style, color=colour, lw=1.8, label=f'steering by {label} (true path)')
        worst = np.linalg.norm(hold['true'][:, :2] - np.array(STATION[0][:2]), axis=1).max()
        notes['hold'].append(f'{label}: up to {worst:.2f} m from the target')
    for ax, key in ((ax_survey, 'survey'), (ax_hold, 'hold')):
        ax.text(0.98, 0.03, '\n'.join(notes[key]), transform=ax.transAxes, ha='right', va='bottom',
                fontsize=9, bbox={'facecolor': 'white', 'alpha': 0.85, 'edgecolor': '#cccccc'})
    ax_survey.set_title('Lawnmower survey at 2.5 m depth')
    ax_survey.legend(loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=2, fontsize=8)
    ax_hold.plot(*STATION[0][:2], 'rx', markersize=12, mew=3, label='target')
    ax_hold.add_patch(plt.Circle(STATION[0][:2], 0.25, fill=False, color='r', ls=':'))
    ax_hold.set_title('Hold position for 40 s (task 1.3); dotted circle 0.25 m')
    ax_hold.legend(loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def statistics(runs):
    print(f"{'over ' + str(runs) + ' random pools':<26}{'survey: path error':>20}{'finished':>10}"
          f"{'hold 30 s':>11}{'hold: worst':>13}{'current':>10}")
    print(f"{'':<26}{'RMS / worst (m)':>20}{'in 300 s':>10}{'≤ 0.25 m':>11}{'median (m)':>13}{'error':>10}")
    for name, setup in SETUPS.items():
        mean_square, worst_path, finished, worst_hold, current = [], [], [], [], []
        for seed in range(runs):
            world = make_world(np.random.default_rng(seed))
            survey = simulate(world, np.random.default_rng(seed + 1), SURVEY, **setup)
            err = cross_track(survey['true'], SURVEY)
            mean_square.append(np.mean(err ** 2))
            worst_path.append(err.max())
            finished.append(survey['t'][-1] < 299.9)
            hold = simulate(world, np.random.default_rng(seed + 2), STATION, hold_s=40.0, **setup)
            window = (hold['t'] > 10) & (hold['t'] <= 40)
            worst_hold.append(np.linalg.norm(hold['true'][window, :2] - np.array(STATION[0][:2]), axis=1).max())
            current.append(np.linalg.norm(hold['current'][-1] - world.current))
        current_cell = f'{np.median(current):.3f}' if setup.get('use_ekf', True) else '-'
        print(f'{name:<26}{np.sqrt(np.mean(mean_square)):>13.2f} / {max(worst_path):<4.2f}{np.mean(finished):>10.0%}'
              f'{np.mean(np.array(worst_hold) <= 0.25):>11.0%}{np.median(worst_hold):>13.2f}{current_cell:>10}')
    print("current error: the EKF's estimate after the hold, median m/s (true current 0.15 m/s)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--seed', type=int, default=3)
    parser.add_argument('--runs', type=int, default=0)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.runs:
        statistics(args.runs)
    else:
        plot(args.seed, OUT / f'rov_seed{args.seed}.png')
        print(f"saved {OUT / f'rov_seed{args.seed}.png'}")


if __name__ == '__main__':
    main()
