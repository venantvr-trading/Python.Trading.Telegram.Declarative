# venantvr/telegram/handler.py
from typing import Union, List

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.decorators import get_command
from venantvr.telegram.tools.logger import logger


class TelegramHandler:
    """
    Classe de base pour les handlers de commandes Telegram.
    Les commandes sont maintenant définies via le décorateur @command dans les sous-classes.
    """

    def process_command(self, command: Command, arguments: list) -> Union[TelegramPayload, List[TelegramPayload], None]:
        """
        Traite une commande en la cherchant dans le registre et en l'exécutant.
        :param command: Commande à traiter.
        :param arguments: Liste des valeurs des arguments pour la commande.
        :return: Résultat de la commande ou None si cette commande n'appartient pas à ce handler.
        """
        command_details = get_command(command.value)

        if not command_details:
            logger.warning(f"Aucune action trouvée pour la commande '{command.value}' dans le registre.")
            output: TelegramPayload = {"text": f"Commande '{command.value}' non reconnue.", "reply_markup": ""}
            return output

        action_func = command_details.get("action")
        # Vérifie si la méthode de commande (ex: 'set_sell_price') existe sur l'instance actuelle ('self')
        if not hasattr(self, action_func.__name__):
            # Cette commande appartient à un autre handler, on l'ignore.
            return None

        kwargs_types = command_details.get("kwargs_types", {})
        arg_names = command_details.get("arg_names", [])
        kwargs = {}

        if len(arguments) != len(arg_names):
            logger.error(f"Nombre d'arguments incorrect pour {command.value}. Attendu: {len(arg_names)}, Reçu: {len(arguments)}")
            output: TelegramPayload = {"text": f"Erreur interne: nombre d'arguments incorrect pour la commande.", "reply_markup": ""}
            return output

        # Conversion et validation des types
        for i, arg_name in enumerate(arg_names):
            try:
                expected_type = kwargs_types.get(arg_name, str)  # str par défaut
                kwargs[arg_name] = expected_type(arguments[i])
            except (ValueError, TypeError) as e:
                logger.error(f"Échec de la conversion du type pour l'argument '{arg_name}': {e}")
                output: TelegramPayload = {
                    "text": f"Argument '{arguments[i]}' pour '{arg_name}' est invalide. Type attendu : {expected_type.__name__}.",
                    "reply_markup": ""
                }
                return output

        # Récupère la méthode liée à l'instance `self` et l'exécute
        bound_action = getattr(self, action_func.__name__)
        return bound_action(**kwargs)

    def bonjour(self) -> TelegramPayload:
        """Exemple de commande qui peut être décorée dans une sous-classe."""
        return {"text": f"Bonjour depuis {self.__class__.__name__}", "reply_markup": ""}
