"""Run every experiment of REPORT.md and save the raw results in results/.

usage (from the "Fuzzy control" folder): .venv/bin/python simulations/run_experiments.py
"""
import csv
import json
import platform
import time
from importlib.metadata import version
from pathlib import Path

import harness as h

RESULTS = Path(__file__).resolve().parent / "results"
RALLIES = 200
SEED = 0


def save_json(name, data):
    (RESULTS / f"{name}.json").write_text(json.dumps(data, indent=2))


def save_csv(name, rows):
    with open(RESULTS / f"{name}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


# ---------- ways to change one hard-coded value of the controller ----------

def with_gains(fast, slow):
    def configure(player):
        player.velocity_fx = {
            "fast_left": lambda x, y: -fast * x,
            "slow_left": lambda x, y: -slow * x,
            "stop": lambda x, y: 0.0,
            "slow_right": lambda x, y: -slow * x,
            "fast_right": lambda x, y: -fast * x,
        }
        player.edge_velocity_fx = {**player.velocity_fx, "stop": lambda x, y: -1.0 * x}
    return configure


def with_edge_stop_gain(gain):
    def configure(player):
        player.edge_velocity_fx["stop"] = lambda x, y: -gain * x
    return configure


def with_near_far(near_end, far_full):
    """near is 1 up to near_end and 0 from far_full; far is the mirror image."""
    def configure(player):
        height = h.BOARD_HEIGHT
        player.y_mf = {
            "near": h.Pong.fuzz.trapmf(player.y_universe, [-1, 0, near_end, far_full]),
            "far": h.Pong.fuzz.trapmf(player.y_universe, [near_end, far_full, height, height + 1]),
        }
    return configure


def with_edge_offset(offset):
    def configure(player):
        player.edge_offset = offset
    return configure


# ---------- experiments ----------

def matches():
    """The real game for 5 minutes, one per controller (steps 1.7, 2.5 and 3.5)."""
    data = {m: h.run_match(m) for m in ("mamdani", "tsk", "edge")}
    save_json("matches", data)
    return data


def prediction_accuracy(seconds=300):
    """predict_impact_x against where the ball really reaches the paddle line (step 3.2)."""
    game = h.new_game("tsk")
    ball, player = game.ball, game.player
    paddle_top = player.racket.rect.top
    pred_up = pred_down = None
    errors_up, errors_down = [], []
    prev_y_speed = ball.y_speed
    for _ in range(seconds * h.Pong.FPS):
        was_descending = ball.y_speed > 0
        h.step(game)
        reached = was_descending and ball.rect.bottom > paddle_top and ball.rect.y <= paddle_top
        if reached and pred_down is not None:
            errors_down.append(ball.rect.centerx - pred_down)
            if pred_up is not None:
                errors_up.append(ball.rect.centerx - pred_up)
            pred_up = pred_down = None
        if ball.y_speed > 0 > prev_y_speed:
            pred_down = player.predict_impact_x()
        if ball.y_speed < 0 < prev_y_speed:
            pred_up, pred_down = player.predict_impact_x(), None
        prev_y_speed = ball.y_speed
    data = {
        "descending": {"impacts": len(errors_down), "exact": sum(e == 0 for e in errors_down),
                       "max_error_px": max(map(abs, errors_down), default=0), "errors": errors_down},
        "ascending": {"impacts": len(errors_up), "exact": sum(e == 0 for e in errors_up),
                      "max_error_px": max(map(abs, errors_up), default=0), "errors": errors_up},
    }
    save_json("prediction_accuracy", data)
    return data


def dead_zone():
    """Commanded velocity for small gaps to the target, tsk vs edge consequents (step 3.4)."""
    game = h.new_game("tsk")
    player = game.player
    rows = []
    for gap in range(0, 61):
        player.method = "tsk"
        tsk = player.make_decision(gap, 30)
        player.method = "edge"
        edge = player.make_decision(gap, 30)
        rows.append({"gap_px": gap, "tsk_velocity": round(tsk, 3), "edge_velocity": round(edge, 3)})
    save_csv("dead_zone", rows)
    return rows


def baseline():
    """Random rallies for the three controllers as they are in Pong.py."""
    data = {}
    for method in ("mamdani", "tsk", "edge"):
        rallies = h.run_rallies(method, RALLIES, seed=SEED)
        data[method] = {"summary": h.summarize(rallies), "rallies": rallies}
    save_json("baseline_rallies", data)
    return data


def sweep(name, method, values, make_configure, label):
    """Change one value, everything else as in Pong.py, same random rallies for every value."""
    rows = []
    for value in values:
        args = value if isinstance(value, tuple) else (value,)
        summary = h.summarize(h.run_rallies(method, RALLIES, make_configure(*args), seed=SEED))
        rows.append({label: "/".join(map(str, args)), **summary})
        print(f"  {name} {label}={rows[-1][label]}: player losses {summary['player_losses']}, "
              f"opponent losses {summary['opponent_losses']}")
    save_csv(name, rows)
    return rows


if __name__ == "__main__":
    RESULTS.mkdir(exist_ok=True)
    started = time.time()
    save_json("meta", {
        "python": platform.python_version(),
        "packages": {p: version(p) for p in ("pygame", "scikit-fuzzy", "numpy", "scipy", "networkx")},
        "fps": h.Pong.FPS, "board": [h.BOARD_WIDTH, h.BOARD_HEIGHT],
        "rallies_per_setting": RALLIES, "seed": SEED,
        "defaults": {"edge_offset": h.Pong.FuzzyPlayer.edge_offset, "gains": [0.25, 0.15],
                     "edge_stop_gain": 1.0, "near_far": [100, 250]},
    })
    print("matches");             matches()
    print("prediction accuracy"); prediction_accuracy()
    print("dead zone");           dead_zone()
    print("baseline rallies");    baseline()
    print("sweeps")
    sweep("sweep_edge_offset", "edge", [30, 32, 35, 38, 40, 42, 45, 48, 50], with_edge_offset, "edge_offset")
    sweep("sweep_edge_stop_gain", "edge", [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5], with_edge_stop_gain, "stop_gain")
    sweep("sweep_gains", "tsk", [(0.1, 0.06), (0.15, 0.09), (0.25, 0.15), (0.4, 0.24), (0.6, 0.36), (1.0, 0.6)],
          with_gains, "fast/slow")
    sweep("sweep_near_far", "tsk", [(25, 75), (50, 150), (100, 250), (150, 350), (250, 400)],
          with_near_far, "near_end/far_full")
    print(f"done in {time.time() - started:.0f} s")
