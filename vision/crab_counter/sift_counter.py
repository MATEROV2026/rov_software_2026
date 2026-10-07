"""Baseline crab counter for MATE 2026 task 2.1.

Every crab on the sample board is a printed copy of one of MATE's three
official reference images, so instead of learning what a crab looks like,
this finds each copy directly: SIFT keypoints matched against the references,
then a RANSAC homography per copy. Nothing to train. It sets the bar, and the
evaluation harness, for a learned detector.

Only standard OpenCV calls (also in the 4.5 that ships with Ubuntu 22.04).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np

REFERENCE_FILES = {
    'green': 'European Green Crab Image.jpg',
    'rock': 'Native Rock Crab.jpg',
    'jonah': 'Jonah crab 2.png',
}


@dataclass
class Detection:
    species: str
    corners: np.ndarray  # 4x2 outline of the crab, scene pixels
    inliers: int

    @property
    def box(self) -> Tuple[int, int, int, int]:
        x, y, w, h = cv2.boundingRect(self.corners.astype(np.float32))
        return x, y, w, h


@dataclass
class _Reference:
    species: str
    points: np.ndarray       # keypoint positions, reference pixels
    descriptors: np.ndarray
    outline: np.ndarray      # 4x2 tight box around the crab, reference pixels


def _crab_outline(image: np.ndarray) -> np.ndarray:
    """Corners of the tight box around the crab (the non-white pixels)."""
    ys, xs = np.nonzero(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) < 200)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    return np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])


def _plausible(corners: np.ndarray, outline: np.ndarray, image_area: float) -> bool:
    """Reject degenerate homographies: twisted, inside-out, or absurd sizes."""
    if not cv2.isContourConvex(corners.astype(np.float32)):
        return False
    area = cv2.contourArea(corners.astype(np.float32))
    if not 0.002 * image_area < area < 0.5 * image_area:
        return False
    sides = np.linalg.norm(corners - np.roll(corners, -1, axis=0), axis=1)
    ref_sides = np.linalg.norm(outline - np.roll(outline, -1, axis=0), axis=1)
    stretch = sides / ref_sides
    return stretch.max() / stretch.min() < 3.0  # tilt is fine, folding is not


def _iou(a: Detection, b: Detection) -> float:
    ax, ay, aw, ah = a.box
    bx, by, bw, bh = b.box
    w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    h = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = w * h
    return inter / float(aw * ah + bw * bh - inter)


class SiftCrabCounter:
    def __init__(self, reference_dir: Path, ratio: float = 0.75, min_inliers: int = 12,
                 reproj_px: float = 6.0, contrast_threshold: float = 0.02) -> None:
        # 0.02 (OpenCV's default is 0.04) keeps the weaker keypoints of small or
        # hazy crabs: in evaluate.py --stress it found 308/315 crabs instead of
        # 302, still with no false boxes. CLAHE equalisation did not help.
        self.sift = cv2.SIFT_create(contrastThreshold=contrast_threshold)
        self.ratio, self.min_inliers, self.reproj_px = ratio, min_inliers, reproj_px
        self.references: List[_Reference] = []
        for species, name in REFERENCE_FILES.items():
            image = cv2.imread(str(Path(reference_dir) / name), cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(Path(reference_dir) / name)
            keypoints, descriptors = self.sift.detectAndCompute(
                cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), None)
            self.references.append(_Reference(
                species, np.float32([k.pt for k in keypoints]), descriptors, _crab_outline(image)))
        self._owner = np.concatenate([np.full(len(r.descriptors), i)
                                      for i, r in enumerate(self.references)])
        self._row = np.concatenate([np.arange(len(r.descriptors)) for r in self.references])
        self._matcher = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 5}, {'checks': 64})
        self._matcher.add([np.concatenate([r.descriptors for r in self.references])])
        self._matcher.train()

    def detect(self, scene: np.ndarray) -> List[Detection]:
        keypoints, descriptors = self.sift.detectAndCompute(
            cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY), None)
        if descriptors is None or len(keypoints) < self.min_inliers:
            return []
        scene_points = np.float32([k.pt for k in keypoints])

        # Each scene keypoint votes for its nearest reference keypoint, if that
        # match is clearly better than the runner-up (Lowe's ratio test).
        pairs: Dict[int, List[Tuple[int, int]]] = {i: [] for i in range(len(self.references))}
        for match in self._matcher.knnMatch(descriptors, k=2):
            if len(match) == 2 and match[0].distance < self.ratio * match[1].distance:
                ref = int(self._owner[match[0].trainIdx])
                pairs[ref].append((match[0].queryIdx, int(self._row[match[0].trainIdx])))

        image_area = float(scene.shape[0] * scene.shape[1])
        detections: List[Detection] = []
        for ref_index, ref in enumerate(self.references):
            if not pairs[ref_index]:
                continue
            idx = np.array(pairs[ref_index])
            src, dst = ref.points[idx[:, 1]], scene_points[idx[:, 0]]
            # Peel off one printed copy at a time until no copy has enough support.
            while len(src) >= self.min_inliers:
                homography, mask = cv2.findHomography(src, dst, cv2.RANSAC, self.reproj_px)
                if homography is None:
                    break
                inliers = mask.ravel().astype(bool)
                if inliers.sum() < self.min_inliers:
                    break
                corners = cv2.perspectiveTransform(ref.outline[None], homography)[0]
                keep = ~inliers
                if _plausible(corners, ref.outline, image_area):
                    detections.append(Detection(ref.species, corners, int(inliers.sum())))
                    contour = corners.astype(np.float32)
                    inside = np.array([cv2.pointPolygonTest(contour, (float(x), float(y)), False) >= 0
                                       for x, y in dst])
                    keep &= ~inside
                src, dst = src[keep], dst[keep]

        # One crab, one label: when copies overlap, the better-supported wins.
        kept: List[Detection] = []
        for det in sorted(detections, key=lambda d: d.inliers, reverse=True):
            if all(_iou(det, other) < 0.3 for other in kept):
                kept.append(det)
        return kept
