import time
from typing import Optional

import requests
from requests import Response

from venantvr.telegram.tools.logger import logger


class TelegramAPIError(Exception):
    """Exception spécifique pour les erreurs de l'API Telegram."""
    pass


class TelegramNetworkError(Exception):
    """Exception spécifique pour les erreurs réseau."""
    pass


class TelegramClient:
    """
    Client HTTP pour l'API Telegram avec gestion d'erreurs et retry automatique.
    Responsabilité unique: communication avec l'API Telegram.
    """
    
    def __init__(self, api_base_url: str, bot_token: str, endpoints: dict):
        self.__api_base_url = api_base_url
        self.__bot_token = bot_token
        self.__text_endpoint = endpoints.get("text", "/sendMessage")
        self.__updates_endpoint = endpoints.get("updates", "/getUpdates")
        self.__url_send = f"{self.__api_base_url}{self.__bot_token}{self.__text_endpoint}"
        self.__url_updates = f"{self.__api_base_url}{self.__bot_token}{self.__updates_endpoint}"

    def send_message(self, payload: dict, max_retries: int = 3) -> Optional[Response]:
        """Envoie un message via l'API Telegram avec retry automatique."""
        return self._post_with_retry(self.__url_send, payload, max_retries)

    def get_updates(self, params: dict, timeout: tuple[int, int] = (3, 30)) -> dict:
        """Récupère les mises à jour via l'API Telegram."""
        try:
            response = requests.get(self.__url_updates, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("Erreur lors de getUpdates: %s", e)
            raise TelegramNetworkError(f"Erreur réseau getUpdates: {e}")

    @staticmethod
    def _post_with_retry(url: str, payload: dict, max_retries: int = 3) -> Optional[Response]:
        """Envoie une requête POST avec retry automatique."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, data=payload, timeout=(3, 10))
                response.raise_for_status()
                return response
                
            except requests.HTTPError as e:
                status_code = e.response.status_code if e.response else None
                
                # Erreurs non-récupérables (4xx sauf 429)
                if status_code and 400 <= status_code < 500 and status_code != 429:
                    logger.error("Erreur HTTP non-récupérable %d: %s", status_code, e.response.text if e.response else str(e))
                    raise TelegramAPIError(f"Erreur API Telegram {status_code}: {e}")
                
                # Erreurs récupérables (5xx, 429, timeout)
                last_exception = e
                wait_time = (2 ** attempt) * 0.5  # backoff exponentiel
                if attempt < max_retries - 1:
                    logger.warning("Tentative %d/%d échouée (HTTP %s), retry dans %.1fs", 
                                 attempt + 1, max_retries, status_code, wait_time)
                    time.sleep(wait_time)
                    
            except (requests.ConnectionError, requests.Timeout) as e:
                last_exception = e
                wait_time = (2 ** attempt) * 0.5
                if attempt < max_retries - 1:
                    logger.warning("Erreur réseau (tentative %d/%d), retry dans %.1fs: %s", 
                                 attempt + 1, max_retries, wait_time, str(e))
                    time.sleep(wait_time)
                    
            except requests.RequestException as e:
                logger.error("Erreur requête inattendue: %s", e)
                raise TelegramNetworkError(f"Erreur réseau: {e}")
        
        # Toutes les tentatives ont échoué
        logger.error("Échec après %d tentatives, abandon", max_retries)
        if isinstance(last_exception, requests.HTTPError):
            raise TelegramAPIError(f"API Error après {max_retries} tentatives: {last_exception}")
        else:
            raise TelegramNetworkError(f"Network Error après {max_retries} tentatives: {last_exception}")