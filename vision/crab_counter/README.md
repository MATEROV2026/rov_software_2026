# Crab counter (MATE 2026 task 2.1): baseline

Counts European green crabs on the sample board, with boxes on green crabs
only, as the image-recognition option (15 pts) requires.

Every crab on the board is a printed copy of one of MATE's three official
reference images, so the baseline finds each copy directly. It matches SIFT
keypoints against the references and fits a RANSAC homography per copy,
with no training. See [`sift_counter.py`](sift_counter.py).

## Setup

```bash
python3 -m venv vision/.venv                          # Python 3.10+
vision/.venv/bin/pip install -r vision/crab_counter/requirements.txt
```

Download MATE's files into `dataset/mate_2026/` (git ignores `dataset/`).
They are from the 2026 resources page at <https://materovcompetition.org/2026>:

- European Green Crab Image.jpg
- Native Rock Crab.jpg
- Jonah crab 2.png
- Crab Sample 1–4.jpg (the practice boards)

## Run

```bash
cd vision/crab_counter
../.venv/bin/python evaluate.py --data ../../dataset/mate_2026            # practice boards
../.venv/bin/python evaluate.py --data ../../dataset/mate_2026 --stress   # + simulated camera conditions
```

Counts are scored against `practice_labels.json`, which holds MATE's four
practice boards counted by eye: 9 green crabs among 35. Annotated images go
to `runs/`:

- `*_competition.jpg`: boxes on green crabs only, plus the count (what the judge sees)
- `*_debug.jpg`: every species, with the number of matched keypoints

## Results (Mac, Apple Silicon)

| Condition | Exact green count (4 boards) |
|---|---|
| Clean photo | 4/4 (every crab found, all three species) |
| Half size, blur, underwater tint, 30° tilt, JPEG q35, noise | 4/4 each |
| Board at one-third size | 2/4 |
| All of the above combined, at half size | 3/4 |

- It never drew a false box. Every failure is a missed crab, so it undercounts.
- Misses happen when a crab is under roughly 80 px across and also degraded.
- Speed is about 130 ms per 1200 px image, about 7–8 frames per second.

What this means for piloting: fill the camera frame with the board. Then the
crabs are larger than in the passing half-size test.

## Next

1. Average the count over a few seconds of video before showing it, so one
   bad frame cannot change the answer.
2. Test against photos of a printed, laminated mock board in water. Simulated
   conditions are not the real camera.
3. If small or hazy crabs still get missed, train a learned detector: a small
   YOLO model trained on synthetic boards (the reference images pasted at
   random sizes and angles, with water tint, glare and blur). Score it with
   this same harness.
4. ROS 2 node on the laptop, then a task 2.1 screen in Mission Control.
