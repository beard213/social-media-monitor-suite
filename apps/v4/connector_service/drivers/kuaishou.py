from __future__ import annotations

import os
from typing import Any

from connector_service.drivers.base import ProviderDriver, ProviderNotConfigured
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


class KuaishouDriver(ProviderDriver):
    """Official/authorized Kuaishou integration slot."""

    name = "kuaishou"

    def __init__(self):
        self.app_id = os.getenv("KUAISHOU_APP_ID", "")
        self.app_secret = os.getenv("KUAISHOU_APP_SECRET", "")
        self.access_token = os.getenv("KUAISHOU_ACCESS_TOKEN", "")

    def health(self) -> dict[str, Any]:
        return {
            "ok": bool(self.app_id and self.app_secret),
            "platform": self.name,
            "credentials_configured": bool(self.app_id and self.app_secret),
            "token_configured": bool(self.access_token),
            "capabilities": {
                "search": False,
                "comments": False,
                "live": False,
                "media_resolve": False,
                "relations": False,
            },
            "message": "驱动框架已就绪；请在 connector_service/drivers/kuaishou.py 中接入已获授权的官方接口。",
        }

    def search(self, request: SearchRequest) -> SearchResponse:
        raise ProviderNotConfigured("快手搜索接口尚未接入")

    def comments(self, request: CommentsRequest) -> CommentsResponse:
        raise ProviderNotConfigured("快手评论接口尚未接入")

    def resolve_media(self, request: ResolveMediaRequest) -> ResolveMediaResponse:
        # TODO(赵帅): provide a fresh authorized media/stream URL when the provider permits it.
        raise ProviderNotConfigured("快手媒体/直播流解析接口尚未接入")

    def relations(self, request: RelationsRequest) -> RelationsResponse:
        # TODO(赵帅): normalize only publicly available relation signals.
        raise ProviderNotConfigured("快手公开账号关系扩列接口尚未接入")
