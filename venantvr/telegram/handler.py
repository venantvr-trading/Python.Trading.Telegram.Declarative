from abc import abstractmethod
from typing import Union

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.menu import Menu
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.classes.types import CommandActionType
from venantvr.telegram.tools.logger import logger


class TelegramHandler:

    def process_command(
        self, command: Command, arguments
    ) -> TelegramPayload or list[TelegramPayload]:
        """
        Processes a command received via Telegram.
        :param command: Command to process.
        :param arguments: List of argument values for the command.
        :return: Result or response to the command.
        """
        # Execute the action associated with the command
        action_data = self.find_action(command)
        if action_data != {}:
            action = action_data.get("action")
            # Find the action definition to know the expected argument names
            kwargs = {}
            for i, (key, expected_type) in enumerate(action_data["kwargs"].items()):
                if i < len(arguments):
                    try:
                        # Convert the argument to expected type if specified
                        kwargs[key] = expected_type(arguments[i])
                    except ValueError:
                        # If conversion fails, return an error message
                        return [
                            {
                                "text": f"Argument '{key}' must be of type {expected_type.__name__}.",
                                "reply_markup": "",
                            }
                        ]

            return action(*action_data.get("args"), **kwargs)  # action(**kwargs)
        else:
            return [{"text": "", "reply_markup": ""}]

    def bonjour(self) -> TelegramPayload:
        return {"text": f"Bonjour {self.__class__.__name__}", "reply_markup": ""}

    @property
    @abstractmethod
    def command_actions(self) -> CommandActionType:
        """
        Property that returns a dictionary of commands and their associated actions.
        """
        pass

    def find_action(
        self, command: Union[Command, Menu]
    ) -> dict:  # <-- Specify possible Enum types
        action_data = {}
        for key, value in self.command_actions.items():
            if command in value:
                action_data = value.get(
                    command, {}
                )  # Using .get with default value is safer
        return action_data

    # noinspection PyUnresolvedReferences
    def register_enums(self):
        """Initializes Command and Menu enums from command_actions."""
        commands = {}
        menus = {}
        for menu, actions in self.command_actions.items():
            menus[menu.name] = menu.value
            for command in actions.keys():
                commands[command.name] = command.value
        Command.register(commands)
        Menu.register(menus)
        logger.info("Command and Menu enums registered from command_actions")
