from __future__ import annotations
import time
import traceback
from datetime import timedelta, timezone
from pathlib import Path
from sqlalchemy import select

from app.db.session import SessionLocal, Base, engine
from app.db.models import (
    MonitorTask,
    Content,
    LiveSession,
    EvidenceFile,
    PushRecord,
    Job,
    AuditResult,
)
from app.services.jobs import claim, done, fail, enqueue
from app.services.discovery import run_discovery
from app.services.comments import fetch_comments
from app.services.capture import capture
from app.services.evidence import register_file
from app.services.asr import transcribe
from app.services.audit import audit_text, audit_file, merge_status
from app.services.push import push_event, push_media
from app.services.expansion import build_expansion_leads
from app.services.relations import fetch_public_relations
from app.services.legacy_douyin import import_legacy_douyin_output
from app.core.config import settings
from app.utils import stable_hash, utcnow

Base.metadata.create_all(engine)


def _is_due(value):
    if value is None:
        return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= utcnow()


def _set_stage(content: Content, stage: str):
    metadata = dict(content.raw_metadata or {})
    metadata["pipeline_stage"] = stage
    metadata[f"{stage}_at"] = str(utcnow())
    content.raw_metadata = metadata


def schedule_due(db):
    tasks = db.scalars(select(MonitorTask).where(MonitorTask.enabled == True)).all()  # noqa: E712
    for task in tasks:
        if _is_due(task.next_run_at):
            jobs = db.scalars(
                select(Job).where(Job.job_type == "discovery", Job.status.in_(["pending", "running"]))
            ).all()
            exists = any(job.payload.get("task_id") == task.id for job in jobs)
            if not exists:
                enqueue(
                    db,
                    "discovery",
                    {
                        "task_id": task.id,
                        "limit": task.profile.result_limit if task.profile else 50,
                    },
                )
            task.next_run_at = utcnow() + timedelta(seconds=task.interval_seconds)
            db.commit()

    sessions = db.scalars(select(LiveSession).where(LiveSession.status == "running")).all()
    for session in sessions:
        if _is_due(session.next_segment_at):
            jobs = db.scalars(
                select(Job).where(Job.job_type == "capture", Job.status.in_(["pending", "running"]))
            ).all()
            exists = any(job.payload.get("live_session_id") == session.id for job in jobs)
            if not exists:
                enqueue(
                    db,
                    "capture",
                    {
                        "content_id": session.content_id,
                        "seconds": session.segment_seconds,
                        "live_session_id": session.id,
                    },
                )
                session.next_segment_at = utcnow() + timedelta(seconds=session.segment_seconds + 5)
                db.commit()


def handle(db, job):
    payload = job.payload
    if job.job_type == "discovery":
        task = db.get(MonitorTask, payload["task_id"])
        if not task:
            raise RuntimeError("task not found")
        return run_discovery(db, task, payload.get("limit"))

    content = db.get(Content, payload["content_id"])
    if not content:
        raise RuntimeError("content not found")

    if job.job_type == "legacy_douyin_import":
        account_name = payload.get("account_name", "")
        if not account_name:
            raise RuntimeError("legacy_douyin_import缺少account_name")
        result = import_legacy_douyin_output(db, content, account_name)
        checks = int(payload.get("checks", 0))
        continuous = settings.legacy_douyin_max_rounds == 0
        should_check_again = (not result.get("found") and checks < settings.legacy_douyin_sync_max_checks) or continuous
        if should_check_again:
            next_job = enqueue(
                db,
                "legacy_douyin_import",
                {
                    "content_id": content.id,
                    "live_session_id": payload.get("live_session_id"),
                    "account_name": account_name,
                    "checks": checks + 1,
                },
                max_attempts=1,
            )
            next_job.run_after = utcnow() + timedelta(seconds=settings.legacy_douyin_sync_interval_seconds)
            db.commit()
        elif payload.get("live_session_id"):
            session = db.get(LiveSession, payload["live_session_id"])
            if session:
                session.status = "completed" if result.get("found") else "failed"
                session.last_error = "" if result.get("found") else "旧抖音流程在等待期内未生成采集文件"
                db.commit()
        return result

    if job.job_type == "comments":
        result = fetch_comments(db, content, payload.get("limit", 100))
        if not any(
            j.payload.get("content_id") == content.id
            for j in db.scalars(
                select(Job).where(Job.job_type == "expand", Job.status.in_(["pending", "running"]))
            ).all()
        ):
            enqueue(db, "expand", {"content_id": content.id})
        return result

    if job.job_type == "relations":
        result = fetch_public_relations(db, content, payload.get("limit", 100))
        _set_stage(content, "relations_collected")
        db.commit()
        return result

    if job.job_type == "expand":
        result = build_expansion_leads(db, content)
        _set_stage(content, "expanded")
        db.commit()
        return result

    if job.job_type == "capture":
        files = capture(content, payload.get("seconds", 120))
        register_file(
            db,
            content.id,
            "video",
            files["video"],
            content.source_url,
            [{"step": "ffmpeg-capture", "at": str(utcnow())}],
        )
        if files["audio"]:
            register_file(
                db,
                content.id,
                "audio",
                files["audio"],
                content.source_url,
                [{"step": "ffmpeg-extract-audio", "at": str(utcnow())}],
            )
        text_path = files["base"] / "text" / (files["video"].stem + ".txt")
        asr_result = (
            transcribe(files["audio"], text_path)
            if files["audio"]
            else {"status": "skipped", "text": ""}
        )
        if text_path.exists():
            register_file(
                db,
                content.id,
                "text",
                text_path,
                content.source_url,
                [{"step": "funasr", "status": asr_result["status"], "at": str(utcnow())}],
            )
        statuses = [audit_file(db, content, "video", files["video"]).status]
        if files["audio"]:
            statuses.append(audit_file(db, content, "audio", files["audio"]).status)
        if text_path.exists():
            statuses.append(
                audit_text(db, content, text_path.read_text(encoding="utf-8"), "text").status
            )
        comments_text = "\n".join(
            comment.text for comment in content.comments if comment.filter_status != "advertising"
        )
        if comments_text:
            statuses.append(audit_text(db, content, comments_text, "comments").status)
        content.risk_status = merge_status(statuses)
        _set_stage(content, "captured")
        if payload.get("live_session_id"):
            session = db.get(LiveSession, payload["live_session_id"])
            if session:
                session.last_error = ""
                session.next_segment_at = utcnow() + timedelta(seconds=5)
        db.commit()
        return {"risk_status": content.risk_status}

    if job.job_type == "audit_text":
        text = "\n".join(
            [
                content.title,
                content.description,
                *[
                    comment.text
                    for comment in content.comments
                    if comment.filter_status != "advertising"
                ],
            ]
        )
        result = audit_text(db, content, text, "metadata_comments")
        content.risk_status = result.status
        _set_stage(content, "audited")
        db.commit()
        return {"status": result.status}

    if job.job_type == "push":
        audits = db.scalars(select(AuditResult).where(AuditResult.content_id == content.id)).all()
        evidence = db.scalars(select(EvidenceFile).where(EvidenceFile.content_id == content.id)).all()
        metadata = content.raw_metadata or {}
        event_payload = {
            "event_id": f"content_{content.id}",
            "platform": content.platform,
            "content_type": content.content_type,
            "title": content.title,
            "description": content.description,
            "source_url": content.source_url,
            "published_at": str(content.published_at) if content.published_at else None,
            "filter_status": content.filter_status,
            "risk_status": content.risk_status,
            "matched_keywords": content.matched_keywords,
            "region_tags": metadata.get("region_tags", []),
            "topic_template": metadata.get("topic_template", "custom"),
            "audits": [
                {
                    "modality": audit.modality,
                    "status": audit.status,
                    "labels": audit.labels,
                    "risk_words": audit.risk_words,
                    "confidence": audit.confidence,
                }
                for audit in audits
            ],
            "evidence": [{"type": item.file_type, "sha256": item.sha256} for item in evidence],
        }
        result = push_event(event_payload)
        record = PushRecord(
            content_id=content.id,
            target="events",
            payload_hash=stable_hash(event_payload),
            status=result.get("status", "unknown"),
            attempt_count=1,
            ack_id=str(result.get("response", {}).get("ack_id", "")),
            last_error=result.get("reason", ""),
        )
        db.add(record)
        if payload.get("include_media"):
            videos = [item for item in evidence if item.file_type == "video"]
            if videos:
                media_result = push_media(content.id, Path(videos[-1].file_path))
                db.add(
                    PushRecord(
                        content_id=content.id,
                        target="media",
                        payload_hash=videos[-1].sha256,
                        status=media_result.get("status", "unknown"),
                        attempt_count=1,
                        ack_id=str(media_result.get("response", {}).get("ack_id", "")),
                        last_error=media_result.get("reason", ""),
                    )
                )
        _set_stage(content, "pushed")
        db.commit()
        return result

    raise RuntimeError(f"unknown job type {job.job_type}")


def main():
    print("worker started")
    while True:
        with SessionLocal() as db:
            try:
                schedule_due(db)
                job = claim(db)
            except Exception:
                traceback.print_exc()
                time.sleep(2)
                continue
            if not job:
                time.sleep(2)
                continue
            try:
                result = handle(db, job)
                done(db, job)
                print("job success", job.id, job.job_type, result)
            except Exception as exc:
                traceback.print_exc()
                fail(db, job, str(exc))


if __name__ == "__main__":
    main()
