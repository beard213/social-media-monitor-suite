from __future__ import annotations

import os
import shutil
import socket
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Content, Job
from app.db.session import get_db
from app.services.jobs import enqueue

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


class YouTubeTaskCreate(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    max_videos: int = Field(default=3, ge=1, le=50)
    max_comments: int = Field(default=100, ge=0, le=2000)
    max_height: int = Field(default=720, ge=144, le=2160)
    download_video: bool = True
    auto_transcribe: bool = True
    auto_audit: bool = True
    audit_media: bool = True
    monitor_enabled: bool = False
    interval_seconds: int = Field(default=1800, ge=300, le=86400)


def proxy_ok():
    try:
        with socket.create_connection(("127.0.0.1", 7890), timeout=2):
            return True
    except OSError:
        return False


@router.get("/health")
def health():
    root = Path(__file__).resolve().parents[2]
    collector = root / "connector_service/youtube/collector.py"
    deno = Path.home() / ".deno/bin/deno"
    return {"ok": collector.exists() and proxy_ok(), "configured": collector.exists(), "collector_exists": collector.exists(), "proxy_port_open": proxy_ok(), "proxy": os.getenv("YOUTUBE_PROXY", "http://127.0.0.1:7890"), "deno_exists": deno.exists(), "deno": str(deno), "ffmpeg": shutil.which("ffmpeg") or "", "cookies_configured": bool(os.getenv("YOUTUBE_COOKIES_FILE"))}


@router.post("/tasks")
def create_task(body: YouTubeTaskCreate, db: Session = Depends(get_db)):
    if "youtube.com" not in body.url and "youtu.be" not in body.url:
        raise HTTPException(400, "请输入有效的YouTube地址")
    job = enqueue(db, "youtube_collect", body.model_dump(), max_attempts=2)
    return {"ok": True, "job_id": job.id, "status": job.status}


@router.get("/tasks")
def tasks(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return db.scalars(select(Job).where(Job.job_type == "youtube_collect").order_by(Job.created_at.desc()).limit(limit)).all()


@router.post("/tasks/{job_id}/retry")
def retry(job_id: int, db: Session = Depends(get_db)):
    old = db.get(Job, job_id)
    if not old or old.job_type != "youtube_collect":
        raise HTTPException(404, "YouTube任务不存在")
    job = enqueue(db, "youtube_collect", dict(old.payload or {}), max_attempts=2)
    return {"ok": True, "job_id": job.id}


@router.delete("/tasks/{job_id}")
def cancel(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or job.job_type != "youtube_collect":
        raise HTTPException(404, "YouTube任务不存在")
    if job.status in {"pending", "running"}:
        job.status = "cancelled"
        db.commit()
    return {"ok": True, "job_id": job.id, "status": job.status}


@router.get("/videos")
def videos(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return db.scalars(select(Content).where(Content.platform == "youtube").order_by(Content.last_seen_at.desc()).limit(limit)).all()
