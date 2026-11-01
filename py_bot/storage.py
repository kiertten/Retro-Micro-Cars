"""FSM aiogram использует те же JSON-сессии, без MemoryStorage."""
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from .session import Store


class JsonStorage(BaseStorage):
    def __init__(self, store: Store):
        self.store = store

    async def set_state(self, key: StorageKey, state=None):
        value = self.store.load_session(key.user_id)
        value["state"] = state.state if hasattr(state, "state") else state
        self.store.save_session(key.user_id, value)

    async def get_state(self, key: StorageKey):
        return self.store.load_session(key.user_id).get("state")

    async def set_data(self, key: StorageKey, data):
        value = self.store.load_session(key.user_id)
        value["data"] = dict(data)
        self.store.save_session(key.user_id, value)

    async def get_data(self, key: StorageKey):
        return self.store.load_session(key.user_id)["data"].copy()

    async def close(self):
        pass
