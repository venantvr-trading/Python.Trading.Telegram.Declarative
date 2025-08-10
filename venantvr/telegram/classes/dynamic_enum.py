from typing import Optional, Type


class DynamicEnumMember:
    """Représente un membre d'un enum dynamique (ex: Command.HELP)."""

    def __init__(self, name: str, value: str, parent_enum: Type['DynamicEnum']):
        self.name = name
        self.value = value
        self.parent_enum = parent_enum

    def __repr__(self) -> str:
        return f"<{self.parent_enum.__name__}.{self.name}: '{self.value}'>"

    def __eq__(self, other) -> bool:
        # Permet la comparaison avec un autre membre ou une chaîne de caractères
        if isinstance(other, DynamicEnumMember):
            return self.value == other.value and self.parent_enum == other.parent_enum
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        # Nécessaire pour utiliser les membres comme clés de dictionnaire
        return hash((self.value, self.parent_enum.__name__))


class DynamicEnum:
    """Classe de base pour créer des enums dont les membres sont injectés."""
    _members: dict[str, DynamicEnumMember] = {}
    _value_map: dict[str, DynamicEnumMember] = {}

    @classmethod
    def register(cls, items: dict[str, str]):
        """Injecte les membres dans la classe enum."""
        if not cls._members:  # Éviter la réinitialisation si déjà peuplé
            for name, value in items.items():
                member = DynamicEnumMember(name, value, parent_enum=cls)
                cls._members[name] = member
                setattr(cls, name, member)
                cls._value_map[value] = member

    @classmethod
    def from_value(cls, value: str) -> Optional[DynamicEnumMember]:
        """Retrouve un membre par sa valeur."""
        if value in cls._value_map:
            return cls._value_map[value]
        # Créer dynamiquement si non existant (pour les handlers)
        name = value.lstrip('/').upper()
        member = DynamicEnumMember(name, value, parent_enum=cls)
        cls._members[name] = member
        setattr(cls, name, member)
        cls._value_map[value] = member
        return member

    @classmethod
    def get_all(cls) -> list[DynamicEnumMember]:
        """Retourne tous les membres enregistrés."""
        return list(cls._members.values())
