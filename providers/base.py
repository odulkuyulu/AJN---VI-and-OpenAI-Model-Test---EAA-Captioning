from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models import ProviderResult


class ProviderError(RuntimeError):
    pass


class ConfigurationRequiredError(ProviderError):
    pass


class AudioEventProvider(ABC):
    name: str

    @abstractmethod
    def analyse(self, media_path: Path, test_id: str) -> ProviderResult:
        raise NotImplementedError

