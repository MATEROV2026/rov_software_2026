"""Score a crab counter on MATE's practice boards.

    vision/.venv/bin/python vision/crab_counter/evaluate.py --data dataset/mate_2026 [--stress]

Prints per-board counts against practice_labels.json and writes annotated
images to vision/crab_counter/runs/: the competition view (boxes on green
crabs only, plus the count) and a debug view (every species). --stress also
re-runs each board through simulated ROV-camera conditions.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from sift_counter import SiftCrabCounter

HERE = Path(__file__).resolve().parent
COLOURS = {'green': (60, 200, 60), 'rock': (40, 140, 255), 'jonah': (200, 80, 255)}


# --- simulated ROV-camera conditions -------------------------------------------

def _resize(img, factor):
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * factor), int(h * factor)), interpolation=cv2.INTER_AREA)


def _underwater(img):
    """Red light dies first underwater; add a blue-green veil and lose contrast."""
    attenuation = np.float32([0.95, 0.85, 0.45])  # B, G, R
    veil = np.float32([110, 95, 40])
    out = img.astype(np.float32) * attenuation * 0.65 + veil * 0.35
    return np.clip(out, 0, 255).astype(np.uint8)


def _tilt(img, degrees):
    """Camera looking at the board at an angle instead of straight down."""
    h, w = img.shape[:2]
    inset = 0.5 * w * (1 - np.cos(np.radians(degrees)))
    squash = h * (1 - np.cos(np.radians(degrees))) / 2
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[inset, squash], [w - inset, squash], [w, h], [0, h]])
    return cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h),
                               borderValue=(120, 60, 30))


def _jpeg(img, quality):
    return cv2.imdecode(cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])[1],
                        cv2.IMREAD_COLOR)


def _noise(img, sigma, seed=0):
    rng = np.random.default_rng(seed)
    return np.clip(img + rng.normal(0, sigma, img.shape), 0, 255).astype(np.uint8)


def conditions(img, stress):
    yield 'clean', img
    if not stress:
        return
    yield 'half size', _resize(img, 0.5)
    yield 'third size', _resize(img, 1 / 3)
    yield 'blur', cv2.GaussianBlur(img, (0, 0), 2.0)
    yield 'underwater tint', _underwater(img)
    yield 'tilt 30°', _tilt(img, 30)
    yield 'jpeg q35', _jpeg(img, 35)
    yield 'noise σ10', _noise(img, 10)
    combined = _jpeg(_noise(cv2.GaussianBlur(_underwater(_tilt(_resize(img, 0.5), 20)), (0, 0), 1.2), 6), 50)
    yield 'all combined', combined


# --- drawing ---------------------------------------------------------------------

def competition_view(img, detections):
    """What the judge sees: boxes on green crabs only, and the count."""
    out = img.copy()
    greens = [d for d in detections if d.species == 'green']
    for det in greens:
        x, y, w, h = det.box
        cv2.rectangle(out, (x, y), (x + w, y + h), COLOURS['green'], 3)
    cv2.putText(out, f'European green crabs: {len(greens)}', (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 6)
    cv2.putText(out, f'European green crabs: {len(greens)}', (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, COLOURS['green'], 3)
    return out


def debug_view(img, detections):
    out = img.copy()
    for det in detections:
        cv2.polylines(out, [det.corners.astype(np.int32)], True, COLOURS[det.species], 3)
        x, y, _, _ = det.box
        cv2.putText(out, f'{det.species} ({det.inliers})', (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOURS[det.species], 2)
    return out


# --- main --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--data', type=Path, required=True,
                        help='folder with the reference images and practice boards')
    parser.add_argument('--labels', type=Path, default=HERE / 'practice_labels.json')
    parser.add_argument('--out', type=Path, default=HERE / 'runs')
    parser.add_argument('--stress', action='store_true')
    args = parser.parse_args()

    labels = {k: v for k, v in json.loads(args.labels.read_text()).items() if not k.startswith('_')}
    counter = SiftCrabCounter(args.data)
    args.out.mkdir(parents=True, exist_ok=True)

    results = {}  # condition -> list of (board, correct green count?)
    timings = []
    print(f"{'board':<20}{'condition':<18}{'green':>9}{'rock':>9}{'jonah':>9}   ms")
    for board, truth in labels.items():
        image = cv2.imread(str(args.data / board), cv2.IMREAD_COLOR)
        for condition, img in conditions(image, args.stress):
            start = time.perf_counter()
            detections = counter.detect(img)
            ms = (time.perf_counter() - start) * 1000
            timings.append(ms)
            got = Counter(d.species for d in detections)
            cells = ''.join(f"{got[s]:>4}/{truth[s]}{' ✓' if got[s] == truth[s] else ' ✗'}"
                            for s in ('green', 'rock', 'jonah'))
            print(f'{board:<20}{condition:<18}{cells}  {ms:5.0f}')
            results.setdefault(condition, []).append(got['green'] == truth['green'])
            if condition in ('clean', 'all combined'):
                stem = f"{Path(board).stem.replace(' ', '_')}_{condition.replace(' ', '_')}"
                cv2.imwrite(str(args.out / f'{stem}_competition.jpg'), competition_view(img, detections))
                cv2.imwrite(str(args.out / f'{stem}_debug.jpg'), debug_view(img, detections))

    print('\nexact green count, per condition:')
    for condition, oks in results.items():
        print(f'  {condition:<18} {sum(oks)}/{len(oks)}')
    print(f'median time per image: {np.median(timings):.0f} ms')


if __name__ == '__main__':
    main()
