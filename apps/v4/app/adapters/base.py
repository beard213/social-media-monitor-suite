from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AdapterItem:
    platform: str
    platform_content_id: str
    content_type: str
    title: str = ""
    description: str = ""
    source_url: str = ""
    media_url: str = ""
    stream_url: str = ""
    cover_url: str = ""
    author_id: str = ""
    published_at: datetime | None = None
    matched_keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PlatformAdapter(ABC):
    name: str

    @abstractmethod
    def search(
        self,
        keywords: list[str],
        content_types: list[str],
        limit: int = 20,
        **options,
    ) -> list[AdapterItem]: ...

    @abstractmethod
    def comments(self, platform_content_id: str, limit: int = 100) -> list[dict]: ...

    def relations(self, author_id: str, limit: int = 100) -> list[dict]:
        """Optional public account-relation expansion endpoint."""
        return []

    def resolve_media(self, platform_content_id: str, content_type: str) -> dict[str, Any]:
        raise RuntimeError(f"{self.name} media resolver is not configured")
