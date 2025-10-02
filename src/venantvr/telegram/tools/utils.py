# telegram/utils.py
from typing import Any, List


def ensure_list(item: Any) -> List[Any]:
    """Convertit un élément en liste s'il ne l'est pas déjà."""
    return [item] if not isinstance(item, list) else item


def is_empty_or_none(value: Any) -> bool:
    """Vérifie si une valeur est vide ou None."""
    return value is None or (isinstance(value, str) and value == "")


def truncate_text(text, max_length=14):
    return text[: max_length - 3] + "..." if len(text) > max_length else text
