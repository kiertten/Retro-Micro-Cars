"""
Функции отрисовки интерфейса игры.

    - draw_menu        - стартовый экран с правилами
    - draw_hud         - индикаторы во время заезда (скорость, круг, время, занос)
    - draw_game_over   - экран завершения гонки

Все функции принимают surface (поверхность Pygame) и рисуют на ней.
"""

import pygame

from py_retro_cars.constants import (
    COLORS,
    GAME_MESSAGES,
    MAX_SPEED,
    TOTAL_LAPS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)


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


def draw_menu(surface, fonts):
    """Стартовый экран: название, правила управления, подсказка."""
    surface.fill(COLORS["bg"])
    draw_text_centered(surface, GAME_MESSAGES["title"], 60, fonts["big"], COLORS["car_body"])
    draw_text_centered(surface, GAME_MESSAGES["subtitle"], 115, fonts["mid"], COLORS["accent"])

    rules = [
        ("W / ↑", "газ (разгон)"),
        ("S / ↓", "тормоз и задний ход"),
        ("A / ←", "руль влево"),
        ("D / →", "руль вправо"),
        ("R", "вернуться в меню"),
    ]
    y = 200
    for key, text in rules:
        key_surf = fonts["mid"].render(key, True, COLORS["accent"])
        text_surf = fonts["mid"].render(text, True, COLORS["text"])
        surface.blit(key_surf, (230, y))
        surface.blit(text_surf, (370, y))
        y += 38

    draw_text_centered(
        surface,
        f"Проедьте {TOTAL_LAPS} круга по трассе, пересекая финиш.",
        y + 20, fonts["small"],
    )
    draw_text_centered(
        surface,
        "На скорости поворачивайте плавно: машину заносит по инерции.",
        y + 45, fonts["small"],
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

    # --- индикатор заноса ---
    if car.drifting:
        draw_text_centered(surface, GAME_MESSAGES["drift"], 20, fonts["big"], COLORS["danger"])


def draw_game_over(surface, fonts, total_frames, best_lap_frames):
    """Экран завершения: затемнение и итоги заезда."""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    surface.blit(overlay, (0, 0))
    draw_text_centered(surface, GAME_MESSAGES["finish"], 190, fonts["huge"], COLORS["good"])
    draw_text_centered(surface, f"Общее время: {format_time(total_frames)}", 290, fonts["mid"])
    draw_text_centered(surface, f"Лучший круг: {format_time(best_lap_frames)}", 330, fonts["mid"], COLORS["accent"])
    draw_text_centered(surface, GAME_MESSAGES["restart_hint"], 420, fonts["small"])
