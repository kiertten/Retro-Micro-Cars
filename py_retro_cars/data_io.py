"""
Работа с файлами: трасса (track.txt), таблица рекордов (records.json), лог.

Все операции с файловой системой собраны здесь, чтобы остальные модули
не знали, откуда берутся данные. Главные принципы:
    - игра НИКОГДА не падает из-за файла: при ошибке пишем в лог и
      используем запасное значение;
    - файлы открываются через `with` и в кодировке UTF-8;
    - пути строятся через pathlib относительно этого модуля, поэтому
      игра запускается из любой директории.

Формат track.txt - текстовая матрица 15 строк x 20 символов:
    #  - асфальт,  .  - трава,  F - финишная линия
Формат records.json:
    {"records": [{"name": "...", "best_lap": 12.34, "total_time": 40.1, "date": "..."}]}
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from py_retro_cars.constants import (
    DEFAULT_TRACK_LAYOUT,
    GRID_COLUMNS,
    GRID_ROWS,
    MAX_RECORDS_STORED,
    RECORDS_SHOWN,
    START_POSITION,
    TILE_SIZE,
)

# Пути к файлам данных (рядом с модулем, независимо от текущей директории).
BASE_DIR = Path(__file__).resolve().parent
TRACK_FILE = BASE_DIR / "track.txt"
RECORDS_FILE = BASE_DIR / "records.json"
LOG_FILE = BASE_DIR / "game_flight.log"

VALID_TILES = set("#.F")

# Общий логгер игры. Пока setup_logging() не вызван, сообщения никуда не идут.
logger = logging.getLogger("retro_cars")


class TrackFormatError(ValueError):
    """Файл трассы прочитан, но его содержимое не подходит для игры."""


# ============================================================
# Логирование
# ============================================================
def setup_logging(log_path=LOG_FILE):
    """
    Подключает запись событий в файл с временными метками.

    Формат строки: 2026-10-10 20:15:03 | INFO | сообщение
    Повторный вызов безопасен: обработчик добавляется один раз.
    """
    logger.setLevel(logging.INFO)
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return
    try:
        handler = logging.FileHandler(log_path, encoding="utf-8")
    except OSError as error:
        # Нет прав на запись и т.п. - играть можно и без лога.
        print(f"Не удалось открыть лог {log_path}: {error}")
        return
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)


# ============================================================
# Трасса
# ============================================================
def validate_track(lines):
    """
    Проверяет матрицу трассы. При проблеме бросает TrackFormatError.

    Проверки: размер 15x20, допустимые символы, есть финиш,
    стартовая позиция машины лежит на асфальте.
    """
    if len(lines) != GRID_ROWS:
        raise TrackFormatError(f"ожидалось {GRID_ROWS} строк, получено {len(lines)}")
    for number, line in enumerate(lines, start=1):
        if len(line) != GRID_COLUMNS:
            raise TrackFormatError(
                f"строка {number}: ожидалось {GRID_COLUMNS} символов, получено {len(line)}"
            )
        bad = set(line) - VALID_TILES
        if bad:
            raise TrackFormatError(f"строка {number}: недопустимые символы {sorted(bad)}")
    if not any("F" in line for line in lines):
        raise TrackFormatError("на трассе нет финишной линии 'F'")
    start_col = int(START_POSITION[0] // TILE_SIZE)
    start_row = int(START_POSITION[1] // TILE_SIZE)
    if lines[start_row][start_col] == ".":
        raise TrackFormatError("стартовая позиция машины находится на траве")


def load_track(path=TRACK_FILE, default=DEFAULT_TRACK_LAYOUT):
    """
    Читает трассу из текстового файла и преобразует символы в матрицу строк.

    При отсутствии файла, ошибке чтения или неверном формате пишет
    предупреждение в лог/консоль и возвращает запасную трассу default.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            # Хвостовые пробелы и пустые строки в конце не считаются частью карты.
            lines = [line.rstrip() for line in file.read().splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        validate_track(lines)
    except FileNotFoundError:
        _warn(f"Файл трассы {Path(path).name} не найден. Используется трасса по умолчанию.")
    except TrackFormatError as error:
        _warn(f"Неверный формат трассы {Path(path).name}: {error}. Используется трасса по умолчанию.")
    except (OSError, UnicodeDecodeError) as error:
        _warn(f"Не удалось прочитать {Path(path).name}: {error}. Используется трасса по умолчанию.")
    else:
        logger.info("Трасса загружена из %s", Path(path).name)
        return lines
    return list(default)


# ============================================================
# Таблица рекордов
# ============================================================
def load_records(path=RECORDS_FILE):
    """
    Читает таблицу рекордов. Всегда возвращает список (возможно, пустой).

    Повреждённые записи пропускаются, повреждённый файл заменяется пустой
    таблицей при ближайшем сохранении.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.info("Файл рекордов ещё не создан")
        return []
    except json.JSONDecodeError:
        _warn(f"Файл {Path(path).name} повреждён (ошибка JSON). Таблица рекордов начата заново.")
        return []
    except (OSError, UnicodeDecodeError) as error:
        _warn(f"Не удалось прочитать {Path(path).name}: {error}")
        return []

    raw = data.get("records") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        _warn(f"В {Path(path).name} неверная структура. Таблица рекордов начата заново.")
        return []

    records = []
    for item in raw:
        if (
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and isinstance(item.get("best_lap"), (int, float))
            and not isinstance(item.get("best_lap"), bool)
            and item["best_lap"] > 0
        ):
            records.append(item)
        else:
            logger.warning("Пропущена некорректная запись рекорда: %r", item)
    return sorted(records, key=lambda r: r["best_lap"])


def save_record(name, best_lap_sec, total_sec, path=RECORDS_FILE):
    """
    Добавляет результат заезда в таблицу рекордов и сохраняет файл в JSON.

    Запись атомарная: сначала пишем во временный файл, затем заменяем им
    оригинал. Если программа упадёт посреди записи, старый файл останется целым.
    Возвращает обновлённый (отсортированный по лучшему кругу) список или None
    при ошибке записи.
    """
    records = load_records(path)
    records.append(
        {
            "name": name,
            "best_lap": round(best_lap_sec, 2),
            "total_time": round(total_sec, 2),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    records = sorted(records, key=lambda r: r["best_lap"])[:MAX_RECORDS_STORED]

    temp_path = Path(path).with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump({"records": records}, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except OSError as error:
        _warn(f"Не удалось сохранить рекорд: {error}")
        return None
    logger.info("Рекорд сохранён: %s, лучший круг %.2f с", name, best_lap_sec)
    return records


def top_records(records, count=RECORDS_SHOWN):
    """Возвращает count лучших записей (список уже отсортирован по кругу)."""
    return records[:count]


# ============================================================
def _warn(message):
    """Предупреждение одновременно в лог и в консоль."""
    logger.warning(message)
    print(message)
