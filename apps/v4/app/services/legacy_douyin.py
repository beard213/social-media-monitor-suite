from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuditResult, Content, EvidenceFile
from app.services.audit import audit_text
from app.services.evidence import register_file
from app.utils import utcnow


def _safe_account_name(room_id: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", room_id.strip())
    return f"v4_douyin_{value or 'room'}"


def _project_root() -> Path | None:
    root = settings.legacy_douyin_output_root.expanduser().resolve()
    if root.name == "douyin_live_dataset" and root.parent.name == "output":
        return root.parent.parent
    return None


def _write_live_source(account_name: str, room_id: str) -> str:
    project_root = _project_root()
    if project_root is None or not project_root.exists():
        return ""
    source_file = project_root / "live_sources.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_url = f"https://live.douyin.com/{room_id}"
    lines = source_file.read_text(encoding="utf-8", errors="ignore").splitlines() if source_file.exists() else []
    prefix = f"{account_name}="
    kept = [line for line in lines if not line.strip().startswith(prefix)]
    kept.append(f"{account_name}={source_url}")
    temp = source_file.with_suffix(".txt.tmp")
    temp.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    temp.replace(source_file)
    return source_url


def _request(method: str, path: str, **kwargs) -> dict[str, Any]:
    base = settings.legacy_douyin_api_url.rstrip("/")
    if not base:
        raise RuntimeError("LEGACY_DOUYIN_API_URL 未配置")
    with httpx.Client(timeout=max(10, settings.http_timeout_seconds)) as client:
        response = client.request(method, f"{base}{path}", **kwargs)
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"旧抖音服务 {path} 返回格式不是JSON对象")
    return data


def start_legacy_douyin(body) -> dict[str, Any]:
    import json as _json
    import urllib.request as _request
    import urllib.error as _error

    if body.platform != "douyin":
        return {}

    base = settings.legacy_douyin_api_url.rstrip("/")

    if not base:
        raise RuntimeError(
            "LEGACY_DOUYIN_API_URL 未配置"
        )

    url = base + "/v1/live/start"

    payload = {
        "platform": "douyin",
        "room_id": body.room_id,
        "source_url": (
            body.source_url
            or
            f"https://live.douyin.com/{body.room_id}"
        ),
        "segment_seconds": body.segment_seconds,
        "title": body.title,
    }

    raw = _json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    request = _request.Request(
        url,
        data=raw,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with _request.urlopen(
            request,
            timeout=30,
        ) as response:
            body_raw = response.read().decode(
                "utf-8",
                errors="ignore",
            )
    except _error.HTTPError as exc:
        detail = exc.read().decode(
            "utf-8",
            errors="ignore",
        )
        raise RuntimeError(
            f"biliup桥接服务HTTP {exc.code}: "
            f"{detail}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"无法连接biliup桥接服务：{exc!r}"
        ) from exc

    try:
        data = _json.loads(body_raw)
    except Exception as exc:
        raise RuntimeError(
            "biliup桥接服务返回的不是JSON："
            + body_raw[:500]
        ) from exc

    if not data.get("ok"):
        raise RuntimeError(
            f"biliup桥接启动失败：{data}"
        )

    return data

def _already_registered(db: Session, path: Path) -> bool:
    return db.scalar(select(EvidenceFile.id).where(EvidenceFile.file_path == str(path))) is not None


def _register_if_new(db: Session, content: Content, file_type: str, path: Path) -> bool:
    if not path.exists() or _already_registered(db, path):
        return False
    register_file(
        db,
        content.id,
        file_type,
        path,
        content.source_url,
        [{"step": "legacy-douyin-import", "at": str(utcnow())}],
    )
    return True


def _status_from_json(raw: Any) -> str:
    text = json.dumps(raw, ensure_ascii=False).lower()
    if any(word in text for word in ["违规", '"block"', '"reject"', '"illegal"']):
        return "违规"
    if any(word in text for word in ["疑似", '"review"', '"suspect"', '"warning"']):
        return "疑似"
    if any(word in text for word in ["合规", '"pass"', '"safe"', '"normal"']):
        return "合规"
    return "unknown"


def import_legacy_douyin_output(
    db: Session,
    content: Content,
    account_name: str,
) -> dict[str, Any]:
    account_dir = (
        settings.legacy_douyin_output_root.expanduser()
        / account_name
    )

    result: dict[str, Any] = {
        "account_dir": str(account_dir),
        "found": False,
        "segments": 0,
        "imported": {
            "video": 0,
            "audio": 0,
            "text": 0,
            "metadata": 0,
            "audit": 0,
        },
    }

    if not account_dir.exists():
        return result

    segment_ids: set[str] = set()

    file_patterns = [
        ("video", "*.mp4"),
        ("video", "*.flv"),
        ("audio", "*.wav"),
        ("text", "*.txt"),
        ("metadata", "*.json"),
    ]

    for folder_name, pattern in file_patterns:
        folder = account_dir / folder_name
        if not folder.exists():
            continue

        for file_path in folder.glob(pattern):
            segment_ids.add(file_path.stem)

    audit_dir = account_dir / "audit"

    if audit_dir.exists():
        for audit_path in audit_dir.glob("*.json"):
            name = audit_path.name

            if name.endswith(".all.audit.json"):
                segment_ids.add(
                    name[:-len(".all.audit.json")]
                )
            elif name.endswith(".audit.json"):
                segment_ids.add(
                    name[:-len(".audit.json")]
                )

    for segment_id in sorted(segment_ids):
        segment_found = False

        video_candidates = [
            account_dir / "video" / f"{segment_id}.mp4",
            account_dir / "video" / f"{segment_id}.flv",
        ]

        for video_path in video_candidates:
            if not video_path.exists():
                continue

            segment_found = True

            if _register_if_new(
                db,
                content,
                "video",
                video_path,
            ):
                result["imported"]["video"] += 1

            break

        audio_path = (
            account_dir
            / "audio"
            / f"{segment_id}.wav"
        )

        if audio_path.exists():
            segment_found = True

            if _register_if_new(
                db,
                content,
                "audio",
                audio_path,
            ):
                result["imported"]["audio"] += 1

        text_path = (
            account_dir
            / "text"
            / f"{segment_id}.txt"
        )

        if text_path.exists():
            segment_found = True

            text_new = _register_if_new(
                db,
                content,
                "text",
                text_path,
            )

            if text_new:
                result["imported"]["text"] += 1

                text_content = text_path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                if text_content.strip():
                    audit = audit_text(
                        db,
                        content,
                        text_content,
                        "legacy_live_text",
                    )
                    content.risk_status = audit.status

        metadata_path = (
            account_dir
            / "metadata"
            / f"{segment_id}.json"
        )

        if metadata_path.exists():
            segment_found = True

            if _register_if_new(
                db,
                content,
                "metadata",
                metadata_path,
            ):
                result["imported"]["metadata"] += 1

        if audit_dir.exists():
            for audit_path in sorted(
                audit_dir.glob(f"{segment_id}*.json")
            ):
                segment_found = True

                if not _register_if_new(
                    db,
                    content,
                    "audit",
                    audit_path,
                ):
                    continue

                result["imported"]["audit"] += 1

                try:
                    raw = json.loads(
                        audit_path.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        )
                    )
                except Exception:
                    raw = {
                        "raw_text": audit_path.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        )
                    }

                status = _status_from_json(raw)

                db.add(
                    AuditResult(
                        content_id=content.id,
                        modality="legacy_audit",
                        detector_name=(
                            "legacy-douyin-detector"
                        ),
                        detector_version="legacy",
                        status=status,
                        response={
                            "source_file": str(audit_path),
                            "legacy_response": raw,
                        },
                    )
                )

                if status != "unknown":
                    content.risk_status = status

        if segment_found:
            result["found"] = True
            result["segments"] += 1

    metadata = dict(content.raw_metadata or {})

    metadata["legacy_account_name"] = account_name
    metadata["legacy_output_root"] = str(
        settings.legacy_douyin_output_root
    )
    metadata["legacy_last_sync_at"] = str(utcnow())
    metadata["legacy_import_counts"] = result["imported"]
    metadata["legacy_segment_count"] = result["segments"]

    if result["found"]:
        metadata["pipeline_stage"] = (
            "legacy_douyin_imported"
        )

    content.raw_metadata = metadata
    content.last_seen_at = utcnow()

    db.commit()

    return result
