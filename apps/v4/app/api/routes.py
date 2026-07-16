from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    MonitorTask,
    TaskProfile,
    Content,
    Comment,
    LiveMessage,
    LiveSession,
    AuditResult,
    EvidenceFile,
    Job,
    PushRecord,
    ExpansionLead,
)
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    SearchIngest,
    CommentIngest,
    LiveMessageItem,
    FilterPreview,
    LiveMonitorStart,
)
from app.adapters.registry import statuses
from app.services.filtering import content_filter
from app.services.jobs import enqueue
from app.services.detector import detector
from app.services.catalog import topic_catalog, region_catalog, detect_regions
from app.services.expansion import list_leads
from app.services.live_monitor import start_live_by_id
from app.core.config import settings
from app.utils import anonymize, hash_id, utcnow

router = APIRouter(prefix="/api")

PROFILE_FIELDS = {
    "topic_template",
    "regions",
    "keyword_match_mode",
    "time_range_hours",
    "sort_by",
    "result_limit",
    "collect_comments",
    "expand_related",
    "auto_audit",
    "auto_capture",
    "auto_push",
    "push_after_review",
    "notes",
}


def _task_dict(task: MonitorTask, db: Session | None = None) -> dict:
    profile = task.profile
    data = {
        "id": task.id,
        "name": task.name,
        "platforms": task.platforms,
        "content_types": task.content_types,
        "include_keywords": task.include_keywords,
        "exclude_keywords": task.exclude_keywords,
        "interval_seconds": task.interval_seconds,
        "enabled": task.enabled,
        "next_run_at": task.next_run_at,
        "last_run_at": task.last_run_at,
        "created_at": task.created_at,
        "topic_template": profile.topic_template if profile else "custom",
        "regions": profile.regions if profile else [],
        "keyword_match_mode": profile.keyword_match_mode if profile else "any",
        "time_range_hours": profile.time_range_hours if profile else 24,
        "sort_by": profile.sort_by if profile else "latest",
        "result_limit": profile.result_limit if profile else 50,
        "collect_comments": profile.collect_comments if profile else False,
        "expand_related": profile.expand_related if profile else False,
        "auto_audit": profile.auto_audit if profile else False,
        "auto_capture": profile.auto_capture if profile else False,
        "auto_push": profile.auto_push if profile else False,
        "push_after_review": profile.push_after_review if profile else True,
        "notes": profile.notes if profile else "",
    }
    if db is not None:
        data["content_count"] = sum(
            1 for content in db.scalars(select(Content)).all()
            if (content.raw_metadata or {}).get("task_id") == task.id
        )
        data["pending_jobs"] = len(
            [
                j
                for j in db.scalars(select(Job).where(Job.status.in_(["pending", "running"]))).all()
                if j.payload.get("task_id") == task.id
            ]
        )
    return data


def _content_stage(db: Session, content: Content) -> str:
    pushed = db.scalar(
        select(func.count(PushRecord.id)).where(PushRecord.content_id == content.id, PushRecord.status == "success")
    ) or 0
    if pushed:
        return "pushed"
    evidence = db.scalar(select(func.count(EvidenceFile.id)).where(EvidenceFile.content_id == content.id)) or 0
    if evidence:
        return "captured"
    audits = db.scalar(select(func.count(AuditResult.id)).where(AuditResult.content_id == content.id)) or 0
    if audits:
        return "audited"
    comments = db.scalar(select(func.count(Comment.id)).where(Comment.content_id == content.id)) or 0
    if comments:
        return "comments_collected"
    return "discovered"


def _content_dict(content: Content, db: Session) -> dict:
    metadata = content.raw_metadata or {}
    return {
        "id": content.id,
        "platform": content.platform,
        "platform_content_id": content.platform_content_id,
        "content_type": content.content_type,
        "title": content.title,
        "description": content.description,
        "source_url": content.source_url,
        "cover_url": content.cover_url,
        "author_alias": content.author_alias,
        "published_at": content.published_at,
        "first_seen_at": content.first_seen_at,
        "last_seen_at": content.last_seen_at,
        "matched_keywords": content.matched_keywords,
        "filter_status": content.filter_status,
        "filter_score": content.filter_score,
        "filter_reasons": content.filter_reasons,
        "risk_status": content.risk_status,
        "region_tags": metadata.get("region_tags") or ([metadata.get("region")] if metadata.get("region") else []),
        "topic_template": metadata.get("topic_template", "custom"),
        "task_id": metadata.get("task_id"),
        "task_name": metadata.get("task_name", ""),
        "engagement": metadata.get("engagement", {}),
        "pipeline_stage": _content_stage(db, content),
        "comment_count": db.scalar(select(func.count(Comment.id)).where(Comment.content_id == content.id)) or 0,
        "lead_count": db.scalar(
            select(func.count(ExpansionLead.id)).where(ExpansionLead.source_content_id == content.id)
        ) or 0,
        "audit_count": db.scalar(select(func.count(AuditResult.id)).where(AuditResult.content_id == content.id)) or 0,
        "evidence_count": db.scalar(select(func.count(EvidenceFile.id)).where(EvidenceFile.content_id == content.id)) or 0,
    }


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(func.count(MonitorTask.id))).scalar()
    return {
        "ok": True,
        "time": utcnow(),
        "detector": detector.health(),
        "platforms": statuses(),
        "live_monitor_bridge": {
            "configured": bool(settings.live_monitor_bridge_url),
            "base_url": settings.live_monitor_bridge_url,
        },
        "push_target": {
            "name": settings.push_target_name,
            "enabled": settings.push_enabled,
            "events_url_configured": bool(settings.push_events_url),
            "media_url_configured": bool(settings.push_media_url),
        },
    }


@router.get("/platforms")
def platforms():
    return statuses()


@router.get("/catalog")
def catalog():
    return {
        "topics": topic_catalog(),
        "regions": region_catalog(),
        "platforms": statuses(),
        "content_types": [
            {"id": "video", "name": "短视频"},
            {"id": "live", "name": "直播"},
        ],
        "intervals": [
            {"seconds": 300, "name": "每5分钟"},
            {"seconds": 600, "name": "每10分钟"},
            {"seconds": 1800, "name": "每30分钟"},
            {"seconds": 3600, "name": "每1小时"},
            {"seconds": 21600, "name": "每6小时"},
            {"seconds": 86400, "name": "每天"},
        ],
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return {
        "tasks": db.scalar(select(func.count(MonitorTask.id))) or 0,
        "contents": db.scalar(select(func.count(Content.id))) or 0,
        "videos": db.scalar(select(func.count(Content.id)).where(Content.content_type == "video")) or 0,
        "lives": db.scalar(select(func.count(Content.id)).where(Content.content_type == "live")) or 0,
        "kept": db.scalar(select(func.count(Content.id)).where(Content.filter_status == "kept")) or 0,
        "advertising": db.scalar(select(func.count(Content.id)).where(Content.filter_status == "advertising")) or 0,
        "comments": db.scalar(select(func.count(Comment.id))) or 0,
        "leads": db.scalar(select(func.count(ExpansionLead.id))) or 0,
        "needs_review": db.scalar(select(func.count(Content.id)).where(Content.filter_status == "needs_review")) or 0,
        "jobs_pending": db.scalar(select(func.count(Job.id)).where(Job.status == "pending")) or 0,
        "jobs_failed": db.scalar(select(func.count(Job.id)).where(Job.status == "failed")) or 0,
        "push_success": db.scalar(
            select(func.count(PushRecord.id)).where(PushRecord.status == "success")
        ) or 0,
    }


@router.post("/filter/preview")
def filter_preview(body: FilterPreview):
    return content_filter.evaluate(body.text, body.include_keywords, body.exclude_keywords)


@router.post("/tasks")
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    payload = body.model_dump()
    profile_data = {key: payload.pop(key) for key in list(payload) if key in PROFILE_FIELDS}
    task = MonitorTask(**payload, next_run_at=utcnow())
    task.profile = TaskProfile(**profile_data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_dict(task, db)


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    rows = db.scalars(select(MonitorTask).order_by(MonitorTask.created_at.desc())).all()
    return [_task_dict(task, db) for task in rows]


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(MonitorTask, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return _task_dict(task, db)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(MonitorTask, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    changes = body.model_dump(exclude_none=True)
    profile = task.profile or TaskProfile(task=task)
    for key, value in changes.items():
        if key in PROFILE_FIELDS:
            setattr(profile, key, value)
        else:
            setattr(task, key, value)
    if task.profile is None:
        task.profile = profile
    db.commit()
    db.refresh(task)
    return _task_dict(task, db)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(MonitorTask, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    db.delete(task)
    db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/run")
def run_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(MonitorTask, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return enqueue(db, "discovery", {"task_id": task_id, "limit": task.profile.result_limit if task.profile else 50})


@router.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(MonitorTask, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    task.enabled = not task.enabled
    db.commit()
    return _task_dict(task, db)


@router.get("/contents")
def list_contents(
    platform: str | None = None,
    content_type: str | None = None,
    filter_status: str | None = None,
    risk_status: str | None = None,
    region: str | None = None,
    topic: str | None = None,
    task_id: int | None = None,
    stage: str | None = None,
    query: str | None = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = select(Content).order_by(Content.first_seen_at.desc()).limit(500)
    if platform:
        q = q.where(Content.platform == platform)
    if content_type:
        q = q.where(Content.content_type == content_type)
    if filter_status:
        q = q.where(Content.filter_status == filter_status)
    if risk_status:
        q = q.where(Content.risk_status == risk_status)
    rows = db.scalars(q).all()
    result = []
    for content in rows:
        item = _content_dict(content, db)
        if region and region not in item["region_tags"]:
            continue
        if topic and item["topic_template"] != topic:
            continue
        if task_id and item["task_id"] != task_id:
            continue
        if stage and item["pipeline_stage"] != stage:
            continue
        if query:
            haystack = "\n".join([content.title, content.description, " ".join(content.matched_keywords or [])])
            if query.lower() not in haystack.lower():
                continue
        result.append(item)
        if len(result) >= limit:
            break
    return result


@router.get("/contents/{content_id}")
def get_content(content_id: int, db: Session = Depends(get_db)):
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(404, "content not found")
    return {
        "content": _content_dict(content, db),
        "comments": db.scalars(
            select(Comment).where(Comment.content_id == content.id).order_by(Comment.like_count.desc())
        ).all(),
        "audits": db.scalars(select(AuditResult).where(AuditResult.content_id == content.id)).all(),
        "evidence": db.scalars(select(EvidenceFile).where(EvidenceFile.content_id == content.id)).all(),
        "leads": db.scalars(
            select(ExpansionLead).where(ExpansionLead.source_content_id == content.id)
        ).all(),
        "push_records": db.scalars(select(PushRecord).where(PushRecord.content_id == content.id)).all(),
    }


@router.get("/evidence/{evidence_id}/view")
def view_evidence(evidence_id: int, db: Session = Depends(get_db)):
    evidence = db.get(EvidenceFile, evidence_id)
    if not evidence:
        raise HTTPException(404, "evidence not found")
    path = Path(evidence.file_path)
    if not path.is_file():
        raise HTTPException(404, "evidence file is not available on this server")
    return FileResponse(path, filename=path.name, content_disposition_type="inline")


@router.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: int, db: Session = Depends(get_db)):
    evidence = db.get(EvidenceFile, evidence_id)
    if not evidence:
        raise HTTPException(404, "evidence not found")
    path = Path(evidence.file_path)
    if not path.is_file():
        raise HTTPException(404, "evidence file is not available on this server")
    return FileResponse(path, filename=path.name, content_disposition_type="attachment")


@router.get("/comments")
def list_comments(
    content_id: int | None = None,
    filter_status: str | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    q = select(Comment).order_by(Comment.created_at.desc()).limit(limit)
    if content_id:
        q = q.where(Comment.content_id == content_id)
    if filter_status:
        q = q.where(Comment.filter_status == filter_status)
    return db.scalars(q).all()


@router.post("/contents/{content_id}/comments/fetch")
def queue_comments(content_id: int, limit: int = 100, db: Session = Depends(get_db)):
    if not db.get(Content, content_id):
        raise HTTPException(404, "content not found")
    return enqueue(db, "comments", {"content_id": content_id, "limit": limit})


@router.post("/contents/{content_id}/relations/fetch")
def queue_relations(content_id: int, limit: int = 100, db: Session = Depends(get_db)):
    if not db.get(Content, content_id):
        raise HTTPException(404, "content not found")
    return enqueue(db, "relations", {"content_id": content_id, "limit": limit})


@router.post("/contents/{content_id}/expand")
def queue_expansion(content_id: int, db: Session = Depends(get_db)):
    if not db.get(Content, content_id):
        raise HTTPException(404, "content not found")
    return enqueue(db, "expand", {"content_id": content_id})


@router.get("/leads")
def expansion_leads(
    content_id: int | None = None,
    status: str | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    return list_leads(db, content_id=content_id, status=status, limit=limit)


@router.patch("/leads/{lead_id}")
def update_lead(lead_id: int, status: str = Query(pattern="^(new|reviewed|dismissed|promoted)$"), db: Session = Depends(get_db)):
    lead = db.get(ExpansionLead, lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    lead.status = status
    db.commit()
    return lead


@router.post("/contents/{content_id}/capture")
def queue_capture(content_id: int, seconds: int = 120, db: Session = Depends(get_db)):
    if not db.get(Content, content_id):
        raise HTTPException(404, "content not found")
    return enqueue(db, "capture", {"content_id": content_id, "seconds": seconds})


@router.post("/contents/{content_id}/audit")
def queue_audit(content_id: int, db: Session = Depends(get_db)):
    if not db.get(Content, content_id):
        raise HTTPException(404, "content not found")
    return enqueue(db, "audit_text", {"content_id": content_id})


@router.post("/contents/{content_id}/review")
def review_content(
    content_id: int,
    status: str = Query(pattern="^(kept|advertising|irrelevant|needs_review)$"),
    db: Session = Depends(get_db),
):
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(404, "content not found")
    content.filter_status = status
    content.filter_reasons = [*(content.filter_reasons or []), f"人工复核:{status}"]
    metadata = dict(content.raw_metadata or {})
    metadata["reviewed_at"] = str(utcnow())
    metadata["review_status"] = status
    content.raw_metadata = metadata
    db.commit()
    return _content_dict(content, db)


@router.post("/live-monitor/start")
def start_live_monitor(body: LiveMonitorStart, db: Session = Depends(get_db)):
    return start_live_by_id(db, body)


@router.get("/live-sessions")
def list_live_sessions(db: Session = Depends(get_db)):
    return db.scalars(select(LiveSession).order_by(LiveSession.started_at.desc())).all()


@router.post("/contents/{content_id}/live/start")
def start_live(
    content_id: int,
    segment_seconds: int = Query(120, ge=30, le=1800),
    db: Session = Depends(get_db),
):
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(404, "content not found")
    if content.content_type != "live":
        raise HTTPException(400, "content is not live")
    running = db.scalar(
        select(LiveSession).where(LiveSession.content_id == content_id, LiveSession.status == "running")
    )
    if running:
        return running
    obj = LiveSession(
        content_id=content_id,
        status="running",
        segment_seconds=segment_seconds,
        next_segment_at=utcnow(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/live-sessions/{session_id}/stop")
def stop_live(session_id: int, db: Session = Depends(get_db)):
    obj = db.get(LiveSession, session_id)
    if not obj:
        raise HTTPException(404, "session not found")
    obj.status = "stopped"
    obj.stopped_at = utcnow()
    db.commit()
    return obj


@router.post("/contents/{content_id}/push")
def queue_push(content_id: int, include_media: bool = True, db: Session = Depends(get_db)):
    if not db.get(Content, content_id):
        raise HTTPException(404, "content not found")
    return enqueue(db, "push", {"content_id": content_id, "include_media": include_media})


@router.get("/push-records")
def list_push_records(limit: int = 100, db: Session = Depends(get_db)):
    return db.scalars(select(PushRecord).order_by(PushRecord.created_at.desc()).limit(limit)).all()


@router.get("/jobs")
def list_jobs(
    status: str | None = None,
    job_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if status:
        q = q.where(Job.status == status)
    if job_type:
        q = q.where(Job.job_type == job_type)
    return db.scalars(q).all()


@router.post("/provider/ingest/search")
def ingest_search(body: SearchIngest, db: Session = Depends(get_db)):
    count = 0
    for item in body.items:
        content = db.scalar(
            select(Content).where(
                Content.platform == item.platform,
                Content.platform_content_id == item.platform_content_id,
            )
        )
        result = content_filter.evaluate(item.title + "\n" + item.description, item.matched_keywords, [])
        if not content:
            content = Content(
                platform=item.platform,
                platform_content_id=item.platform_content_id,
                content_type=item.content_type,
            )
            db.add(content)
            count += 1
        content.title = item.title
        content.description = item.description
        content.source_url = item.source_url
        content.media_url = item.media_url
        content.stream_url = item.stream_url
        content.cover_url = item.cover_url
        content.author_alias = anonymize(item.author_id)
        content.published_at = item.published_at
        content.matched_keywords = item.matched_keywords
        metadata = dict(item.metadata or {})
        metadata["region_tags"] = metadata.get("region_tags") or detect_regions(item.title + "\n" + item.description)
        metadata["pipeline_stage"] = "discovered"
        content.raw_metadata = metadata
        content.filter_status = result["status"]
        content.filter_score = result["score"]
        content.filter_reasons = result["reasons"]
        content.last_seen_at = utcnow()
    db.commit()
    return {"ok": True, "created": count, "received": len(body.items)}


@router.post("/provider/ingest/comments")
def ingest_comments(body: CommentIngest, db: Session = Depends(get_db)):
    content = db.scalar(
        select(Content).where(
            Content.platform == body.platform,
            Content.platform_content_id == body.platform_content_id,
        )
    )
    if not content:
        raise HTTPException(404, "content not found")
    created = 0
    for item in body.comments:
        hashed = hash_id(item.platform_comment_id)
        if db.scalar(
            select(Comment).where(
                Comment.platform == body.platform,
                Comment.platform_comment_id_hash == hashed,
            )
        ):
            continue
        result = content_filter.evaluate(item.text, [], [])
        db.add(
            Comment(
                content_id=content.id,
                platform=body.platform,
                platform_comment_id_hash=hashed,
                author_alias=anonymize(item.author_id),
                text=item.text,
                like_count=item.like_count,
                published_at=item.published_at,
                filter_status=result["status"],
            )
        )
        created += 1
    db.commit()
    return {"ok": True, "created": created}


@router.post("/provider/ingest/live-message")
def ingest_live_message(body: LiveMessageItem, db: Session = Depends(get_db)):
    content = db.scalar(
        select(Content).where(
            Content.platform == body.platform,
            Content.platform_content_id == body.platform_content_id,
        )
    )
    if not content:
        raise HTTPException(404, "content not found")
    message = LiveMessage(
        content_id=content.id,
        message_type=body.message_type,
        author_alias=anonymize(body.author_id),
        text=body.text,
        event_time=body.event_time or utcnow(),
        raw_metadata=body.metadata,
    )
    db.add(message)
    db.commit()
    return {"ok": True}

@router.delete("/live-sessions/{session_id}")
def delete_live_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """删除直播监测会话，保留已采集的历史内容和检测证据。"""

    obj = db.get(LiveSession, session_id)

    if obj is None:
        raise HTTPException(
            status_code=404,
            detail="直播会话不存在",
        )

    content_id = obj.content_id

    # 先把会话状态改为停止，避免删除过程中继续作为运行会话。
    obj.status = "stopped"
    obj.last_error = "用户删除直播监测任务"
    db.flush()

    # 只删除直播会话。
    # Content、视频、音频、转写及检测记录仍然保留。
    db.delete(obj)
    db.commit()

    return {
        "ok": True,
        "message": "直播监测任务已删除",
        "session_id": session_id,
        "content_id": content_id,
        "history_preserved": True,
    }

