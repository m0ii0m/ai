# Task 4.1: fuzzy Pong controllers

`FuzzyPlayer` in `Pong.py` has three controllers, chosen with the class attribute `method`:

| `method` | controller |
|---|---|
| `"mamdani"` | scikit-fuzzy, 6 rules (`x_dist` left/centre/right × `y_dist` near/far), centroid defuzzification, follows the ball (grade 3.0) |
| `"tsk"` | hand-written first-order TSK on the same rules: each rule proposes `v = -k * x_diff`, output = weighted average clipped to ±10 px/frame (grade 4.0) |
| `"edge"` | the TSK steered to a target: the predicted impact point shifted by 40 px, so the ball hits the outer quarter of the paddle and speeds up by 10 % (grade 5.0) |

**Edge strategy.** `predict_impact_x` replays `Ball.move` frame by frame (same rounding, same wall
bounces) to find where the ball will reach the paddle. While the ball goes up, the paddle waits under
that point; once it comes down, the prediction is exact and the paddle aims at ±40 px from it, on the
side that needs the shortest move and stays on the board. In this mode the `stop` rule proposes
`v = -gap` instead of 0, so the paddle lands exactly on its target.

## Tests

Headless runs of `Pong.py` (unchanged) against `NaiveOponent`, with the pygame clock replaced by a frame
counter: a 5-minute match per controller, and 200 rallies from random starts (same starts for every
setting). Rallies lost on the very first pass are start artefacts and are left out.

| controller | 5-min match (lost / won) | random rallies lost | ball speed when lost | returns hit with the edge |
|---|---|---|---|---|
| Mamdani | 4 / 1 | 94.5 % | 8.0 px/frame | 9 % |
| TSK | 4 / 1 | 59 % | 9.9 px/frame | 23 % |
| **Edge** | **0 / 9** | **0 %** | (never) | **100 %** |

Mamdani saturates around ±8.9 px/frame (centroid of a set of non-zero width) and loses first; the TSK
only loses once the ball is faster than the paddle limit (10 px/frame).

**Impact prediction**, compared with the real impact point during a 5-minute match:

| prediction made when the ball… | exact | within 3 px | worst error |
|---|---|---|---|
| starts coming down | 64 / 64 | 64 / 64 | 0 px |
| starts going up | 29 / 64 | 53 / 64 | 577 px (most likely a point scored: the ball is reset) |

## Sensitivity tests

One value changed at a time, everything else as in `Pong.py`, on the same 200 random rallies.

**Edge mode, aimed offset `edge_offset`** (edge zone: 30 < |dx| < 50)

| edge_offset [px] | 30 | 32 to 48 | 50 |
|---|---|---|---|
| rallies lost | 0 % | 0 % | all |
| returns hit with the edge | 1 % | 100 % | (none) |

Every value from 32 to 48 px gives identical games: the contact point changes the ball speed, never its
direction. At 30 px the ball misses the outer quarter, at 50 px it misses the paddle.

**Edge mode, gain of the `stop` rule** (`v = -k * gap`)

| k | 0 | 0.25 | 0.5 | **1 (Pong.py)** | 1.5 |
|---|---|---|---|---|---|
| rallies lost | 5.4 % | 0 % | 0 % | **0 %** | 0 % |

With k = 0 the commanded speed drops under 0.5 px/frame within 10 px of the target, pygame rounds the
move away, and the paddle stalls short of the edge zone.

**TSK ball following, gains of the `fast` / `slow` rules**

| fast / slow | 0.1 / 0.06 | 0.15 / 0.09 | **0.25 / 0.15 (Pong.py)** | 0.4 / 0.24 | 0.6 / 0.36 | 1.0 / 0.6 |
|---|---|---|---|---|---|---|
| rallies lost | 100 % | 97 % | **59 %** | 33 % | 1.8 % | 2.4 % |
| ball speed when lost [px/frame] | 6.2 | 8.1 | **9.9** | 11.1 | 11.3 | 11.0 |

With low gains the paddle lags behind, hits the ball with its edge by accident and speeds it up itself.

**TSK ball following, where `near` turns into `far`**

| near ends / far full [px] | 25 / 75 | 50 / 150 | **100 / 250 (Pong.py)** | 150 / 350 | 250 / 400 |
|---|---|---|---|---|---|
| rallies lost | 85.5 % | 63.9 % | **59.0 %** | 59.0 % | 57.2 % |

A small `near` zone leaves the paddle on its `slow` rules for most of the flight; beyond 100 / 250 the
result barely changes.
