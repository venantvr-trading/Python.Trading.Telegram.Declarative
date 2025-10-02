import json
import queue
import time
from typing import Callable, Union

from python_trading_telegram_declarative.base import BaseService
from python_trading_telegram_declarative.classes.command import Command
from python_trading_telegram_declarative.classes.enums import DynamicEnumMember
from python_trading_telegram_declarative.classes.menu import Menu
from python_trading_telegram_declarative.classes.payload import TelegramPayload
from python_trading_telegram_declarative.classes.types import CurrentPrompt
from python_trading_telegram_declarative.handler import TelegramHandler
from python_trading_telegram_declarative.history import TelegramHistoryManager
from python_trading_telegram_declarative.tools.logger import logger
from python_trading_telegram_declarative.tools.utils import truncate_text

CommandsHandlers = list[Callable[[Command], str]]


class TelegramNotificationService(BaseService):
    """
    Orchestrates Telegram command and interaction management.
    """

    def __init__(
            self,
            api_base_url,
            bot_token,
            chat_id,
            endpoints,
            history_manager: TelegramHistoryManager,
    ):
        super().__init__(api_base_url, bot_token, chat_id, endpoints, history_manager)
        self._history_manager = history_manager
        self._interactive_prompts = ["ask", "respond"]
        self._telegram_handlers: list[TelegramHandler] = []
        logger.info("Telegram service initialized with chat_id=%s", chat_id)

    # noinspection PyMethodMayBeStatic
    def menu_keyboard(
            self, commands: list[Union[Command, Menu]], items_per_line=3
    ) -> list[TelegramPayload]:
        """
        Displays a help menu with available commands as interactive buttons.
        """
        # noinspection PyUnresolvedReferences
        buttons = [
            {
                "text": truncate_text(cmd.name.replace("_", " ").capitalize(), 14),
                "callback_data": cmd.value,
            }
            for cmd in commands
        ]
        inline_keyboard = [
            buttons[i: i + items_per_line]
            for i in range(0, len(buttons), items_per_line)
        ]
        keyboard: TelegramPayload = {
            "text": "Here are the available commands:",
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
                logger.info("Handler added: %s", telegram_handler.__class__.__name__)
        else:
            self._telegram_handlers = []
            logger.info("Handlers reset")

    def _search_in_handlers(self, command_key: Command) -> dict:
        """Searches for an action associated with a command in the handlers."""
        for handler in self._telegram_handlers:
            for _, value in handler.command_actions.items():
                if command_key in value:
                    # logger.debug("Command found: %s in handler %s", command_key, handler.__class__.__name__)
                    return value.get(command_key, {})
        # logger.debug("Command not found: %s", command_key)
        return {}

    def process_commands(self):
        """Processes commands from the incoming queue."""
        logger.info("Starting command processing")
        while True:
            try:
                update = self.incoming_queue.get(timeout=0.1)
                self.incoming_queue.task_done()
                if update is None:
                    logger.info("Stop signal received, ending command processing")
                    break

                # logger.debug("Update received: %s", update)
                messages: list[TelegramPayload] = []
                chat_id, msg_type, content = self.parse_update(update)

                if not chat_id:
                    logger.warning("No chat_id found in update: %s", update)
                    continue

                if msg_type == "text":
                    # logger.debug("Traitement d'un message texte: %s", content['text'])
                    messages = self._handle_text_message(content["text"], chat_id)
                elif msg_type == "callback_query":
                    # logger.debug("Traitement d'une callback_query: %s", content)
                    messages = self._handle_callback_query(update, chat_id)
                else:
                    logger.warning("Unknown message type: %s", msg_type)

                if messages:
                    logger.debug("Sending messages: %s", messages)
                    self.send_message(messages)
                else:
                    logger.debug("No message to send for this update")

            except queue.Empty:
                # logger.debug("No update in queue")
                time.sleep(0.1)
            except Exception as e:
                logger.exception(f"Error during command processing: %s", e)

    def _handle_callback_query(
            self, update: dict, chat_id: int
    ) -> list[TelegramPayload]:
        """Processes a Telegram callback query."""
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
                # logger.debug("Menu displayed: %s", sub_menu_actions.keys())
                return self.menu_keyboard(list(sub_menu_actions.keys()))
            else:
                logger.warning(f"Unrecognized enum type or enum is None: %s", enum)
                return []

    # noinspection PyUnresolvedReferences
    def _handle_text_message(self, text: str, chat_id: int) -> list[TelegramPayload]:
        """Processes a received text message."""
        # logger.debug("Text message received: %s", text)
        if text == "/help":  # Direct comparison with command value
            top_menu = []
            for handler in self._telegram_handlers:
                for menu in handler.command_actions:
                    if menu != Menu.from_value("/none"):
                        top_menu.append(menu)
            # logger.debug("Affichage du menu principal: %s", top_menu)
            return self.menu_keyboard(top_menu)

        current_prompt = self._history_manager.get_last_active_prompt(chat_id)
        if current_prompt and current_prompt.action == "ask":
            # logger.debug("Interactive prompt detected: %s", current_prompt)
            current_prompt.arguments.append(text)
            return self._process_interactive_prompt(
                "respond", current_prompt.command, current_prompt.arguments, chat_id
            )

        return []

    # noinspection PyUnusedLocal
    def _execute_command(
            self, command: Union[Command, DynamicEnumMember], arguments: list, chat_id: int
    ) -> list[TelegramPayload]:
        """Executes a command by searching for its action in the handlers."""
        command_details = self._search_in_handlers(command)
        responses = []
        for handler in self._telegram_handlers:
            response = handler.process_command(command=command, arguments=arguments)
            if isinstance(response, list):
                responses.extend(response)
            elif isinstance(response, dict):
                responses.append(response)
        # logger.debug("Responses for command %s: %s", command, responses)
        return responses

    def _process_interactive_prompt(
            self,
            action: str,
            command: Union[Command, DynamicEnumMember],
            arguments: list,
            chat_id: int,
    ) -> list[TelegramPayload]:
        """Processes an interactive prompt (ask/respond) with multiple questions."""
        # logger.debug("Traitement du prompt: action=%s, command=%s, arguments=%s", action, command, arguments)
        command_details = self._search_in_handlers(command)

        if action == "ask":
            # Get the list of prompts (replaces 'ask' with 'asks')
            prompts = command_details.get("asks", [])
            if not prompts:
                logger.warning("No prompt defined for command %s", command)
                return []

            # Ask the first question
            prompt_message = prompts[0]
            # logger.debug("Envoi du premier message de prompt: %s", prompt_message)
            self.send_message(prompt_message)
            new_prompt = CurrentPrompt(
                action, command, arguments, current_prompt_index=0
            )
            self._history_manager.log_prompt(new_prompt, chat_id)
            return []

        elif action == "respond":
            current_prompt = self._history_manager.get_last_active_prompt(chat_id)
            if not current_prompt:
                logger.warning("No active prompt found for chat_id=%s", chat_id)
                return []

            # Add the current response
            current_prompt.arguments = arguments
            prompts = command_details.get("asks", [])
            next_prompt_index = current_prompt.current_prompt_index + 1

            if next_prompt_index < len(prompts):
                # Ask the next question
                prompt_message = prompts[next_prompt_index]
                # logger.debug("Envoi du message de prompt suivant (index %d): %s", next_prompt_index, prompt_message)
                self.send_message(prompt_message)
                current_prompt.current_prompt_index = next_prompt_index
                self._history_manager.log_prompt(current_prompt, chat_id)
                return []
            else:
                # All questions have been asked, execute the action
                handler = command_details.get("respond")
                if handler:
                    new_arguments = handler(arguments)
                    # logger.debug("Executing command with new arguments: %s", new_arguments)
                    self._history_manager.resolve_active_prompt(chat_id)
                    return self._execute_command(command, new_arguments, chat_id)
                else:
                    logger.warning("No 'respond' handler for command %s", command)
                    self._history_manager.resolve_active_prompt(chat_id)
                    return []

        return []
