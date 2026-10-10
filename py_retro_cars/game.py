"""
Основной игровой цикл и логика гонки.

Игра - конечный автомат из трёх состояний (MENU -> PLAY -> OVER).
Класс Game хранит состояние гонки, а функция main() создаёт окно
и крутит цикл: события -> обновление -> отрисовка.
"""

import sys

import pygame

from py_retro_cars.car import Car
from py_retro_cars.constants import (
    FPS,
    STATE_MENU,
    STATE_OVER,
    STATE_PLAY,
    TOTAL_LAPS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from py_retro_cars.skid_marks import SkidMarks
from py_retro_cars.track import Track
from py_retro_cars.ui import draw_game_over, draw_hud, draw_menu

# Матрица трассы делится на нижнюю половину (y > этого значения):
# проезд через неё засчитывается как контрольная точка круга.
CHECKPOINT_Y = 440


class Game:
    """Состояние гонки: машина, трасса, круги, таймеры."""

    def __init__(self):
        self.track = Track()
        self.skids = SkidMarks()
        self.state = STATE_MENU
        self.reset()

    def reset(self):
        """Подготавливает новый заезд."""
        self.car = Car()
        self.skids.clear()
        self.lap = 0                 # число завершённых кругов
        self.lap_frames = 0          # время текущего круга (в кадрах)
        self.total_frames = 0        # общее время заезда
        self.best_lap_frames = 0     # лучший круг (0 - ещё нет)
        self.checkpoint_passed = False
        self.was_on_finish = False

    # ------------------------------------------------------------
    def handle_event(self, event):
        """Обработка одиночных событий клавиатуры (смена состояний)."""
        if event.type != pygame.KEYDOWN:
            return
        match self.state:
            case "MENU":
                self.reset()
                self.state = STATE_PLAY
            case "OVER":
                if event.key == pygame.K_r:
                    self.state = STATE_MENU
            case "PLAY":
                if event.key == pygame.K_r:
                    self.state = STATE_MENU

    def update(self, keys):
        """Один кадр симуляции (только в состоянии PLAY)."""
        if self.state != STATE_PLAY:
            return

        self.car.update(keys, self.track)
        self.lap_frames += 1
        self.total_frames += 1

        # Следы протектора оставляем только в заносе и только на асфальте.
        if self.car.drifting:
            for wx, wy in self.car.rear_wheels():
                self.skids.add(wx, wy)
        self.skids.update()

        self._check_laps()

    def _check_laps(self):
        """Считает круги: контрольная точка внизу + пересечение финиша вперёд."""
        if self.car.y > CHECKPOINT_Y:
            self.checkpoint_passed = True

        on_finish = self.track.on_finish(self.car.x, self.car.y)
        crossed = on_finish and not self.was_on_finish
        self.was_on_finish = on_finish

        # Круг засчитывается, если проехали контрольную точку и едем вправо
        # (по трассе - по часовой стрелке), а не катаемся туда-сюда по финишу.
        if crossed and self.checkpoint_passed and self.car.vx > 0:
            self.lap += 1
            if self.best_lap_frames == 0 or self.lap_frames < self.best_lap_frames:
                self.best_lap_frames = self.lap_frames
            self.lap_frames = 0
            self.checkpoint_passed = False
            if self.lap >= TOTAL_LAPS:
                self.state = STATE_OVER

    def draw(self, screen, fonts):
        """Отрисовка текущего состояния."""
        if self.state == STATE_MENU:
            draw_menu(screen, fonts)
            return
        self.track.draw(screen)
        self.skids.draw(screen)
        self.car.draw(screen)
        draw_hud(screen, fonts, self.car, self.lap, self.lap_frames, self.best_lap_frames)
        if self.state == STATE_OVER:
            draw_game_over(screen, fonts, self.total_frames, self.best_lap_frames)


def main():
    """Создаёт окно и запускает игровой цикл."""
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Retro Micro Cars - ЛР 1")
    clock = pygame.time.Clock()
    fonts = {
        "tiny": pygame.font.Font(None, 20),
        "small": pygame.font.Font(None, 26),
        "mid": pygame.font.Font(None, 34),
        "big": pygame.font.Font(None, 56),
        "huge": pygame.font.Font(None, 96),
    }
    game = Game()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            game.handle_event(event)

        game.update(pygame.key.get_pressed())
        game.draw(screen, fonts)
        pygame.display.flip()
        clock.tick(FPS)
