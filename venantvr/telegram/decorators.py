from typing import Callable, Dict, List, Optional

from .classes.command import Command
from .classes.menu import Menu

COMMAND_REGISTRY: Dict[str, dict] = {}

def command(
        name: str,
        menu: Optional[str] = None,
        description: str = "",
        asks: Optional[List[str]] = None,
        kwargs_types: Optional[Dict[str, Callable]] = None
):
    def decorator(func: Callable):
        command_enum = Command.from_value(name)
        menu_enum = Menu.from_value(menu) if menu else None
        arg_names = list(func.__code__.co_varnames[1:func.__code__.co_argcount])
        COMMAND_REGISTRY[name] = {
            "action": func,
            "enum": command_enum,
            "menu": menu_enum,
            "arg_names": arg_names,
            "asks": asks or [],
            "kwargs_types": kwargs_types or {},
            "description": description
        }
        return func
    return decorator