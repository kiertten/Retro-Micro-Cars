"""
Класс гоночной машины.

Машина хранит состояние (координаты, угол, скорость, вектор движения),
принимает управление с клавиатуры и рисует спрайт, повёрнутый на угол theta.
Сама математика вынесена в physics.py.
"""

import math

import pygame

from py_retro_cars import physics
from py_retro_cars.constants import (
    CAR_LENGTH,
    CAR_WIDTH,
    COLORS,
    GRASS_GRIP_K,
    GRASS_MAX_SPEED,
    GRIP_K,
    MAX_SPEED,
    START_ANGLE,
    START_POSITION,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)


class Car:
    """Машина, которой управляет игрок."""

    def __init__(self, x=START_POSITION[0], y=START_POSITION[1], theta=START_ANGLE):
        self.x = float(x)           # координаты центра
        self.y = float(y)
        self.theta = theta          # угол кузова, рад (0 - вправо, ось Y вниз)
        self.speed = 0.0            # линейная скорость вдоль кузова
        self.vx = 0.0               # фактический вектор движения
        self.vy = 0.0
        self.grip_k = GRIP_K        # коэффициент сцепления K
        self.drifting = False       # флаг заноса (для HUD и следов)
        self.on_grass = False       # True, если центр машины на траве
        self.base_sprite = self._build_sprite()

    # ------------------------------------------------------------
    # Спрайт
    # ------------------------------------------------------------
    @staticmethod
    def _build_sprite():
        """Рисует машинку в горизонтальном положении (нос смотрит вправо)."""
        sprite = pygame.Surface((CAR_LENGTH, CAR_WIDTH), pygame.SRCALPHA)
        # Колёса - четыре тёмных прямоугольника по углам кузова.
        for wx in (3, CAR_LENGTH - 10):
            for wy in (0, CAR_WIDTH - 4):
                pygame.draw.rect(sprite, COLORS["wheel"], (wx, wy, 7, 4))
        # Кузов, крыша и лобовое стекло.
        pygame.draw.rect(sprite, COLORS["car_body"], (0, 2, CAR_LENGTH, CAR_WIDTH - 4), border_radius=4)
        pygame.draw.rect(sprite, COLORS["car_roof"], (8, 4, 10, CAR_WIDTH - 8), border_radius=2)
        pygame.draw.rect(sprite, COLORS["car_glass"], (18, 4, 5, CAR_WIDTH - 8), border_radius=1)
        return sprite

    # ------------------------------------------------------------
    # Геометрия
    # ------------------------------------------------------------
    def corners(self, x=None, y=None):
        """Координаты четырёх углов кузова с учётом поворота (для коллизий)."""
        cx = self.x if x is None else x
        cy = self.y if y is None else y
        cos_t, sin_t = math.cos(self.theta), math.sin(self.theta)
        half_l, half_w = CAR_LENGTH / 2, CAR_WIDTH / 2
        points = []
        for lx, ly in ((half_l, half_w), (half_l, -half_w), (-half_l, half_w), (-half_l, -half_w)):
            points.append((cx + lx * cos_t - ly * sin_t, cy + lx * sin_t + ly * cos_t))
        return points

    def rear_wheels(self):
        """Позиции задних колёс - здесь остаются следы протектора."""
        cos_t, sin_t = math.cos(self.theta), math.sin(self.theta)
        back = -CAR_LENGTH / 2 + 5
        side = CAR_WIDTH / 2 - 2
        return [
            (self.x + back * cos_t - s * side * sin_t, self.y + back * sin_t + s * side * cos_t)
            for s in (1, -1)
        ]

    # ------------------------------------------------------------
    # Обновление
    # ------------------------------------------------------------
    def update(self, keys, track):
        """
        Один шаг симуляции.

        keys  - объект, поддерживающий keys[pygame.K_x] (результат get_pressed)
        track - Track: по нему определяется покрытие под машиной
        """
        throttle = keys[pygame.K_w] or keys[pygame.K_UP]
        brake = keys[pygame.K_s] or keys[pygame.K_DOWN]
        steer = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (
            1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0
        )

        # 0) покрытие под центром машины определяет K и предел скорости:
        #    на траве оба параметра принудительно снижаются (ЛР 2).
        self.on_grass = track.is_grass(self.x, self.y)
        self.grip_k = GRASS_GRIP_K if self.on_grass else GRIP_K
        max_speed = GRASS_MAX_SPEED if self.on_grass else MAX_SPEED

        # 1) скорость, 2) угол кузова, 3) вектор движения с учётом сцепления K
        self.speed = physics.update_speed(self.speed, throttle, brake, max_speed)
        self.theta = physics.update_heading(self.theta, self.speed, steer)
        self.vx, self.vy = physics.update_velocity(self.vx, self.vy, self.theta, self.speed, self.grip_k)

        # 4) занос: определяем флаг и теряем часть скорости
        self.drifting = physics.is_drifting(self.vx, self.vy, self.theta)
        self.speed = physics.apply_drift_loss(self.speed, self.drifting)

        # 5) перемещение. Трава не блокирует машину (в ней нельзя застрять);
        #    удерживаем только в границах окна.
        self.x += self.vx
        self.y += self.vy
        margin = max(CAR_LENGTH, CAR_WIDTH) / 2
        if self.x < margin or self.x > WINDOW_WIDTH - margin:
            self.x = min(max(self.x, margin), WINDOW_WIDTH - margin)
            self.vx = 0.0
        if self.y < margin or self.y > WINDOW_HEIGHT - margin:
            self.y = min(max(self.y, margin), WINDOW_HEIGHT - margin)
            self.vy = 0.0

    @property
    def velocity(self):
        """Модуль фактической скорости (для HUD)."""
        return math.hypot(self.vx, self.vy)

    @property
    def slip_degrees(self):
        """Угол заноса в градусах (для HUD)."""
        return math.degrees(physics.slip_angle(self.vx, self.vy, self.theta))

    # ------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------
    def draw(self, surface):
        """Рисует спрайт, повёрнутый на угол theta."""
        # В Pygame положительный угол вращает против часовой, а ось Y направлена
        # вниз, поэтому передаём -theta в градусах.
        rotated = pygame.transform.rotate(self.base_sprite, -math.degrees(self.theta))
        surface.blit(rotated, rotated.get_rect(center=(self.x, self.y)))
