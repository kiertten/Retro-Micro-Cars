"""
Трасса: чтение символьной матрицы, определение покрытия и отрисовка.

Трасса - матрица строк. Обычно её передаёт data_io.load_track() (файл
track.txt); по умолчанию используется DEFAULT_TRACK_LAYOUT из constants.py.
Символы:
    '#' - асфальт, '.' - трава, 'F' - финишная линия.
"""

import pygame

from py_retro_cars.constants import (
    COLORS,
    GRID_COLUMNS,
    GRID_ROWS,
    TILE_SIZE,
    DEFAULT_TRACK_LAYOUT,
)


class Track:
    """Хранит матрицу трассы и умеет отвечать «что находится в точке (x, y)»."""

    def __init__(self, layout=None):
        self.layout = layout if layout is not None else DEFAULT_TRACK_LAYOUT
        # Прямоугольники финишных плиток - для детекта пересечения линии.
        self.finish_rects = [
            pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            for r, row in enumerate(self.layout)
            for c, ch in enumerate(row)
            if ch == "F"
        ]
        # Фон трассы рисуется один раз и затем только копируется на экран.
        self.surface = self._render()

    def tile_at(self, px, py):
        """Возвращает символ плитки по пиксельным координатам ('.' вне окна)."""
        gx = int(px // TILE_SIZE)
        gy = int(py // TILE_SIZE)
        if 0 <= gx < GRID_COLUMNS and 0 <= gy < GRID_ROWS:
            return self.layout[gy][gx]
        return "."

    def is_drivable(self, px, py):
        """True, если в точке асфальт или финиш (не трава)."""
        return self.tile_at(px, py) in ("#", "F")

    def is_grass(self, px, py):
        """True, если в точке трава (в том числе вне окна)."""
        return self.tile_at(px, py) == "."

    def on_finish(self, px, py):
        """True, если точка лежит на финишной линии."""
        return self.tile_at(px, py) == "F"

    def _render(self):
        """Один раз отрисовывает всю трассу на отдельную поверхность."""
        surface = pygame.Surface((GRID_COLUMNS * TILE_SIZE, GRID_ROWS * TILE_SIZE))
        for r, row in enumerate(self.layout):
            for c, ch in enumerate(row):
                rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if ch == ".":
                    pygame.draw.rect(surface, COLORS["grass"], rect)
                else:
                    pygame.draw.rect(surface, COLORS["asphalt"], rect)
                if ch == "F":
                    self._draw_checkers(surface, rect)
        return surface

    @staticmethod
    def _draw_checkers(surface, rect):
        """Рисует шахматный узор финишной линии 4x4 в пределах плитки."""
        cell = rect.width // 4
        for i in range(4):
            for j in range(4):
                color = COLORS["finish_a"] if (i + j) % 2 == 0 else COLORS["finish_b"]
                pygame.draw.rect(
                    surface, color,
                    (rect.x + i * cell, rect.y + j * cell, cell, cell),
                )

    def draw(self, surface):
        """Копирует готовую трассу на экран."""
        surface.blit(self.surface, (0, 0))
