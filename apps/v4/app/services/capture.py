from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.adapters.registry import get_adapter
from app.core.config import settings
from app.db.models import Content
from app.utils import utcnow


def _resolve_source(content: Content) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Resolve a fresh media URL for real platforms immediately before FFmpeg runs."""
    headers: dict[str, str] = {}
    metadata: dict[str, Any] = {}

    if content.platform in {"douyin", "kuaishou"}:
        adapter = get_adapter(content.platform)
        if hasattr(adapter, "resolve_media"):
            try:
                resolved = adapter.resolve_media(content.platform_content_id, content.content_type)
                source = resolved.get("stream_url") or resolved.get("media_url")
                headers = {str(k): str(v) for k, v in (resolved.get("request_headers") or {}).items()}
                metadata = {
                    "expires_at": resolved.get("expires_at"),
                    **(resolved.get("metadata") or {}),
                }
                if source:
                    return source, headers, metadata
            except Exception as exc:
                # Some authorized providers return a durable media URL directly in search.
                # Use it as a fallback, but preserve the refresh failure for evidence logs.
                metadata["resolve_warning"] = str(exc)

    source = content.stream_url or content.media_url
    if not source:
        raise RuntimeError("连接器没有提供授权 media_url/stream_url，无法采集")
    stored = content.raw_metadata or {}
    if not headers:
        headers = {str(k): str(v) for k, v in (stored.get("request_headers") or {}).items()}
    metadata = {**stored.get("resolve_metadata", {}), **metadata}
    return source, headers, metadata


def capture(content: Content, seconds: int | None = None):
    source, request_headers, resolve_metadata = _resolve_source(content)
    if not shutil.which("ffmpeg"):
        raise RuntimeError("未安装 ffmpeg")

    seconds = seconds or settings.default_segment_seconds
    stamp = utcnow().strftime("%Y%m%d_%H%M%S")
    base = settings.storage_root / content.platform / content.platform_content_id
    for directory in ["video", "audio", "text", "metadata", "comments", "audit", "logs"]:
        (base / directory).mkdir(parents=True, exist_ok=True)

    video = base / "video" / f"{stamp}.mp4"
    audio = base / "audio" / f"{stamp}.wav"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-rw_timeout",
        "15000000",
        "-reconnect",
        "1",
        "-reconnect_streamed",
        "1",
        "-reconnect_delay_max",
        "5",
    ]
    if request_headers:
        header_blob = "".join(f"{key}: {value}\r\n" for key, value in request_headers.items())
        command.extend(["-headers", header_blob])
    command.extend(
        [
            "-i",
            source,
            "-t",
            str(seconds),
            "-map",
            "0:v?",
            "-map",
            "0:a?",
            "-c",
            "copy",
            str(video),
        ]
    )
    process = subprocess.run(command, capture_output=True, text=True)
    (base / "logs" / f"{stamp}.ffmpeg.log").write_text(
        process.stdout + "\n" + process.stderr,
        encoding="utf-8",
    )
    if not video.exists() or video.stat().st_size < 1024:
        raise RuntimeError("ffmpeg采集失败，请查看日志")

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-acodec",
            "pcm_s16le",
            str(audio),
        ],
        check=False,
    )
    return {
        "video": video,
        "audio": audio if audio.exists() else None,
        "base": base,
        "resolve_metadata": resolve_metadata,
        "request_headers_used": list(request_headers),
    }
