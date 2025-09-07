import queue
import unittest
from unittest.mock import Mock, patch

from tests.test_helpers import (create_test_message, create_test_messages,
                                create_test_payload)
from venantvr.telegram.client import TelegramAPIError, TelegramNetworkError
from venantvr.telegram.message_queue import MessageReceiver, MessageSender


# noinspection PyUnresolvedReferences,PyTypeChecker
class TestMessageSender(unittest.TestCase):
    """Unit tests for MessageSender."""

    def setUp(self):
        """Initial setup for each test."""
        self.mock_client = Mock()
        self.mock_history_manager = Mock()
        self.chat_id = "123456"
        self.sender = MessageSender(
            self.mock_client, self.chat_id, self.mock_history_manager
        )

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.sender._MessageSender__chat_id, self.chat_id)
        self.assertIsNotNone(self.sender._MessageSender__outgoing_queue)
        self.assertIsNone(self.sender._MessageSender__sender_thread)

    def test_send_valid_message(self):
        """Test adding a valid message to the queue."""
        # Arrange
        message = create_test_payload("Hello", "")

        # Act
        self.sender.send_message(message)

        # Assert
        self.assertFalse(self.sender._MessageSender__outgoing_queue.empty())
        queued_message = self.sender._MessageSender__outgoing_queue.get()
        self.assertEqual(queued_message, message)

    def test_send_invalid_message(self):
        """Test rejecting an invalid message."""
        # Arrange
        message = create_test_payload()  # Message without content

        # Act
        with patch("venantvr.telegram.message_queue.logger") as mock_logger:
            self.sender.send_message(message)

        # Assert
        attrs = self.sender._get_test_attributes()
        self.assertTrue(attrs["outgoing_queue"].empty())
        mock_logger.warning.assert_called()

    def test_send_multiple_messages(self):
        """Test sending multiple messages."""
        # Arrange
        messages = create_test_messages(["Message 1", "Message 2"])

        # Act
        self.sender.send_message(messages)

        # Assert
        self.assertEqual(self.sender._MessageSender__outgoing_queue.qsize(), 2)

    def test_build_payload(self):
        """Test payload construction."""
        # Arrange
        message = create_test_payload("Test", '{"inline_keyboard":[]}')

        # Act
        payload = self.sender._build_payload(message)

        # Assert
        self.assertEqual(payload["chat_id"], self.chat_id)
        self.assertEqual(payload["text"], "Test")
        self.assertEqual(payload["reply_markup"], '{"inline_keyboard":[]}')

    def test_is_valid_message_static_method(self):
        """Test static message validation method."""
        # Test valid message
        valid_message = create_test_message("Hello")
        self.assertTrue(MessageSender._is_valid_message(valid_message))

        # Test invalid message
        invalid_message = create_test_payload()
        self.assertFalse(MessageSender._is_valid_message(invalid_message))

        # Test message None
        self.assertFalse(MessageSender._is_valid_message(None))

    def test_flush_queue(self):
        """Test queue flushing."""
        # Arrange
        messages = create_test_messages(["Message 1", "Message 2"])
        for msg in messages:
            self.sender._MessageSender__outgoing_queue.put(msg)

        # Act
        self.sender.flush_queue()

        # Assert
        attrs = self.sender._get_test_attributes()
        self.assertTrue(attrs["outgoing_queue"].empty())
        self.assertEqual(self.mock_client.send_message.call_count, 2)
        self.assertEqual(self.mock_history_manager.log_interaction.call_count, 2)

    @patch("threading.Thread")
    def test_start_thread(self, mock_thread_class):
        """Test sending thread startup."""
        # Arrange
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        mock_thread_class.return_value = mock_thread

        # Act
        self.sender.start()

        # Assert
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

    def test_stop_thread(self):
        """Test thread shutdown."""
        # Arrange
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.sender._MessageSender__sender_thread = mock_thread

        # Act
        with patch.object(self.sender, "flush_queue") as mock_flush:
            self.sender.stop()

        # Assert
        self.assertTrue(self.sender._MessageSender__stop_event.is_set())
        mock_flush.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_send_payload_with_error_handling(self):
        """Test error handling during sending."""
        # Arrange
        self.mock_client.send_message.side_effect = TelegramAPIError("API Error")
        payload = {"chat_id": self.chat_id, "text": "Test"}

        # Act & Assert - Should raise since error is not caught in _send_payload
        with self.assertRaises(TelegramAPIError):
            self.sender._send_payload(payload)
        self.mock_history_manager.log_interaction.assert_called_once()


# noinspection PyUnresolvedReferences,PyTypeChecker
class TestMessageReceiver(unittest.TestCase):
    """Unit tests for MessageReceiver."""

    def setUp(self):
        """Initial setup for each test."""
        self.mock_client = Mock()
        self.mock_history_manager = Mock()
        self.receiver = MessageReceiver(self.mock_client, self.mock_history_manager)

    def test_init(self):
        """Test initialization."""
        self.assertIsNotNone(self.receiver.incoming_queue)
        self.assertIsNone(self.receiver._MessageReceiver__last_update_id)
        self.assertIsNone(self.receiver._MessageReceiver__receiver_thread)

    def test_parse_update_text_message(self):
        """Test parsing a text message."""
        # Arrange
        update = {"message": {"text": "Hello", "chat": {"id": 123}}}

        # Act
        chat_id, msg_type, content = MessageReceiver.parse_update(update)

        # Assert
        self.assertEqual(chat_id, 123)
        self.assertEqual(msg_type, "text")
        self.assertEqual(content["text"], "Hello")

    def test_parse_update_callback_query(self):
        """Test parsing a callback query."""
        # Arrange
        update = {
            "callback_query": {"data": "/command", "message": {"chat": {"id": 456}}}
        }

        # Act
        chat_id, msg_type, content = MessageReceiver.parse_update(update)

        # Assert
        self.assertEqual(chat_id, 456)
        self.assertEqual(msg_type, "callback_query")
        self.assertEqual(content["data"], "/command")

    def test_parse_update_unknown(self):
        """Test parsing an unknown update."""
        # Arrange
        update = {"unknown_field": "value"}

        # Act
        chat_id, msg_type, content = MessageReceiver.parse_update(update)

        # Assert
        self.assertIsNone(chat_id)
        self.assertEqual(msg_type, "unknown")
        self.assertEqual(content, update)

    @patch("threading.Thread")
    def test_start_thread(self, mock_thread_class):
        """Test reception thread startup."""
        # Arrange
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False
        mock_thread_class.return_value = mock_thread

        # Act
        self.receiver.start()

        # Assert
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

    def test_stop_thread(self):
        """Test de l'arrêt du thread."""
        # Arrange
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.receiver._MessageReceiver__receiver_thread = mock_thread

        # Act
        self.receiver.stop()

        # Assert
        self.assertTrue(self.receiver._MessageReceiver__stop_event.is_set())
        # Verify that a stop signal has been added to the queue
        signal = self.receiver.incoming_queue.get()
        self.assertIsNone(signal)
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_incoming_queue_property(self):
        """Test access to the incoming_queue property."""
        # Act
        queue_ref = self.receiver.incoming_queue

        # Assert
        self.assertIsInstance(queue_ref, queue.Queue)
        self.assertIs(queue_ref, self.receiver._MessageReceiver__incoming_queue)

    @patch("time.sleep")
    def test_message_receiver_network_error_handling(self, mock_sleep):
        """Test network error handling in reception thread."""
        # Arrange
        self.mock_client.get_updates.side_effect = TelegramNetworkError("Network error")
        self.receiver._MessageReceiver__stop_event = Mock()
        self.receiver._MessageReceiver__stop_event.is_set.side_effect = [
            False,
            True,
        ]  # Stop après une itération

        # Act
        with patch("venantvr.telegram.message_queue.logger") as mock_logger:
            self.receiver._message_receiver()

        # Assert
        mock_logger.warning.assert_called()
        mock_sleep.assert_called_with(3)  # 3 second wait in case of network error

    def test_process_updates_from_api(self):
        """Test processing updates received from the API."""
        # Arrange
        updates = {
            "result": [
                {"update_id": 1, "message": {"text": "Test", "chat": {"id": 789}}}
            ]
        }
        self.mock_client.get_updates.return_value = updates
        self.receiver._MessageReceiver__stop_event = Mock()
        self.receiver._MessageReceiver__stop_event.is_set.side_effect = [False, True]

        # Act
        self.receiver._message_receiver()

        # Assert
        self.assertEqual(self.receiver._MessageReceiver__last_update_id, 1)
        self.assertFalse(self.receiver.incoming_queue.empty())
        self.mock_history_manager.log_interaction.assert_called_once()


# noinspection PyUnresolvedReferences,PyTypeChecker
class TestIntegration(unittest.TestCase):
    """Integration tests between MessageSender and MessageReceiver."""

    def test_sender_receiver_integration(self):
        """Test integration between sender and receiver."""
        # Arrange
        mock_client = Mock()
        mock_history_manager = Mock()
        chat_id = "123"

        sender = MessageSender(mock_client, chat_id, mock_history_manager)
        receiver = MessageReceiver(mock_client, mock_history_manager)

        # Simulate an API response
        mock_client.get_updates.return_value = {
            "result": [
                {"update_id": 1, "message": {"text": "/start", "chat": {"id": 123}}}
            ]
        }

        # Act - Process an incoming message
        receiver._MessageReceiver__stop_event = Mock()
        receiver._MessageReceiver__stop_event.is_set.side_effect = [False, True]
        receiver._message_receiver()

        # Get message from queue
        received_update = receiver.incoming_queue.get()

        # Send a response
        response_message = create_test_payload("Welcome!", "")
        sender.send_message(response_message)
        sender.flush_queue()

        # Assert
        self.assertEqual(received_update["update_id"], 1)
        mock_client.send_message.assert_called_once()
        self.assertEqual(
            mock_history_manager.log_interaction.call_count, 2
        )  # 1 incoming, 1 outgoing


if __name__ == "__main__":
    unittest.main()
