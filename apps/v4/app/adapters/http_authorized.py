from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.adapters.base import PlatformAdapter, AdapterItem


def parse_datetime(value: Any) -> datetime | None:
    """Normalize connector JSON date values before SQLAlchemy writes them.

    Authorized connector responses are JSON, so timestamps normally arrive as ISO strings
    or Unix seconds.  Keeping this normalization at the adapter boundary makes every
    downstream service receive a real ``datetime`` object.
    """
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return datetime.fromtimestamp(int(text), tz=timezone.utc)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"unsupported datetime value: {value!r}") from exc
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise ValueError(f"unsupported datetime value type: {type(value).__name__}")


class AuthorizedHTTPAdapter(PlatformAdapter):
    def __init__(self, name: str, base_url: str, token: str = "", timeout: int = 60):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    @property
    def enabled(self):
        return bool(self.base_url)

    def _headers(self):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError(f"{self.name} 授权连接器未配置")
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"{self.name} 连接器返回格式错误：根节点必须是JSON对象")
        return data

    def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "configured": False, "message": "connector URL is empty"}
        try:
            with httpx.Client(timeout=min(self.timeout, 10)) as client:
                response = client.get(f"{self.base_url}/health", headers=self._headers())
                response.raise_for_status()
                data = response.json()
            return {"ok": bool(data.get("ok", True)), "configured": True, "details": data}
        except Exception as exc:  # health endpoint must not crash the task-center API
            return {"ok": False, "configured": True, "message": str(exc)}

    def search(self, keywords, content_types, limit=20, **options):
        payload = {
            "keywords": keywords,
            "content_types": content_types,
            "limit": limit,
            "regions": options.get("regions", []),
            "time_range_hours": options.get("time_range_hours", 24),
            "sort_by": options.get("sort_by", "latest"),
            "keyword_match_mode": options.get("keyword_match_mode", "any"),
        }
        data = self._post("/v1/search", payload)
        rows = data.get("items", [])
        if not isinstance(rows, list):
            raise RuntimeError(f"{self.name} 连接器返回格式错误：items必须是数组")
        items: list[AdapterItem] = []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            item["published_at"] = parse_datetime(item.get("published_at"))
            items.append(AdapterItem(platform=self.name, **item))
        return items

    def comments(self, platform_content_id, limit=100):
        data = self._post(
            "/v1/comments",
            {"platform_content_id": platform_content_id, "limit": limit},
        )
        rows = data.get("comments", [])
        if not isinstance(rows, list):
            raise RuntimeError(f"{self.name} 连接器返回格式错误：comments必须是数组")
        comments = []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            item["published_at"] = parse_datetime(item.get("published_at"))
            comments.append(item)
        return comments


    def relations(self, author_id: str, limit: int = 100) -> list[dict[str, Any]]:
        data = self._post(
            "/v1/relations",
            {"author_id": author_id, "limit": limit},
        )
        rows = data.get("relations", [])
        if not isinstance(rows, list):
            raise RuntimeError(f"{self.name} 连接器返回格式错误：relations必须是数组")
        return [item for item in rows if isinstance(item, dict)]

    def resolve_media(self, platform_content_id: str, content_type: str) -> dict[str, Any]:
        """Resolve a fresh media/stream URL immediately before capture.

        Real platform stream URLs are frequently signed and short lived.  The connector
        owns refresh logic; the task center only consumes the normalized response.
        """
        return self._post(
            "/v1/media/resolve",
            {"platform_content_id": platform_content_id, "content_type": content_type},
        )
