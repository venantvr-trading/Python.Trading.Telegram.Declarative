import os
import queue
import threading
import time
from typing import Callable, Dict, List, Optional

import requests
from dotenv import load_dotenv

from venantvr.telegram.classes.command import Command
from venantvr.telegram.decorators import COMMAND_REGISTRY

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def command(name: str, description: str = "", asks: Optional[List[str]] = None, kwargs_types: Optional[Dict[str, Callable]] = None):
    def decorator(func: Callable):
        command_enum = Command.from_value(name)
        arg_names = list(func.__code__.co_varnames[1:func.__code__.co_argcount])
        COMMAND_REGISTRY[name] = {
            "action": func,
            "enum": command_enum,
            "arg_names": arg_names,
            "asks": asks or [],
            "kwargs_types": kwargs_types or {}
        }
        return func

    return decorator


class TelegramHandler:
    def process_command(self, command: Command, arguments: list) -> Optional[dict]:
        command_details = COMMAND_REGISTRY.get(command.value)
        if not command_details: return None

        action_func = command_details.get("action")
        arg_names = command_details.get("arg_names", [])
        kwargs_types = command_details.get("kwargs_types", {})

        if len(arguments) != len(arg_names):
            return {"text": "Erreur: Nombre d'arguments incorrect."}

        kwargs = {}
        for i, arg_name in enumerate(arg_names):
            try:
                expected_type = kwargs_types.get(arg_name, str)
                kwargs[arg_name] = expected_type(arguments[i])
            except (ValueError, TypeError):
                return {"text": f"L'argument '{arguments[i]}' est invalide."}

        if hasattr(self, action_func.__name__):
            bound_action = getattr(self, action_func.__name__)
            return bound_action(**kwargs)
        return None


class TelegramBot:
    def __init__(self, bot_token, chat_id):
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id
        self.last_update_id = None
        self.incoming_queue = queue.Queue()
        self.outgoing_queue = queue.Queue()
        self.handler = None
        self.active_prompts = {}

        threading.Thread(target=self._receiver, daemon=True).start()
        threading.Thread(target=self._sender, daemon=True).start()
        threading.Thread(target=self._processor, daemon=True).start()
        print("Bot initialisé. Threads démarrés.")

    def _receiver(self):
        while True:
            try:
                params = {"timeout": 30}
                if self.last_update_id:
                    params["offset"] = self.last_update_id + 1
                response = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=35)
                response.raise_for_status()
                updates = response.json().get("result", [])
                for update in updates:
                    self.last_update_id = update["update_id"]
                    self.incoming_queue.put(update)
            except requests.RequestException:
                time.sleep(3)
            except Exception as e:
                print(f"Erreur dans _receiver: {e}")

    def _sender(self):
        while True:
            payload = self.outgoing_queue.get()
            if payload is None: break
            try:
                requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
            except Exception as e:
                print(f"Erreur dans _sender: {e}")
            self.outgoing_queue.task_done()

    def _processor(self):
        while True:
            update = self.incoming_queue.get()
            if update is None: break

            response_payload = None
            if "message" in update and "text" in update["message"]:
                text = update["message"]["text"]
                chat_id = str(update["message"]["chat"]["id"])

                if chat_id in self.active_prompts:
                    prompt_info = self.active_prompts.pop(chat_id)
                    command_name = prompt_info['command']
                    cmd_enum = Command.from_value(command_name)
                    arguments = [text]
                    if self.handler:
                        response_payload = self.handler.process_command(cmd_enum, arguments)
                else:
                    command_name = text.split(' ')[0]
                    command_details = COMMAND_REGISTRY.get(command_name)

                    if command_details:
                        if command_details.get("asks"):
                            self.active_prompts[chat_id] = {'command': command_name}
                            first_question = command_details["asks"][0]
                            response_payload = {"text": first_question}
                        else:
                            cmd_enum = Command.from_value(command_name)
                            if self.handler:
                                response_payload = self.handler.process_command(cmd_enum, [])

            if response_payload:
                if 'chat_id' not in response_payload:
                    response_payload['chat_id'] = self.chat_id
                if 'text' not in response_payload:
                    response_payload['text'] = ''
                self.send_message(response_payload)
            self.incoming_queue.task_done()

    def send_message(self, payload: dict):
        self.outgoing_queue.put(payload)

    def stop(self):
        self.outgoing_queue.put(None)
        self.incoming_queue.put(None)
        print("Signal d'arrêt envoyé aux threads.")


class MySimpleHandler(TelegramHandler):

    @command(name="/menu", description="Afficher le menu d'aide")
    def menu(self) -> dict:
        """Construit et retourne un message texte listant les commandes."""

        text_response = "Voici les commandes disponibles à taper :\n"
        for cmd_name, cmd_details in COMMAND_REGISTRY.items():
            description = cmd_details.get("description", "Pas de description.")
            text_response += f"\n• `{cmd_name}` : {description}"

        return {"text": text_response, "parse_mode": "Markdown"}

    @command(
        name="/bonjour",
        description="Salutation personnalisée",
        asks=["Quel est votre nom ?"],
        kwargs_types={"name": str}
    )
    def bonjour(self, name: str) -> dict:
        """Salue l'utilisateur par son nom."""
        return {"text": f"Bonjour, {name} ! Bienvenue."}


if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("ERREUR : Impossible de trouver BOT_TOKEN ou CHAT_ID.")
        print("Veuillez créer un fichier .env et y mettre vos identifiants.")
    else:
        bot = TelegramBot(bot_token=BOT_TOKEN, chat_id=CHAT_ID)
        my_handler = MySimpleHandler()
        bot.handler = my_handler

        print(f"Bot démarré pour le chat ID {CHAT_ID}.")
        print("Envoyez /menu ou /bonjour à votre bot.")
        print("Appuyez sur Ctrl+C pour arrêter.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            bot.stop()
            print("\nBot arrêté proprement.")
