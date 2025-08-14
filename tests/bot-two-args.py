import json
import os
import time
from typing import Dict

from dotenv import load_dotenv

from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.menu import Menu
from venantvr.telegram.classes.payload import TelegramPayload
from venantvr.telegram.decorators import command, COMMAND_REGISTRY
from venantvr.telegram.handler import TelegramHandler
from venantvr.telegram.history import TelegramHistoryManager
from venantvr.telegram.notification import TelegramNotificationService
from venantvr.telegram.tools.logger import logger

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

API_BASE_URL = "https://api.telegram.org/bot"
ENDPOINTS = {
    "text": "/sendMessage",
    "updates": "/getUpdates"
}


class MySimpleHandler(TelegramHandler):
    @command(name="/help", menu="/main", description="Afficher le menu principal")
    def help(self) -> TelegramPayload:
        """Retourne un clavier interactif avec les commandes disponibles."""
        logger.debug("Exécution de la commande /help")
        buttons = [
            [{"text": cmd["enum"].name.capitalize(), "callback_data": cmd["enum"].value}]
            for cmd in COMMAND_REGISTRY.values() if cmd["menu"] == Menu.from_value("/main")
        ]
        payload: TelegramPayload = {
            "text": "Veuillez choisir une option :",
            "reply_markup": json.dumps({"inline_keyboard": buttons})
        }
        logger.debug("Payload généré pour /help: %s", payload)
        return payload

    @command(
        name="/bonjour",
        menu="/main",
        description="Salutation personnalisée avec nom et âge",
        asks=[
            "Quel est votre nom ?",
            "Quel est votre âge ?"
        ],
        kwargs_types={
            "name": str,
            "age": int
        }
    )
    def bonjour(self, name: str, age: int) -> TelegramPayload:
        """Salue l'utilisateur par son nom et commente son âge."""
        logger.debug("Exécution de la commande /bonjour avec name=%s, age=%s", name, age)
        if age < 18:
            message_age = "vous êtes jeune !"
        else:
            message_age = "vous êtes un adulte."
        payload: TelegramPayload = {"text": f"Bonjour, {name} ! À {age} ans, {message_age}", "reply_markup": ""}
        logger.debug("Payload généré pour /bonjour: %s", payload)
        return payload

    @property
    def command_actions(self) -> Dict[Menu, Dict[Command, Dict]]:
        """Définit les actions associées aux commandes."""
        menu_main = Menu.from_value("/main")
        actions = {
            menu_main: {
                Command.from_value("/help"): {"action": self.help, "args": (), "kwargs": {}},
                Command.from_value("/bonjour"): {"action": self.bonjour, "args": (), "kwargs": {"name": str, "age": int}},
            }
        }
        logger.debug("command_actions défini: %s", actions)
        return actions


if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("ERREUR : Impossible de trouver BOT_TOKEN ou CHAT_ID.")
        print("Veuillez créer un fichier .env et y mettre vos identifiants.")
    else:
        db_path = "test_bot_two_args.db"
        history_manager = TelegramHistoryManager(db_path)

        bot = TelegramNotificationService(
            api_base_url=API_BASE_URL,
            bot_token=BOT_TOKEN,
            chat_id=CHAT_ID,
            endpoints=ENDPOINTS,
            history_manager=history_manager
        )

        my_handler = MySimpleHandler()
        bot.handler = my_handler
        logger.info("COMMAND_REGISTRY après instanciation: %s", COMMAND_REGISTRY)

        print(f"Bot démarré pour le chat ID {CHAT_ID}.")
        print("Envoyez /help ou /bonjour à votre bot.")
        print("Appuyez sur Ctrl+C pour arrêter.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            bot.stop()
            print("\nBot arrêté proprement.")
            os.remove(db_path)
