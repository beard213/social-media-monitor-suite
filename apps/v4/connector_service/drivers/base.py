from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from connector_service.models import (
    CommentsRequest,
    CommentsResponse,
    ResolveMediaRequest,
    ResolveMediaResponse,
    RelationsRequest,
    RelationsResponse,
    SearchRequest,
    SearchResponse,
)


class ProviderNotConfigured(RuntimeError):
    pass


class ProviderDriver(ABC):
    name: str

    @abstractmethod
    def health(self) -> dict[str, Any]: ...

    @abstractmethod
    def search(self, request: SearchRequest) -> SearchResponse: ...

    @abstractmethod
    def comments(self, request: CommentsRequest) -> CommentsResponse: ...

    @abstractmethod
    def resolve_media(self, request: ResolveMediaRequest) -> ResolveMediaResponse: ...

    @abstractmethod
    def relations(self, request: RelationsRequest) -> RelationsResponse: ...
