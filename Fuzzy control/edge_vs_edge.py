#!/usr/bin/env python3
# Two FuzzyPlayer controllers in edge mode playing against each other
import pygame

from Pong import Ball, FuzzyPlayer, PongGame

PADDLE_MAX_SPEED = float("inf")
BALL_MAX_SPEED = 20


class BottomEdgePlayer(FuzzyPlayer):
    method = "edge"


class TopEdgePlayer(FuzzyPlayer):

    method = "edge"

    def predict_impact_x(self) -> int:
        ball = self.ball
        x, y = ball.rect.x, ball.rect.y
        x_speed, y_speed = ball.x_speed, ball.y_speed
        right_wall = self.board.surface.get_width() - ball.rect.width
        bottom_paddle_top = self.board.surface.get_height() - self.racket.rect.height
        for _ in range(1000):
            x += round(x_speed)
            y += round(y_speed)
            if x < 0 or x > right_wall:
                x_speed *= -1
            if y_speed < 0 and y < self.racket.rect.bottom:
                return x + ball.rect.width // 2
            if y_speed > 0 and y + ball.rect.height > bottom_paddle_top:
                y_speed *= -1
        return ball.rect.centerx

    def choose_target(self) -> int:
        impact_x = self.predict_impact_x()
        if self.ball.y_speed > 0:
            # the opponent may change the ball speed
            return impact_x

        # the paddle centre must stay on the board
        half = self.racket.rect.width // 2
        width = self.board.surface.get_width()
        candidates = [
            x
            for x in (impact_x - self.edge_offset, impact_x + self.edge_offset)
            if half <= x <= width - half
        ]
        if not candidates:
            # a fast ball can overshoot a side wall for one frame
            return max(half, min(impact_x, width - half))
        # pick the edge that needs the shortest move
        return min(candidates, key=lambda x: abs(x - self.racket.rect.centerx))

    def act(self, x_diff: int, y_diff: int):
        # y_diff is negative above the ball, the fuzzy sets expect a distance >= 0
        super().act(x_diff, -y_diff)


score = {"top": 0, "bottom": 0}
ball_reset = Ball.reset


def reset_and_score(ball: Ball):
    winner = "bottom" if ball.rect.y < 0 else "top"
    score[winner] += 1
    print(f"point for {winner:6s}  ball speed {abs(ball.x_speed):5.2f}  "
          f"score top {score['top']} - {score['bottom']} bottom")
    pygame.display.set_caption(f"Edge vs edge   top {score['top']} - {score['bottom']} bottom")
    ball_reset(ball)


ball_bounce_y_power = Ball.bounce_y_power


def bounce_y_power_capped(ball: Ball):
    red, green, blue = ball.color
    ball.color = (red, min(green, 245), blue)
    ball_bounce_y_power(ball)
    ball.x_speed = max(-BALL_MAX_SPEED, min(ball.x_speed, BALL_MAX_SPEED))
    ball.y_speed = max(-BALL_MAX_SPEED, min(ball.y_speed, BALL_MAX_SPEED))


if __name__ == "__main__":
    Ball.reset = reset_and_score
    Ball.bounce_y_power = bounce_y_power_capped
    game = PongGame(800, 400, TopEdgePlayer, BottomEdgePlayer)
    # the controllers read racket.max_speed on every frame
    for paddle in (game.opponent_paddle, game.player_paddle):
        paddle.max_speed = PADDLE_MAX_SPEED
    pygame.display.set_caption("Edge vs edge   top 0 - 0 bottom")
    game.run()
