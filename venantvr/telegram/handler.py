from abc import abstractmethod
from typing import Union

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.menu import Menu
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.classes.types import CommandActionType
from venantvr.telegram.tools.logger import logger


class TelegramHandler:

    def process_command(self, command: Command, arguments) -> TelegramPayload or list[TelegramPayload]:
        """
        Traite une commande reçue via Telegram.
        :param command: Commande à traiter.
        :param arguments: Liste des valeurs des arguments pour la commande.
        :return: Résultat ou réponse à la commande.
        """
        # Exécuter l'action associée à la commande
        action_data = self.find_action(command)
        if action_data != {}:
            action = action_data.get("action")
            # Trouver la définition de l'action pour connaître les noms des arguments attendus
            kwargs = {}
            for i, (key, expected_type) in enumerate(action_data["kwargs"].items()):
                if i < len(arguments):
                    try:
                        # Convertir l'argument en type attendu s'il est spécifié
                        kwargs[key] = expected_type(arguments[i])
                    except ValueError:
                        # Si la conversion échoue, on retourne un message d'erreur
                        return [{"text": f"Argument '{key}' doit être de type {expected_type.__name__}.",
                                 "reply_markup": ""}]

            return action(*action_data.get("args"), **kwargs)  # action(**kwargs)
        else:
            return [{"text": "",
                     "reply_markup": ""}]

    def bonjour(self) -> TelegramPayload:
        return {"text": f"Bonjour {self.__class__.__name__}",
                "reply_markup": ""}

    @property
    @abstractmethod
    def command_actions(self) -> CommandActionType:
        """
        Propriété qui retourne un dictionnaire de commandes et leurs actions associées.
        """
        pass

    def find_action(self, command: Union[Command, Menu]) -> dict:  # <-- Préciser les types d'Enum possibles
        action_data = {}
        for key, value in self.command_actions.items():
            if command in value:
                action_data = value.get(command, {})  # Utiliser .get avec une valeur par défaut est plus sûr
        return action_data

    # noinspection PyUnresolvedReferences
    def register_enums(self):
        """Initialise les enums Command et Menu à partir de command_actions."""
        commands = {}
        menus = {}
        for menu, actions in self.command_actions.items():
            menus[menu.name] = menu.value
            for command in actions.keys():
                commands[command.name] = command.value
        Command.register(commands)
        Menu.register(menus)
        logger.info("Enums Command et Menu enregistrés à partir de command_actions")
