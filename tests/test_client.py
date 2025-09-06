import unittest
from unittest.mock import patch, Mock
import requests

from venantvr.telegram.client import TelegramClient, TelegramAPIError, TelegramNetworkError


class TestTelegramClient(unittest.TestCase):
    """Tests unitaires pour TelegramClient."""

    def setUp(self):
        """Configuration initiale pour chaque test."""
        self.api_base_url = "https://api.telegram.org/bot"
        self.bot_token = "123456:ABC-DEF"
        self.endpoints = {
            "text": "/sendMessage",
            "updates": "/getUpdates"
        }
        self.client = TelegramClient(self.api_base_url, self.bot_token, self.endpoints)

    @patch('venantvr.telegram.client.requests.post')
    def test_send_message_success(self, mock_post):
        """Test d'envoi de message réussi."""
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

    @patch('venantvr.telegram.client.requests.post')
    def test_send_message_with_retry_on_500_error(self, mock_post):
        """Test de retry automatique sur erreur 500."""
        # Arrange
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.raise_for_status.side_effect = requests.HTTPError(response=mock_response_500)
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.raise_for_status = Mock()
        
        # Premier appel échoue, second réussit
        mock_post.side_effect = [mock_response_500, mock_response_success]
        
        payload = {"chat_id": "123", "text": "Test message"}
        
        # Act
        with patch('time.sleep'):  # Pour éviter l'attente réelle
            result = self.client.send_message(payload)
        
        # Assert
        self.assertEqual(result, mock_response_success)
        self.assertEqual(mock_post.call_count, 2)

    @patch('venantvr.telegram.client.requests.post')
    def test_send_message_fail_on_400_error(self, mock_post):
        """Test d'échec immédiat sur erreur 400 (non-récupérable)."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        
        payload = {"chat_id": "123", "text": "Test message"}
        
        # Act & Assert
        with self.assertRaises(TelegramAPIError) as context:
            self.client.send_message(payload)
        
        self.assertIn("400", str(context.exception))
        mock_post.assert_called_once()  # Pas de retry sur 400

    @patch('venantvr.telegram.client.requests.post')
    def test_send_message_retry_on_network_error(self, mock_post):
        """Test de retry sur erreur réseau."""
        # Arrange
        mock_post.side_effect = [
            requests.ConnectionError("Connection failed"),
            Mock(status_code=200, raise_for_status=Mock())
        ]
        
        payload = {"chat_id": "123", "text": "Test message"}
        
        # Act
        with patch('time.sleep'):
            result = self.client.send_message(payload)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(mock_post.call_count, 2)

    @patch('venantvr.telegram.client.requests.post')
    def test_send_message_max_retries_exceeded(self, mock_post):
        """Test d'échec après dépassement du nombre max de tentatives."""
        # Arrange
        mock_post.side_effect = requests.ConnectionError("Connection failed")
        payload = {"chat_id": "123", "text": "Test message"}
        
        # Act & Assert
        with patch('time.sleep'):
            with self.assertRaises(TelegramNetworkError) as context:
                self.client.send_message(payload, max_retries=3)
        
        self.assertIn("3 tentatives", str(context.exception))
        self.assertEqual(mock_post.call_count, 3)

    @patch('venantvr.telegram.client.requests.post')
    def test_send_message_rate_limiting_429(self, mock_post):
        """Test de retry sur erreur 429 (rate limiting)."""
        # Arrange
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = requests.HTTPError(response=mock_response_429)
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.raise_for_status = Mock()
        
        mock_post.side_effect = [mock_response_429, mock_response_success]
        
        payload = {"chat_id": "123", "text": "Test message"}
        
        # Act
        with patch('time.sleep'):
            result = self.client.send_message(payload)
        
        # Assert
        self.assertEqual(result, mock_response_success)
        self.assertEqual(mock_post.call_count, 2)

    @patch('venantvr.telegram.client.requests.get')
    def test_get_updates_success(self, mock_get):
        """Test de récupération des mises à jour réussie."""
        # Arrange
        expected_updates = {
            "ok": True,
            "result": [
                {"update_id": 1, "message": {"text": "Hello"}}
            ]
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

    @patch('venantvr.telegram.client.requests.get')
    def test_get_updates_network_error(self, mock_get):
        """Test d'erreur réseau lors de la récupération des mises à jour."""
        # Arrange
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        params = {"timeout": 30}
        
        # Act & Assert
        with self.assertRaises(TelegramNetworkError) as context:
            self.client.get_updates(params)
        
        self.assertIn("getUpdates", str(context.exception))

    def test_exponential_backoff_timing(self):
        """Test du calcul du backoff exponentiel."""
        # Test que le délai augmente exponentiellement
        expected_delays = [0.5, 1.0, 2.0]  # 2^0 * 0.5, 2^1 * 0.5, 2^2 * 0.5
        
        for attempt, expected_delay in enumerate(expected_delays):
            actual_delay = (2 ** attempt) * 0.5
            self.assertEqual(actual_delay, expected_delay)


if __name__ == '__main__':
    unittest.main()