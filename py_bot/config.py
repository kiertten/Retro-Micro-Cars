"""Пути не зависят от рабочей директории PyCharm."""
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
TRACK_PATH = BASE_DIR.parent / "py_retro_cars" / "track.txt"
RECORDS_PATH = TRACK_PATH.with_name("records.json")
DATA_DIR = BASE_DIR / "data"
