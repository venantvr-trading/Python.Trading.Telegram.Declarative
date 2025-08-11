# Telegram Command Arguments Handler

Cette librairie facilite la gestion et la validation des arguments passés aux commandes dans un bot Telegram.

## Fonctionnalités principales

- Extraction automatique des arguments des commandes Telegram en fonction des types attendus.
- Validation et conversion des paramètres reçus via les messages ou callback queries.
- Gestion centralisée des commandes Telegram et de leurs paramètres.
- Simplification du traitement des interactions complexes avec plusieurs arguments dans un contexte Telegram.

## Usage

La librairie permet de définir des commandes Telegram avec leurs paramètres typés, puis d’extraire proprement les arguments reçus dans les messages ou callbacks, en
garantissant leur cohérence et en réduisant le code redondant.

```python
@property
def command_actions(self) -> CommandActionType:
    # noinspection PyUnresolvedReferences
    return {
        Menu.from_value("/positions"): {
            Command.from_value("/bonjour"): {
                "action": self.bonjour,
                "args": (),
                "kwargs": {}
            },
            Command.from_value("/show_positions"): {
                "action": lambda: self.commands_helper.show_positions(self.__db_path),
                "args": (),
                "kwargs": {}
            },
        },
        Menu.from_value("/none"): {
            Command.from_value("/set_sell_price"): {
                "action": self.commands_helper.set_sell_price,
                "args": (self.__db_path,),
                "kwargs": {
                    "position_id": str,
                    "percentage_change": float,
                    # "new_sale_price": float
                },
                "asks": [
                    {"text": "Veuillez entrer l'ID de la position:", "reply_markup": ""},
                    {"text": "Veuillez entrer le pourcentage de changement du prix de vente (ex. 10 pour +10%):", "reply_markup": ""},
                    # {"text": "Veuillez entrer le nouveau prix de vente (ex. 100.50):", "reply_markup": ""}
                ],
                "respond": lambda args: [
                    self.extract_number(arg, expected_type=type_)
                    for arg, type_ in zip(args[-len(self.command_actions[Menu.from_value("/none")][Command.from_value("/set_sell_price")]["kwargs"]):],
                                          self.command_actions[Menu.from_value("/none")][Command.from_value("/set_sell_price")]["kwargs"].values())
                ]
            }
        }
    }
```

## Logs

```text
2025-08-11 10:29:37,615 - INFO - _message_receiver : {"ok": true, "result": []}
2025-08-11 10:29:43,812 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157805, "message": {"message_id": 2103, "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754900983, "text": "/start", "entities": [{"offset": 0, "length": 6, "type": "bot_command"}]}}]}
2025-08-11 10:29:47,364 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157806, "message": {"message_id": 2104, "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754900987, "text": "/help", "entities": [{"offset": 0, "length": 5, "type": "bot_command"}]}}]}
2025-08-11 10:29:47,434 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Voici les commandes disponibles:", "reply_markup": "{\"inline_keyboard\": [[{\"text\": \"Ccxt\", \"callback_data\": \"/ccxt\"}, {\"text\": \"Positions\", \"callback_data\": \"/positions\"}, {\"text\": \"Bot\", \"callback_data\": \"/bot\"}]]}"}
2025-08-11 10:29:55,930 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157807, "callback_query": {"id": "ANONYMIZED_CALLBACK_ID_1", "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "message": {"message_id": 2105, "from": {"id": BOT_ID, "is_bot": true, "first_name": "BOT_NAME", "username": "bot_anonymized"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754900987, "text": "Voici les commandes disponibles:", "reply_markup": {"inline_keyboard": [[{"text": "Ccxt", "callback_data": "/ccxt"}, {"text": "Positions", "callback_data": "/positions"}, {"text": "Bot", "callback_data": "/bot"}]]}}, "chat_instance": "ANONYMIZED_CHAT_INSTANCE_1", "data": "/ccxt"}}]}
2025-08-11 10:29:55,964 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Voici les commandes disponibles:", "reply_markup": "{\"inline_keyboard\": [[{\"text\": \"Bonjour\", \"callback_data\": \"/bonjour\"}, {\"text\": \"Get price\", \"callback_data\": \"/get_price\"}, {\"text\": \"Set offline\", \"callback_data\": \"/set_offline\"}], [{\"text\": \"Set online\", \"callback_data\": \"/set_online\"}, {\"text\": \"Execute buy\", \"callback_data\": \"/execute_buy\"}, {\"text\": \"Disable buy\", \"callback_data\": \"/disable_buy\"}], [{\"text\": \"Execute sell\", \"callback_data\": \"/execute_sell\"}, {\"text\": \"Disable sell\", \"callback_data\": \"/disable_sell\"}, {\"text\": \"Get balance\", \"callback_data\": \"/get_balance\"}]]}"}
2025-08-11 10:29:57,688 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157808, "callback_query": {"id": "ANONYMIZED_CALLBACK_ID_2", "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "message": {"message_id": 2106, "from": {"id": BOT_ID, "is_bot": true, "first_name": "BOT_NAME", "username": "bot_anonymized"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754900996, "text": "Voici les commandes disponibles:", "reply_markup": {"inline_keyboard": [[{"text": "Bonjour", "callback_data": "/bonjour"}, {"text": "Get price", "callback_data": "/get_price"}, {"text": "Set offline", "callback_data": "/set_offline"}], [{"text": "Set online", "callback_data": "/set_online"}, {"text": "Execute buy", "callback_data": "/execute_buy"}, {"text": "Disable buy", "callback_data": "/disable_buy"}], [{"text": "Execute sell", "callback_data": "/execute_sell"}, {"text": "Disable sell", "callback_data": "/disable_sell"}, {"text": "Get balance", "callback_data": "/get_balance"}]]}}, "chat_instance": "ANONYMIZED_CHAT_INSTANCE_1", "data": "/bonjour"}}]}
2025-08-11 10:29:57,750 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Bonjour CcxtExchange", "reply_markup": ""}
2025-08-11 10:29:57,910 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Bonjour PositionsManager", "reply_markup": ""}
2025-08-11 10:29:58,103 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Bonjour TradingBot", "reply_markup": ""}
2025-08-11 10:30:00,857 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157809, "callback_query": {"id": "ANONYMIZED_CALLBACK_ID_3", "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "message": {"message_id": 2105, "from": {"id": BOT_ID, "is_bot": true, "first_name": "BOT_NAME", "username": "bot_anonymized"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754900987, "text": "Voici les commandes disponibles:", "reply_markup": {"inline_keyboard": [[{"text": "Ccxt", "callback_data": "/ccxt"}, {"text": "Positions", "callback_data": "/positions"}, {"text": "Bot", "callback_data": "/bot"}]]}}, "chat_instance": "ANONYMIZED_CHAT_INSTANCE_1", "data": "/positions"}}]}
2025-08-11 10:30:00,956 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Voici les commandes disponibles:", "reply_markup": "{\"inline_keyboard\": [[{\"text\": \"Bonjour\", \"callback_data\": \"/bonjour\"}, {\"text\": \"Show positions\", \"callback_data\": \"/show_positions\"}]]}"}
2025-08-11 10:30:03,295 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157810, "callback_query": {"id": "ANONYMIZED_CALLBACK_ID_4", "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "message": {"message_id": 2110, "from": {"id": BOT_ID, "is_bot": true, "first_name": "BOT_NAME", "username": "bot_anonymized"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754901001, "text": "Voici les commandes disponibles:", "reply_markup": {"inline_keyboard": [[{"text": "Bonjour", "callback_data": "/bonjour"}, {"text": "Show positions", "callback_data": "/show_positions"}]]}}, "chat_instance": "ANONYMIZED_CHAT_INSTANCE_1", "data": "/show_positions"}}]}
2025-08-11 10:30:03,463 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Positions ouvertes:\n\u2022 ID: POSITION_ID\n  - Purchase Price: 116444.40\n  - Tokens: 0.000572\n  - Sale Price: 116560844.40\n  - Next Price: 115279.96\n", "reply_markup": "{\"inline_keyboard\": [[{\"text\": \"Changer le prix de vente\", \"callback_data\": \"ask:/set_sell_price:POSITION_ID\"}]]}"}
2025-08-11 10:30:04,993 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157811, "callback_query": {"id": "ANONYMIZED_CALLBACK_ID_5", "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "message": {"message_id": 2111, "from": {"id": BOT_ID, "is_bot": true, "first_name": "BOT_NAME", "username": "bot_anonymized"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754901003, "text": "Positions ouvertes:\n\u2022 ID: POSITION_ID\n  - Purchase Price: 116444.40\n  - Tokens: 0.000572\n  - Sale Price: 116560844.40\n  - Next Price: 115279.96", "reply_markup": {"inline_keyboard": [[{"text": "Changer le prix de vente", "callback_data": "ask:/set_sell_price:POSITION_ID"}]]}}, "chat_instance": "ANONYMIZED_CHAT_INSTANCE_1", "data": "ask:/set_sell_price:POSITION_ID"}}]}
2025-08-11 10:30:05,010 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Veuillez entrer l'ID de la position:", "reply_markup": ""}
2025-08-11 10:30:15,657 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157812, "message": {"message_id": 2113, "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754901015, "text": "POSITION_ID"}}]}
2025-08-11 10:30:15,720 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Veuillez entrer le pourcentage de changement du prix de vente (ex. 10 pour +10%):", "reply_markup": ""}
2025-08-11 10:30:18,953 - INFO - _message_receiver : {"ok": true, "result": [{"update_id": 466157813, "message": {"message_id": 2115, "from": {"id": USER_ID, "is_bot": false, "first_name": "USER_NAME", "username": "user_anonymized", "language_code": "fr"}, "chat": {"id": USER_ID, "first_name": "USER_NAME", "username": "user_anonymized", "type": "private"}, "date": 1754901018, "text": "10000"}}]}
2025-08-11 10:30:18,980 - INFO - _message_sender : {"chat_id": USER_ID, "text": "Sell price for position POSITION_ID updated to 11760884.399999999", "reply_markup": ""}
```