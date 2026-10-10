"""
Точка входа в приложение Retro Micro Cars.

При запуске этого файла:
1. Родительская директория добавляется в sys.path, чтобы пакет py_retro_cars
   импортировался независимо от текущей рабочей директории.
2. Запускается главный игровой цикл из game.py.

Запуск:
    cd retro_micro_cars/py_retro_cars/
    python3 main.py
"""

import sys
from pathlib import Path

# Позволяет запускать main.py напрямую из папки py_retro_cars/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py_retro_cars.game import main

# Запускаем игру только при прямом выполнении файла, не при импорте.
if __name__ == "__main__":
    main()
