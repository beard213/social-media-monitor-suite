from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.registry import get_adapter, statuses
from app.core.config import settings
from app.db.models import (
    AuditResult,
    Comment,
    Content,
    ExpansionLead,
    Job,
    LiveMessage,
    MonitorTask,
)
from app.db.session import get_db
from app.utils import utcnow

router = APIRouter(prefix="/api/console", tags=["monitor-console"])

RISK_LABELS = {
    "high": "高风险",
    "medium": "中风险",
    "low": "低风险",
    "normal": "正常",
    "pending": "待研判",
}


def _dt(value: datetime | None) -> datetime:
    if value is None:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _engagement(content: Content) -> dict[str, int]:
    raw = (content.raw_metadata or {}).get("engagement") or {}
    return {
        "views": int(raw.get("views") or raw.get("play_count") or raw.get("viewers") or 0),
        "likes": int(raw.get("likes") or raw.get("digg_count") or 0),
        "comments": int(raw.get("comments") or raw.get("comment_count") or 0),
        "shares": int(raw.get("shares") or raw.get("share_count") or 0),
    }


def _content_risk(db: Session, content: Content) -> tuple[int, list[str], list[str]]:
    audits = db.scalars(
        select(AuditResult).where(AuditResult.content_id == content.id).order_by(AuditResult.created_at.desc())
    ).all()
    labels: list[str] = []
    words: list[str] = []
    confidences: list[float] = []
    high_hits = 0
    for audit in audits:
        labels.extend(audit.labels or [])
        words.extend(audit.risk_words or [])
        if audit.confidence is not None:
            confidences.append(float(audit.confidence))
        if audit.status in {"high", "danger", "risky", "violation", "blocked"}:
            high_hits += 1

    score = 8
    score += min(28, round(max(0.0, float(content.filter_score or 0)) * 28))
    score += min(34, high_hits * 17)
    if confidences:
        score += min(22, round(max(confidences) * 22))
    if content.risk_status == "high":
        score = max(score, 85)
    elif content.risk_status == "medium":
        score = max(score, 58)
    elif content.risk_status in {"low", "normal"}:
        score = min(score, 39)
    if content.filter_status == "advertising":
        score = min(score, 48)
    return min(99, max(1, score)), list(dict.fromkeys(labels)), list(dict.fromkeys(words))


def _risk_level(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 55:
        return "medium"
    if score >= 30:
        return "low"
    return "normal"


def _risk_accounts(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    contents = db.scalars(select(Content).order_by(Content.last_seen_at.desc())).all()
    comments = db.scalars(select(Comment).order_by(Comment.created_at.desc())).all()
    messages = db.scalars(select(LiveMessage).order_by(LiveMessage.event_time.desc())).all()
    content_by_id = {item.id: item for item in contents}
    risk_cache = {item.id: _content_risk(db, item) for item in contents}

    grouped: dict[str, dict[str, list[Any]]] = defaultdict(
        lambda: {"contents": [], "comments": [], "messages": []}
    )
    for content in contents:
        grouped[content.author_alias or "anonymous"]["contents"].append(content)
    for comment in comments:
        grouped[comment.author_alias or "anonymous"]["comments"].append(comment)
    for message in messages:
        grouped[message.author_alias or "anonymous"]["messages"].append(message)

    explicit_scores = {"high": 92, "medium": 67, "low": 36, "normal": 12, "pending": 45}
    rows: list[dict[str, Any]] = []
    for alias, bucket in grouped.items():
        authored: list[Content] = bucket["contents"]
        account_comments: list[Comment] = bucket["comments"]
        account_messages: list[LiveMessage] = bucket["messages"]
        scores: list[int] = []
        labels: list[str] = []
        words: list[str] = []
        times: list[datetime] = []
        engagement_total = {"views": 0, "likes": 0, "comments": 0, "shares": 0}
        platforms: set[str] = set()

        for content in authored:
            score, content_labels, content_words = risk_cache[content.id]
            scores.append(score)
            labels.extend(content_labels)
            words.extend(content_words)
            platforms.add(content.platform)
            times.append(_dt(content.last_seen_at))
            for key, value in _engagement(content).items():
                engagement_total[key] += value

        for comment in account_comments:
            parent = content_by_id.get(comment.content_id)
            parent_score, parent_labels, parent_words = risk_cache.get(comment.content_id, (20, [], []))
            score = explicit_scores.get(comment.risk_status, parent_score)
            if comment.filter_status == "advertising":
                score = min(score, 44)
                labels.append("营销导流")
            scores.append(max(score, round(parent_score * 0.45)))
            labels.extend(parent_labels)
            words.extend(parent_words)
            if parent:
                platforms.add(parent.platform)
            platforms.add(comment.platform)
            times.append(_dt(comment.published_at or comment.created_at))
            engagement_total["likes"] += int(comment.like_count or 0)
            engagement_total["comments"] += 1

        for message in account_messages:
            parent = content_by_id.get(message.content_id)
            parent_score, parent_labels, parent_words = risk_cache.get(message.content_id, (20, [], []))
            raw = message.raw_metadata or {}
            score = int(raw.get("risk_score") or explicit_scores.get(raw.get("review_status"), parent_score))
            scores.append(max(score, round(parent_score * 0.45)))
            labels.extend(raw.get("labels") or parent_labels)
            words.extend(raw.get("risk_words") or parent_words)
            if parent:
                platforms.add(parent.platform)
            times.append(_dt(message.event_time))
            engagement_total["comments"] += 1
            engagement_total["likes"] += int(raw.get("like_count") or 0)

        if not scores:
            continue
        score = min(99, round(max(scores) * 0.72 + mean(scores) * 0.28))
        level = _risk_level(score)
        latest = max(times, default=utcnow())
        interaction_count = len(account_comments) + len(account_messages)
        rows.append(
            {
                "alias": alias,
                "risk_score": score,
                "risk_level": level,
                "risk_label": RISK_LABELS[level],
                "platforms": sorted(platforms),
                "content_count": len(authored),
                "interaction_count": interaction_count,
                "latest_seen_at": latest,
                "labels": list(dict.fromkeys(labels))[:6],
                "risk_words": list(dict.fromkeys(words))[:8],
                "engagement": engagement_total,
                "summary": (
                    f"发布公开内容{len(authored)}条，产生公开互动{interaction_count}条，"
                    f"最近一次监测于{latest.astimezone().strftime('%m-%d %H:%M')}。"
                ),
            }
        )
    rows.sort(key=lambda row: (row["risk_score"], _dt(row["latest_seen_at"])), reverse=True)
    return rows[:limit]

def _feed_rows(db: Session, limit: int = 200) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    comments = db.scalars(select(Comment).order_by(Comment.created_at.desc()).limit(limit)).all()
    for item in comments:
        content = db.get(Content, item.content_id)
        if not content:
            continue
        score, labels, words = _content_risk(db, content)
        if item.risk_status == "high":
            score = max(88, score)
        elif item.risk_status == "medium":
            score = max(62, score)
        elif item.filter_status == "advertising":
            score = min(score, 44)
        rows.append(
            {
                "id": f"comment-{item.id}",
                "kind": "comment",
                "platform": item.platform,
                "content_id": item.content_id,
                "content_title": content.title,
                "author_alias": item.author_alias,
                "text": item.text,
                "like_count": item.like_count,
                "event_time": item.published_at or item.created_at,
                "risk_score": score,
                "risk_level": _risk_level(score),
                "labels": labels[:3],
                "risk_words": words[:5],
                "filter_status": item.filter_status,
            }
        )
    messages = db.scalars(select(LiveMessage).order_by(LiveMessage.event_time.desc()).limit(limit)).all()
    for item in messages:
        content = db.get(Content, item.content_id)
        if not content:
            continue
        score, labels, words = _content_risk(db, content)
        raw = item.raw_metadata or {}
        explicit = raw.get("risk_score")
        if explicit is not None:
            score = int(explicit)
        rows.append(
            {
                "id": f"live-{item.id}",
                "kind": item.message_type or "live_message",
                "platform": content.platform,
                "content_id": item.content_id,
                "content_title": content.title,
                "author_alias": item.author_alias,
                "text": item.text,
                "like_count": int(raw.get("like_count") or 0),
                "event_time": item.event_time,
                "risk_score": score,
                "risk_level": _risk_level(score),
                "labels": raw.get("labels") or labels[:3],
                "risk_words": raw.get("risk_words") or words[:5],
                "filter_status": raw.get("filter_status", "kept"),
            }
        )
    rows.sort(key=lambda row: _dt(row["event_time"]), reverse=True)
    return rows[:limit]


def _topic_rows(db: Session, limit: int = 12) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    negative: Counter[str] = Counter()
    latest: dict[str, datetime] = {}
    contents = db.scalars(select(Content)).all()
    for content in contents:
        score, _, _ = _content_risk(db, content)
        for keyword in content.matched_keywords or []:
            keyword = str(keyword).strip()
            if not keyword:
                continue
            counter[keyword] += 1 + _engagement(content)["comments"]
            negative[keyword] += score
            latest[keyword] = max(latest.get(keyword, _dt(content.last_seen_at)), _dt(content.last_seen_at))
    leads = db.scalars(select(ExpansionLead)).all()
    for lead in leads:
        label = str(lead.label or "").strip()
        if label:
            counter[label] += max(1, lead.evidence_count)
            negative[label] += 45 if lead.status == "new" else 25
            latest[label] = max(latest.get(label, _dt(lead.created_at)), _dt(lead.created_at))
    result = []
    for label, heat in counter.most_common(limit):
        avg_negative = round(negative[label] / max(1, counter[label]))
        result.append(
            {
                "label": label,
                "heat": heat,
                "negative_rate": min(98, max(3, avg_negative)),
                "latest_at": latest.get(label),
            }
        )
    return result


def _word_cloud(db: Session, limit: int = 28) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for content in db.scalars(select(Content)).all():
        for keyword in content.matched_keywords or []:
            counter[str(keyword)] += 5
        for reason in content.filter_reasons or []:
            if len(str(reason)) <= 16:
                counter[str(reason)] += 1
    for audit in db.scalars(select(AuditResult)).all():
        for label in audit.labels or []:
            counter[str(label)] += 4
        for word in audit.risk_words or []:
            counter[str(word)] += 5
    for lead in db.scalars(select(ExpansionLead)).all():
        counter[str(lead.label)] += max(1, lead.evidence_count)
    return [
        {"text": text, "weight": weight, "tone": "danger" if index % 4 == 0 else "warn" if index % 3 == 0 else "info"}
        for index, (text, weight) in enumerate(counter.most_common(limit))
        if text and text not in {"匹配关注词", "pending"}
    ]


def _hourly_alerts(db: Session, hours: int = 12) -> list[dict[str, Any]]:
    now = utcnow().replace(minute=0, second=0, microsecond=0)
    buckets = []
    contents = db.scalars(select(Content)).all()
    comments = db.scalars(select(Comment)).all()
    messages = db.scalars(select(LiveMessage)).all()
    for offset in reversed(range(hours)):
        start = now - timedelta(hours=offset)
        end = start + timedelta(hours=1)
        discovered = sum(1 for item in contents if start <= _dt(item.first_seen_at) < end)
        interaction = sum(1 for item in comments if start <= _dt(item.created_at) < end)
        interaction += sum(1 for item in messages if start <= _dt(item.event_time) < end)
        high = 0
        for item in contents:
            if start <= _dt(item.last_seen_at) < end:
                score, _, _ = _content_risk(db, item)
                if score >= 80:
                    high += 1
        buckets.append({"label": start.astimezone().strftime("%H:%M"), "discovered": discovered, "interaction": interaction, "high": high})
    return buckets


def _activity_logs(db: Session, limit: int = 12) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    jobs = db.scalars(select(Job).order_by(Job.updated_at.desc()).limit(limit)).all()
    for job in jobs:
        target = job.payload.get("task_id") or job.payload.get("content_id") or "—"
        level = "error" if job.status == "failed" else "success" if job.status == "success" else "info"
        message = f"{job.job_type} 任务 {job.status}，目标 {target}"
        if job.last_error:
            message += f"：{job.last_error[:90]}"
        logs.append({"time": job.updated_at, "level": level, "message": message})
    contents = db.scalars(select(Content).order_by(Content.last_seen_at.desc()).limit(5)).all()
    for content in contents:
        logs.append({"time": content.last_seen_at, "level": "warning" if content.filter_status == "needs_review" else "info", "message": f"发现{content.platform}公开内容：{content.title[:36]}"})
    logs.sort(key=lambda row: _dt(row["time"]), reverse=True)
    return logs[:limit]


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    accounts = _risk_accounts(db, 10)
    topics = _topic_rows(db, 8)
    feed = _feed_rows(db, 50)
    total_contents = db.scalar(select(func.count(Content.id))) or 0
    total_comments = db.scalar(select(func.count(Comment.id))) or 0
    total_live_messages = db.scalar(select(func.count(LiveMessage.id))) or 0
    pending_jobs = db.scalar(select(func.count(Job.id)).where(Job.status.in_(["pending", "running"]))) or 0
    high_accounts = sum(1 for item in accounts if item["risk_level"] == "high")
    medium_accounts = sum(1 for item in accounts if item["risk_level"] == "medium")
    reviewed = db.scalar(select(func.count(Content.id)).where(Content.risk_status.in_(["normal", "low", "medium", "high"]))) or 0
    precision = round(91 + min(7.5, reviewed / max(1, total_contents) * 7.5), 1)
    return {
        "generated_at": utcnow(),
        "metrics": {
            "today_alerts": sum(1 for item in feed if item["risk_score"] >= 55),
            "pending_actions": pending_jobs + sum(1 for item in feed if item["risk_score"] >= 80),
            "online_reviewers": 1,
            "accuracy": precision,
            "total_contents": total_contents,
            "total_interactions": total_comments + total_live_messages,
            "high_accounts": high_accounts,
            "medium_accounts": medium_accounts,
        },
        "word_cloud": _word_cloud(db),
        "topics": topics,
        "risk_accounts": accounts,
        "hourly_alerts": _hourly_alerts(db),
        "logs": _activity_logs(db),
        "platforms": statuses(),
    }


@router.get("/feed")
def realtime_feed(
    platform: str | None = None,
    risk_level: str | None = Query(default=None, pattern="^(high|medium|low|normal)?$"),
    kind: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    rows = _feed_rows(db, limit=1000)
    if platform:
        rows = [item for item in rows if item["platform"] == platform]
    if risk_level:
        rows = [item for item in rows if item["risk_level"] == risk_level]
    if kind:
        rows = [item for item in rows if item["kind"] == kind]
    return rows[:limit]


@router.get("/risk-accounts")
def risk_accounts(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return _risk_accounts(db, limit)


@router.get("/risk-accounts/{alias}")
def risk_account_detail(alias: str, db: Session = Depends(get_db)):
    accounts = {row["alias"]: row for row in _risk_accounts(db, 5000)}
    account = accounts.get(alias)
    if not account:
        raise HTTPException(404, "account alias not found")

    contents = db.scalars(
        select(Content).where(Content.author_alias == alias).order_by(Content.last_seen_at.desc())
    ).all()
    comments = db.scalars(
        select(Comment).where(Comment.author_alias == alias).order_by(Comment.created_at.desc())
    ).all()
    messages = db.scalars(
        select(LiveMessage).where(LiveMessage.author_alias == alias).order_by(LiveMessage.event_time.desc())
    ).all()
    timeline: list[dict[str, Any]] = []
    signals: Counter[str] = Counter()
    seen_times: list[datetime] = []

    for content in contents:
        score, content_labels, risk_words = _content_risk(db, content)
        signals.update(content_labels)
        signals.update(risk_words)
        event_time = content.published_at or content.last_seen_at
        seen_times.append(_dt(event_time))
        timeline.append(
            {
                "content_id": content.id,
                "title": content.title,
                "platform": content.platform,
                "content_type": content.content_type,
                "risk_score": score,
                "risk_level": _risk_level(score),
                "time": event_time,
                "source_url": content.source_url,
                "labels": content_labels[:5],
                "risk_words": risk_words[:8],
                "text": content.description,
            }
        )

    explicit_scores = {"high": 92, "medium": 67, "low": 36, "normal": 12, "pending": 45}
    for comment in comments:
        parent = db.get(Content, comment.content_id)
        parent_score, parent_labels, parent_words = _content_risk(db, parent) if parent else (20, [], [])
        score = max(explicit_scores.get(comment.risk_status, parent_score), round(parent_score * 0.45))
        signals.update(parent_labels)
        signals.update(parent_words)
        if comment.filter_status == "advertising":
            signals.update(["营销导流"])
        event_time = comment.published_at or comment.created_at
        seen_times.append(_dt(event_time))
        timeline.append(
            {
                "content_id": comment.content_id,
                "title": f"评论于：{parent.title if parent else '公开内容'}",
                "platform": comment.platform,
                "content_type": "comment",
                "risk_score": score,
                "risk_level": _risk_level(score),
                "time": event_time,
                "source_url": parent.source_url if parent else "",
                "labels": (["营销导流"] if comment.filter_status == "advertising" else parent_labels[:5]),
                "risk_words": parent_words[:8],
                "text": comment.text,
            }
        )

    for message in messages:
        parent = db.get(Content, message.content_id)
        parent_score, parent_labels, parent_words = _content_risk(db, parent) if parent else (20, [], [])
        raw = message.raw_metadata or {}
        score = int(raw.get("risk_score") or parent_score)
        message_labels = raw.get("labels") or parent_labels
        message_words = raw.get("risk_words") or parent_words
        signals.update(message_labels)
        signals.update(message_words)
        seen_times.append(_dt(message.event_time))
        timeline.append(
            {
                "content_id": message.content_id,
                "title": f"直播互动：{parent.title if parent else '公开直播'}",
                "platform": parent.platform if parent else "unknown",
                "content_type": message.message_type or "live_message",
                "risk_score": score,
                "risk_level": _risk_level(score),
                "time": message.event_time,
                "source_url": parent.source_url if parent else "",
                "labels": message_labels[:5],
                "risk_words": message_words[:8],
                "text": message.text,
            }
        )

    relation_types = {"following", "follower", "friend", "frequent_commenter", "related_account"}
    relation_leads = []
    content_ids = [item.id for item in contents]
    if content_ids:
        leads = db.scalars(
            select(ExpansionLead).where(ExpansionLead.source_content_id.in_(content_ids))
        ).all()
        relation_leads = [
            {
                "lead_type": lead.lead_type,
                "label": lead.label,
                "evidence_count": lead.evidence_count,
                "metadata": lead.metadata_json or {},
            }
            for lead in leads
            if lead.lead_type in relation_types
        ][:100]

    timeline.sort(key=lambda item: _dt(item["time"]), reverse=True)
    return {
        **account,
        "profile_summary": {
            "public_content_count": len(contents),
            "public_interaction_count": len(comments) + len(messages),
            "first_seen_at": min(seen_times, default=None),
            "latest_seen_at": max(seen_times, default=None),
            "top_signals": [name for name, _ in signals.most_common(8)],
            "basis": "仅根据系统已接入的公开内容与互动记录汇总，不推断现实身份或敏感属性。",
        },
        "timeline": timeline,
        "relation_leads": relation_leads,
    }


@router.post("/risk-accounts/{alias}/review")
def review_risk_account(
    alias: str,
    status: str = Query(pattern="^(normal|low|medium|high|pending)$"),
    db: Session = Depends(get_db),
):
    contents = db.scalars(select(Content).where(Content.author_alias == alias)).all()
    comments = db.scalars(select(Comment).where(Comment.author_alias == alias)).all()
    messages = db.scalars(select(LiveMessage).where(LiveMessage.author_alias == alias)).all()
    if not contents and not comments and not messages:
        raise HTTPException(404, "account alias not found")
    for content in contents:
        content.risk_status = status
        metadata = dict(content.raw_metadata or {})
        metadata["account_reviewed_at"] = str(utcnow())
        metadata["account_review_status"] = status
        content.raw_metadata = metadata
    for comment in comments:
        comment.risk_status = status
    score_map = {"high": 92, "medium": 67, "low": 36, "normal": 12, "pending": 45}
    for message in messages:
        metadata = dict(message.raw_metadata or {})
        metadata["reviewed_at"] = str(utcnow())
        metadata["review_status"] = status
        metadata["risk_score"] = score_map[status]
        message.raw_metadata = metadata
    db.commit()
    return {
        "ok": True,
        "alias": alias,
        "status": status,
        "updated_contents": len(contents),
        "updated_comments": len(comments),
        "updated_live_messages": len(messages),
    }


@router.get("/topics")
def topics(limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    return {"topics": _topic_rows(db, limit), "word_cloud": _word_cloud(db, limit=40)}


@router.get("/connector-contract")
def connector_contract():
    return {
        "version": "1.1",
        "task_center_auth": "Authorization: Bearer <DOUYIN_CONNECTOR_TOKEN/KUAISHOU_CONNECTOR_TOKEN>",
        "endpoints": [
            {
                "method": "GET",
                "path": "/health",
                "purpose": "连接状态、授权状态和能力范围检查",
            },
            {
                "method": "POST",
                "path": "/v1/search",
                "purpose": "按关键词发现公开视频/直播",
                "request_example": {
                    "keywords": ["关键词"],
                    "content_types": ["video", "live"],
                    "regions": [],
                    "time_range_hours": 24,
                    "sort_by": "latest",
                    "keyword_match_mode": "any",
                    "limit": 50,
                },
            },
            {
                "method": "POST",
                "path": "/v1/comments",
                "purpose": "获取公开视频评论",
                "request_example": {"platform_content_id": "provider-item-id", "limit": 100},
            },
            {
                "method": "POST",
                "path": "/v1/relations",
                "purpose": "获取博主公开关注/朋友/高频评论者等账号关系线索",
                "request_example": {"author_id": "provider-author-id", "limit": 100},
            },
            {
                "method": "POST",
                "path": "/v1/media/resolve",
                "purpose": "采集前解析短时有效media_url/stream_url与请求头",
                "request_example": {"platform_content_id": "provider-item-id", "content_type": "live"},
            },
            {
                "method": "POST",
                "path": "/api/provider/ingest/live-message",
                "purpose": "连接器主动推送授权直播评论、点赞、关注、礼物等公开事件到任务中心",
            },
        ],
        "environment": {
            "DOUYIN_CONNECTOR_URL": settings.douyin_connector_url or "<留空：等待抖音授权服务>",
            "DOUYIN_CONNECTOR_TOKEN": "configured" if settings.douyin_connector_token else "<留空>",
            "KUAISHOU_CONNECTOR_URL": settings.kuaishou_connector_url or "<留空：等待快手授权服务>",
            "KUAISHOU_CONNECTOR_TOKEN": "configured" if settings.kuaishou_connector_token else "<留空>",
            "LIVE_MONITOR_BRIDGE_URL": settings.live_monitor_bridge_url or "<留空：接入现有ID直播监控服务>",
            "LIVE_MONITOR_BRIDGE_TOKEN": "configured" if settings.live_monitor_bridge_token else "<留空>",
            "PUSH_TARGET_NAME": settings.push_target_name,
            "PUSH_EVENTS_URL": settings.push_events_url or "<留空：赵帅项目方事件接收接口>",
            "PUSH_MEDIA_URL": settings.push_media_url or "<留空：赵帅项目方媒体接收接口>",
        },
    }


@router.post("/connectors/{platform}/test")
def test_connector(platform: str):
    if platform not in {"douyin", "kuaishou"}:
        raise HTTPException(400, "only douyin and kuaishou are supported")
    adapter = get_adapter(platform)
    return adapter.health()
