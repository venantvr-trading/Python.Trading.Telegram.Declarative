import json
import queue
import threading
import time
from typing import List, Union

from python_trading_telegram_declarative.classes.payload import TelegramPayload
from python_trading_telegram_declarative.client import (TelegramAPIError, TelegramClient,
                                      TelegramNetworkError)
from python_trading_telegram_declarative.history import TelegramHistoryManager
from python_trading_telegram_declarative.tools.logger import logger
from python_trading_telegram_declarative.tools.utils import ensure_list, is_empty_or_none


class MessageSender:
    """
    Manages asynchronous message sending via queue.
    Single responsibility: outgoing queue processing.
    """

    def __init__(
            self,
            client: TelegramClient,
            chat_id: str,
            history_manager: TelegramHistoryManager,
    ):
        self.__client = client
        self.__chat_id = chat_id
        self.__history_manager = history_manager
        self.__outgoing_queue = queue.Queue()
        self.__sender_thread = None
        self.__stop_event = threading.Event()

    def start(self):
        """Starts the sender thread."""
        if self.__sender_thread is None or not self.__sender_thread.is_alive():
            self.__stop_event.clear()
            self.__sender_thread = threading.Thread(
                target=self._message_sender, daemon=True
            )
            self.__sender_thread.start()
            logger.info("MessageSender started")

    def stop(self):
        """Stops the sender thread cleanly."""
        logger.info("Stopping MessageSender")
        self.__stop_event.set()
        self.flush_queue()
        if self.__sender_thread and self.__sender_thread.is_alive():
            self.__sender_thread.join(timeout=5)
        logger.info("MessageSender stopped")

    def send_message(self, messages: Union[TelegramPayload, List[TelegramPayload]]):
        """Adds one or more messages to the outgoing queue."""
        for message in ensure_list(messages):
            if self._is_valid_message(message):
                self.__outgoing_queue.put(message)
            else:
                logger.warning("Message ignored (empty or no content): %s", message)

    def flush_queue(self):
        """Immediately empties the outgoing queue."""
        logger.info("Immediate flush of outgoing queue")
        while not self.__outgoing_queue.empty():
            try:
                message = self.__outgoing_queue.get_nowait()
                self.__outgoing_queue.task_done()
                if self._is_valid_message(message):
                    payload = self._build_payload(message)
                    self._send_payload(payload)
                else:
                    logger.warning(
                        "Message without text content or markup: %s", message
                    )
            except queue.Empty:
                break

    def _message_sender(self):
        """Message sending thread."""
        logger.info("Starting message sending thread")
        while not self.__stop_event.is_set():
            try:
                message = self.__outgoing_queue.get(timeout=0.1)
                self.__outgoing_queue.task_done()

                if not message:
                    continue

                if self._is_valid_message(message):
                    payload = self._build_payload(message)
                    logger.info("Sending message: %s", json.dumps(payload))
                    self._send_payload(payload)
                else:
                    logger.warning(
                        "Message without text content or markup: %s", message
                    )

            except queue.Empty:
                time.sleep(0.1)
            except (TelegramAPIError, TelegramNetworkError) as e:
                logger.error(f"Telegram error during sending: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error in MessageSender: %s", e)

    def _build_payload(self, message: TelegramPayload) -> dict:
        """Builds a payload for the Telegram API."""
        return {
            "chat_id": self.__chat_id,
            "text": message.get("text", ""),
            "reply_markup": message.get("reply_markup", ""),
        }

    def _send_payload(self, payload: dict):
        """Sends a payload and logs the interaction."""
        self.__history_manager.log_interaction(
            "outgoing", payload["chat_id"], "message", payload
        )
        self.__client.send_message(payload)

    # noinspection PyTypedDict
    @staticmethod
    def _is_valid_message(message: TelegramPayload) -> bool:
        """Checks if a message contains valid content."""
        return message and any(
            not is_empty_or_none(message.get(key)) for key in ["text", "reply_markup"]
        )

    # Test helpers - for testing purposes only
    def _get_test_attributes(self) -> dict:
        """Get internal attributes for testing. Not for production use."""
        return {
            "chat_id": self.__chat_id,
            "outgoing_queue": self.__outgoing_queue,
            "sender_thread": self.__sender_thread,
            "stop_event": self.__stop_event,
        }


class MessageReceiver:
    """
    Manages message reception via polling.
    Single responsibility: retrieving Telegram updates.
    """

    def __init__(self, client: TelegramClient, history_manager: TelegramHistoryManager):
        self.__client = client
        self.__history_manager = history_manager
        self.__last_update_id = None
        self.__incoming_queue = queue.Queue()
        self.__receiver_thread = None
        self.__stop_event = threading.Event()

    @property
    def incoming_queue(self) -> queue.Queue:
        """Access to the incoming messages queue."""
        return self.__incoming_queue

    def start(self):
        """Starts the reception thread."""
        if self.__receiver_thread is None or not self.__receiver_thread.is_alive():
            self.__stop_event.clear()
            self.__receiver_thread = threading.Thread(
                target=self._message_receiver, daemon=True
            )
            self.__receiver_thread.start()
            logger.info("MessageReceiver started")

    def stop(self):
        """Stops the reception thread cleanly."""
        logger.info("Stopping MessageReceiver")
        self.__stop_event.set()
        self.__incoming_queue.put(None)  # Stop signal
        if self.__receiver_thread and self.__receiver_thread.is_alive():
            self.__receiver_thread.join(timeout=5)
        logger.info("MessageReceiver stopped")

    def _message_receiver(self):
        """Message reception thread."""
        logger.info("Starting message reception thread")
        while not self.__stop_event.is_set():
            try:
                params = {"timeout": 30}
                if self.__last_update_id is not None:
                    params["offset"] = self.__last_update_id + 1

                updates = self.__client.get_updates(params)
                logger.info("Updates received: %s", json.dumps(updates))

                for update in updates.get("result", []):
                    self.__last_update_id = update.get("update_id")
                    chat_id, message_type, content = self.parse_update(update)
                    if chat_id:
                        self.__history_manager.log_interaction(
                            "incoming",
                            chat_id,
                            message_type,
                            content,
                            update.get("update_id"),
                        )
                    self.__incoming_queue.put(update)

            except TelegramNetworkError as e:
                logger.warning("Network error in MessageReceiver: %s", e)
                time.sleep(3)
            except Exception as e:
                logger.exception(f"Unexpected error in MessageReceiver: %s", e)
                time.sleep(1)

    @staticmethod
    def parse_update(update: dict) -> tuple[int | None, str, dict]:
        """Parses a Telegram update."""
        if "message" in update and "text" in update.get("message", {}):
            chat_id = update.get("message", {}).get("chat", {}).get("id")
            content = {"text": update["message"]["text"]}
            return chat_id, "text", content
        elif "callback_query" in update:
            chat_id = (
                update.get("callback_query", {})
                .get("message", {})
                .get("chat", {})
                .get("id")
            )
            content = {"data": update["callback_query"]["data"]}
            return chat_id, "callback_query", content
        return None, "unknown", update

    # Test helpers - for testing purposes only
    def _get_test_attributes(self) -> dict:
        """Get internal attributes for testing. Not for production use."""
        return {
            "last_update_id": self.__last_update_id,
            "incoming_queue": self.__incoming_queue,
            "receiver_thread": self.__receiver_thread,
            "stop_event": self.__stop_event,
        }
