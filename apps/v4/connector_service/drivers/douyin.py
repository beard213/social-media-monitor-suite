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


class DouyinDriver(ProviderDriver):
    """Official/authorized Douyin integration slot.

    Replace the three TODO bodies after the application receives the corresponding
    official scopes or an authorized industry data service supplies equivalent APIs.
    Keep provider credentials inside this connector; never expose them to the browser.
    """

    name = "douyin"

    def __init__(self):
        self.client_key = os.getenv("DOUYIN_CLIENT_KEY", "")
        self.client_secret = os.getenv("DOUYIN_CLIENT_SECRET", "")
        self.access_token = os.getenv("DOUYIN_ACCESS_TOKEN", "")
        self.refresh_token = os.getenv("DOUYIN_REFRESH_TOKEN", "")
        self.open_id = os.getenv("DOUYIN_OPEN_ID", "")

    def health(self) -> dict[str, Any]:
        return {
            "ok": bool(self.client_key and self.client_secret),
            "platform": self.name,
            "credentials_configured": bool(self.client_key and self.client_secret),
            "user_token_configured": bool(self.access_token and self.open_id),
            "capabilities": {
                "search": False,
                "comments": False,
                "live": False,
                "media_resolve": False,
                "relations": False,
            },
            "message": "驱动框架已就绪；请在 connector_service/drivers/douyin.py 中接入已获授权的官方接口。",
        }

    def search(self, request: SearchRequest) -> SearchResponse:
        # TODO(赵帅): map SearchRequest to the approved official search API, paginate,
        # normalize provider fields to SearchItem, and return SearchResponse.
        raise ProviderNotConfigured("抖音搜索接口尚未接入")

    def comments(self, request: CommentsRequest) -> CommentsResponse:
        # TODO(赵帅): call the approved public-comment API using platform_content_id.
        raise ProviderNotConfigured("抖音评论接口尚未接入")

    def resolve_media(self, request: ResolveMediaRequest) -> ResolveMediaResponse:
        # TODO(赵帅): return a fresh, authorized media/stream URL plus required headers and expiry.
        raise ProviderNotConfigured("抖音媒体/直播流解析接口尚未接入")

    def relations(self, request: RelationsRequest) -> RelationsResponse:
        # TODO(赵帅): normalize only publicly available following/friend/commenter relations.
        raise ProviderNotConfigured("抖音公开账号关系扩列接口尚未接入")
