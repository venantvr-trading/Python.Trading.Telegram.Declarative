import queue
import re
import threading
from abc import abstractmethod
from typing import Union, Optional

from venantvr.telegram.client import TelegramClient
from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.enums import DynamicEnum, DynamicEnumMember
from venantvr.telegram.classes.menu import Menu
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.message_queue import MessageSender, MessageReceiver
from venantvr.telegram.tools.logger import logger


class TelegramService:
    """
    Service principal orchestrant les composants Telegram.
    Architecture avec séparation claire des responsabilités.
    """
    
    def __init__(self, api_base_url: str, bot_token: str, chat_id: str, endpoints: dict, 
                 history_manager: TelegramHistoryManager):
        self.__chat_id = chat_id
        self.__history_manager = history_manager
        
        # Composants avec responsabilités séparées
        self.__client = TelegramClient(api_base_url, bot_token, endpoints)
        self.__sender = MessageSender(self.__client, chat_id, history_manager)
        self.__receiver = MessageReceiver(self.__client, history_manager)
        
        # Processeur de commandes
        self.__processor_thread = None
        self.__stop_event = threading.Event()
        
        logger.info("TelegramService initialisé avec chat_id=%s", chat_id)

    @property
    def incoming_queue(self) -> queue.Queue:
        """Accès à la file d'attente des messages entrants."""
        return self.__receiver.incoming_queue

    def start(self):
        """Démarre tous les composants du service."""
        logger.info("Démarrage du TelegramService")
        self.__sender.start()
        self.__receiver.start()
        self._start_command_processor()

    def stop(self):
        """Arrête tous les composants du service."""
        logger.info("Arrêt du TelegramService")
        self.__stop_event.set()
        self.__sender.stop()
        self.__receiver.stop()
        
        if self.__processor_thread and self.__processor_thread.is_alive():
            self.__processor_thread.join(timeout=5)
        logger.info("TelegramService arrêté")

    def send_message(self, messages: Union[TelegramPayload, list[TelegramPayload]]):
        """Envoie un ou plusieurs messages."""
        self.__sender.send_message(messages)

    def flush_outgoing_queue(self):
        """Vide immédiatement la file d'attente sortante."""
        self.__sender.flush_queue()

    def test_updates(self):
        """Teste l'endpoint getUpdates."""
        try:
            params = {"timeout": 5}
            updates = self.__client.get_updates(params)
            logger.info("Test getUpdates réussi: %s", updates)
            return updates
        except Exception as e:
            logger.error("Erreur lors du test de getUpdates: %s", e)
            return None

    def _start_command_processor(self):
        """Démarre le processeur de commandes."""
        if self.__processor_thread is None or not self.__processor_thread.is_alive():
            self.__processor_thread = threading.Thread(target=self._process_commands, daemon=True)
            self.__processor_thread.start()

    @abstractmethod
    def _process_commands(self):
        """
        Traite les commandes à partir de la file d'attente entrante.
        À implémenter dans les classes dérivées.
        """
        pass

    def parse_update(self, update: dict) -> tuple[Optional[int], str, dict]:
        """Utilitaire pour extraire les informations d'une mise à jour."""
        return self.__receiver.parse_update(update)

    def parse_command(self, command_update: dict) -> tuple[Optional[str], Optional[DynamicEnumMember], list]:
        """Parse une commande depuis une callback query."""
        data = command_update.get("callback_query", {}).get("data", "")
        pattern = r'^((?:ask|respond|cancel|confirm):)?(\/\w+)(?::(.*))?$'
        match = re.match(pattern, data)
        if not match:
            return None, None, []
        
        action, command_str, params_str = match.groups()
        action = action[:-1] if action else None
        enum_command = self._cast_to_enum(command_str, [Command, Menu])
        arguments = params_str.split(';') if params_str else []
        return action, enum_command, arguments

    @staticmethod
    def _cast_to_enum(value: str, enums: list[type[DynamicEnum]]) -> Optional[DynamicEnumMember]:
        """Tente de caster une chaîne dans l'un des enums dynamiques."""
        for enum_class in enums:
            try:
                return enum_class.from_value(value)
            except ValueError:
                pass
        return None