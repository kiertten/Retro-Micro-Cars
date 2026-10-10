"""
Следы протектора, которые остаются на асфальте при заносе.

Каждый след - точка с «временем жизни». Старые точки постепенно
бледнеют и удаляются, чтобы не накапливаться бесконечно.
"""

import pygame

from py_retro_cars.constants import (
    COLORS,
    SKID_LIFETIME_FRAMES,
    SKID_MAX_MARKS,
    SKID_WIDTH,
)


class SkidMarks:
    """Коллекция следов колёс с постепенным исчезновением."""

    def __init__(self):
        # Каждая запись: [x, y, оставшееся_время_жизни]
        self.marks = []

    def add(self, x, y):
        """Добавляет точку следа; при переполнении удаляет самые старые."""
        self.marks.append([x, y, SKID_LIFETIME_FRAMES])
        if len(self.marks) > SKID_MAX_MARKS:
            del self.marks[: len(self.marks) - SKID_MAX_MARKS]

    def update(self):
        """Уменьшает время жизни и отфильтровывает исчезнувшие следы."""
        for mark in self.marks:
            mark[2] -= 1
        # Списковое включение: оставляем только «живые» следы.
        self.marks = [m for m in self.marks if m[2] > 0]

    def clear(self):
        """Стирает все следы (при рестарте)."""
        self.marks = []

    def draw(self, surface):
        """Рисует следы полупрозрачными кругами: чем старше, тем бледнее."""
        size = SKID_WIDTH * 2
        dot = pygame.Surface((size, size), pygame.SRCALPHA)
        for x, y, life in self.marks:
            alpha = int(200 * life / SKID_LIFETIME_FRAMES)
            dot.fill((0, 0, 0, 0))
            pygame.draw.circle(dot, (*COLORS["skid"], alpha), (SKID_WIDTH, SKID_WIDTH), SKID_WIDTH)
            surface.blit(dot, (x - SKID_WIDTH, y - SKID_WIDTH))
