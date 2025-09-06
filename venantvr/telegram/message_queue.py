import json
import queue
import threading
import time
from typing import Union, List

from venantvr.telegram.client import TelegramClient, TelegramAPIError, TelegramNetworkError
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.tools.logger import logger
from venantvr.telegram.tools.utils import ensure_list, is_empty_or_none


class MessageSender:
    """
    Gère l'envoi asynchrone des messages via une file d'attente.
    Responsabilité unique: traitement de la file sortante.
    """
    
    def __init__(self, client: TelegramClient, chat_id: str, history_manager: TelegramHistoryManager):
        self.__client = client
        self.__chat_id = chat_id
        self.__history_manager = history_manager
        self.__outgoing_queue = queue.Queue()
        self.__sender_thread = None
        self.__stop_event = threading.Event()

    def start(self):
        """Démarre le thread d'envoi."""
        if self.__sender_thread is None or not self.__sender_thread.is_alive():
            self.__stop_event.clear()
            self.__sender_thread = threading.Thread(target=self._message_sender, daemon=True)
            self.__sender_thread.start()
            logger.info("MessageSender démarré")

    def stop(self):
        """Arrête le thread d'envoi proprement."""
        logger.info("Arrêt du MessageSender")
        self.__stop_event.set()
        self.flush_queue()
        if self.__sender_thread and self.__sender_thread.is_alive():
            self.__sender_thread.join(timeout=5)
        logger.info("MessageSender arrêté")

    def send_message(self, messages: Union[TelegramPayload, List[TelegramPayload]]):
        """Ajoute un ou plusieurs messages à la file d'attente sortante."""
        for message in ensure_list(messages):
            if self._is_valid_message(message):
                self.__outgoing_queue.put(message)
            else:
                logger.warning("Message ignoré (vide ou sans contenu): %s", message)

    def flush_queue(self):
        """Vide immédiatement la file d'attente sortante."""
        logger.info("Vidage immédiat de la file d'attente sortante")
        while not self.__outgoing_queue.empty():
            try:
                message = self.__outgoing_queue.get_nowait()
                self.__outgoing_queue.task_done()
                if self._is_valid_message(message):
                    payload = self._build_payload(message)
                    self._send_payload(payload)
                else:
                    logger.warning("Message sans contenu textuel ou markup: %s", message)
            except queue.Empty:
                break

    def _message_sender(self):
        """Thread d'envoi des messages."""
        logger.info("Démarrage du thread d'envoi de messages")
        while not self.__stop_event.is_set():
            try:
                message = self.__outgoing_queue.get(timeout=0.1)
                self.__outgoing_queue.task_done()
                
                if not message:
                    continue
                    
                if self._is_valid_message(message):
                    payload = self._build_payload(message)
                    logger.info("Envoi message: %s", json.dumps(payload))
                    self._send_payload(payload)
                else:
                    logger.warning("Message sans contenu textuel ou markup: %s", message)
                    
            except queue.Empty:
                time.sleep(0.1)
            except (TelegramAPIError, TelegramNetworkError) as e:
                logger.error(f"Erreur Telegram lors de l'envoi: {e}")
            except Exception as e:
                logger.exception(f"Erreur inattendue dans MessageSender: %s", e)

    def _build_payload(self, message: TelegramPayload) -> dict:
        """Construit un payload pour l'API Telegram."""
        return {
            "chat_id": self.__chat_id,
            "text": message.get("text", ""),
            "reply_markup": message.get("reply_markup", "")
        }

    def _send_payload(self, payload: dict):
        """Envoie un payload et log l'interaction."""
        self.__history_manager.log_interaction('outgoing', payload['chat_id'], 'message', payload)
        self.__client.send_message(payload)

    # noinspection PyTypedDict
    @staticmethod
    def _is_valid_message(message: TelegramPayload) -> bool:
        """Vérifie si un message contient du contenu valide."""
        return message and any(not is_empty_or_none(message.get(key)) for key in ["text", "reply_markup"])
    
    # Test helpers - for testing purposes only
    def _get_test_attributes(self) -> dict:
        """Get internal attributes for testing. Not for production use."""
        return {
            "chat_id": self.__chat_id,
            "outgoing_queue": self.__outgoing_queue,
            "sender_thread": self.__sender_thread,
            "stop_event": self.__stop_event
        }


class MessageReceiver:
    """
    Gère la réception des messages via polling.
    Responsabilité unique: récupération des mises à jour Telegram.
    """
    
    def __init__(self, client: TelegramClient, history_manager: TelegramHistoryManager):
        self.__client = client
        self.__history_manager = history_manager
        self.__last_update_id = None
        self.__incoming_queue = queue.Queue()
        self.__receiver_thread = None
        self.__stop_event = threading.Event()

    @property
    def incoming_queue(self) -> queue.Queue:
        """Accès à la file d'attente des messages entrants."""
        return self.__incoming_queue

    def start(self):
        """Démarre le thread de réception."""
        if self.__receiver_thread is None or not self.__receiver_thread.is_alive():
            self.__stop_event.clear()
            self.__receiver_thread = threading.Thread(target=self._message_receiver, daemon=True)
            self.__receiver_thread.start()
            logger.info("MessageReceiver démarré")

    def stop(self):
        """Arrête le thread de réception proprement."""
        logger.info("Arrêt du MessageReceiver")
        self.__stop_event.set()
        self.__incoming_queue.put(None)  # Signal d'arrêt
        if self.__receiver_thread and self.__receiver_thread.is_alive():
            self.__receiver_thread.join(timeout=5)
        logger.info("MessageReceiver arrêté")

    def _message_receiver(self):
        """Thread de réception des messages."""
        logger.info("Démarrage du thread de réception de messages")
        while not self.__stop_event.is_set():
            try:
                params = {"timeout": 30}
                if self.__last_update_id is not None:
                    params["offset"] = self.__last_update_id + 1

                updates = self.__client.get_updates(params)
                logger.info("Updates reçues: %s", json.dumps(updates))

                for update in updates.get("result", []):
                    self.__last_update_id = update.get("update_id")
                    chat_id, message_type, content = self.parse_update(update)
                    if chat_id:
                        self.__history_manager.log_interaction('incoming', chat_id, message_type, content, update.get("update_id"))
                    self.__incoming_queue.put(update)

            except TelegramNetworkError as e:
                logger.warning("Erreur réseau dans MessageReceiver: %s", e)
                time.sleep(3)
            except Exception as e:
                logger.exception(f"Erreur inattendue dans MessageReceiver: %s", e)
                time.sleep(1)

    @staticmethod
    def parse_update(update: dict) -> tuple[int | None, str, dict]:
        """Parse une mise à jour Telegram."""
        if "message" in update and "text" in update.get("message", {}):
            chat_id = update.get("message", {}).get("chat", {}).get("id")
            content = {"text": update["message"]["text"]}
            return chat_id, 'text', content
        elif "callback_query" in update:
            chat_id = update.get("callback_query", {}).get("message", {}).get("chat", {}).get("id")
            content = {"data": update["callback_query"]["data"]}
            return chat_id, 'callback_query', content
        return None, 'unknown', update
    
    # Test helpers - for testing purposes only
    def _get_test_attributes(self) -> dict:
        """Get internal attributes for testing. Not for production use."""
        return {
            "last_update_id": self.__last_update_id,
            "incoming_queue": self.__incoming_queue,
            "receiver_thread": self.__receiver_thread,
            "stop_event": self.__stop_event
        }