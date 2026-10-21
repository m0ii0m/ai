"""Headless Pong runs for FuzzyPlayer (bottom) against NaiveOponent (top).

Pong.py is not modified: the harness wraps a few Ball methods to count events,
replaces the pygame clock with a frame counter, and lets each experiment adjust
the player after it is created.
"""
import os
import random
import sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"  # no window
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402
import Pong  # noqa: E402

BOARD_WIDTH, BOARD_HEIGHT = 800, 400

# simulated clock: frame n happens at n / FPS seconds, so the collision cooldown keeps its length
clock = {"frame": 0}
pygame.time.get_ticks = lambda: clock["frame"] * 1000 // Pong.FPS


class Events:
    """What happened since the last clear()."""

    def clear(self):
        self.loser = None
        self.speed_at_loss = 0.0
        self.edge_hits = {"player": 0, "opponent": 0}

    def __init__(self):
        self.clear()


events = Events()
_reset = Pong.Ball.reset
_bounce_y_power = Pong.Ball.bounce_y_power


def _side(ball):
    return "player" if ball.rect.y > BOARD_HEIGHT // 2 else "opponent"


def _counting_reset(ball):
    events.loser = _side(ball)
    events.speed_at_loss = abs(ball.x_speed)
    _reset(ball)


def _counting_bounce_y_power(ball):
    events.edge_hits[_side(ball)] += 1
    # Ball.bounce_y_power adds 10 to the green channel up to 260, which pygame rejects
    red, green, blue = ball.color
    ball.color = (red, min(green, 245), blue)
    _bounce_y_power(ball)


Pong.Ball.reset = _counting_reset
Pong.Ball.bounce_y_power = _counting_bounce_y_power


def new_game(method, configure=None):
    """A fresh game; `configure(player)` may change the controller before play."""
    Pong.FuzzyPlayer.method = method
    game = Pong.PongGame(BOARD_WIDTH, BOARD_HEIGHT, Pong.NaiveOponent, Pong.FuzzyPlayer)
    if configure:
        configure(game.player)
    return game


def step(game):
    """One frame, in the same order as PongGame.run."""
    clock["frame"] += 1
    game.ball.move(game.board, game.player_paddle, game.opponent_paddle)
    for p in (game.oponent, game.player):
        p.act(p.racket.rect.centerx - game.ball.rect.centerx,
              p.racket.rect.centery - game.ball.rect.centery)


def run_match(method, seconds=300, configure=None):
    """The real game, from the real starting position, for `seconds` of play."""
    game = new_game(method, configure)
    points = []   # (time [s], loser, ball speed)
    edge_hits = {"player": 0, "opponent": 0}
    events.clear()
    for frame in range(seconds * Pong.FPS):
        step(game)
        if events.loser:
            points.append((round(frame / Pong.FPS, 1), events.loser, round(events.speed_at_loss, 2)))
            for side in edge_hits:
                edge_hits[side] += events.edge_hits[side]
            events.clear()
    for side in edge_hits:
        edge_hits[side] += events.edge_hits[side]
    return {"points": points, "edge_hits": edge_hits}


def run_rallies(method, rallies=200, configure=None, seed=0, max_seconds=600):
    """Rallies from random starts; every start sends the ball to the opponent first.

    The same seed gives the same starts, so settings are compared on the same rallies.
    """
    rng = random.Random(seed)
    game = new_game(method, configure)
    ball = game.ball
    results = []
    for _ in range(rallies):
        speed = rng.uniform(3, 6)
        ball.rect.x = rng.randint(100, BOARD_WIDTH - 120)
        ball.rect.y = rng.randint(150, 230)
        ball.x_speed = speed * rng.choice((-1, 1))
        ball.y_speed = -speed                      # towards the opponent
        game.player_paddle.rect.x = rng.randint(0, BOARD_WIDTH - 80)
        game.opponent_paddle.rect.x = rng.randint(0, BOARD_WIDTH - 80)
        clock["frame"] += 1000                     # leave any collision cooldown behind
        events.clear()
        touched = {"player": False, "opponent": False}
        player_returns = 0
        start = clock["frame"]
        while events.loser is None and clock["frame"] - start < max_seconds * Pong.FPS:
            y_speed = ball.y_speed
            step(game)
            if events.loser is None and (y_speed > 0) != (ball.y_speed > 0):
                touched["player" if y_speed > 0 else "opponent"] = True
                player_returns += y_speed > 0
        results.append({
            "loser": events.loser,                          # None: rally still going at max_seconds
            "first_pass": events.loser is not None and not touched[events.loser],
            "speed_at_loss": round(events.speed_at_loss, 2),
            "seconds": round((clock["frame"] - start) / Pong.FPS, 1),
            "returns_player": player_returns,
            "edge_hits_player": events.edge_hits["player"],
            "edge_hits_opponent": events.edge_hits["opponent"],
        })
    return results


def summarize(rallies):
    """Counts and averages over a list returned by run_rallies."""
    in_rally = [r for r in rallies if r["loser"] and not r["first_pass"]]
    player_losses = [r for r in in_rally if r["loser"] == "player"]
    opponent_losses = [r for r in in_rally if r["loser"] == "opponent"]
    returns = sum(r["returns_player"] for r in rallies)
    edge_hits = sum(r["edge_hits_player"] for r in rallies)

    def mean(values):
        return round(sum(values) / len(values), 2) if values else None

    return {
        "rallies": len(rallies),
        "first_pass_player": sum(r["first_pass"] and r["loser"] == "player" for r in rallies),
        "first_pass_opponent": sum(r["first_pass"] and r["loser"] == "opponent" for r in rallies),
        "unfinished": sum(r["loser"] is None for r in rallies),
        "player_losses": len(player_losses),
        "opponent_losses": len(opponent_losses),
        "player_loss_rate": round(len(player_losses) / len(in_rally), 3) if in_rally else None,
        "speed_at_player_loss_mean": mean([r["speed_at_loss"] for r in player_losses]),
        "speed_at_player_loss_min": min((r["speed_at_loss"] for r in player_losses), default=None),
        "speed_at_opponent_loss_mean": mean([r["speed_at_loss"] for r in opponent_losses]),
        "rally_seconds_mean": mean([r["seconds"] for r in in_rally]),
        "player_returns": returns,
        "player_edge_hit_rate": round(edge_hits / returns, 3) if returns else None,
    }
