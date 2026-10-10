"""
Функции отрисовки интерфейса игры.

    - draw_menu        - стартовый экран с правилами и таблицей рекордов
    - draw_records     - таблица лучших кругов
    - draw_name_input  - ввод имени после финиша
    - draw_hud         - индикаторы во время заезда (скорость, круг, время, занос)
    - draw_game_over   - итоги заезда и таблица рекордов

Все функции принимают surface (поверхность Pygame) и рисуют на ней.
"""

import pygame

from py_retro_cars.constants import (
    COLORS,
    GAME_MESSAGES,
    MAX_SPEED,
    FPS,
    TOTAL_LAPS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from py_retro_cars.data_io import top_records


def format_time(frames, fps=60):
    """Переводит кадры в строку 'М:СС.сс'."""
    seconds = frames / fps
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def draw_text_centered(surface, text, y, font, color=None):
    """Рисует текст по центру окна по горизонтали."""
    rendered = font.render(text, True, color or COLORS["text"])
    surface.blit(rendered, (WINDOW_WIDTH // 2 - rendered.get_width() // 2, y))


def draw_panel(surface, rect, alpha=170):
    """Рисует полупрозрачную тёмную панель под текстом."""
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((10, 10, 10, alpha))
    surface.blit(panel, rect.topleft)


def draw_records(surface, fonts, records, x, y):
    """Рисует таблицу «Лучшие круги» (топ RECORDS_SHOWN) с левым краем x."""
    surface.blit(fonts["mid"].render(GAME_MESSAGES["records_title"], True, COLORS["accent"]), (x, y))
    shown = top_records(records)
    if not shown:
        surface.blit(fonts["small"].render(GAME_MESSAGES["records_empty"], True, COLORS["text"]), (x, y + 42))
        return
    for place, record in enumerate(shown, start=1):
        row_y = y + 42 + (place - 1) * 30
        label = f"{place}. {record['name']}"
        surface.blit(fonts["small"].render(label, True, COLORS["text"]), (x, row_y))
        lap = fonts["small"].render(format_time(record["best_lap"] * FPS), True, COLORS["good"])
        surface.blit(lap, (x + 300 - lap.get_width(), row_y))


def draw_menu(surface, fonts, records):
    """Стартовый экран: название, правила управления, таблица рекордов."""
    surface.fill(COLORS["bg"])
    draw_text_centered(surface, GAME_MESSAGES["title"], 40, fonts["big"], COLORS["car_body"])
    draw_text_centered(surface, GAME_MESSAGES["subtitle"], 95, fonts["mid"], COLORS["accent"])

    # Названия клавиш пишем словами: у стандартного шрифта Pygame нет стрелок.
    rules = [
        ("W / Вверх", "газ (разгон)"),
        ("S / Вниз", "тормоз, задний ход"),
        ("A / Влево", "руль влево"),
        ("D / Вправо", "руль вправо"),
        ("R", "вернуться в меню"),
    ]
    y = 170
    for key, text in rules:
        surface.blit(fonts["small"].render(key, True, COLORS["accent"]), (40, y))
        surface.blit(fonts["small"].render(text, True, COLORS["text"]), (190, y))
        y += 34

    draw_records(surface, fonts, records, 440, 160)

    draw_text_centered(
        surface, f"Проедьте {TOTAL_LAPS} круга по трассе, пересекая финиш.", 380, fonts["small"]
    )
    draw_text_centered(
        surface, "На траве сцепление и скорость падают, на скорости машину заносит.", 408, fonts["small"]
    )
    draw_text_centered(surface, GAME_MESSAGES["menu_hint"], WINDOW_HEIGHT - 70, fonts["mid"], COLORS["good"])


def draw_hud(surface, fonts, car, lap, lap_frames, best_lap_frames):
    """Индикаторы во время заезда."""
    # --- верхняя панель: круг и время ---
    draw_panel(surface, pygame.Rect(10, 10, 230, 78))
    surface.blit(fonts["small"].render(f"Круг: {min(lap + 1, TOTAL_LAPS)} / {TOTAL_LAPS}", True, COLORS["text"]), (20, 18))
    surface.blit(fonts["small"].render(f"Время: {format_time(lap_frames)}", True, COLORS["text"]), (20, 42))
    best = format_time(best_lap_frames) if best_lap_frames else "--:--.--"
    surface.blit(fonts["small"].render(f"Лучший: {best}", True, COLORS["accent"]), (20, 66))

    # --- нижняя панель: спидометр и угол заноса ---
    draw_panel(surface, pygame.Rect(10, WINDOW_HEIGHT - 70, 230, 60))
    ratio = min(1.0, car.velocity / MAX_SPEED)
    surface.blit(fonts["small"].render(f"Скорость: {int(car.velocity * 20)} км/ч", True, COLORS["text"]), (20, WINDOW_HEIGHT - 63))
    pygame.draw.rect(surface, (60, 60, 60), (20, WINDOW_HEIGHT - 38, 200, 10))
    bar_color = COLORS["danger"] if ratio > 0.85 else COLORS["good"]
    pygame.draw.rect(surface, bar_color, (20, WINDOW_HEIGHT - 38, int(200 * ratio), 10))
    surface.blit(fonts["tiny"].render(f"Угол заноса: {car.slip_degrees:4.0f}°", True, COLORS["text"]), (20, WINDOW_HEIGHT - 24))

    # --- подсказка: трава снижает сцепление и скорость ---
    if car.on_grass:
        draw_text_centered(surface, GAME_MESSAGES["grass"], WINDOW_HEIGHT - 30, fonts["small"], COLORS["accent"])

    # --- индикатор заноса ---
    if car.drifting:
        draw_text_centered(surface, GAME_MESSAGES["drift"], 20, fonts["big"], COLORS["danger"])


def draw_name_input(surface, fonts, name, total_frames, best_lap_frames):
    """Экран ввода имени после финиша: затемнение, итоги и поле ввода."""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    draw_text_centered(surface, GAME_MESSAGES["finish"], 100, fonts["huge"], COLORS["good"])
    draw_text_centered(surface, f"Общее время: {format_time(total_frames)}", 210, fonts["mid"])
    draw_text_centered(surface, f"Лучший круг: {format_time(best_lap_frames)}", 250, fonts["mid"], COLORS["accent"])
    draw_text_centered(surface, GAME_MESSAGES["enter_name"], 330, fonts["mid"])

    box = pygame.Rect(WINDOW_WIDTH // 2 - 160, 375, 320, 44)
    pygame.draw.rect(surface, (30, 30, 30), box)
    pygame.draw.rect(surface, COLORS["accent"], box, 2)
    # Мигающий курсор (переключается раз в полсекунды).
    cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
    surface.blit(fonts["mid"].render(name + cursor, True, COLORS["text"]), (box.x + 12, box.y + 10))
    draw_text_centered(surface, GAME_MESSAGES["enter_hint"], 435, fonts["small"])


def draw_game_over(surface, fonts, total_frames, best_lap_frames, records, saved_ok):
    """Экран завершения: итоги заезда и таблица рекордов."""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 215))
    surface.blit(overlay, (0, 0))
    draw_text_centered(surface, f"Общее время: {format_time(total_frames)}", 50, fonts["mid"])
    draw_text_centered(surface, f"Лучший круг: {format_time(best_lap_frames)}", 90, fonts["mid"], COLORS["accent"])
    draw_records(surface, fonts, records, WINDOW_WIDTH // 2 - 150, 160)
    if saved_ok is False:
        draw_text_centered(surface, "Не удалось сохранить результат в файл", 400, fonts["small"], COLORS["danger"])
    draw_text_centered(surface, GAME_MESSAGES["restart_hint"], 480, fonts["small"])
