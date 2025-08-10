import queue
import re
import threading
import time
from abc import abstractmethod
from typing import Callable, List, Union, Optional

import requests
from requests import Response

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.dynamic_enum import DynamicEnum, DynamicEnumMember
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.tools.logger import logger
from venantvr.telegram.tools.utils import ensure_list, is_empty_or_none

CommandsHandlers = list[Callable[[Command], str]]


class BaseService:
    """
    Classe de base pour gérer l'envoi et la réception de messages Telegram.
    """

    def __init__(self, api_base_url, bot_token, chat_id, endpoints, history_manager: TelegramHistoryManager):
        super().__init__()
        self.__api_base_url = api_base_url
        self.__bot_token = bot_token
        self.__chat_id = chat_id
        self.__text_endpoint = endpoints.get("text")
        self.__updates_endpoint = endpoints.get("updates")
        self.__url_send = f"{self.__api_base_url}{self.__bot_token}{self.__text_endpoint}"
        self.__url_updates = f"{self.__api_base_url}{self.__bot_token}{self.__updates_endpoint}"
        self.__history_manager = history_manager
        self.__last_update_id = None
        self.__incoming_queue = queue.Queue()
        self.__outgoing_queue = queue.Queue()

        logger.debug("URL d'envoi: %s", self.__url_send)
        logger.debug("URL de réception: %s", self.__url_updates)

        self.__sender_thread = threading.Thread(target=self._message_sender, daemon=True)
        self.__receiver_thread = threading.Thread(target=self._message_receiver, daemon=True)
        self.__processor_thread = threading.Thread(target=self.process_commands, daemon=True)

        self.__sender_thread.start()
        self.__receiver_thread.start()
        self.__processor_thread.start()

    @property
    def incoming_queue(self) -> queue.Queue:
        """Fournit un accès protégé à la file d'attente des messages entrants."""
        return self.__incoming_queue

    def send_message(self, messages: Union[TelegramPayload, List[TelegramPayload]]):
        """Envoie un ou plusieurs messages à la file d'attente sortante."""
        for message in ensure_list(messages):
            if any(not is_empty_or_none(message.get(key)) for key in ["text", "reply_markup"]):
                logger.debug("Ajout du message à la file sortante: %s", message)
                self.__outgoing_queue.put(message)
            else:
                logger.warning("Message ignoré (vide ou sans contenu): %s", message)

    def flush_outgoing_queue(self):
        """Vide immédiatement la file d'attente sortante en envoyant tous les messages."""
        logger.info("Vidage immédiat de la file d'attente sortante")
        while not self.__outgoing_queue.empty():
            try:
                message = self.__outgoing_queue.get_nowait()
                self.__outgoing_queue.task_done()
                logger.debug("Message extrait immédiatement: %s", message)
                if message and any(not is_empty_or_none(message.get(key)) for key in ["text", "reply_markup"]):
                    payload = {"chat_id": self.__chat_id, "text": message.get("text", ""), "reply_markup": message.get("reply_markup", "")}
                    logger.debug("Envoi immédiat du payload à Telegram: %s", payload)
                    self.__history_manager.log_interaction('outgoing', payload['chat_id'], 'message', payload)
                    self._post(payload)
                else:
                    logger.warning("Message sans contenu textuel ou markup: %s", message)
            except queue.Empty:
                break

    def test_updates(self):
        """Teste l'endpoint getUpdates pour vérifier la réception des mises à jour."""
        try:
            params = {"timeout": 5}
            if self.__last_update_id is not None:
                params["offset"] = self.__last_update_id + 1
            logger.debug("Test de l'endpoint getUpdates avec params: %s", params)
            response = requests.get(self.__url_updates, params=params, timeout=(3, 10))
            response.raise_for_status()
            updates = response.json()
            logger.info("Résultat du test getUpdates: %s", updates)
            return updates
        except requests.RequestException as e:
            logger.error("Erreur lors du test de getUpdates: %s", e)
            return None

    def _message_sender(self):
        """Envoie les messages de la file sortante à Telegram."""
        logger.info("Démarrage du thread d'envoi de messages")
        while True:
            try:
                message = self.__outgoing_queue.get(timeout=0.1)
                self.__outgoing_queue.task_done()
                if not message:
                    logger.debug("Message vide reçu dans la file sortante")
                    continue
                if any(not is_empty_or_none(message.get(key)) for key in ["text", "reply_markup"]):
                    payload = {"chat_id": self.__chat_id, "text": message.get("text", ""), "reply_markup": message.get("reply_markup", "")}
                    logger.debug("Envoi du payload à Telegram: %s", payload)
                    self.__history_manager.log_interaction('outgoing', payload['chat_id'], 'message', payload)
                    self._post(payload)
                else:
                    logger.warning("Message sans contenu textuel ou markup: %s", message)
            except queue.Empty:
                logger.debug("Aucune mise à jour dans la file sortante")
                time.sleep(0.1)
            except Exception as e:
                logger.exception(f"Erreur lors de l'envoi du message: %s", e)

    def _post(self, payload):
        """Envoie une requête POST à l'API Telegram."""

        response: Optional[Response] = None

        try:
            logger.debug("Envoi de la requête POST à %s avec payload: %s", self.__url_send, payload)
            response = requests.post(self.__url_send, data=payload, timeout=(3, 10))
            response.raise_for_status()
            logger.debug("Réponse de l'API Telegram: %s", response.json())
        except requests.HTTPError as e:
            logger.error("Erreur HTTP lors de l'envoi à Telegram: %s, réponse: %s", e, response.text)
            raise
        except requests.RequestException as e:
            logger.error("Erreur réseau lors de l'envoi à Telegram: %s", e)
            raise

    def _message_receiver(self):
        """Reçoit les mises à jour de Telegram et les place dans la file entrante."""
        logger.info("Démarrage du thread de réception de messages")
        while True:
            try:
                params = {"timeout": 30}
                if self.__last_update_id is not None:
                    params["offset"] = self.__last_update_id + 1

                logger.debug("Envoi de la requête GET à %s avec params: %s", self.__url_updates, params)
                response = requests.get(self.__url_updates, params=params, timeout=(3, 30))
                response.raise_for_status()
                updates = response.json()
                if not updates.get("result"):
                    logger.debug("Aucune mise à jour reçue de Telegram")
                else:
                    logger.debug("Mises à jour reçues: %s", updates)

                for update in updates.get("result", []):
                    self.__last_update_id = update.get("update_id")
                    chat_id, message_type, content = self.parse_update(update)
                    if chat_id:
                        self.__history_manager.log_interaction('incoming', chat_id, message_type, content, update.get("update_id"))
                    self.__incoming_queue.put(update)
                    logger.debug("Mise à jour ajoutée à la file entrante: %s", update)

            except Exception as e:
                logger.exception(f"Erreur inconnue dans le thread de réception: %s", e)
                time.sleep(1)

    # noinspection PyMethodMayBeStatic
    def parse_update(self, update: dict) -> tuple[Optional[int], str, dict]:
        """Utilitaire pour extraire les informations clés d'une mise à jour de Telegram."""
        if "message" in update and "text" in update.get("message", {}):
            chat_id = update.get("message", {}).get("chat", {}).get("id")
            content = {"text": update["message"]["text"]}
            return chat_id, 'text', content
        elif "callback_query" in update:
            chat_id = update.get("callback_query", {}).get("message", {}).get("chat", {}).get("id")
            content = {"data": update["callback_query"]["data"]}
            return chat_id, 'callback_query', content
        return None, 'unknown', update

    def stop(self):
        """Arrête les threads et vide les files d'attente."""
        logger.info("Arrêt des threads Telegram")
        self.__incoming_queue.put(None)
        self.__outgoing_queue.put(None)
        self.flush_outgoing_queue()
        self.__sender_thread.join()
        self.__receiver_thread.join()
        self.__processor_thread.join()
        logger.info("Tous les threads Telegram arrêtés")

    @abstractmethod
    def process_commands(self) -> dict or list[TelegramPayload]:
        pass

    # noinspection PyMethodMayBeStatic
    def _cast_to_enum(self, value: str, enums: list[type[DynamicEnum]]) -> Optional[DynamicEnumMember]:
        """
        Tente de caster une chaîne dans l'un des enums dynamiques donnés.
        """
        for enum_class in enums:
            try:
                return enum_class.from_value(value)
            except ValueError:
                pass
        return None

    def parse_command(self, command_update: dict) -> tuple[Optional[str], Optional[DynamicEnumMember], list]:
        from venantvr.telegram.classes.command import Command
        from venantvr.telegram.classes.menu import Menu
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
