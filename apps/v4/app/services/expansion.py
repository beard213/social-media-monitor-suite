from __future__ import annotations
import re
from collections import Counter
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.db.models import Content, ExpansionLead

STOPWORDS = {
    "希望", "尽快", "问题", "事情", "这个", "那个", "我们", "他们", "已经", "需要", "进行",
    "相关", "现场", "公开", "视频", "直播", "评论", "可以", "没有", "不是", "因为", "所以",
    "免费", "咨询", "点击", "头像", "微信", "全国", "接单",
}


def _terms(text: str) -> list[str]:
    chunks = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z0-9_-]{3,30}", text)
    return [x for x in chunks if x not in STOPWORDS and not x.isdigit()]


def build_expansion_leads(db: Session, content: Content) -> dict:
    """Create anonymized, content-level leads from comments/hashtags/related public content."""
    db.execute(
        delete(ExpansionLead).where(
            ExpansionLead.source_content_id == content.id,
            ExpansionLead.lead_type.in_(["comment_topic", "hashtag", "related_content"]),
        )
    )
    counter: Counter[str] = Counter()
    for comment in content.comments:
        if comment.filter_status != "advertising":
            counter.update(_terms(comment.text))
    for kw in content.matched_keywords or []:
        counter[kw] += 2

    created = 0
    for label, count in counter.most_common(12):
        if count < 1:
            continue
        db.add(
            ExpansionLead(
                source_content_id=content.id,
                lead_type="comment_topic",
                label=label,
                evidence_count=count,
                metadata_json={"scope": "public_content", "identity_tracking": False},
            )
        )
        created += 1

    metadata = content.raw_metadata or {}
    for tag in metadata.get("hashtags", [])[:10]:
        db.add(
            ExpansionLead(
                source_content_id=content.id,
                lead_type="hashtag",
                label=str(tag),
                evidence_count=1,
                metadata_json={"scope": "public_content", "identity_tracking": False},
            )
        )
        created += 1

    for item in metadata.get("related_public_content", [])[:20]:
        label = item.get("title") or item.get("url") or "关联公开内容"
        db.add(
            ExpansionLead(
                source_content_id=content.id,
                lead_type="related_content",
                label=str(label)[:300],
                evidence_count=1,
                metadata_json={
                    "url": item.get("url", ""),
                    "platform_content_id": item.get("platform_content_id", ""),
                    "scope": "public_content",
                    "identity_tracking": False,
                },
            )
        )
        created += 1

    for item in metadata.get("related_public_accounts", [])[:50]:
        label = item.get("account_alias") or item.get("account_id") or "关联公开账号"
        db.add(
            ExpansionLead(
                source_content_id=content.id,
                lead_type=item.get("relation_type", "related_account"),
                label=str(label)[:300],
                evidence_count=max(1, int(item.get("evidence_count") or 1)),
                metadata_json={
                    "profile_url": item.get("profile_url", ""),
                    "platform_account_id": item.get("account_id", ""),
                    "scope": "public_relation",
                    "identity_tracking": False,
                },
            )
        )
        created += 1
    db.commit()
    return {"created": created}


def list_leads(db: Session, content_id: int | None = None, status: str | None = None, limit: int = 200):
    q = select(ExpansionLead).order_by(ExpansionLead.created_at.desc()).limit(limit)
    if content_id:
        q = q.where(ExpansionLead.source_content_id == content_id)
    if status:
        q = q.where(ExpansionLead.status == status)
    return db.scalars(q).all()
