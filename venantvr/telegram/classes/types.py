from typing import Dict, Callable, Tuple, Union, Optional
from typing import TypedDict

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.enums import DynamicEnumMember
from venantvr.telegram.classes.menu import Menu

# Définir des types pour les arguments possibles
ArgumentType = Union[int, str, float]  # Ajoutez d'autres types si nécessaire


class Action(TypedDict):
    action: Callable
    args: Tuple[ArgumentType, ...]
    kwargs: Dict[str, ArgumentType]
    # confirm: bool


class CurrentPrompt:
    def __init__(self, action: str, command: Union[Command, DynamicEnumMember], arguments: list, current_prompt_index: int = 0):
        self.action = action
        self.command = command
        self.arguments = arguments
        self.current_prompt_index = current_prompt_index


class BoolGuard:
    def __init__(self, initial_value):
        self.__value = initial_value

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, new_value):
        if not isinstance(new_value, bool):
            raise ValueError("La valeur doit être un booléen")
        self.__value = new_value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__value:
            self.__value = False


CommandActionType = Union[
    dict[Optional[Menu], dict[Optional[Command], Union[dict, Action]]],
    dict[Optional[DynamicEnumMember], dict[Optional[DynamicEnumMember], Union[dict, Action]]],
]
