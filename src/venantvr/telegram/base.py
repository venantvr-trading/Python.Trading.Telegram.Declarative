from abc import abstractmethod
from typing import Callable

from venantvr.telegram.classes.command import Command
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.service import TelegramService

CommandsHandlers = list[Callable[[Command], str]]


class BaseService(TelegramService):
    """
    Base class inheriting from the new TelegramService.
    Maintains compatibility with existing API while benefiting
    from refactored architecture.
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
        self.start()  # Auto-start for compatibility with old API

    @abstractmethod
    def process_commands(self):
        """
        Abstract method that derived classes must implement.
        Maintains compatibility with the old interface.
        """
        pass

    def _process_commands(self):
        """
        Concrete implementation that delegates to the abstract method.
        Allows compatibility with existing architecture.
        """
        return self.process_commands()
