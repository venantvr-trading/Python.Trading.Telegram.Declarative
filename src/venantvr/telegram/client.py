import time
from typing import Optional

import requests
from requests import Response

from venantvr.telegram.tools.logger import logger


class TelegramAPIError(Exception):
    """Specific exception for Telegram API errors."""

    pass


class TelegramNetworkError(Exception):
    """Specific exception for network errors."""

    pass


class TelegramClient:
    """
    HTTP client for Telegram API with error handling and automatic retry.
    Single responsibility: communication with Telegram API.
    """

    def __init__(self, api_base_url: str, bot_token: str, endpoints: dict):
        self.__api_base_url = api_base_url
        self.__bot_token = bot_token
        self.__text_endpoint = endpoints.get("text", "/sendMessage")
        self.__updates_endpoint = endpoints.get("updates", "/getUpdates")
        self.__url_send = (
            f"{self.__api_base_url}{self.__bot_token}{self.__text_endpoint}"
        )
        self.__url_updates = (
            f"{self.__api_base_url}{self.__bot_token}{self.__updates_endpoint}"
        )

    def send_message(self, payload: dict, max_retries: int = 3) -> Optional[Response]:
        """Sends a message via Telegram API with automatic retry."""
        return self._post_with_retry(self.__url_send, payload, max_retries)

    def get_updates(self, params: dict, timeout: tuple[int, int] = (3, 30)) -> dict:
        """Retrieves updates via Telegram API."""
        try:
            response = requests.get(self.__url_updates, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("Error during getUpdates: %s", e)
            raise TelegramNetworkError(f"getUpdates network error: {e}")

    @staticmethod
    def _post_with_retry(
            url: str, payload: dict, max_retries: int = 3
    ) -> Optional[Response]:
        """Sends a POST request with automatic retry."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = requests.post(url, data=payload, timeout=(3, 10))
                response.raise_for_status()
                return response

            except requests.HTTPError as e:
                status_code = e.response.status_code if e.response else None

                # Non-recoverable errors (4xx except 429)
                if status_code and 400 <= status_code < 500 and status_code != 429:
                    logger.error(
                        "Non-recoverable HTTP error %d: %s",
                        status_code,
                        e.response.text if e.response else str(e),
                    )
                    raise TelegramAPIError(f"Telegram API error {status_code}: {e}")

                # Recoverable errors (5xx, 429, timeout)
                last_exception = e
                wait_time = (2 ** attempt) * 0.5  # exponential backoff
                if attempt < max_retries - 1:
                    logger.warning(
                        "Attempt %d/%d failed (HTTP %s), retrying in %.1fs",
                        attempt + 1,
                        max_retries,
                        status_code,
                        wait_time,
                    )
                    time.sleep(wait_time)

            except (requests.ConnectionError, requests.Timeout) as e:
                last_exception = e
                wait_time = (2 ** attempt) * 0.5
                if attempt < max_retries - 1:
                    logger.warning(
                        "Network error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries,
                        wait_time,
                        str(e),
                    )
                    time.sleep(wait_time)

            except requests.RequestException as e:
                logger.error("Unexpected request error: %s", e)
                raise TelegramNetworkError(f"Network error: {e}")

        # All attempts failed
        logger.error("Failed after %d attempts, giving up", max_retries)
        if isinstance(last_exception, requests.HTTPError):
            raise TelegramAPIError(
                f"API Error after {max_retries} attempts: {last_exception}"
            )
        else:
            raise TelegramNetworkError(
                f"Network Error after {max_retries} attempts: {last_exception}"
            )
