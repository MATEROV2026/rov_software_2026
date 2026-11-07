# MATE Floats! 2027 station

The shore-side half of the 2027 float task, which is worth 70 points. It
receives the float's data packets, checks each profile against MATE's
scoring rules, and draws the two graphs the judge scores. The rules come
from the *2027 MATE Floats Preview Mission* (Explorer), published at
<https://materovcompetition.org/2026>.

```bash
python3 -m venv float_station/.venv            # Python 3.10+
float_station/.venv/bin/pip install -r float_station/requirements.txt
cd float_station && .venv/bin/python app.py
```

Packets can come from three places: **Listen** (a serial radio receiver),
**Open log…** (a saved text file, one packet per line), or **Simulate run**.
`simulator.py` also prints runs, including broken ones (`--drift`,
`--touch-bottom`, `--skip 2.5`), for practice and testing.

## What the station checks, per profile

| Points | Rule | Shown as |
|---|---|---|
| 5 | One packet before the first dive ("Mic'd Up") | `pre-dive` in the log |
| 10 | Top of float goes from the surface to 4.0 m or deeper, and back up | deepest depth |
| 5 | At least 10 packets from the profile | packet count |
| 5 | 7 consecutive packets, 5 s apart, top of float within 2.0 m ± 0.33 m | `hold 1/7`…`7/7` |
| 5 | A packet within ±20 cm of each of 4.0, 3.5 … 0.0 m on the way up, temperature within 2 °C of MATE's readout, plus a light value | `4.0 m sample`… |
| −5 | Touching the pool bottom (estimated from depth plus float height) | warning |

The two graphs are 5 points each: temperature against depth, and light
against depth (value on X, depth on Y). Enter **MATE's temperature** from
the pool readout so the temperature check can run.

For a regional pool, change the hold, max and pool depths; the required
sample depths follow automatically. If the pressure sensor is not at the
top of the float, enter **Sensor below top** and tell the judge the offset
before deploying, as MATE requires.

## What the float must send (for the float firmware)

The station can only award what the packets prove:

1. **One packet per line, MATE's style**, starting with the company number
   MATE assigns: `EX01 1:51:42 UTC 9.8 kpa  1.00 meters 23.6oC  0.546 V`.
   Include a light unit. You may append an NMEA-style `*HH` checksum so the
   station drops lines garbled by radio noise.
2. **A packet at the surface before each dive**, and one when it surfaces.
3. **Log every 5 s during the hold.** MATE checks 7 *consecutive* packets
   5 s apart. Logging faster breaks that: 7 packets 1 s apart cover only 6 s.
4. **Log at each 0.5 m level on the way up** (4.0, 3.5 … 0.0 m). A timer
   alone can step over a ±20 cm window.
5. **Transmit the whole log after surfacing** (at least 10 packets). Radio
   doesn't work under water. Other teams transmit at the same time, so
   filter by company number on the receiver too.

## Not done yet

- Entering MATE's data by hand for the fallback graphs, used when the float fails.
- A pick list of profiles to score when there are more than two.
- Testing with the real radio receiver once the float team picks one.
