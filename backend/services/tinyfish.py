import os
import requests
from dotenv import load_dotenv
from typing import Any, Dict

load_dotenv()


class TinyFishClient:
    SEARCH_ENDPOINT = "https://api.search.tinyfish.ai"
    FETCH_ENDPOINT = "https://api.fetch.tinyfish.ai"

    def __init__(self):
        self.api_key = os.getenv("TINYFISH_API_KEY")

        if not self.api_key:
            self.headers = {}
        else:
            self.headers = {
                "X-API-Key": self.api_key
            }

    def _ensure_key(self):
        if not self.api_key:
            raise RuntimeError(
                "TinyFish API key not configured. Add TINYFISH_API_KEY to .env"
            )

    def search(self, query: str, timeout: int = 15) -> Dict[str, Any]:
        self._ensure_key()

        response = requests.get(
            self.SEARCH_ENDPOINT,
            headers=self.headers,
            params={"query": query},
            timeout=timeout
        )

        response.raise_for_status()
        return response.json()

    def fetch(self, urls: list, timeout: int = 30) -> Dict[str, Any]:
        self._ensure_key()

        response = requests.post(
            self.FETCH_ENDPOINT,
            headers=self.headers,
            json={
                "urls": urls,
                "format": "markdown"
            },
            timeout=timeout
        )

        response.raise_for_status()
        return response.json()