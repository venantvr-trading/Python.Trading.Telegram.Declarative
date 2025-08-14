from venantvr.telegram.decorators import command
from venantvr.telegram.handler import TelegramHandler


class MySimpleHandler(TelegramHandler):
    @command(name="/menu", menu="/menu", description="Afficher le menu")
    def menu(self) -> dict:
        return {}

    @command(name="/bonjour1", menu="/menu", description="Dire bonjour 1")
    def bonjour1(self) -> dict:
        return {"text": "Bonjour, le monde 1 !"}

    @command(name="/bonjour2", menu="/menu", description="Dire bonjour 2")
    def bonjour2(self) -> dict:
        return {"text": "Bonjour, le monde 2 !"}

    @command(
        name="/bonjour",
        menu="/menu",
        description="Salutation personnalisée avec nom et âge",
        asks=["Quel est votre nom ?", "Quel est votre âge ?"],
        kwargs_types={"name": str, "age": int}
    )
    def bonjour(self, name: str, age: int) -> dict:
        message_age = "vous êtes jeune !" if age < 18 else "vous êtes un adulte."
        return {"text": f"Bonjour, {name} ! À {age} ans, {message_age}"}
