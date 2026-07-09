from abc import ABC, abstractmethod

from src.models import ScoredIdea


class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, ideas: list[ScoredIdea]) -> bool:
        pass
