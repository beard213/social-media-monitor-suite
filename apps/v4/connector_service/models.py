from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)
    content_types: list[Literal["video", "live"]] = ["video"]
    regions: list[str] = []
    time_range_hours: int = Field(default=24, ge=1, le=8760)
    sort_by: Literal["latest", "hot", "relevance"] = "latest"
    keyword_match_mode: Literal["any", "all", "exact"] = "any"
    limit: int = Field(default=50, ge=1, le=500)


class SearchItem(BaseModel):
    platform_content_id: str
    content_type: Literal["video", "live"]
    title: str = ""
    description: str = ""
    source_url: str = ""
    media_url: str = ""
    stream_url: str = ""
    cover_url: str = ""
    author_id: str = ""
    published_at: datetime | None = None
    matched_keywords: list[str] = []
    metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    items: list[SearchItem]
    cursor: str | None = None
    has_more: bool = False


class CommentsRequest(BaseModel):
    platform_content_id: str
    limit: int = Field(default=100, ge=1, le=1000)


class CommentItem(BaseModel):
    platform_comment_id: str
    author_id: str = ""
    text: str
    like_count: int = 0
    published_at: datetime | None = None
    metadata: dict[str, Any] = {}


class CommentsResponse(BaseModel):
    comments: list[CommentItem]
    cursor: str | None = None
    has_more: bool = False


class ResolveMediaRequest(BaseModel):
    platform_content_id: str
    content_type: Literal["video", "live"]


class ResolveMediaResponse(BaseModel):
    media_url: str = ""
    stream_url: str = ""
    expires_at: datetime | None = None
    request_headers: dict[str, str] = {}
    metadata: dict[str, Any] = {}


class RelationsRequest(BaseModel):
    author_id: str = Field(min_length=1, max_length=256)
    limit: int = Field(default=100, ge=1, le=1000)


class RelationItem(BaseModel):
    account_id: str = ""
    account_alias: str = ""
    relation_type: Literal["following", "follower", "friend", "frequent_commenter", "related_account"] = "related_account"
    profile_url: str = ""
    evidence_count: int = 1
    source: str = "authorized_connector"
    metadata: dict[str, Any] = {}


class RelationsResponse(BaseModel):
    relations: list[RelationItem]
    cursor: str | None = None
    has_more: bool = False
