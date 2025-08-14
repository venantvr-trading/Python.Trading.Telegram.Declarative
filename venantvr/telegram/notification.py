# venantvr/telegram/notification.py
import json
import queue
import time
from typing import Union

from venantvr.telegram.base import BaseService
from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.dynamic_enum import DynamicEnumMember
from venantvr.telegram.classes.menu import Menu
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.classes.types import CurrentPrompt
from venantvr.telegram.decorators import get_command, get_commands_for_menu, get_top_level_menus
from venantvr.telegram.handler import TelegramHandler
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.tools.logger import logger
from venantvr.telegram.tools.utils import truncate_text


class TelegramNotificationService(BaseService):
    """
    Orchestre la gestion des commandes et des interactions Telegram.
    """

    def __init__(self, api_base_url, bot_token, chat_id, endpoints, history_manager: TelegramHistoryManager):
        super().__init__(api_base_url, bot_token, chat_id, endpoints, history_manager)
        self._history_manager = history_manager
        self._interactive_prompts = ["ask", "respond"]
        self._telegram_handlers: list[TelegramHandler] = []
        logger.info("Service Telegram initialisé avec chat_id=%s", chat_id)

    # noinspection PyMethodMayBeStatic
    def menu_keyboard(self, commands: list[Union[Command, Menu]], items_per_line=3) -> list[TelegramPayload]:
        """Affiche un menu avec les commandes disponibles sous forme de boutons interactifs."""
        buttons = [
            {
                "text": truncate_text(cmd.name.replace("_", " ").capitalize(), 14),
                "callback_data": cmd.value
            }
            for cmd in commands
        ]
        inline_keyboard = [buttons[i:i + items_per_line] for i in range(0, len(buttons), items_per_line)]
        keyboard: TelegramPayload = {
            "text": "Voici les commandes disponibles:",
            "reply_markup": json.dumps({"inline_keyboard": inline_keyboard}),
        }
        return [keyboard]

    @property
    def handler(self):
        return self._telegram_handlers

    @handler.setter
    def handler(self, telegram_handler: TelegramHandler):
        if telegram_handler is not None:
            if telegram_handler not in self._telegram_handlers:
                self._telegram_handlers.append(telegram_handler)
                logger.info("Handler instance ajouté: %s", telegram_handler.__class__.__name__)
        else:
            self._telegram_handlers = []
            logger.info("Handlers réinitialisés")

    def process_commands(self):
        """Traite les commandes à partir de la file d'attente entrante."""
        logger.info("Démarrage du traitement des commandes")
        while True:
            try:
                update = self.incoming_queue.get(timeout=0.1)
                self.incoming_queue.task_done()
                if update is None:
                    break

                messages: list[TelegramPayload] = []
                chat_id, msg_type, content = self.parse_update(update)
                if not chat_id:
                    continue

                if msg_type == 'text':
                    messages = self._handle_text_message(content['text'], chat_id)
                elif msg_type == 'callback_query':
                    messages = self._handle_callback_query(update, chat_id)

                if messages:
                    self.send_message(messages)

            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:
                logger.exception(f"Erreur lors du traitement de la commande: %s", e)

    def _handle_callback_query(self, update: dict, chat_id: int) -> list[TelegramPayload]:
        """Traite une requête de callback Telegram."""
        action, enum, arguments = self.parse_command(update)

        if action in self._interactive_prompts:
            return self._process_interactive_prompt(action, enum, arguments, chat_id)

        if isinstance(enum, Command):
            return self._execute_command(enum, arguments, chat_id)
        elif isinstance(enum, Menu):
            menu_commands = get_commands_for_menu(enum)
            command_enums = [cmd['enum'] for cmd in menu_commands]
            return self.menu_keyboard(command_enums)
        else:
            logger.warning(f"Type d'enum non reconnu ou enum est None: %s", enum)
            return []

    def _handle_text_message(self, text: str, chat_id: int) -> list[TelegramPayload]:
        """Traite un message texte reçu."""
        if text.startswith("/"):
            command_name = text.split(' ')[0]
            if command_name == "/help":
                top_menus = get_top_level_menus()
                return self.menu_keyboard(top_menus)

        current_prompt = self._history_manager.get_last_active_prompt(chat_id)
        if current_prompt and current_prompt.action == "ask":
            # Le texte est une réponse à une question
            current_prompt.arguments.append(text)
            return self._process_interactive_prompt("respond", current_prompt.command, current_prompt.arguments, chat_id)

        return []

    def _execute_command(self, command: Union[Command, DynamicEnumMember], arguments: list, chat_id: int) -> list[TelegramPayload]:
        """Exécute une commande en la déléguant au bon handler."""
        responses = []
        for handler in self._telegram_handlers:
            response = handler.process_command(command=command, arguments=arguments)
            if response is not None:  # Le handler a traité la commande
                if isinstance(response, list):
                    responses.extend(response)
                else:
                    responses.append(response)
        if not responses:
            logger.warning(f"La commande '{command.value}' n'a retourné aucune réponse d'un handler.")
        return responses

    def _process_interactive_prompt(self, action: str, command: Union[Command, DynamicEnumMember], arguments: list, chat_id: int) -> list[TelegramPayload]:
        """Traite un prompt interactif (ask/respond)."""
        command_details = get_command(command.value)
        if not command_details:
            logger.error(f"Impossible de traiter un prompt pour une commande non enregistrée '{command.value}'")
            return []

        if action == "ask":
            # Démarre une nouvelle conversation interactive
            prompts = command_details.get("asks", [])
            # `arguments` contient ici les args pré-remplis via le callback (ex: ask:/cmd:arg1)
            new_prompt = CurrentPrompt(action, command, arguments, current_prompt_index=len(arguments))
            self._history_manager.log_prompt(new_prompt, chat_id)

            if new_prompt.current_prompt_index < len(prompts):
                # Pose la première question nécessaire
                question = prompts[new_prompt.current_prompt_index]
                return [{"text": question, "reply_markup": ""}]
            else:
                # Tous les arguments étaient déjà fournis, on exécute
                self._history_manager.resolve_active_prompt(chat_id)
                return self._execute_command(command, arguments, chat_id)

        elif action == "respond":
            current_prompt = self._history_manager.get_last_active_prompt(chat_id)
            if not current_prompt:
                logger.warning("Aucun prompt actif trouvé pour une action 'respond' pour chat_id=%s", chat_id)
                return []

            # `arguments` contient maintenant toutes les réponses collectées, y compris la dernière
            current_prompt.arguments = arguments
            current_prompt.current_prompt_index = len(arguments)
            prompts = command_details.get("asks", [])

            if current_prompt.current_prompt_index < len(prompts):
                # Il reste des questions à poser
                question = prompts[current_prompt.current_prompt_index]
                # On met à jour l'historique du prompt avec la nouvelle réponse
                self._history_manager.log_prompt(current_prompt, chat_id)
                return [{"text": question, "reply_markup": ""}]
            else:
                # Toutes les réponses sont collectées, on exécute la commande
                self._history_manager.resolve_active_prompt(chat_id)
                return self._execute_command(command, current_prompt.arguments, chat_id)

        return []