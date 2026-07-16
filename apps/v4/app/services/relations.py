from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.adapters.registry import get_adapter
from app.db.models import Content, ExpansionLead

RELATION_TYPES = {"following", "follower", "friend", "frequent_commenter", "related_account"}


def fetch_public_relations(db: Session, content: Content, limit: int = 100) -> dict:
    """Fetch public account-relation leads through the authorized connector.

    Only public platform identifiers/aliases and evidence links are retained.
    The task center does not infer real-world identity, political affiliation,
    or other sensitive personal attributes from the relation graph.
    """

    metadata = dict(content.raw_metadata or {})
    author_ref = str(metadata.get("provider_author_ref") or "").strip()
    if not author_ref:
        return {"received": 0, "created": 0, "reason": "provider_author_ref missing"}

    rows = get_adapter(content.platform).relations(author_ref, limit=limit)
    db.execute(
        delete(ExpansionLead).where(
            ExpansionLead.source_content_id == content.id,
            ExpansionLead.lead_type.in_(sorted(RELATION_TYPES)),
        )
    )

    created = 0
    for item in rows:
        relation_type = str(item.get("relation_type") or "related_account")
        if relation_type not in RELATION_TYPES:
            relation_type = "related_account"
        alias = str(item.get("account_alias") or item.get("account_id") or "公开关联账号")[:300]
        db.add(
            ExpansionLead(
                source_content_id=content.id,
                lead_type=relation_type,
                label=alias,
                evidence_count=max(1, int(item.get("evidence_count") or 1)),
                metadata_json={
                    "platform_account_id": item.get("account_id", ""),
                    "profile_url": item.get("profile_url", ""),
                    "relation_type": relation_type,
                    "source": item.get("source", "authorized_connector"),
                    "scope": "public_relation",
                    "identity_tracking": False,
                    **(item.get("metadata") or {}),
                },
            )
        )
        created += 1

    metadata["public_relations_collected"] = True
    metadata["public_relation_count"] = created
    content.raw_metadata = metadata
    db.commit()
    return {"received": len(rows), "created": created}
