import queue
import re
import threading
from abc import abstractmethod
from typing import Optional, Union

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.enums import DynamicEnum, DynamicEnumMember
from venantvr.telegram.classes.menu import Menu
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.client import TelegramClient
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.message_queue import MessageReceiver, MessageSender
from venantvr.telegram.tools.logger import logger


class TelegramService:
    """
    Main service orchestrating Telegram components.
    Architecture with clear separation of responsibilities.
    """

    def __init__(
            self,
            api_base_url: str,
            bot_token: str,
            chat_id: str,
            endpoints: dict,
            history_manager: TelegramHistoryManager,
    ):
        self.__chat_id = chat_id
        self.__history_manager = history_manager

        # Components with separated responsibilities
        self.__client = TelegramClient(api_base_url, bot_token, endpoints)
        self.__sender = MessageSender(self.__client, chat_id, history_manager)
        self.__receiver = MessageReceiver(self.__client, history_manager)

        # Command processor
        self.__processor_thread = None
        self.__stop_event = threading.Event()

        logger.info("TelegramService initialized with chat_id=%s", chat_id)

    @property
    def incoming_queue(self) -> queue.Queue:
        """Access to the incoming messages queue."""
        return self.__receiver.incoming_queue

    def start(self):
        """Starts all service components."""
        logger.info("Starting TelegramService")
        self.__sender.start()
        self.__receiver.start()
        self._start_command_processor()

    def stop(self):
        """Stops all service components."""
        logger.info("Stopping TelegramService")
        self.__stop_event.set()
        self.__sender.stop()
        self.__receiver.stop()

        if self.__processor_thread and self.__processor_thread.is_alive():
            self.__processor_thread.join(timeout=5)
        logger.info("TelegramService stopped")

    def send_message(self, messages: Union[TelegramPayload, list[TelegramPayload]]):
        """Sends one or more messages."""
        self.__sender.send_message(messages)

    def flush_outgoing_queue(self):
        """Immediately empties the outgoing queue."""
        self.__sender.flush_queue()

    def test_updates(self):
        """Tests the getUpdates endpoint."""
        try:
            params = {"timeout": 5}
            updates = self.__client.get_updates(params)
            logger.info("getUpdates test successful: %s", updates)
            return updates
        except Exception as e:
            logger.error("Error during getUpdates test: %s", e)
            return None

    def _start_command_processor(self):
        """Starts the command processor."""
        if self.__processor_thread is None or not self.__processor_thread.is_alive():
            self.__processor_thread = threading.Thread(
                target=self._process_commands, daemon=True
            )
            self.__processor_thread.start()

    @abstractmethod
    def _process_commands(self):
        """
        Processes commands from the incoming queue.
        To be implemented in derived classes.
        """
        pass

    def parse_update(self, update: dict) -> tuple[Optional[int], str, dict]:
        """Utility to extract information from an update."""
        return self.__receiver.parse_update(update)

    def parse_command(
            self, command_update: dict
    ) -> tuple[Optional[str], Optional[DynamicEnumMember], list]:
        """Parses a command from a callback query."""
        data = command_update.get("callback_query", {}).get("data", "")
        pattern = r"^((?:ask|respond|cancel|confirm):)?(\/\w+)(?::(.*))?$"
        match = re.match(pattern, data)
        if not match:
            return None, None, []

        action, command_str, params_str = match.groups()
        action = action[:-1] if action else None
        enum_command = self._cast_to_enum(command_str, [Command, Menu])
        arguments = params_str.split(";") if params_str else []
        return action, enum_command, arguments

    @staticmethod
    def _cast_to_enum(
            value: str, enums: list[type[DynamicEnum]]
    ) -> Optional[DynamicEnumMember]:
        """Attempts to cast a string to one of the dynamic enums."""
        for enum_class in enums:
            try:
                return enum_class.from_value(value)
            except ValueError:
                pass
        return None
