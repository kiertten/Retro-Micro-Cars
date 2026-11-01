"""
Основной игровой цикл и логика гонки.

Игра - конечный автомат: MENU -> PLAY -> NAME -> OVER -> MENU.
    MENU - стартовый экран с таблицей рекордов
    PLAY - заезд
    NAME - ввод имени игрока после финиша
    OVER - итоги и таблица рекордов

Класс Game хранит состояние гонки, а функция main() создаёт окно
и крутит цикл: события -> обновление -> отрисовка.
Работа с файлами (трасса, рекорды, лог) вынесена в data_io.py.
"""

import sys
import hashlib

import pygame

from py_retro_cars import data_io
from py_retro_cars.car import Car
from py_retro_cars.constants import (
    DEFAULT_PLAYER_NAME,
    FPS,
    NAME_MAX_LEN,
    STATE_MENU,
    STATE_NAME,
    STATE_OVER,
    STATE_PLAY,
    TOTAL_LAPS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from py_retro_cars.data_io import logger
from py_retro_cars.skid_marks import SkidMarks
from py_retro_cars.track import Track
from py_retro_cars.timing import reference_route
from py_retro_cars.ui import draw_game_over, draw_hud, draw_menu, draw_name_input

# Проезд ниже этой линии (пиксели по Y) засчитывается как контрольная точка круга.
CHECKPOINT_Y = 440

# Занос короче этого числа кадров (~0.25 с) в лог не попадает.
DRIFT_LOG_FRAMES = 15


class Game:
    """Состояние гонки: машина, трасса, круги, таймеры, рекорды."""

    def __init__(self, track_path=data_io.TRACK_FILE, records_path=data_io.RECORDS_FILE):
        # Трасса читается из track.txt; при проблемах - запасная (см. data_io).
        self.track = Track(data_io.load_track(track_path))
        self.track_id = hashlib.sha256("\n".join(self.track.layout).encode("utf-8")).hexdigest()
        try:
            self.sector_route = reference_route(self.track.layout)
        except ValueError:
            self.sector_route = []
            logger.warning("Для этой формы трассы секторные ворота не определены")
        self.records_path = records_path
        self.records = data_io.load_records(records_path)
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
        self.timing_started = False
        self.sector_crossings = []
        self.best_lap_sectors = None
        self._sector_previous_position = (self.car.x,self.car.y)
        self._sector_previous_frame = 0
        self.checkpoint_passed = False
        self.was_on_finish = False
        self.name_input = ""         # вводимое имя игрока
        self.saved_ok = None         # результат сохранения рекорда
        self._drift_frames = 0       # сколько кадров подряд длится занос
        self._drift_logged = False   # занос уже записан в лог
        self._was_on_grass = False

    # ------------------------------------------------------------
    def handle_event(self, event):
        """Обработка одиночных событий клавиатуры (смена состояний, ввод имени)."""
        if event.type != pygame.KEYDOWN:
            return
        match self.state:
            case "MENU":
                self.reset()
                self.state = STATE_PLAY
                logger.info("Старт заезда")
            case "PLAY":
                if event.key == pygame.K_r:
                    logger.info("Заезд прерван игроком")
                    self.state = STATE_MENU
            case "NAME":
                self._handle_name_key(event)
            case "OVER":
                if event.key == pygame.K_r:
                    self.state = STATE_MENU

    def _handle_name_key(self, event):
        """Ввод имени: Enter - сохранить, Backspace - стереть, остальное - текст."""
        if event.key == pygame.K_RETURN:
            self._save_result()
        elif event.key == pygame.K_BACKSPACE:
            self.name_input = self.name_input[:-1]
        elif event.unicode and event.unicode.isprintable() and len(self.name_input) < NAME_MAX_LEN:
            self.name_input += event.unicode

    def _save_result(self):
        """Записывает результат в records.json и переходит на экран итогов."""
        name = self.name_input.strip() or DEFAULT_PLAYER_NAME
        saved = data_io.save_record(
            name, self.best_lap_frames / FPS, self.total_frames / FPS, self.records_path,
            sectors=self.best_lap_sectors, track_id=self.track_id
        )
        self.saved_ok = saved is not None
        if saved is not None:
            self.records = saved
        self.state = STATE_OVER

    def update(self, keys):
        """Один кадр симуляции (только в состоянии PLAY)."""
        if self.state != STATE_PLAY:
            return

        self.car.update(keys, self.track)
        if self.timing_started:
            self.lap_frames += 1
            self.total_frames += 1

        # Следы протектора - только при заносе на асфальте.
        if self.car.drifting and not self.car.on_grass:
            for wx, wy in self.car.rear_wheels():
                self.skids.add(wx, wy)
        self.skids.update()

        self._log_transitions()
        self._check_laps()

    def _log_transitions(self):
        """
        Пишет в лог занос и въезд/выезд на траву - только смену состояния.

        Занос логируется, когда длится больше DRIFT_LOG_FRAMES кадров подряд:
        так короткие дребезжания на пороге угла не засоряют лог.
        """
        self._drift_frames = self._drift_frames + 1 if self.car.drifting else 0
        if self._drift_frames == DRIFT_LOG_FRAMES:
            logger.info("Занос: скорость %.1f, угол %.0f°", self.car.velocity, self.car.slip_degrees)
            self._drift_logged = True
        elif self._drift_frames == 0 and self._drift_logged:
            logger.info("Занос закончился")
            self._drift_logged = False
        if self.car.on_grass != self._was_on_grass:
            logger.info("Машина %s трассу", "покинула" if self.car.on_grass else "вернулась на")
            self._was_on_grass = self.car.on_grass

    def _check_laps(self):
        """Считает круги: контрольная точка внизу + пересечение финиша вправо."""
        # Две горизонтальные границы на середине высоты дорожного кольца:
        # справа пересечение сверху вниз, слева — снизу вверх. Покрытие
        # не влияет на замер: игра разрешает ехать по траве.
        position = (self.car.x, self.car.y)
        if self.sector_route and self.timing_started and len(self.sector_crossings) < 2:
            center_x = (min(p[0] for p in self.sector_route)+max(p[0] for p in self.sector_route)+1)*20
            center_y = (min(p[1] for p in self.sector_route)+max(p[1] for p in self.sector_route)+1)*20
            x0,y0 = self._sector_previous_position
            x1,y1 = position
            expected = len(self.sector_crossings)
            forward = (y0 < center_y <= y1) if expected == 0 else (y0 > center_y >= y1)
            if forward:
                fraction = (center_y-y0)/(y1-y0)
                crossing_x = x0+fraction*(x1-x0)
                correct_side = crossing_x >= center_x if expected == 0 else crossing_x < center_x
                if correct_side:
                    frames = self._sector_previous_frame+fraction*(self.lap_frames-self._sector_previous_frame)
                    self.sector_crossings.append(frames)
                    logger.info("Сектор S%s: отметка %.3f с",len(self.sector_crossings),frames/FPS)
        self._sector_previous_position = position
        self._sector_previous_frame = self.lap_frames
        if self.car.y > CHECKPOINT_Y:
            self.checkpoint_passed = True

        on_finish = self.track.on_finish(self.car.x, self.car.y)
        crossed = on_finish and not self.was_on_finish
        self.was_on_finish = on_finish

        if crossed and self.car.vx > 0 and not self.timing_started:
            self.timing_started = True
            self.lap_frames = self.total_frames = 0
            self._sector_previous_frame = 0
            self.checkpoint_passed = False
            self.sector_crossings = []
            logger.info("Хронометраж начат на финишной линии")
            return

        if crossed and self.checkpoint_passed and self.car.vx > 0:
            self.lap += 1
            logger.info("Круг %d завершён за %.2f с", self.lap, self.lap_frames / FPS)
            if self.best_lap_frames == 0 or self.lap_frames < self.best_lap_frames:
                self.best_lap_frames = self.lap_frames
                if len(self.sector_crossings)==2:
                    a,b = self.sector_crossings
                    self.best_lap_sectors = [round(v/FPS,3) for v in (a,b-a,self.lap_frames-b)]
                    if not all(v>0 for v in self.best_lap_sectors):
                        self.best_lap_sectors = None
                else:
                    self.best_lap_sectors = None
            self.lap_frames = 0
            self._sector_previous_frame = 0
            self.sector_crossings = []
            self.checkpoint_passed = False
            if self.lap >= TOTAL_LAPS:
                logger.info("Финиш: общее время %.2f с, лучший круг %.2f с",
                            self.total_frames / FPS, self.best_lap_frames / FPS)
                self.state = STATE_NAME

    def draw(self, screen, fonts):
        """Отрисовка текущего состояния."""
        if self.state == STATE_MENU:
            draw_menu(screen, fonts, self.records)
            return
        self.track.draw(screen)
        self.skids.draw(screen)
        self.car.draw(screen)
        draw_hud(screen, fonts, self.car, self.lap, self.lap_frames, self.best_lap_frames)
        if self.state == STATE_NAME:
            draw_name_input(screen, fonts, self.name_input, self.total_frames, self.best_lap_frames)
        elif self.state == STATE_OVER:
            draw_game_over(screen, fonts, self.total_frames, self.best_lap_frames,
                           self.records, self.saved_ok)


def main():
    """Создаёт окно и запускает игровой цикл."""
    data_io.setup_logging()
    logger.info("Игра запущена")
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Retro Micro Cars - ЛР 1–3")
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
                logger.info("Игра закрыта")
                pygame.quit()
                sys.exit()
            game.handle_event(event)

        game.update(pygame.key.get_pressed())
        game.draw(screen, fonts)
        pygame.display.flip()
        clock.tick(FPS)
