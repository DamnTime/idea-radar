from abc import ABC, abstractmethod
from datetime import datetime

import httpx

from src.models import ContentItem


class BaseScraper(ABC):
    def __init__(self, config: dict, http_client: httpx.AsyncClient):
        self.config = config
        self.client = http_client

    @abstractmethod
    async def fetch(self, since: datetime) -> list[ContentItem]:
        pass

    def _generate_id(self, source_type: str, subtype: str, native_id: str) -> str:
        return f"{source_type}:{subtype}:{native_id}"
