from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.registry import get_adapter
from app.core.config import settings
from app.db.models import Content, LiveSession
from app.schemas import LiveMonitorStart
from app.services.catalog import detect_regions
from app.services.jobs import enqueue
from app.services.legacy_douyin import start_legacy_douyin
from app.utils import anonymize, utcnow


def _bridge_headers() -> dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if settings.live_monitor_bridge_token:
        headers["Authorization"] = f"Bearer {settings.live_monitor_bridge_token}"
    return headers


def _resolve_from_existing_live_service(body: LiveMonitorStart) -> dict[str, Any]:
    """Optional bridge for the already completed ID-based live monitor.

    The external service contract is documented in ``docs/直播ID接入协议.md``.
    """

    if not settings.live_monitor_bridge_url:
        return {}
    payload = {
        "platform": body.platform,
        "room_id": body.room_id,
        "segment_seconds": body.segment_seconds,
        "keywords": body.keywords,
        "regions": body.regions,
    }
    with httpx.Client(timeout=settings.http_timeout_seconds) as client:
        response = client.post(
            f"{settings.live_monitor_bridge_url.rstrip('/')}/v1/live/resolve",
            headers=_bridge_headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("直播监控桥接服务返回格式错误")
    return data


def start_live_by_id(db: Session, body: LiveMonitorStart) -> dict[str, Any]:
    content = db.scalar(
        select(Content).where(
            Content.platform == body.platform,
            Content.platform_content_id == body.room_id,
        )
    )
    created = content is None
    if content is None:
        content = Content(
            platform=body.platform,
            platform_content_id=body.room_id,
            content_type="live",
        )
        db.add(content)

    resolved: dict[str, Any] = {}
    resolve_errors: list[str] = []
    if body.stream_url:
        resolved = {"stream_url": body.stream_url, "source": "manual_test_url"}
    else:
        try:
            resolved = _resolve_from_existing_live_service(body)
        except Exception as exc:
            resolve_errors.append(f"直播桥接服务：{exc}")
        if not (resolved.get("stream_url") or resolved.get("media_url")) and body.platform == "douyin":
            try:
                legacy = start_legacy_douyin(body)
                if legacy:
                    resolved = legacy
            except Exception as exc:
                resolve_errors.append(f"旧抖音直播流程：{exc}")
        # biliup 本地采集链路：
        # 对应账号输出目录存在时，直接进入外部结果同步流程。
        if not (
            resolved.get("stream_url")
            or resolved.get("media_url")
            or resolved.get("external_pipeline_started")
        ) and body.platform == "douyin":
            local_account_name = (
                f"v4_douyin_{body.room_id}"
            )
            local_account_dir = (
                settings.legacy_douyin_output_root
                .expanduser()
                / local_account_name
            )

            if local_account_dir.exists():
                resolved = {
                    "source": "biliup_local_output",
                    "source_url": (
                        body.source_url
                        or
                        f"https://live.douyin.com/"
                        f"{body.room_id}"
                    ),
                    "legacy_account_name": (
                        local_account_name
                    ),
                    "external_pipeline_started": True,
                    "title": (
                        body.title
                        or
                        f"抖音直播间 {body.room_id}"
                    ),
                }

        if not (
            resolved.get("stream_url")
            or resolved.get("media_url")
            or resolved.get("external_pipeline_started")
        ) and body.platform != "demo":
            try:
                resolved = get_adapter(body.platform).resolve_media(body.room_id, "live")
                resolved["source"] = "platform_connector"
            except Exception as exc:
                resolve_errors.append(f"平台连接器：{exc}")

    content.title = body.title or resolved.get("title") or f"{body.platform}直播间 {body.room_id}"
    content.description = body.notes or resolved.get("description") or "通过直播ID接入的监测对象"
    content.source_url = body.source_url or resolved.get("source_url") or ""
    content.stream_url = resolved.get("stream_url") or body.stream_url or content.stream_url
    content.media_url = resolved.get("media_url") or content.media_url
    content.cover_url = resolved.get("cover_url") or content.cover_url
    content.author_alias = anonymize(body.author_id or str(resolved.get("author_id") or body.room_id))
    content.matched_keywords = body.keywords
    content.first_seen_at = content.first_seen_at or utcnow()
    content.last_seen_at = utcnow()
    content.filter_status = "kept"
    metadata = dict(content.raw_metadata or {})
    metadata.update(
        {
            "entry_mode": "live_id",
            "room_id": body.room_id,
            "topic_template": body.topic_template,
            "region_tags": detect_regions(" ".join([content.title, content.description]), body.regions)
            or body.regions,
            "provider_author_ref": body.author_id or resolved.get("author_id", ""),
            "request_headers": resolved.get("request_headers") or {},
            "stream_expires_at": resolved.get("expires_at"),
            "resolve_source": resolved.get("source", "unresolved"),
            "resolve_errors": resolve_errors,
            "pipeline_stage": "live_registered",
            "push_target": settings.push_target_name,
            "legacy_account_name": resolved.get("legacy_account_name", ""),
            "external_pipeline_started": bool(resolved.get("external_pipeline_started")),
        }
    )
    content.raw_metadata = metadata
    db.flush()

    external_started = bool(resolved.get("external_pipeline_started"))
    ready = bool(content.stream_url or content.media_url or external_started)
    running = db.scalar(
        select(LiveSession).where(
            LiveSession.content_id == content.id,
            LiveSession.status.in_(["running", "waiting_source"]),
        )
    )
    if running is None:
        running = LiveSession(
            content_id=content.id,
            status=("running_external" if external_started else "running" if ready else "waiting_source"),
            segment_seconds=body.segment_seconds,
            next_segment_at=utcnow(),
        )
        db.add(running)
        db.flush()
    else:
        running.status = "running_external" if external_started else "running" if ready else "waiting_source"
        running.segment_seconds = body.segment_seconds
        running.next_segment_at = utcnow()
        running.last_error = "" if ready else "等待直播ID解析服务返回stream_url"

    if body.auto_capture and external_started:
        enqueue(
            db,
            "legacy_douyin_import",
            {
                "content_id": content.id,
                "live_session_id": running.id if running.id else None,
                "account_name": resolved.get("legacy_account_name", ""),
                "checks": 0,
            },
            max_attempts=1,
        )
    elif body.auto_capture and ready:
        enqueue(
            db,
            "capture",
            {
                "content_id": content.id,
                "seconds": body.segment_seconds,
                "live_session_id": running.id if running.id else None,
            },
        )
    if body.auto_push:
        enqueue(db, "push", {"content_id": content.id, "include_media": True})
    db.commit()
    db.refresh(content)
    db.refresh(running)

    return {
        "ok": True,
        "created": created,
        "ready_for_capture": ready,
        "content_id": content.id,
        "live_session_id": running.id,
        "session_status": running.status,
        "platform": body.platform,
        "room_id": body.room_id,
        "stream_source": metadata["resolve_source"],
        "resolve_errors": resolve_errors,
        "message": (
            "旧抖音直播采集、转写与检测流程已启动，结果将同步到本系统"
            if external_started
            else "直播ID已接入并进入分片监控队列"
            if ready
            else "直播ID已登记；等待现有直播服务或平台连接器返回stream_url"
        ),
    }
