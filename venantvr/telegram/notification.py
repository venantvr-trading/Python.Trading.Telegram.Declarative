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
from venantvr.telegram.decorators import COMMAND_REGISTRY
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
        logger.debug("Menu keyboard généré: %s", keyboard)
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
        logger.debug("Recherche de la commande %s dans command_actions", command_key)
        for handler in self._telegram_handlers:
            for _, value in handler.command_actions.items():
                if command_key in value:
                    logger.debug("Commande trouvée dans command_actions: %s, détails: %s", command_key, value[command_key])
                    return value.get(command_key, {})
        # Vérifier dans COMMAND_REGISTRY si non trouvé dans command_actions
        # noinspection PyUnresolvedReferences
        command_details = COMMAND_REGISTRY.get(command_key.value, {})
        logger.debug("Commande %s dans COMMAND_REGISTRY: %s", command_key, command_details)
        return command_details

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

                logger.debug("Mise à jour reçue: %s", update)
                messages: list[TelegramPayload] = []
                chat_id, msg_type, content = self.parse_update(update)

                if not chat_id:
                    logger.warning("Aucun chat_id trouvé dans la mise à jour: %s", update)
                    continue

                if msg_type == 'text':
                    logger.debug("Traitement d'un message texte: %s", content['text'])
                    messages = self._handle_text_message(content['text'], chat_id)
                elif msg_type == 'callback_query':
                    logger.debug("Traitement d'une callback_query: %s", content)
                    messages = self._handle_callback_query(update, chat_id)
                else:
                    logger.warning("Type de message inconnu: %s", msg_type)

                if messages:
                    logger.debug("Messages à envoyer: %s", messages)
                    self.send_message(messages)
                else:
                    logger.debug("Aucun message à envoyer pour cette mise à jour")

            except queue.Empty:
                logger.debug("Aucune mise à jour dans la file d'attente")
                time.sleep(0.1)
            except Exception as e:
                logger.exception("Erreur lors du traitement de la commande: %s", e)

    def _handle_text_message(self, text: str, chat_id: int) -> list[TelegramPayload]:
        """Traite un message texte reçu."""
        logger.debug("Message texte reçu: %s pour chat_id: %s", text, chat_id)
        if text in ["/help", "/menu"]:
            logger.debug("Commande /help ou /menu détectée")
            top_menu = []
            for handler in self._telegram_handlers:
                for menu in handler.command_actions:
                    if menu != Menu.from_value("/none"):
                        top_menu.append(menu)
            logger.debug("Menus principaux: %s", top_menu)
            return self.menu_keyboard(top_menu)

        current_prompt = self._history_manager.get_last_active_prompt(chat_id)
        if current_prompt and current_prompt.action == "ask":
            logger.debug("Prompt interactif détecté: %s", current_prompt)
            current_prompt.arguments.append(text)
            return self._process_interactive_prompt("respond", current_prompt.command, current_prompt.arguments, chat_id)

        # Vérifier si la commande existe dans COMMAND_REGISTRY
        command_name = text.split(' ')[0]
        command_details = COMMAND_REGISTRY.get(command_name, {})
        logger.debug("Commande %s dans COMMAND_REGISTRY: %s", command_name, command_details)
        if command_details:
            if command_details.get("asks"):
                logger.debug("Commande %s nécessite des prompts", command_name)
                return self._process_interactive_prompt("ask", Command.from_value(command_name), [], chat_id)
            return self._execute_command(Command.from_value(command_name), [], chat_id)
        logger.debug("Commande non reconnue: %s", command_name)
        return []

    def _handle_callback_query(self, update: dict, chat_id: int) -> list[TelegramPayload]:
        """Traite une requête de callback Telegram."""
        action, enum, arguments = self.parse_command(update)
        logger.debug("Callback query: action=%s, enum=%s, arguments=%s", action, enum, arguments)

        if action in self._interactive_prompts:
            return self._process_interactive_prompt(action, enum, arguments, chat_id)
        else:
            if enum and enum.parent_enum == Command:
                command_details = COMMAND_REGISTRY.get(enum.value, {})
                logger.debug("Commande %s dans COMMAND_REGISTRY: %s", enum, command_details)
                if command_details.get("asks"):
                    logger.debug("Commande %s via callback nécessite des prompts", enum)
                    return self._process_interactive_prompt("ask", enum, [], chat_id)
                return self._execute_command(enum, arguments, chat_id)
            elif enum and enum.parent_enum == Menu:
                sub_menu_actions = {}
                for handler in self._telegram_handlers:
                    for menu, actions in handler.command_actions.items():
                        if enum == menu:
                            sub_menu_actions.update(actions)
                logger.debug("Menu affiché: %s", sub_menu_actions.keys())
                return self.menu_keyboard(list(sub_menu_actions.keys()))
            else:
                logger.warning("Type d'enum non reconnu ou enum est None: %s", enum)
                return []

    def _execute_command(self, command: Union[Command, DynamicEnumMember], arguments: list, chat_id: int) -> list[TelegramPayload]:
        """Exécute une commande en recherchant son action dans les handlers."""
        command_details = self._search_in_handlers(command)
        logger.debug("Détails de la commande %s: %s", command, command_details)
        responses = []
        for handler in self._telegram_handlers:
            response = handler.process_command(command=command, arguments=arguments)
            logger.debug("Réponse du handler pour %s: %s", command, response)
            if isinstance(response, list):
                responses.extend(response)
            elif isinstance(response, dict):
                responses.append(response)
        logger.debug("Réponses finales pour la commande %s: %s", command, responses)
        return responses

    def _process_interactive_prompt(self, action: str, command: Union[Command, DynamicEnumMember], arguments: list, chat_id: int) -> list[TelegramPayload]:
        """Traite un prompt interactif (ask/respond) avec plusieurs questions."""
        logger.debug("Traitement du prompt: action=%s, command=%s, arguments=%s", action, command, arguments)
        command_details = COMMAND_REGISTRY.get(command.value, {})
        logger.debug("Détails de la commande pour prompt %s: %s", command, command_details)

        if action == "ask":
            prompts = command_details.get("asks", [])
            if not prompts:
                logger.warning("Aucun prompt défini pour la commande %s", command)
                return [{"text": "Erreur : Cette commande nécessite des arguments.", "reply_markup": ""}]

            prompt_message = prompts[0]
            logger.debug("Envoi du premier message de prompt: %s", prompt_message)
            payload: TelegramPayload = {"text": prompt_message, "reply_markup": ""}
            self.send_message(payload)
            new_prompt = CurrentPrompt(action, command, arguments, current_prompt_index=0)
            self._history_manager.log_prompt(new_prompt, chat_id)
            return []

        elif action == "respond":
            current_prompt = self._history_manager.get_last_active_prompt(chat_id)
            if not current_prompt:
                logger.warning("Aucun prompt actif trouvé pour chat_id=%s", chat_id)
                return [{"text": "Erreur : Aucun prompt actif.", "reply_markup": ""}]

            current_prompt.arguments = arguments
            prompts = command_details.get("asks", [])
            next_prompt_index = current_prompt.current_prompt_index + 1

            if next_prompt_index < len(prompts):
                prompt_message = prompts[next_prompt_index]
                logger.debug("Envoi du message de prompt suivant (index %d): %s", next_prompt_index, prompt_message)
                payload: TelegramPayload = {"text": prompt_message, "reply_markup": ""}
                self.send_message(payload)
                current_prompt.current_prompt_index = next_prompt_index
                self._history_manager.log_prompt(current_prompt, chat_id)
                return []
            else:
                self._history_manager.resolve_active_prompt(chat_id)
                return self._execute_command(command, arguments, chat_id)

        return []
