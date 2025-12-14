import json
import os
from datetime import datetime
from threading import Lock

TRACKING_FILE = "tracking/tracking.json"
_lock = Lock()


class Tracker:
    def __init__(self, filepath: str = TRACKING_FILE):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        """Create tracking file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"users": {}}, f, ensure_ascii=False, indent=4)

    def _load(self) -> dict:
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def log_query(self, message, word: str, direction: str):
        """
        Logs a translation query.

        direction: 'uz-en' or 'en-uz'
        """
        user_id = str(message.from_user.id)
        username = message.from_user.username
        first_name = message.from_user.first_name

        record = {
            "word": word.strip().lower(),
            "direction": direction,
            "timestamp": datetime.utcnow().isoformat()
        }

        with _lock:  # protects against simultaneous writes
            data = self._load()

            users = data.setdefault("users", {})

            if user_id not in users:
                users[user_id] = {
                    "username": username,
                    "first_name": first_name,
                    "created_at": datetime.utcnow().isoformat(),
                    "queries": []
                }

            users[user_id]["queries"].append(record)

            self._save(data)
