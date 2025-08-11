import json
import queue
import time
from typing import Callable, Union

from venantvr.telegram.base import BaseService
from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.dynamic_enum import DynamicEnumMember
from venantvr.telegram.classes.menu import Menu
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.classes.types import CurrentPrompt
from venantvr.telegram.handler import TelegramHandler
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.tools.logger import logger
from venantvr.telegram.tools.utils import truncate_text

CommandsHandlers = list[Callable[[Command], str]]


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
        """
        Affiche un menu d'aide avec les commandes disponibles sous forme de boutons interactifs.
        """
        # noinspection PyUnresolvedReferences
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
                logger.info("Handler ajouté: %s", telegram_handler.__class__.__name__)
        else:
            self._telegram_handlers = []
            logger.info("Handlers réinitialisés")

    def _search_in_handlers(self, command_key: Command) -> dict:
        """Recherche une action associée à une commande dans les handlers."""
        for handler in self._telegram_handlers:
            for _, value in handler.command_actions.items():
                if command_key in value:
                    # logger.debug("Commande trouvée: %s dans handler %s", command_key, handler.__class__.__name__)
                    return value.get(command_key, {})
        # logger.debug("Commande non trouvée: %s", command_key)
        return {}

    def process_commands(self):
        """Traite les commandes à partir de la file d'attente entrante."""
        logger.info("Démarrage du traitement des commandes")
        while True:
            try:
                update = self.incoming_queue.get(timeout=0.1)
                self.incoming_queue.task_done()
                if update is None:
                    logger.info("Signal d'arrêt reçu, fin du traitement des commandes")
                    break

                # logger.debug("Mise à jour reçue: %s", update)
                messages: list[TelegramPayload] = []
                chat_id, msg_type, content = self.parse_update(update)

                if not chat_id:
                    logger.warning("Aucun chat_id trouvé dans la mise à jour: %s", update)
                    continue

                if msg_type == 'text':
                    # logger.debug("Traitement d'un message texte: %s", content['text'])
                    messages = self._handle_text_message(content['text'], chat_id)
                elif msg_type == 'callback_query':
                    # logger.debug("Traitement d'une callback_query: %s", content)
                    messages = self._handle_callback_query(update, chat_id)
                else:
                    logger.warning("Type de message inconnu: %s", msg_type)

                if messages:
                    logger.debug("Envoi des messages: %s", messages)
                    self.send_message(messages)
                else:
                    logger.debug("Aucun message à envoyer pour cette mise à jour")

            except queue.Empty:
                # logger.debug("Aucune mise à jour dans la file d'attente")
                time.sleep(0.1)
            except Exception as e:
                logger.exception(f"Erreur lors du traitement de la commande: %s", e)

    def _handle_callback_query(self, update: dict, chat_id: int) -> list[TelegramPayload]:
        """Traite une requête de callback Telegram."""
        action, enum, arguments = self.parse_command(update)
        # logger.debug("Callback query: action=%s, enum=%s, arguments=%s", action, enum, arguments)

        if action in self._interactive_prompts:
            return self._process_interactive_prompt(action, enum, arguments, chat_id)
        else:
            if enum and enum.parent_enum == Command:
                return self._execute_command(enum, arguments, chat_id)
            elif enum and enum.parent_enum == Menu:
                sub_menu_actions = {}
                for handler in self._telegram_handlers:
                    for menu, actions in handler.command_actions.items():
                        if enum == menu:
                            sub_menu_actions.update(actions)
                # logger.debug("Menu affiché: %s", sub_menu_actions.keys())
                return self.menu_keyboard(list(sub_menu_actions.keys()))
            else:
                logger.warning(f"Type d'enum non reconnu ou enum est None: %s", enum)
                return []

    # noinspection PyUnresolvedReferences
    def _handle_text_message(self, text: str, chat_id: int) -> list[TelegramPayload]:
        """Traite un message texte reçu."""
        # logger.debug("Message texte reçu: %s", text)
        if text == "/help":  # Comparaison directe avec la valeur de la commande
            top_menu = []
            for handler in self._telegram_handlers:
                for menu in handler.command_actions:
                    if menu != Menu.from_value("/none"):
                        top_menu.append(menu)
            # logger.debug("Affichage du menu principal: %s", top_menu)
            return self.menu_keyboard(top_menu)

        current_prompt = self._history_manager.get_last_active_prompt(chat_id)
        if current_prompt and current_prompt.action == "ask":
            # logger.debug("Prompt interactif détecté: %s", current_prompt)
            current_prompt.arguments.append(text)
            return self._process_interactive_prompt("respond", current_prompt.command, current_prompt.arguments, chat_id)

        return []

    # noinspection PyUnusedLocal
    def _execute_command(self, command: Union[Command, DynamicEnumMember], arguments: list, chat_id: int) -> list[TelegramPayload]:
        """Exécute une commande en recherchant son action dans les handlers."""
        command_details = self._search_in_handlers(command)
        responses = []
        for handler in self._telegram_handlers:
            response = handler.process_command(command=command, arguments=arguments)
            if isinstance(response, list):
                responses.extend(response)
            elif isinstance(response, dict):
                responses.append(response)
        # logger.debug("Réponses pour la commande %s: %s", command, responses)
        return responses

    def _process_interactive_prompt(self, action: str, command: Union[Command, DynamicEnumMember], arguments: list, chat_id: int) -> list[TelegramPayload]:
        """Traite un prompt interactif (ask/respond) avec plusieurs questions."""
        # logger.debug("Traitement du prompt: action=%s, command=%s, arguments=%s", action, command, arguments)
        command_details = self._search_in_handlers(command)

        if action == "ask":
            # Récupérer la liste des prompts (remplace 'ask' par 'asks')
            prompts = command_details.get("asks", [])
            if not prompts:
                logger.warning("Aucun prompt défini pour la commande %s", command)
                return []

            # Poser la première question
            prompt_message = prompts[0]
            # logger.debug("Envoi du premier message de prompt: %s", prompt_message)
            self.send_message(prompt_message)
            new_prompt = CurrentPrompt(action, command, arguments, current_prompt_index=0)
            self._history_manager.log_prompt(new_prompt, chat_id)
            return []

        elif action == "respond":
            current_prompt = self._history_manager.get_last_active_prompt(chat_id)
            if not current_prompt:
                logger.warning("Aucun prompt actif trouvé pour chat_id=%s", chat_id)
                return []

            # Ajouter la réponse actuelle
            current_prompt.arguments = arguments
            prompts = command_details.get("asks", [])
            next_prompt_index = current_prompt.current_prompt_index + 1

            if next_prompt_index < len(prompts):
                # Poser la question suivante
                prompt_message = prompts[next_prompt_index]
                # logger.debug("Envoi du message de prompt suivant (index %d): %s", next_prompt_index, prompt_message)
                self.send_message(prompt_message)
                current_prompt.current_prompt_index = next_prompt_index
                self._history_manager.log_prompt(current_prompt, chat_id)
                return []
            else:
                # Toutes les questions ont été posées, exécuter l'action
                handler = command_details.get("respond")
                if handler:
                    new_arguments = handler(arguments)
                    # logger.debug("Exécution de la commande avec nouveaux arguments: %s", new_arguments)
                    self._history_manager.resolve_active_prompt(chat_id)
                    return self._execute_command(command, new_arguments, chat_id)
                else:
                    logger.warning("Aucun handler 'respond' pour la commande %s", command)
                    self._history_manager.resolve_active_prompt(chat_id)
                    return []

        return []
