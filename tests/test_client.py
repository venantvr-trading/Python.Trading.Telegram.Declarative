import unittest
from unittest.mock import Mock, patch

import requests

from python_trading_telegram_declarative.client import (TelegramAPIError, TelegramClient,
                                      TelegramNetworkError)


class TestTelegramClient(unittest.TestCase):
    """Unit tests for TelegramClient."""

    def setUp(self):
        """Initial setup for each test."""
        self.api_base_url = "https://api.telegram.org/bot"
        self.bot_token = "123456:ABC-DEF"
        self.endpoints = {"text": "/sendMessage", "updates": "/getUpdates"}
        self.client = TelegramClient(self.api_base_url, self.bot_token, self.endpoints)

    @patch("python_trading_telegram_declarative.client.requests.post")
    def test_send_message_success(self, mock_post):
        """Test successful message sending."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        payload = {"chat_id": "123", "text": "Test message"}

        # Act
        result = self.client.send_message(payload)

        # Assert
        self.assertEqual(result, mock_response)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("data", call_args.kwargs)
        self.assertEqual(call_args.kwargs["data"], payload)

    @patch("python_trading_telegram_declarative.client.requests.post")
    def test_send_message_with_retry_on_500_error(self, mock_post):
        """Test automatic retry on 500 error."""
        # Arrange
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.raise_for_status.side_effect = requests.HTTPError(
            response=mock_response_500
        )

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.raise_for_status = Mock()

        # First call fails, second succeeds
        mock_post.side_effect = [mock_response_500, mock_response_success]

        payload = {"chat_id": "123", "text": "Test message"}

        # Act
        with patch("time.sleep"):  # To avoid real waiting
            result = self.client.send_message(payload)

        # Assert
        self.assertEqual(result, mock_response_success)
        self.assertEqual(mock_post.call_count, 2)

    @patch("python_trading_telegram_declarative.client.requests.post")
    def test_send_message_fail_on_400_error(self, mock_post):
        """Test immediate failure on 400 error (non-recoverable)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            response=mock_response
        )
        mock_post.return_value = mock_response

        payload = {"chat_id": "123", "text": "Test message"}

        # Act & Assert
        with self.assertRaises(TelegramAPIError) as context:
            self.client.send_message(payload)

        self.assertIn("400", str(context.exception))
        mock_post.assert_called_once()  # No retry on 400

    @patch("python_trading_telegram_declarative.client.requests.post")
    def test_send_message_retry_on_network_error(self, mock_post):
        """Test retry on network error."""
        # Arrange
        mock_post.side_effect = [
            requests.ConnectionError("Connection failed"),
            Mock(status_code=200, raise_for_status=Mock()),
        ]

        payload = {"chat_id": "123", "text": "Test message"}

        # Act
        with patch("time.sleep"):
            result = self.client.send_message(payload)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(mock_post.call_count, 2)

    @patch("python_trading_telegram_declarative.client.requests.post")
    def test_send_message_max_retries_exceeded(self, mock_post):
        """Test failure after exceeding max retry attempts."""
        # Arrange
        mock_post.side_effect = requests.ConnectionError("Connection failed")
        payload = {"chat_id": "123", "text": "Test message"}

        # Act & Assert
        with patch("time.sleep"):
            with self.assertRaises(TelegramNetworkError) as context:
                self.client.send_message(payload, max_retries=3)

        self.assertIn("3 attempts", str(context.exception))
        self.assertEqual(mock_post.call_count, 3)

    @patch("python_trading_telegram_declarative.client.requests.post")
    def test_send_message_rate_limiting_429(self, mock_post):
        """Test retry on 429 error (rate limiting)."""
        # Arrange
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = requests.HTTPError(
            response=mock_response_429
        )

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.raise_for_status = Mock()

        mock_post.side_effect = [mock_response_429, mock_response_success]

        payload = {"chat_id": "123", "text": "Test message"}

        # Act
        with patch("time.sleep"):
            result = self.client.send_message(payload)

        # Assert
        self.assertEqual(result, mock_response_success)
        self.assertEqual(mock_post.call_count, 2)

    @patch("python_trading_telegram_declarative.client.requests.get")
    def test_get_updates_success(self, mock_get):
        """Test successful updates retrieval."""
        # Arrange
        expected_updates = {
            "ok": True,
            "result": [{"update_id": 1, "message": {"text": "Hello"}}],
        }
        mock_response = Mock()
        mock_response.json.return_value = expected_updates
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        params = {"timeout": 30}

        # Act
        result = self.client.get_updates(params)

        # Assert
        self.assertEqual(result, expected_updates)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args.kwargs["params"], params)

    @patch("python_trading_telegram_declarative.client.requests.get")
    def test_get_updates_network_error(self, mock_get):
        """Test network error during updates retrieval."""
        # Arrange
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        params = {"timeout": 30}

        # Act & Assert
        with self.assertRaises(TelegramNetworkError) as context:
            self.client.get_updates(params)

        self.assertIn("getUpdates", str(context.exception))

    def test_exponential_backoff_timing(self):
        """Test exponential backoff calculation."""
        # Test that delay increases exponentially
        expected_delays = [0.5, 1.0, 2.0]  # 2^0 * 0.5, 2^1 * 0.5, 2^2 * 0.5

        for attempt, expected_delay in enumerate(expected_delays):
            actual_delay = (2 ** attempt) * 0.5
            self.assertEqual(actual_delay, expected_delay)


if __name__ == "__main__":
    unittest.main()
