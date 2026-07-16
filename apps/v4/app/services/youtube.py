from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditResult, Comment, Content, EvidenceFile
from app.services.audit import audit_file, audit_text, merge_status
from app.services.evidence import register_file
from app.services.jobs import enqueue
from app.utils import utcnow

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "connector_service" / "youtube" / "collector.py"
PYTHON = ROOT / ".venv" / "bin" / "python"
OUTPUT = Path(os.getenv("YOUTUBE_OUTPUT_ROOT", "/data4/home/minghuazhao/youtube-monitor-data/output"))
PROXY = os.getenv("YOUTUBE_PROXY", "http://127.0.0.1:7890")
DENO = Path(os.getenv("YOUTUBE_DENO_BIN", str(Path.home() / ".deno/bin/deno")))


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_time(value: Any, upload_date: Any = None):
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), timezone.utc)
        except Exception:
            pass
    if upload_date:
        try:
            return datetime.strptime(str(upload_date), "%Y%m%d").replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def exists_evidence(db: Session, path: Path) -> bool:
    return db.scalar(select(EvidenceFile.id).where(EvidenceFile.file_path == str(path.resolve()))) is not None


def add_evidence(db: Session, content: Content, kind: str, path: Path, step: str) -> bool:
    if not path.exists() or not path.is_file() or exists_evidence(db, path):
        return False
    register_file(db, content.id, kind, path.resolve(), content.source_url, [{"step": step, "at": str(utcnow())}])
    return True


def srt_text(path: Path) -> str:
    out = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.isdigit() or "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line and (not out or out[-1] != line):
            out.append(line)
    return "\n".join(out)


def extract_audio(video: Path, audio: Path) -> bool:
    if audio.exists() and audio.stat().st_size > 1024:
        return True
    result = subprocess.run([
        "ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=7200, check=False)
    return result.returncode == 0 and audio.exists()


def transcribe_audio(audio: Path, text_path: Path) -> dict[str, Any]:
    if text_path.exists() and text_path.stat().st_size:
        return {"status": "existing", "text": text_path.read_text(encoding="utf-8", errors="ignore")}
    errors = []
    for name in ("app.services.asr", "app.services.transcription", "app.services.transcriber"):
        try:
            module = importlib.import_module(name)
            fn = getattr(module, "transcribe", None)
            if callable(fn):
                result = fn(audio, text_path)
                text = text_path.read_text(encoding="utf-8", errors="ignore") if text_path.exists() else ""
                return {"status": (result or {}).get("status", "success") if isinstance(result, dict) else "success", "text": text, "module": name}
        except Exception as exc:
            errors.append(f"{name}: {exc!r}")
    return {"status": "failed", "text": "", "errors": errors}


def has_audit(db: Session, content_id: int, modality: str) -> bool:
    return db.scalar(select(AuditResult.id).where(AuditResult.content_id == content_id, AuditResult.modality == modality)) is not None


def import_video(db: Session, folder: Path, options: dict[str, Any]):
    metadata = load_json(folder / "metadata.json", {})
    if not isinstance(metadata, dict):
        return None
    video_id = str(metadata.get("video_id") or folder.name).strip()
    if not video_id:
        return None
    source_url = str(metadata.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}")
    content = db.scalar(select(Content).where(Content.platform == "youtube", Content.platform_content_id == video_id))
    created = content is None
    if content is None:
        content = Content(platform="youtube", platform_content_id=video_id, content_type="video")
        db.add(content)
        db.flush()
    content.title = str(metadata.get("title") or video_id)
    content.description = str(metadata.get("description") or "")
    content.source_url = source_url
    content.media_url = source_url
    content.cover_url = str(metadata.get("thumbnail") or "")
    content.author_alias = str(metadata.get("channel") or metadata.get("channel_id") or "youtube")[:80]
    content.published_at = parse_time(metadata.get("timestamp"), metadata.get("upload_date"))
    content.filter_status = "kept"
    content.last_seen_at = utcnow()
    raw = dict(content.raw_metadata or {})
    raw.update(metadata)
    raw.update({"pipeline_stage": "youtube_importing", "youtube_local_dir": str(folder.resolve()), "youtube_options": options})
    content.raw_metadata = raw
    db.flush()

    comments = load_json(folder / "comments.json", [])
    comments_created = 0
    if isinstance(comments, list):
        for item in comments:
            if not isinstance(item, dict) or not str(item.get("text") or "").strip():
                continue
            key = "|".join([str(item.get("comment_id") or ""), str(item.get("author") or ""), str(item.get("timestamp") or ""), str(item.get("text") or "")])
            digest = hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest()
            if db.scalar(select(Comment.id).where(Comment.platform == "youtube", Comment.platform_comment_id_hash == digest)):
                continue
            db.add(Comment(content_id=content.id, platform="youtube", platform_comment_id_hash=digest, author_alias=str(item.get("author") or "anonymous")[:80], text=str(item.get("text")), like_count=int(item.get("like_count") or 0), published_at=parse_time(item.get("timestamp")), filter_status="kept", risk_status="pending"))
            comments_created += 1

    for name, kind in (("metadata.json", "metadata"), ("comments.json", "comments"), ("manifest.json", "manifest")):
        add_evidence(db, content, kind, folder / name, "youtube-import")
    for cover in list(folder.glob("*.jpg")) + list(folder.glob("*.webp")):
        add_evidence(db, content, "cover", cover, "youtube-thumbnail")

    videos = list(folder.glob("*.mp4")) + list(folder.glob("*.mkv")) + list(folder.glob("*.webm"))
    video = videos[0] if videos else None
    if video:
        add_evidence(db, content, "video", video, "yt-dlp")

    text_path = folder / f"{video_id}.txt"
    transcript = ""
    subtitles = sorted(folder.glob("*.srt"))
    if subtitles:
        for subtitle in subtitles:
            add_evidence(db, content, "subtitle", subtitle, "yt-dlp-subtitle")
        transcript = srt_text(subtitles[0])
        if transcript:
            text_path.write_text(transcript, encoding="utf-8")

    audio = folder / f"{video_id}.wav"
    asr = {"status": "skipped"}
    if video and options.get("auto_transcribe", True) and extract_audio(video, audio):
        add_evidence(db, content, "audio", audio, "ffmpeg-extract-audio")
        if not transcript:
            asr = transcribe_audio(audio, text_path)
            transcript = str(asr.get("text") or "")
    if text_path.exists():
        add_evidence(db, content, "text", text_path, "youtube-transcription")

    statuses = []
    audit_errors = []
    if options.get("auto_audit", True):
        text_map = {
            "youtube_metadata": "\n".join([content.title, content.description]),
            "youtube_comments": "\n".join(str(x.get("text") or "") for x in comments if isinstance(x, dict)),
            "youtube_transcript": transcript,
        }
        for modality, text in text_map.items():
            if text.strip() and not has_audit(db, content.id, modality):
                try:
                    statuses.append(audit_text(db, content, text, modality).status)
                except Exception as exc:
                    audit_errors.append(f"{modality}: {exc!r}")
        if options.get("audit_media", True):
            for modality, path in (("video", video), ("audio", audio if audio.exists() else None)):
                if path and not has_audit(db, content.id, modality):
                    try:
                        statuses.append(audit_file(db, content, modality, path).status)
                    except Exception as exc:
                        audit_errors.append(f"{modality}: {exc!r}")
    content.risk_status = merge_status(statuses) if statuses else (content.risk_status or "unknown")
    raw = dict(content.raw_metadata or {})
    raw.update({"pipeline_stage": "youtube_processed", "youtube_comments_created": comments_created, "youtube_asr": asr, "youtube_audit_errors": audit_errors, "youtube_processed_at": str(utcnow())})
    content.raw_metadata = raw
    db.commit()
    return {"content_id": content.id, "video_id": video_id, "created": created, "comments_created": comments_created, "risk_status": content.risk_status, "audit_errors": audit_errors}


def run_youtube_job(db: Session, payload: dict[str, Any]):
    url = str(payload.get("url") or "").strip()
    if not url or ("youtube.com" not in url and "youtu.be" not in url):
        raise RuntimeError("请输入有效的YouTube频道、播放列表或视频地址")
    max_videos = max(1, min(int(payload.get("max_videos", 3)), 50))
    max_comments = max(0, min(int(payload.get("max_comments", 100)), 2000))
    max_height = max(144, min(int(payload.get("max_height", 720)), 2160))
    command = [str(PYTHON if PYTHON.exists() else Path(sys.executable)), str(COLLECTOR), "--limit", str(max_videos), "--max-comments", str(max_comments), "--max-height", str(max_height), "--proxy", str(payload.get("proxy") or PROXY)]
    if not payload.get("download_video", True):
        command.append("--metadata-only")
    command.append(url)
    env = os.environ.copy()
    env["PATH"] = str(DENO.parent) + os.pathsep + env.get("PATH", "")
    env.setdefault("http_proxy", PROXY)
    env.setdefault("https_proxy", PROXY)
    env.setdefault("HTTP_PROXY", PROXY)
    env.setdefault("HTTPS_PROXY", PROXY)
    env.setdefault("NO_PROXY", "127.0.0.1,localhost,0.0.0.0,::1")
    env.setdefault("no_proxy", env["NO_PROXY"])
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=int(payload.get("timeout_seconds", 14400)), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"YouTube采集失败 returncode={result.returncode}\n{(result.stdout or '')[-4000:]}")
    options = {"auto_transcribe": bool(payload.get("auto_transcribe", True)), "auto_audit": bool(payload.get("auto_audit", True)), "audit_media": bool(payload.get("audit_media", True))}
    imported = []
    for manifest in sorted(OUTPUT.rglob("manifest.json")):
        item = import_video(db, manifest.parent, options)
        if item:
            imported.append(item)
    if payload.get("monitor_enabled", False):
        next_job = enqueue(db, "youtube_collect", dict(payload), max_attempts=1)
        next_job.run_after = utcnow() + timedelta(seconds=max(300, int(payload.get("interval_seconds", 1800))))
        db.commit()
    return {"ok": True, "videos_imported": len(imported), "items": imported, "collector_output": (result.stdout or "")[-2000:]}
