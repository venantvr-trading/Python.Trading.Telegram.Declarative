import json
import sqlite3
from datetime import datetime
from typing import Optional

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.enums import DynamicEnumMember
from venantvr.telegram.classes.types import CurrentPrompt


class TelegramHistoryManager:

    def __init__(self, db_path: str):
        self.__db_path = db_path
        self._create_schema()

    def _create_schema(self):
        """Crée la table pour l'historique si elle n'existe pas."""
        with sqlite3.connect(self.__db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    direction TEXT NOT NULL, -- 'incoming' or 'outgoing'
                    chat_id INTEGER NOT NULL,
                    update_id INTEGER, -- Uniquement pour 'incoming'
                    message_type TEXT NOT NULL, -- 'text', 'callback_query'
                    content TEXT NOT NULL, -- Le message/payload en JSON
                    is_prompt BOOLEAN DEFAULT FALSE,
                    prompt_status TEXT DEFAULT NULL -- 'active', 'resolved'
                )
            """
            )
            conn.commit()

    def log_interaction(
            self,
            direction: str,
            chat_id: int,
            message_type: str,
            content: dict,
            update_id: Optional[int] = None,
    ):
        """Journalise une interaction générique."""
        with sqlite3.connect(self.__db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO interactions (timestamp, direction, chat_id, update_id, message_type, content)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now(),
                    direction,
                    chat_id,
                    update_id,
                    message_type,
                    json.dumps(content),
                ),
            )
            conn.commit()

    def log_prompt(self, prompt: CurrentPrompt, chat_id: int):
        """Journalise le début d'une commande interactive."""
        # noinspection PyUnresolvedReferences
        content = {
            "action": prompt.action,
            "command": prompt.command.value,
            "arguments": prompt.arguments,
            "current_prompt_index": prompt.current_prompt_index,
        }
        with sqlite3.connect(self.__db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO interactions (timestamp, direction, chat_id, message_type, content, is_prompt, prompt_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now(),
                    "system",
                    chat_id,
                    "prompt_start",
                    json.dumps(content),
                    True,
                    "active",
                ),
            )
            conn.commit()

    def get_last_active_prompt(self, chat_id: int) -> Optional[CurrentPrompt]:
        """Récupère le dernier prompt actif pour un chat donné."""
        with sqlite3.connect(self.__db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT content FROM interactions
                WHERE chat_id = ? AND is_prompt = TRUE AND prompt_status = 'active'
                ORDER BY timestamp DESC
                LIMIT 1
            """,
                (chat_id,),
            )
            row = cursor.fetchone()
            if row:
                content = json.loads(row[0])
                payload: DynamicEnumMember = Command.from_value(content["command"])
                return CurrentPrompt(
                    action=content["action"],
                    command=payload,
                    arguments=content["arguments"],
                    current_prompt_index=content.get("current_prompt_index", 0),
                )
        return None

    def resolve_active_prompt(self, chat_id: int):
        """Marque le prompt actif comme résolu."""
        with sqlite3.connect(self.__db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE interactions
                SET prompt_status = 'resolved'
                WHERE chat_id = ? AND prompt_status = 'active'
            """,
                (chat_id,),
            )
            conn.commit()
