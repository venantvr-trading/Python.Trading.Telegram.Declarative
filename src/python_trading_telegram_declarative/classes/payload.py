from typing import Any, TypedDict


class TelegramPayload(TypedDict):
    text: str
    reply_markup: Any
