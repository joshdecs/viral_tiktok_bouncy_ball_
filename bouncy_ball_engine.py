import math
import random
from collections import deque
from dataclasses import dataclass

import pygame


# Config

WIDTH, HEIGHT = 800, 600
FPS = 120

# Arena circle
MARGIN = 50  # padding to window
ARENA_COLOR = (255, 255, 255)
BG_COLOR = (0, 0, 0)

# Ball visuals / physics
BALL_BASE_RADIUS = 15
BALL_MAX_RATIO = 0.8  # cap at 80% of arena radius
GROWTH_PER_SEC = 12.0  # pixels per second until cap
RESTIUTION = 0.95      # energy kept after bounce (normal component)
TANGENTIAL_FRICTION = 0.99  # friction applied to tangential component on bounce
LINEAR_FRICTION = 0.999     # tiny air friction per frame on velocity
GRAVITY = 200.0             # px/s^2 downward

# Trails
TRAIL_LEN = 140                  # tail positions kept for motion trail
IMPACT_LIFETIME = 0.6            # seconds
IMPACT_WIDTH = 2
TRAIL_WIDTH = 2

# Color cycling
COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255),
    (255, 255, 0), (255, 0, 255), (0, 255, 255),
]


@dataclass
class Arena:
    cx: float
    cy: float
    radius: float

    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, ARENA_COLOR, (int(self.cx), int(self.cy)), int(self.radius), 2)


class TrailManager:
    """Keeps a motion trail and discrete 'impact strings' on collisions."""
    def __init__(self):
        self.motion_trail = deque(maxlen=TRAIL_LEN)  # [(x, y)]
        self.impacts: list[tuple[tuple[float, float], float, tuple[int, int, int]]] = []

    def push_position(self, x: float, y: float):
        self.motion_trail.append((x, y))

    def add_impact(self, pos: tuple[float, float], color: tuple[int, int, int]):
        self.impacts.append((pos, IMPACT_LIFETIME, color))

    def update(self, dt: float):
        alive = []
        for (pos, t, col) in self.impacts:
            t -= dt
            if t > 0:
                alive.append((pos, t, col))
        self.impacts = alive

    def draw(self, surface: pygame.Surface, ball_pos: tuple[float, float], color: tuple[int, int, int]):
        bx, by = ball_pos
        for (pos, t, col) in self.impacts:
            alpha = max(0, min(255, int(255 * (t / IMPACT_LIFETIME))))
            tmp = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.line(tmp, (*col, alpha), pos, (bx, by), IMPACT_WIDTH)
            surface.blit(tmp, (0, 0))

        if len(self.motion_trail) > 1:
            pts = list(self.motion_trail)
            for i in range(1, len(pts)):
                fade = i / len(pts)
                alpha = int(180 * fade)
                tmp = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                pygame.draw.line(tmp, (*color, alpha), pts[i - 1], pts[i], TRAIL_WIDTH)
                surface.blit(tmp, (0, 0))


class Ball:
    def __init__(self, arena: Arena):
        self.x = arena.cx
        self.y = arena.cy - arena.radius * 0.5
        ang = random.uniform(-math.pi, math.pi)
        speed = 250.0
        self.vx = speed * math.cos(ang)
        self.vy = -150.0  

        self.radius = BALL_BASE_RADIUS
        self.color_index = 0

        self.arena = arena
        self.trails = TrailManager()

    @property
    def color(self) -> tuple[int, int, int]:
        return COLORS[self.color_index]

    def cycle_color(self):
        self.color_index = (self.color_index + 1) % len(COLORS)

    def _reflect_on_circle(self, normal_x: float, normal_y: float):
        """
        Reflect the velocity on a circular boundary, applying normal restitution
        and tangential friction. n must be normalized.
        """
        vn = self.vx * normal_x + self.vy * normal_y
        vt_x = self.vx - vn * normal_x
        vt_y = self.vy - vn * normal_y

        vn_reflected = -vn * RESTIUTION
        vt_x *= TANGENTIAL_FRICTION
        vt_y *= TANGENTIAL_FRICTION

        self.vx = vn_reflected * normal_x + vt_x
        self.vy = vn_reflected * normal_y + vt_y

    def update(self, dt: float):
        self.vy += GRAVITY * dt

        self.vx *= LINEAR_FRICTION
        self.vy *= LINEAR_FRICTION

        self.x += self.vx * dt
        self.y += self.vy * dt

        target_max = self.arena.radius * BALL_MAX_RATIO
        if self.radius < target_max:
            self.radius = min(target_max, self.radius + GROWTH_PER_SEC * dt)

        dx = self.x - self.arena.cx
        dy = self.y - self.arena.cy
        dist = math.hypot(dx, dy)
        max_dist = self.arena.radius - self.radius

        if dist > max_dist:
            if dist == 0:
                nx, ny = 1.0, 0.0
            else:
                nx, ny = dx / dist, dy / dist

            self.x = self.arena.cx + nx * max_dist
            self.y = self.arena.cy + ny * max_dist

            self._reflect_on_circle(nx, ny)

            self.trails.add_impact((self.x, self.y), self.color)

            self.cycle_color()

        self.trails.push_position(self.x, self.y)
        self.trails.update(dt)

    def draw(self, surface: pygame.Surface):
        self.trails.draw(surface, (self.x, self.y), self.color)
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Bouncing Ball — Smooth Physics")
        self.window = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        cx, cy = WIDTH // 2, HEIGHT // 2
        radius = min(WIDTH, HEIGHT) // 2 - MARGIN
        self.arena = Arena(cx, cy, radius)
        self.ball = Ball(self.arena)

        self.running = True

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  
            self._handle_events()
            self._update(dt)
            self._draw()

        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False

    def _update(self, dt: float):
        self.ball.update(dt)

    def _draw(self):
        self.window.fill(BG_COLOR)
        self.arena.draw(self.window)
        self.ball.draw(self.window)
        pygame.display.flip()


if __name__ == "__main__":
    App().run()
