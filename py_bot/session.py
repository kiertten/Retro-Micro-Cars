"""Атомарные JSON-сессии пользователей сервиса аналитики."""
import json
import logging
import os
import tempfile
from pathlib import Path
from .config import DATA_DIR

logger = logging.getLogger(__name__)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Store:
    def __init__(self, root=DATA_DIR):
        self.root = Path(root)

    def path(self, kind, user_id):
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("user_id должен быть положительным целым числом")
        return self.root / kind / f"{user_id}.json"

    def read(self, kind, user_id):
        try:
            value = json.loads(self.path(kind, user_id).read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Ожидался JSON-объект")
            return value
        except FileNotFoundError:
            return {}
        except (ValueError, UnicodeError):
            logger.warning("Повреждён файл %s пользователя %s", kind, user_id)
            return {}

    def load_session(self, user_id):
        value = self.read("sessions", user_id)
        state = value.get("state")
        if state not in (None, "Engineer:MENU", "Engineer:UPLOAD", "Engineer:RESULT"):
            value["state"] = None
        if not isinstance(value.get("data"), dict):
            value["data"] = {}
        for key in ("screen_message_id", "screen_chat_id"):
            if type(value.get(key)) is not int or value[key] <= 0:
                value.pop(key, None)
        return value

    def save_session(self, user_id, value):
        atomic_json(self.path("sessions", user_id), value)
