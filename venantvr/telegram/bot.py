import queue
import threading
import time
from typing import Optional, Dict

import requests

from .classes.command import Command
from .classes.menu import Menu
from .decorators import COMMAND_REGISTRY
from .handler import TelegramHandler


class TelegramBot:
    def __init__(self, bot_token: str, chat_id: str):
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id
        self.last_update_id = None
        self.incoming_queue = queue.Queue()
        self.outgoing_queue = queue.Queue()
        self.handler: Optional[TelegramHandler] = None
        self.active_prompts: Dict[str, Dict] = {}  # chat_id -> {'command': str, 'arguments': list}

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
                r = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=35)
                r.raise_for_status()
                updates = r.json().get("result", [])
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
            if payload is None:
                break
            try:
                requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
            except Exception as e:
                print(f"Erreur dans _sender: {e}")
            self.outgoing_queue.task_done()

    def _processor(self):
        while True:
            update = self.incoming_queue.get()
            if update is None:
                break

            response_payload = None

            if "message" in update and "text" in update["message"]:
                text = update["message"]["text"]
                chat_id = str(update["message"]["chat"]["id"])

                # --- Cas : l'utilisateur est en plein prompt multi-questions ---
                if chat_id in self.active_prompts:
                    prompt_info = self.active_prompts[chat_id]
                    command_name = prompt_info['command']
                    command_details = COMMAND_REGISTRY[command_name]

                    # Ajouter la réponse courante
                    prompt_info['arguments'].append(text)

                    # Vérifier s'il reste des questions
                    num_questions = len(command_details.get("asks", []))
                    if len(prompt_info['arguments']) < num_questions:
                        next_index = len(prompt_info['arguments'])
                        response_payload = {"text": command_details["asks"][next_index]}
                    else:
                        # Toutes les réponses reçues → exécuter la commande
                        cmd_enum = Command.from_value(command_name)
                        if self.handler:
                            response_payload = self.handler.process_command(cmd_enum, prompt_info['arguments'])
                        # Nettoyer le prompt actif
                        del self.active_prompts[chat_id]

                else:
                    # --- Cas : commande saisie ---
                    command_name = text.split(' ')[0]
                    command_details = COMMAND_REGISTRY.get(command_name)

                    if command_details:
                        # --- Cas spécial : /menu ---
                        if command_name == "/menu":
                            menu_str = command_details.get("menu") or "/menu"
                            response_payload = self._build_menu_keyboard(menu_str)

                        # --- Cas : commande avec prompts ---
                        elif command_details.get("asks"):
                            self.active_prompts[chat_id] = {"command": command_name, "arguments": []}
                            response_payload = {"text": command_details["asks"][0]}

                        # --- Cas : commande directe ---
                        else:
                            cmd_enum = Command.from_value(command_name)
                            if self.handler:
                                response_payload = self.handler.process_command(cmd_enum, [])

            # --- Cas : clic sur un bouton de menu ---
            elif "callback_query" in update:
                cmd_str = update["callback_query"]["data"]
                cmd_enum = Command.from_value(cmd_str)
                if self.handler:
                    response_payload = self.handler.process_command(cmd_enum, [])

            # --- Envoi de la réponse ---
            if response_payload:
                response_payload.setdefault('chat_id', self.chat_id)
                response_payload.setdefault('text', '')
                self.send_message(response_payload)

            self.incoming_queue.task_done()

    def _build_menu_keyboard(self, menu) -> dict:
        # Si menu est une string, convertit en enum ; sinon, assume que c'est déjà un Menu
        if isinstance(menu, str):
            menu_enum = Menu.from_value(menu)
        else:
            menu_enum = menu

        buttons = []
        for cmd_details in COMMAND_REGISTRY.values():
            if cmd_details.get('menu') == menu_enum:
                btn_text = cmd_details['enum'].name.capitalize()
                buttons.append([{"text": btn_text, "callback_data": cmd_details['enum'].value}])

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
