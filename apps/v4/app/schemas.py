from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

Platform = Literal["douyin", "kuaishou", "demo"]
ContentType = Literal["video", "live"]
MatchMode = Literal["any", "all", "exact"]
SortMode = Literal["latest", "hot", "relevance"]


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    platforms: list[Platform] = Field(min_length=1)
    content_types: list[ContentType] = ["video", "live"]
    include_keywords: list[str] = Field(min_length=1)
    exclude_keywords: list[str] = []
    interval_seconds: int = Field(default=300, ge=60, le=86400)
    enabled: bool = True

    topic_template: str = "custom"
    regions: list[str] = []
    keyword_match_mode: MatchMode = "any"
    time_range_hours: int = Field(default=24, ge=1, le=24 * 365)
    sort_by: SortMode = "latest"
    result_limit: int = Field(default=50, ge=1, le=500)
    collect_comments: bool = True
    expand_related: bool = True
    auto_audit: bool = True
    auto_capture: bool = False
    auto_push: bool = False
    push_after_review: bool = True
    notes: str = Field(default="", max_length=2000)


class TaskUpdate(BaseModel):
    name: str | None = None
    platforms: list[Platform] | None = None
    content_types: list[ContentType] | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    interval_seconds: int | None = Field(default=None, ge=60, le=86400)
    enabled: bool | None = None

    topic_template: str | None = None
    regions: list[str] | None = None
    keyword_match_mode: MatchMode | None = None
    time_range_hours: int | None = Field(default=None, ge=1, le=24 * 365)
    sort_by: SortMode | None = None
    result_limit: int | None = Field(default=None, ge=1, le=500)
    collect_comments: bool | None = None
    expand_related: bool | None = None
    auto_audit: bool | None = None
    auto_capture: bool | None = None
    auto_push: bool | None = None
    push_after_review: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)


class SearchIngestItem(BaseModel):
    platform: Platform
    platform_content_id: str
    content_type: ContentType
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


class SearchIngest(BaseModel):
    items: list[SearchIngestItem]


class CommentItem(BaseModel):
    platform_comment_id: str
    author_id: str = ""
    text: str
    like_count: int = 0
    published_at: datetime | None = None


class CommentIngest(BaseModel):
    platform: Platform
    platform_content_id: str
    comments: list[CommentItem]


class LiveMessageItem(BaseModel):
    platform: Platform
    platform_content_id: str
    message_type: str = "comment"
    author_id: str = ""
    text: str = ""
    event_time: datetime | None = None
    metadata: dict[str, Any] = {}


class FilterPreview(BaseModel):
    text: str
    include_keywords: list[str] = []
    exclude_keywords: list[str] = []


class LiveMonitorStart(BaseModel):
    """Start monitoring a known live room/account ID.

    The task center can run immediately when ``stream_url`` is supplied by the
    existing live-capture component.  When it is empty, the configured platform
    connector is asked to resolve the room ID into a fresh authorized stream URL.
    """

    platform: Platform
    room_id: str = Field(min_length=1, max_length=256)
    title: str = Field(default="", max_length=300)
    source_url: str = Field(default="", max_length=2000)
    stream_url: str = Field(default="", max_length=5000)
    author_id: str = Field(default="", max_length=256)
    keywords: list[str] = []
    regions: list[str] = []
    topic_template: str = "custom"
    segment_seconds: int = Field(default=120, ge=30, le=1800)
    auto_capture: bool = True
    auto_push: bool = False
    notes: str = Field(default="", max_length=2000)
