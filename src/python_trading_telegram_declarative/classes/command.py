from python_trading_telegram_declarative.classes.enums import DynamicEnum


class Command(DynamicEnum):
    """
    Enum dynamique pour les commandes. Les membres sont injectés au démarrage
    via la méthode `Command.register({...})`.
    """

    # Les membres comme HELP, BONJOUR, etc. seront ajoutés dynamiquement.
    pass
