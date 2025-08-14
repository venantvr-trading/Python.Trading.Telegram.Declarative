import os
import time

from dotenv import load_dotenv

from tests.handler import MySimpleHandler
from venantvr.telegram.bot import TelegramBot

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


if __name__ == "__main__":
    if "VOTRE" in BOT_TOKEN or "VOTRE" in CHAT_ID:
        print("ERREUR : Veuillez configurer votre BOT_TOKEN et CHAT_ID en haut du fichier.")
    else:
        bot = TelegramBot(bot_token=BOT_TOKEN, chat_id=CHAT_ID)

        my_handler = MySimpleHandler()

        bot.handler = my_handler

        print(f"Bot démarré pour le chat ID {CHAT_ID}.")
        print("Envoyez /menu à votre bot.")
        print("Appuyez sur Ctrl+C pour arrêter.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            bot.stop()
            print("\nBot arrêté proprement.")
