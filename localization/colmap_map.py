"""Locate the camera in a COLMAP map: the map layer under the EKF.

COLMAP builds the map offline from a sweep of photos: 3-D points, each with
the SIFT descriptors of the photos that saw it. During a dive, each camera
frame is matched against those descriptors and its pose solved with PnP
(OpenCV solvePnPRansac). That pose is a fix the EKF in rov_ekf.py can use in
place of known markers.

colmap_dir/ is a 100-photo test sweep with the ZED's left camera, in air.
This leaves photos out, rebuilds the map from the rest (every point
re-triangulated from the remaining photos only), finds each left-out photo
with OpenCV SIFT, and compares with where COLMAP's full reconstruction put
it. The map has no units, so errors are a share of the distance from the
camera to the scene.

    python localization/colmap_map.py                 # every 5th photo left out
    python localization/colmap_map.py --block 50 100  # map from photos 0-49 only
"""
from __future__ import annotations

import argparse
import sqlite3
import struct
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / 'colmap_dir'
OUT = Path(__file__).resolve().parent / 'runs'
# COLMAP camera model id: where fx, fy, cx, cy and the distortion (k1, k2, p1, p2) sit in its params
CAMERA_MODELS = {0: (0, 0, 1, 2, ()),            # SIMPLE_PINHOLE
                 1: (0, 1, 2, 3, ()),            # PINHOLE
                 2: (0, 0, 1, 2, (3,)),          # SIMPLE_RADIAL, COLMAP's default
                 3: (0, 0, 1, 2, (3, 4)),        # RADIAL
                 4: (0, 1, 2, 3, (4, 5, 6, 7))}  # OPENCV
RATIO = 0.8          # Lowe's ratio test
REPROJ_PX = 4.0      # RANSAC: a match this close to where the pose puts it agrees with the pose
MIN_INLIERS = 30     # fewer agreeing matches: no fix
CHI2_3D_95 = 7.81


@dataclass
class Photo:
    name: str
    R: np.ndarray          # world -> camera rotation
    t: np.ndarray          # world -> camera translation
    K: np.ndarray
    dist: np.ndarray       # OpenCV (k1, k2, p1, p2)
    xy: np.ndarray         # (n, 2) keypoints; COLMAP puts the top-left pixel's centre at (0.5, 0.5)
    point_ids: np.ndarray  # (n,) map point seen at each keypoint, -1 for none

    @property
    def center(self):
        return -self.R.T @ self.t


@dataclass
class Map:
    points: np.ndarray       # (m, 3)
    descriptors: np.ndarray  # (d, 128) RootSIFT, one per photo that saw a point
    owner: np.ndarray        # (d,) the point each descriptor belongs to


@dataclass
class Fix:
    R: np.ndarray            # world -> camera
    t: np.ndarray
    points: np.ndarray       # (n, 3) matched map points
    pixels: np.ndarray       # (n, 2) where the camera saw them
    inliers: np.ndarray      # the matches that agree with the pose
    covariance: np.ndarray   # (3, 3) of the camera centre, from pixel noise alone

    @property
    def center(self):
        return -self.R.T @ self.t


def rotation(qw, qx, qy, qz):
    return np.array([[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qw * qz), 2 * (qx * qz + qw * qy)],
                     [2 * (qx * qy + qw * qz), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qw * qx)],
                     [2 * (qx * qz - qw * qy), 2 * (qy * qz + qw * qx), 1 - 2 * (qx * qx + qy * qy)]])


def read_cameras(path):
    data, cameras, offset = path.read_bytes(), {}, 8
    for _ in range(struct.unpack_from('<Q', data)[0]):
        camera_id, model, _, _ = struct.unpack_from('<IiQQ', data, offset)
        offset += 24
        if model not in CAMERA_MODELS:
            raise ValueError(f'COLMAP camera model {model} is not supported; use SIMPLE_RADIAL or OPENCV')
        fx, fy, cx, cy, d = CAMERA_MODELS[model]
        n = max(fx, fy, cx, cy, *d) + 1
        p = np.frombuffer(data, '<f8', n, offset)
        offset += 8 * n
        dist = np.zeros(4)
        dist[:len(d)] = p[list(d)]
        cameras[camera_id] = np.array([[p[fx], 0, p[cx]], [0, p[fy], p[cy]], [0, 0, 1.0]]), dist
    return cameras


def read_model(folder):
    """COLMAP's sparse model (cameras.bin, images.bin, points3D.bin): photos by name, points by id."""
    cameras = read_cameras(folder / 'cameras.bin')
    keypoint = np.dtype([('xy', '<f8', 2), ('point_id', '<i8')])
    data, photos, offset = (folder / 'images.bin').read_bytes(), {}, 8
    for _ in range(struct.unpack_from('<Q', data)[0]):
        _, qw, qx, qy, qz, tx, ty, tz, camera_id = struct.unpack_from('<I7dI', data, offset)
        end = data.index(b'\0', offset + 64)
        name = data[offset + 64:end].decode()
        n = struct.unpack_from('<Q', data, end + 1)[0]
        rows = np.frombuffer(data, keypoint, n, end + 9)
        offset = end + 9 + keypoint.itemsize * n
        photos[name] = Photo(name, rotation(qw, qx, qy, qz), np.array([tx, ty, tz]), *cameras[camera_id],
                             rows['xy'].copy(), rows['point_id'].copy())
    data, points, offset = (folder / 'points3D.bin').read_bytes(), {}, 8
    for _ in range(struct.unpack_from('<Q', data)[0]):
        point_id, x, y, z = struct.unpack_from('<Q3d', data, offset)
        points[point_id] = np.array([x, y, z])
        offset += 51 + 8 * struct.unpack_from('<Q', data, offset + 43)[0]   # skip colour, error, track
    return photos, points


def read_descriptors(database):
    """Each photo's SIFT descriptors from COLMAP's database.db, in keypoint order."""
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?immutable=1', uri=True)) as db:
        names = dict(db.execute('SELECT image_id, name FROM images'))
        return {names[i]: np.frombuffer(blob, np.uint8).reshape(rows, cols)
                for i, rows, cols, blob in db.execute('SELECT image_id, rows, cols, data FROM descriptors')}


def root_sift(descriptors):
    """OpenCV's SIFT descriptors in the RootSIFT form COLMAP stores (there as uint8, times 512)."""
    d = descriptors / np.maximum(descriptors.sum(axis=1, keepdims=True), 1e-9)
    return np.sqrt(d).astype(np.float32)


def build_map(photos, descriptors, names, min_views=2, max_error_px=4.0, min_angle=np.radians(1.5)):
    """A map from these photos alone: each point seen by at least min_views of
    them is re-triangulated from those views, so a photo left out adds nothing."""
    ids, rays, descs, photo_of = [], [], [], []
    for i, name in enumerate(names):
        photo = photos[name]
        seen = photo.point_ids >= 0
        ids.append(photo.point_ids[seen])
        rays.append(cv2.undistortPoints(photo.xy[seen].reshape(-1, 1, 2), photo.K, photo.dist)[:, 0])
        descs.append(descriptors[name][seen])
        photo_of.append(np.full(seen.sum(), i))
    ids, rays, descs, photo_of = map(np.concatenate, (ids, rays, descs, photo_of))
    P = np.array([np.hstack((photos[n].R, photos[n].t[:, None])) for n in names])[photo_of]
    unique, point, views = np.unique(ids, return_inverse=True, return_counts=True)

    # Each sighting gives two linear equations in the point X: (u P3 - P1) X = 0 and (v P3 - P2) X = 0.
    rows = (rays[:, :1] * P[:, 2] - P[:, 0], rays[:, 1:] * P[:, 2] - P[:, 1])
    weight = np.ones(len(ids))
    for _ in range(2):   # the second pass divides by depth, turning the equations into image error
        M, b = np.zeros((len(unique), 3, 3)), np.zeros((len(unique), 3))
        for a in rows:
            a = a * weight[:, None]
            np.add.at(M, point, a[:, :3, None] * a[:, None, :3])
            np.add.at(b, point, -a[:, 3:] * a[:, :3])
        X = np.einsum('nij,nj->ni', np.linalg.pinv(M), b)
        in_camera = np.einsum('nij,nj->ni', P[:, :, :3], X[point]) + P[:, :, 3]
        weight = 1 / np.maximum(np.abs(in_camera[:, 2]), 1e-9)

    focal = np.array([photos[n].K[0, 0] for n in names])[photo_of]
    error_px = focal * np.linalg.norm(in_camera[:, :2] / in_camera[:, 2:] - rays, axis=1)
    bad = np.zeros(len(unique), bool)
    np.logical_or.at(bad, point, (in_camera[:, 2] <= 0) | (error_px > max_error_px))
    # Triangulation angle, roughly: twice the widest ray from the mean viewing direction.
    to_camera = np.array([photos[n].center for n in names])[photo_of] - X[point]
    to_camera /= np.linalg.norm(to_camera, axis=1, keepdims=True)
    mean = np.zeros_like(X)
    np.add.at(mean, point, to_camera)
    mean /= np.linalg.norm(mean, axis=1, keepdims=True)
    angle = np.zeros(len(unique))
    np.maximum.at(angle, point, 2 * np.arccos(np.clip(np.sum(to_camera * mean[point], axis=1), -1, 1)))

    keep = (views >= min_views) & ~bad & (angle >= min_angle)
    used = keep[point]
    return Map(X[keep], descs[used].astype(np.float32) / 512, (np.cumsum(keep) - 1)[point[used]])


def calibration(photos, names):
    """One calibration for the live camera: the median over the map photos.
    The ZED's left image is already rectified, so they barely differ."""
    return (np.median([photos[n].K for n in names], axis=0),
            np.median([photos[n].dist for n in names], axis=0))


def solve_pose(points, pixels, K, dist):
    """PnP with RANSAC, refined on the matches that agree. None if too few agree."""
    if len(points) < MIN_INLIERS:
        return None
    ok, rvec, tvec, inliers = cv2.solvePnPRansac(points, pixels, K, dist, iterationsCount=1000,
                                                 reprojectionError=REPROJ_PX, confidence=0.9999,
                                                 flags=cv2.SOLVEPNP_EPNP)
    if not ok or inliers is None or len(inliers) < MIN_INLIERS:
        return None
    rvec, tvec = cv2.solvePnPRefineLM(points[inliers[:, 0]], pixels[inliers[:, 0]], K, dist, rvec, tvec)
    # RANSAC sorted the matches by a rough pose: sort them again by the refined one, and refine on those.
    off = np.linalg.norm(cv2.projectPoints(points, rvec, tvec, K, dist)[0][:, 0] - pixels, axis=1)
    inliers = np.flatnonzero(off < REPROJ_PX)
    if len(inliers) < MIN_INLIERS:
        return None
    rvec, tvec = cv2.solvePnPRefineLM(points[inliers], pixels[inliers], K, dist, rvec, tvec)
    projected, J = cv2.projectPoints(points[inliers], rvec, tvec, K, dist)
    residual = (projected[:, 0] - pixels[inliers]).ravel()
    pose_covariance = residual @ residual / (len(residual) - 6) * np.linalg.inv(J[:, :6].T @ J[:, :6])
    R, dR = cv2.Rodrigues(rvec)
    t = tvec[:, 0]
    # d(centre) / d(rvec, tvec), where centre = -R^T t
    G = np.hstack((np.column_stack([-dR[k].reshape(3, 3).T @ t for k in range(3)]), -R.T))
    return Fix(R, t, points, pixels, inliers, G @ pose_covariance @ G.T)


class Locator:
    """Finds camera frames in a map: SIFT, ratio-tested matches, then solve_pose."""

    def __init__(self, the_map, K, dist):
        self.map, self.K, self.dist = the_map, K, dist
        self.sift = cv2.SIFT_create(contrastThreshold=0.02)
        self.matcher = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 4}, {'checks': 64})
        self.matcher.add([the_map.descriptors])
        self.matcher.train()

    def features(self, gray):
        keypoints, descriptors = self.sift.detectAndCompute(gray, None)
        if descriptors is None:
            return np.zeros((0, 2)), np.zeros((0, 128), np.float32)
        return np.array([k.pt for k in keypoints]) + 0.5, root_sift(descriptors)   # to COLMAP's pixel centres

    def match(self, xy, descriptors):
        """Ratio test against the nearest descriptor of a *different* map point:
        a point seen by several photos has several near-identical descriptors."""
        found, pixels = [], []
        for q, near in enumerate(self.matcher.knnMatch(descriptors, k=6) if len(descriptors) else []):
            best = self.map.owner[near[0].trainIdx]
            other = next((m.distance for m in near[1:] if self.map.owner[m.trainIdx] != best), np.inf)
            if near[0].distance < RATIO * other:
                found.append(best)
                pixels.append(xy[q])
        return self.map.points[found].reshape(-1, 3), np.array(pixels).reshape(-1, 2)

    def locate(self, gray):
        return solve_pose(*self.match(*self.features(gray)), self.K, self.dist)


def evaluate(data, left_out):
    """Map from the other photos, then find each left-out photo in it."""
    photos, _ = read_model(data / 'sparse' / '0')
    kept = [n for n in sorted(photos) if n not in left_out]
    the_map = build_map(photos, read_descriptors(data / 'database.db'), kept)
    locator = Locator(the_map, *calibration(photos, kept))
    results = []
    for name in left_out:
        truth = photos[name]
        gray = cv2.imread(str(data / 'images' / name), cv2.IMREAD_GRAYSCALE)
        start = time.perf_counter()
        points, pixels = locator.match(*locator.features(gray))
        fix = solve_pose(points, pixels, locator.K, locator.dist)
        result = {'name': name, 'matches': len(points), 'ms': 1000 * (time.perf_counter() - start), 'fix': fix}
        if fix:
            e = fix.center - truth.center
            result['distance'] = np.median((fix.points[fix.inliers] @ truth.R.T + truth.t)[:, 2])
            result['error'] = np.linalg.norm(e) / result['distance']
            result['rotation'] = np.degrees(np.arccos(np.clip((np.trace(fix.R @ truth.R.T) - 1) / 2, -1, 1)))
            result['mahalanobis'] = e @ np.linalg.solve(fix.covariance, e)
        results.append(result)
    return photos, kept, the_map, results


def plot(data, photos, kept, the_map, results, path):
    located = [r for r in results if r['fix']]
    example = sorted(located, key=lambda r: r['error'])[len(located) // 2]
    fig, (ax_photo, ax_map, ax_err) = plt.subplots(1, 3, figsize=(18, 5.2),
                                                   gridspec_kw={'width_ratios': [1.45, 1, 1]})
    fix = example['fix']
    agree = np.zeros(len(fix.points), bool)
    agree[fix.inliers] = True
    ax_photo.imshow(cv2.cvtColor(cv2.imread(str(data / 'images' / example['name'])), cv2.COLOR_BGR2RGB))
    ax_photo.plot(*(fix.pixels[~agree] - 0.5).T, 'x', color='#e74c3c', ms=4, label='match the pose rejects')
    ax_photo.plot(*(fix.pixels[agree] - 0.5).T, 'o', color='#2ecc71', ms=2.5, label='match that agrees')
    ax_photo.set_title(f"{example['name']}, left out of the map: {agree.sum()} of {len(agree)} matches agree",
                       fontsize=10)
    ax_photo.legend(loc='lower right', fontsize=8)
    ax_photo.axis('off')

    # Top view: COLMAP's x (right) and z (forward) for this sweep; the inset zooms in on the camera.
    centres = np.array([photos[n].center for n in kept])
    near = np.linalg.norm(the_map.points - centres.mean(axis=0), axis=1)
    pts = the_map.points[near < np.percentile(near, 85)]
    ax_map.scatter(pts[:, 0], pts[:, 2], s=0.5, color='#7f8c8d', alpha=0.35, label='map points')
    inset = ax_map.inset_axes([0.03, 0.04, 0.46, 0.42])
    true = np.array([photos[r['name']].center for r in located])
    drawn = true + 20 * (np.array([r['fix'].center for r in located]) - true)
    for ax in (ax_map, inset):
        ax.plot(centres[:, 0], centres[:, 2], '.-', color='#bdc3c7', lw=0.8, ms=4, label='map photos (camera path)')
        for a, b in zip(true, drawn):
            ax.plot([a[0], b[0]], [a[2], b[2]], '-', color='#e74c3c', lw=1.5)
        ax.plot(true[:, 0], true[:, 2], 'o', mfc='none', color='k', ms=5, label="left out: COLMAP's position")
    ax_map.plot([], [], '-', color='#e74c3c', lw=1.5, label='error to where it was located, drawn 20x')
    inset.set_aspect('equal', adjustable='datalim')
    inset.tick_params(labelsize=6)
    inset.set_title('camera area, zoomed in', fontsize=7)
    ax_map.indicate_inset_zoom(inset, edgecolor='#555555')
    ax_map.set_aspect('equal')
    ax_map.set_xlabel('x (map units, no scale)')
    ax_map.set_ylabel('z, forward (map units)')
    ax_map.set_title('Top view of the map', fontsize=10)
    ax_map.legend(loc='upper right', fontsize=7.5)

    names = [r['name'][4:7] for r in results]
    errors = [100 * r['error'] if r['fix'] else 0 for r in results]
    ax_err.bar(names, errors, color=['#2e86c1' if r['fix'] else '#e74c3c' for r in results])
    ax_err.axhline(100 * np.median([r['error'] for r in located]), color='k', ls='--', lw=1, label='median')
    ax_err.set_xlabel('left-out photo')
    ax_err.set_ylabel('camera position error (% of distance to scene)')
    ax_err.tick_params(axis='x', labelrotation=90, labelsize=7)
    ax_err.secondary_yaxis('right', functions=(lambda p: 3 * p, lambda cm: cm / 3)).set_ylabel(
        'cm, if the scene were 3 m away')
    ax_err.set_title(f'{len(located)} of {len(results)} left-out photos located', fontsize=10)
    ax_err.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--data', type=Path, default=DATA, help='COLMAP project: sparse/0, database.db, images/')
    parser.add_argument('--every', type=int, default=5, help='leave out every n-th photo')
    parser.add_argument('--block', type=int, nargs=2, metavar=('FIRST', 'END'),
                        help='leave out photos FIRST..END-1 (in name order) instead')
    args = parser.parse_args()
    names = sorted(read_model(args.data / 'sparse' / '0')[0])
    left_out = names[slice(*args.block)] if args.block else names[2::args.every]
    photos, kept, the_map, results = evaluate(args.data, left_out)
    print(f'map from {len(kept)} photos: {len(the_map.points):,} points re-triangulated without the '
          f'{len(left_out)} left out, {len(the_map.descriptors):,} descriptors\n')
    print(f"{'photo':<14}{'matches':>8}{'agree':>7}{'error*':>9}{'rotation':>10}{'time':>9}")
    for r in results:
        if r['fix']:
            print(f"{r['name']:<14}{r['matches']:>8}{len(r['fix'].inliers):>7}{100 * r['error']:>8.2f}%"
                  f"{r['rotation']:>9.2f}°{r['ms']:>6.0f} ms")
        else:
            print(f"{r['name']:<14}{r['matches']:>8}{'not located':>17}{'':>10}{r['ms']:>6.0f} ms")
    located = [r for r in results if r['fix']]
    error = 100 * np.array([r['error'] for r in located])
    rot = np.array([r['rotation'] for r in located])
    scale = np.sqrt(np.percentile([r['mahalanobis'] for r in located], 95) / CHI2_3D_95)
    print('* camera position error, as a share of the distance from the camera to the scene\n')
    print(f'located {len(located)} of {len(results)}; position error median {np.median(error):.2f}%, '
          f'worst {error.max():.2f}%: {3 * np.median(error):.1f} cm / {3 * error.max():.1f} cm '
          f'if the scene were 3 m away')
    print(f'rotation error median {np.median(rot):.2f}°, worst {rot.max():.2f}°; '
          f"time median {np.median([r['ms'] for r in results]):.0f} ms per photo (SIFT, matching, PnP)")
    print(f"PnP's own uncertainty (pixel noise only) is {scale:.1f}x too small to cover 95% of the errors")
    OUT.mkdir(exist_ok=True)
    path = OUT / (f'colmap_block{args.block[0]}-{args.block[1]}.png' if args.block else f'colmap_every{args.every}.png')
    plot(args.data, photos, kept, the_map, results, path)
    print(f'saved {path}')


if __name__ == '__main__':
    main()
