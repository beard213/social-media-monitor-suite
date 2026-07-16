from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.adapters.registry import get_adapter
from app.db.models import Content, MonitorTask, Job
from app.services.filtering import content_filter
from app.services.catalog import detect_regions
from app.services.jobs import enqueue
from app.utils import anonymize, utcnow


def _has_job(db: Session, job_type: str, content_id: int) -> bool:
    jobs = db.scalars(
        select(Job).where(Job.job_type == job_type, Job.status.in_(["pending", "running"]))
    ).all()
    return any(j.payload.get("content_id") == content_id for j in jobs)


def run_discovery(db: Session, task: MonitorTask, limit: int | None = None):
    profile = task.profile
    result_limit = limit or (profile.result_limit if profile else 50)
    options = {
        "regions": profile.regions if profile else [],
        "time_range_hours": profile.time_range_hours if profile else 24,
        "sort_by": profile.sort_by if profile else "latest",
        "keyword_match_mode": profile.keyword_match_mode if profile else "any",
    }
    stats = {
        "found": 0,
        "created": 0,
        "updated": 0,
        "comments_queued": 0,
        "audit_queued": 0,
        "expansion_queued": 0,
        "relations_queued": 0,
        "errors": [],
    }
    touched: list[Content] = []
    for platform in task.platforms:
        try:
            adapter = get_adapter(platform)
            items = adapter.search(task.include_keywords, task.content_types, result_limit, **options)
            stats["found"] += len(items)
            for item in items:
                obj = db.scalar(
                    select(Content).where(
                        Content.platform == item.platform,
                        Content.platform_content_id == item.platform_content_id,
                    )
                )
                text = f"{item.title}\n{item.description}"
                filter_result = content_filter.evaluate(text, task.include_keywords, task.exclude_keywords)
                if not obj:
                    obj = Content(
                        platform=item.platform,
                        platform_content_id=item.platform_content_id,
                        content_type=item.content_type,
                    )
                    db.add(obj)
                    stats["created"] += 1
                else:
                    stats["updated"] += 1
                obj.title = item.title
                obj.description = item.description
                obj.source_url = item.source_url
                obj.media_url = item.media_url
                obj.stream_url = item.stream_url
                obj.cover_url = item.cover_url
                obj.author_alias = anonymize(item.author_id)
                obj.published_at = item.published_at
                obj.last_seen_at = utcnow()
                obj.matched_keywords = item.matched_keywords or filter_result["matched"]
                obj.filter_status = filter_result["status"]
                obj.filter_score = filter_result["score"]
                obj.filter_reasons = filter_result["reasons"]
                metadata = dict(item.metadata or {})
                metadata["provider_author_ref"] = item.author_id
                metadata["task_id"] = task.id
                metadata["task_name"] = task.name
                metadata["topic_template"] = profile.topic_template if profile else "custom"
                metadata["region_tags"] = detect_regions(text, profile.regions if profile else [])
                metadata["pipeline_stage"] = "discovered"
                metadata["search_options"] = options
                obj.raw_metadata = metadata
                db.flush()
                touched.append(obj)
            db.commit()
        except Exception as exc:
            db.rollback()
            stats["errors"].append({"platform": platform, "error": str(exc)})

    for content in touched:
        if profile and profile.collect_comments and not _has_job(db, "comments", content.id):
            enqueue(db, "comments", {"content_id": content.id, "limit": 100})
            stats["comments_queued"] += 1
        if profile and profile.auto_audit and not _has_job(db, "audit_text", content.id):
            enqueue(db, "audit_text", {"content_id": content.id})
            stats["audit_queued"] += 1
        if profile and profile.expand_related:
            if (content.raw_metadata or {}).get("provider_author_ref") and not _has_job(db, "relations", content.id):
                enqueue(db, "relations", {"content_id": content.id, "limit": 100})
                stats["relations_queued"] += 1
            if not _has_job(db, "expand", content.id):
                enqueue(db, "expand", {"content_id": content.id})
                stats["expansion_queued"] += 1
        if profile and profile.auto_capture and content.filter_status == "kept" and not _has_job(db, "capture", content.id):
            enqueue(db, "capture", {"content_id": content.id, "seconds": 120})
        if profile and profile.auto_push and not profile.push_after_review and not _has_job(db, "push", content.id):
            enqueue(db, "push", {"content_id": content.id, "include_media": True})

    task.last_run_at = utcnow()
    task.next_run_at = utcnow() + timedelta(seconds=task.interval_seconds)
    db.commit()
    if stats["errors"] and stats["found"] == 0:
        details = "; ".join(f"{item['platform']}: {item['error']}" for item in stats["errors"])
        raise RuntimeError(f"所有平台搜索均失败：{details}")
    return stats
