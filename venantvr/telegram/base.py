from abc import abstractmethod
from typing import Callable

from venantvr.telegram.classes.command import Command
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.service import TelegramService

CommandsHandlers = list[Callable[[Command], str]]


class BaseService(TelegramService):
    """
    Classe de base héritant du nouveau TelegramService.
    Maintient la compatibilité avec l'API existante tout en bénéficiant 
    de l'architecture refactorisée.
    """

    def __init__(self, api_base_url, bot_token, chat_id, endpoints, history_manager: TelegramHistoryManager):
        super().__init__(api_base_url, bot_token, chat_id, endpoints, history_manager)
        self.start()  # Auto-démarrage pour compatibilité avec l'ancienne API

    @abstractmethod
    def process_commands(self):
        """
        Méthode abstraite que les classes dérivées doivent implémenter.
        Maintient la compatibilité avec l'ancienne interface.
        """
        pass
    
    def _process_commands(self):
        """
        Implémentation concrète qui délègue à la méthode abstraite.
        Permet la compatibilité avec l'architecture existante.
        """
        return self.process_commands()
