from typing import Optional

from .classes.command import Command
from .decorators import COMMAND_REGISTRY


class TelegramHandler:
    def process_command(self, command: Command, arguments: list) -> Optional[dict]:
        command_details = COMMAND_REGISTRY.get(command.value)
        if not command_details:
            return {"text": "Commande inconnue."}

        action_func = command_details.get("action")
        arg_names = command_details.get("arg_names", [])
        kwargs_types = command_details.get("kwargs_types", {})

        if len(arguments) != len(arg_names):
            return {"text": f"Erreur: {len(arg_names)} argument(s) attendu(s), reçu {len(arguments)}."}

        kwargs = {}
        for i, arg_name in enumerate(arg_names):
            try:
                expected_type = kwargs_types.get(arg_name, str)
                kwargs[arg_name] = expected_type(arguments[i])
            except (ValueError, TypeError):
                return {"text": f"L'argument '{arguments[i]}' pour '{arg_name}' est invalide. Type attendu : {expected_type.__name__}."}

        if hasattr(self, action_func.__name__):
            bound_action = getattr(self, action_func.__name__)
            return bound_action(**kwargs)
        return {"text": "Erreur: impossible d'exécuter la commande."}
