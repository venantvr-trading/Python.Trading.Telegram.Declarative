from venantvr.telegram.classes.dynamic_enum import DynamicEnum


class Command(DynamicEnum):
    """
    Enum dynamique pour les commandes. Les membres sont injectés au démarrage
    via la méthode `Command.register({...})`.
    """
    # Les membres comme HELP, BONJOUR, etc. seront ajoutés dynamiquement.
    pass
