import unittest
from unittest.mock import Mock, patch
import queue

from venantvr.telegram.service import TelegramService
from venantvr.telegram.classes.enums import DynamicEnumMember
from tests.test_helpers import create_test_payload


class ConcreteTestService(TelegramService):
    """Implémentation concrète pour les tests."""
    
    def _process_commands(self):
        """Implémentation concrète de la méthode abstraite."""
        pass


# noinspection PyUnresolvedReferences,PyTypeChecker
class TestTelegramService(unittest.TestCase):
    """Tests unitaires pour TelegramService."""

    def setUp(self):
        """Configuration initiale pour chaque test."""
        self.api_base_url = "https://api.telegram.org/bot"
        self.bot_token = "123456:ABC-DEF"
        self.chat_id = "123456"
        self.endpoints = {
            "text": "/sendMessage",
            "updates": "/getUpdates"
        }
        self.mock_history_manager = Mock()
        
        with patch('venantvr.telegram.service.TelegramClient'), \
             patch('venantvr.telegram.service.MessageSender'), \
             patch('venantvr.telegram.service.MessageReceiver'):
            self.service = ConcreteTestService(
                self.api_base_url,
                self.bot_token,
                self.chat_id,
                self.endpoints,
                self.mock_history_manager
            )

    def test_init(self):
        """Test de l'initialisation du service."""
        self.assertEqual(self.service._TelegramService__chat_id, self.chat_id)
        self.assertIsNotNone(self.service._TelegramService__client)
        self.assertIsNotNone(self.service._TelegramService__sender)
        self.assertIsNotNone(self.service._TelegramService__receiver)

    def test_start_service(self):
        """Test du démarrage du service."""
        # Act
        self.service.start()
        
        # Assert
        self.service._TelegramService__sender.start.assert_called_once()
        self.service._TelegramService__receiver.start.assert_called_once()

    def test_stop_service(self):
        """Test de l'arrêt du service."""
        # Arrange
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.service._TelegramService__processor_thread = mock_thread
        
        # Act
        self.service.stop()
        
        # Assert
        self.assertTrue(self.service._TelegramService__stop_event.is_set())
        self.service._TelegramService__sender.stop.assert_called_once()
        self.service._TelegramService__receiver.stop.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_send_message(self):
        """Test de l'envoi de message."""
        # Arrange
        message = create_test_payload("Test message", "")
        
        # Act
        self.service.send_message(message)
        
        # Assert
        self.service._TelegramService__sender.send_message.assert_called_once_with(message)

    def test_flush_outgoing_queue(self):
        """Test du vidage de la file sortante."""
        # Act
        self.service.flush_outgoing_queue()
        
        # Assert
        self.service._TelegramService__sender.flush_queue.assert_called_once()

    def test_incoming_queue_property(self):
        """Test de l'accès à la file entrante."""
        # Arrange
        mock_queue = Mock(spec=queue.Queue)
        self.service._TelegramService__receiver.incoming_queue = mock_queue
        
        # Act
        result = self.service.incoming_queue
        
        # Assert
        self.assertEqual(result, mock_queue)

    def test_test_updates(self):
        """Test de la méthode test_updates."""
        # Arrange
        expected_updates = {"ok": True, "result": []}
        self.service._TelegramService__client.get_updates.return_value = expected_updates
        
        # Act
        result = self.service.test_updates()
        
        # Assert
        self.assertEqual(result, expected_updates)
        self.service._TelegramService__client.get_updates.assert_called_once_with({"timeout": 5})

    def test_test_updates_with_error(self):
        """Test de test_updates avec erreur."""
        # Arrange
        self.service._TelegramService__client.get_updates.side_effect = Exception("Network error")
        
        # Act
        result = self.service.test_updates()
        
        # Assert
        self.assertIsNone(result)

    def test_parse_update(self):
        """Test de la méthode parse_update."""
        # Arrange
        update = {"message": {"text": "Hello"}}
        expected_result = (123, 'text', {"text": "Hello"})
        self.service._TelegramService__receiver.parse_update.return_value = expected_result
        
        # Act
        result = self.service.parse_update(update)
        
        # Assert
        self.assertEqual(result, expected_result)
        self.service._TelegramService__receiver.parse_update.assert_called_once_with(update)

    def test_parse_command_with_action(self):
        """Test du parsing d'une commande avec action."""
        # Arrange
        command_update = {
            "callback_query": {
                "data": "ask:/test_command:param1;param2"
            }
        }
        
        with patch.object(self.service, '_cast_to_enum') as mock_cast:
            mock_enum = Mock(spec=DynamicEnumMember)
            mock_cast.return_value = mock_enum
            
            # Act
            action, enum_command, arguments = self.service.parse_command(command_update)
        
        # Assert
        self.assertEqual(action, "ask")
        self.assertEqual(enum_command, mock_enum)
        self.assertEqual(arguments, ["param1", "param2"])

    def test_parse_command_without_action(self):
        """Test du parsing d'une commande sans action."""
        # Arrange
        command_update = {
            "callback_query": {
                "data": "/simple_command"
            }
        }
        
        with patch.object(self.service, '_cast_to_enum') as mock_cast:
            mock_enum = Mock(spec=DynamicEnumMember)
            mock_cast.return_value = mock_enum
            
            # Act
            action, enum_command, arguments = self.service.parse_command(command_update)
        
        # Assert
        self.assertIsNone(action)
        self.assertEqual(enum_command, mock_enum)
        self.assertEqual(arguments, [])

    def test_parse_command_invalid_format(self):
        """Test du parsing avec format invalide."""
        # Arrange
        command_update = {
            "callback_query": {
                "data": "invalid_format"
            }
        }
        
        # Act
        action, enum_command, arguments = self.service.parse_command(command_update)
        
        # Assert
        self.assertIsNone(action)
        self.assertIsNone(enum_command)
        self.assertEqual(arguments, [])

    def test_cast_to_enum_success(self):
        """Test du cast vers enum réussi."""
        # Arrange
        value = "/test"
        mock_enum_class = Mock()
        mock_enum_member = Mock(spec=DynamicEnumMember)
        mock_enum_class.from_value.return_value = mock_enum_member
        
        # Act
        result = TelegramService._cast_to_enum(value, [mock_enum_class])
        
        # Assert
        self.assertEqual(result, mock_enum_member)
        mock_enum_class.from_value.assert_called_once_with(value)

    def test_cast_to_enum_failure(self):
        """Test du cast vers enum en échec."""
        # Arrange
        value = "/unknown"
        mock_enum_class = Mock()
        mock_enum_class.from_value.side_effect = ValueError("Not found")
        
        # Act
        result = TelegramService._cast_to_enum(value, [mock_enum_class])
        
        # Assert
        self.assertIsNone(result)

    def test_cast_to_enum_multiple_enums(self):
        """Test du cast avec plusieurs enums possibles."""
        # Arrange
        value = "/command"
        mock_enum1 = Mock()
        mock_enum1.from_value.side_effect = ValueError("Not in enum1")
        
        mock_enum2 = Mock()
        mock_enum_member = Mock(spec=DynamicEnumMember)
        mock_enum2.from_value.return_value = mock_enum_member
        
        # Act
        result = TelegramService._cast_to_enum(value, [mock_enum1, mock_enum2])
        
        # Assert
        self.assertEqual(result, mock_enum_member)
        mock_enum1.from_value.assert_called_once_with(value)
        mock_enum2.from_value.assert_called_once_with(value)

    @patch('threading.Thread')
    def test_start_command_processor(self, mock_thread_class):
        """Test du démarrage du processeur de commandes."""
        # Arrange
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        mock_thread_class.return_value = mock_thread
        
        # Act
        self.service._start_command_processor()
        
        # Assert
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()
        self.assertEqual(self.service._TelegramService__processor_thread, mock_thread)

    def test_start_command_processor_already_running(self):
        """Test du démarrage quand le processeur est déjà actif."""
        # Arrange
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.service._TelegramService__processor_thread = mock_thread
        
        # Act
        with patch('threading.Thread') as mock_thread_class:
            self.service._start_command_processor()
        
        # Assert
        mock_thread_class.assert_not_called()  # Ne doit pas créer un nouveau thread


# noinspection PyTypeChecker
class TestServiceIntegration(unittest.TestCase):
    """Tests d'intégration pour TelegramService."""

    @patch('venantvr.telegram.service.TelegramClient')
    @patch('venantvr.telegram.service.MessageSender')
    @patch('venantvr.telegram.service.MessageReceiver')
    def test_full_service_lifecycle(self, mock_receiver_class, mock_sender_class, mock_client_class):
        """Test du cycle de vie complet du service."""
        # Arrange
        mock_client = Mock()
        mock_sender = Mock()
        mock_receiver = Mock()
        mock_receiver.incoming_queue = queue.Queue()
        
        mock_client_class.return_value = mock_client
        mock_sender_class.return_value = mock_sender
        mock_receiver_class.return_value = mock_receiver
        
        history_manager = Mock()
        
        # Act
        service = ConcreteTestService(
            "https://api.telegram.org/bot",
            "123456:ABC",
            "789",
            {"text": "/sendMessage", "updates": "/getUpdates"},
            history_manager
        )
        
        # Start service
        service.start()
        
        # Send a message
        test_message = create_test_payload("Test", "")
        service.send_message(test_message)
        
        # Stop service
        service.stop()
        
        # Assert
        mock_sender.start.assert_called_once()
        mock_receiver.start.assert_called_once()
        mock_sender.send_message.assert_called_once_with(test_message)
        mock_sender.stop.assert_called_once()
        mock_receiver.stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()