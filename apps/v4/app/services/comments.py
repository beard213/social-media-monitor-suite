from sqlalchemy import select
from sqlalchemy.orm import Session
from app.adapters.registry import get_adapter
from app.db.models import Content, Comment
from app.services.filtering import content_filter
from app.utils import anonymize, hash_id


def fetch_comments(db: Session, content: Content, limit: int = 100):
    rows = get_adapter(content.platform).comments(content.platform_content_id, limit)
    created = 0
    advertising = 0
    for item in rows:
        raw_id = str(item.get("platform_comment_id") or f"{content.platform_content_id}:{item.get('text', '')}")
        hashed = hash_id(raw_id)
        if db.scalar(
            select(Comment).where(
                Comment.platform == content.platform,
                Comment.platform_comment_id_hash == hashed,
            )
        ):
            continue
        result = content_filter.evaluate(item.get("text", ""), [], [])
        if result["status"] == "advertising":
            advertising += 1
        db.add(
            Comment(
                content_id=content.id,
                platform=content.platform,
                platform_comment_id_hash=hashed,
                author_alias=anonymize(str(item.get("author_id", ""))),
                text=item.get("text", ""),
                like_count=int(item.get("like_count", 0) or 0),
                published_at=item.get("published_at"),
                filter_status=result["status"],
            )
        )
        created += 1
    metadata = dict(content.raw_metadata or {})
    metadata["comments_collected"] = True
    metadata["comment_count_collected"] = len(content.comments) + created
    metadata["pipeline_stage"] = "comments_collected"
    content.raw_metadata = metadata
    db.commit()
    return {"received": len(rows), "created": created, "advertising": advertising}
