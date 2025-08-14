import os
import queue
import threading
import time
from typing import Callable, Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


class DynamicEnumMember:
    def __init__(self, name: str, value: str, parent_enum: type['DynamicEnum']):
        self.name = name
        self.value = value
        self.parent_enum = parent_enum

    def __repr__(self) -> str:
        return f"<{self.parent_enum.__name__}.{self.name}: '{self.value}'>"

    def __eq__(self, other) -> bool:
        if isinstance(other, DynamicEnumMember): return self.value == other.value
        if isinstance(other, str): return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


class DynamicEnum:
    _members: dict[str, DynamicEnumMember] = {}
    _value_map: dict[str, DynamicEnumMember] = {}

    @classmethod
    def from_value(cls, value: str) -> DynamicEnumMember:
        if value in cls._value_map: return cls._value_map[value]
        name = value.lstrip('/').upper().replace("_", "")
        if not name: name = "ROOT"
        member = DynamicEnumMember(name, value, parent_enum=cls)
        cls._members[name] = member
        setattr(cls, name, member)
        cls._value_map[value] = member
        return member


class Command(DynamicEnum): pass


class Menu(DynamicEnum): pass


COMMAND_REGISTRY: Dict[str, Dict[str, Any]] = {}


def command(name: str, menu: str, description: str = ""):
    def decorator(func: Callable):
        command_enum = Command.from_value(name)
        menu_enum = Menu.from_value(menu)
        COMMAND_REGISTRY[name] = {"action": func, "menu": menu_enum, "enum": command_enum}
        return func

    return decorator


class TelegramHandler:
    def process_command(self, command: Command, arguments: list) -> Optional[dict]:
        command_details = COMMAND_REGISTRY.get(command.value)
        if not command_details: return None

        action_func = command_details.get("action")
        if hasattr(self, action_func.__name__):
            bound_action = getattr(self, action_func.__name__)
            return bound_action()
        return None


class TelegramBot:
    def __init__(self, bot_token, chat_id):
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id
        self.last_update_id = None
        self.incoming_queue = queue.Queue()
        self.outgoing_queue = queue.Queue()
        self.handler = None

        threading.Thread(target=self._receiver, daemon=True).start()
        threading.Thread(target=self._sender, daemon=True).start()
        threading.Thread(target=self._processor, daemon=True).start()
        print("Bot initialisé. Threads démarrés.")

    def _receiver(self):
        """Récupère les messages de Telegram (long polling)."""
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
                time.sleep(10)

    def _sender(self):
        """Envoie les messages en attente dans la file sortante."""
        while True:
            payload = self.outgoing_queue.get()
            if payload is None: break
            try:
                requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
            except Exception as e:
                print(f"Erreur dans _sender: {e}")
            self.outgoing_queue.task_done()

    def _processor(self):
        """Traite les messages de la file entrante."""
        while True:
            update = self.incoming_queue.get()
            if update is None: break

            response_payload = None
            if "message" in update and "text" in update["message"]:
                text = update["message"]["text"]
                if text == "/menu":
                    response_payload = self._build_menu_keyboard("/menu")

            elif "callback_query" in update:
                command_str = update["callback_query"]["data"]
                cmd_enum = Command.from_value(command_str)
                if self.handler:
                    response_payload = self.handler.process_command(cmd_enum, [])

            if response_payload:
                response_payload['chat_id'] = self.chat_id
                self.send_message(response_payload)
            self.incoming_queue.task_done()

    def _build_menu_keyboard(self, menu_str: str) -> dict:
        """Construit un clavier de menu."""
        menu_enum = Menu.from_value(menu_str)
        buttons = []
        for cmd_details in COMMAND_REGISTRY.values():
            if cmd_details['menu'] == menu_enum:
                button_text = cmd_details['enum'].name.capitalize()
                buttons.append([{"text": button_text, "callback_data": cmd_details['enum'].value}])

        return {
            "text": "Veuillez choisir une option :",
            "reply_markup": {"inline_keyboard": buttons}
        }

    def send_message(self, payload: dict):
        self.outgoing_queue.put(payload)

    def stop(self):
        self.outgoing_queue.put(None)
        self.incoming_queue.put(None)
        print("Signal d'arrêt envoyé aux threads.")


class MySimpleHandler(TelegramHandler):
    """Un handler simple avec une seule commande."""

    @command(name="/bonjour", menu="/menu", description="Dire bonjour")
    def bonjour(self) -> dict:
        """Retourne un simple message de salutation."""
        return {"text": "Bonjour, le monde !"}


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
