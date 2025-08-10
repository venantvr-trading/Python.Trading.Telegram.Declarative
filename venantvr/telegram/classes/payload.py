from typing import TypedDict, Any


class TelegramPayload(TypedDict):
    text: str
    reply_markup: Any
