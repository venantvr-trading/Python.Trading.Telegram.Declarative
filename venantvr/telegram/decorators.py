# venantvr/telegram/decorators.py
from typing import Callable, Any, Dict, List, Optional

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.menu import Menu

# Le registre global qui stockera toutes les définitions de commandes.
COMMAND_REGISTRY: Dict[str, Dict[str, Any]] = {}


def command(
        name: str,
        menu: str,
        asks: List[str] = None,
        kwargs_types: Dict[str, Callable] = None,
        description: str = ""
):
    """
    Décorateur pour enregistrer une fonction comme une commande du bot.

    :param name: La chaîne de la commande (ex: "/help"). Doit être unique.
    :param menu: Le menu parent auquel cette commande appartient (ex: "/main").
    :param asks: Une liste de questions à poser à l'utilisateur pour recueillir les arguments.
                 L'ordre des questions doit correspondre à l'ordre des arguments de la fonction.
    :param kwargs_types: Un dictionnaire qui mappe les noms des arguments à leur type attendu (ex: {"montant": float}).
    :param description: Une courte description de la commande pour les menus d'aide.
    """

    # noinspection PyUnresolvedReferences
    def decorator(func: Callable):
        command_name = name.strip()
        menu_name = menu.strip()

        if command_name in COMMAND_REGISTRY:
            raise ValueError(f"La commande '{command_name}' est déjà enregistrée.")

        # Enregistrement dynamique dans les enums pour conserver la compatibilité
        command_enum = Command.from_value(command_name)
        menu_enum = Menu.from_value(menu_name)

        # La signature de la fonction décorée fournit les noms des arguments
        # On ignore le premier argument qui est 'self'
        arg_names = list(func.__code__.co_varnames[1:func.__code__.co_argcount])

        # Validation : les arguments de la fonction doivent correspondre à kwargs_types et asks
        if kwargs_types and set(arg_names) != set(kwargs_types.keys()):
            raise ValueError(
                f"Incohérence entre les arguments de la fonction {arg_names} et les clés de kwargs_types "
                f"{list(kwargs_types.keys())} pour la commande '{command_name}'"
            )
        if asks and len(asks) != len(arg_names):
            raise ValueError(
                f"Le nombre de questions dans 'asks' ({len(asks)}) ne correspond pas au nombre d'arguments "
                f"de la fonction ({len(arg_names)}) pour la commande '{command_name}'"
            )

        COMMAND_REGISTRY[command_name] = {
            "action": func,
            "menu": menu_enum,
            "asks": asks or [],
            "kwargs_types": kwargs_types or {},
            "description": description,
            "enum": command_enum,
            "arg_names": arg_names,
        }

        return func

    return decorator


def get_command(command_name: str) -> Optional[Dict[str, Any]]:
    """Récupère la définition d'une commande depuis le registre."""
    return COMMAND_REGISTRY.get(command_name)


def get_commands_for_menu(menu_enum: Menu) -> List[Dict[str, Any]]:
    """Récupère toutes les commandes appartenant à un menu spécifique."""
    commands = [
        cmd for cmd in COMMAND_REGISTRY.values()
        if cmd["menu"] == menu_enum
    ]
    return sorted(commands, key=lambda cmd: cmd['enum'].value)


def get_top_level_menus() -> List[Menu]:
    """Récupère tous les menus uniques de premier niveau, en excluant '/none'."""
    menus = {
        cmd["menu"] for cmd in COMMAND_REGISTRY.values()
        if cmd["menu"] != Menu.from_value("/none")
    }
    return sorted(list(menus), key=lambda m: m.value)
