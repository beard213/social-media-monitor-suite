from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.db.session import SessionLocal, Base, engine
from app.db.models import (
    AuditResult,
    Comment,
    Content,
    ExpansionLead,
    Job,
    LiveMessage,
    MonitorTask,
    TaskProfile,
)
from app.utils import hash_id, utcnow

Base.metadata.create_all(engine)
now = utcnow()

content_specs = [
    {
        "pid": "demo-live-001", "type": "live", "title": "演示直播：项目现场公开情况说明", "author": "账号_红帆01",
        "desc": "演示数据：直播间围绕项目情况、工资发放和现场处置进行公开讨论。", "keywords": ["项目情况", "劳动权益"],
        "risk": "high", "score": .92, "eng": {"viewers": 3240, "comments": 620, "likes": 5100, "shares": 340},
        "labels": ["煽动对立", "传播谣言"], "words": ["大家一起", "不要相信", "转发"],
    },
    {
        "pid": "demo-live-002", "type": "live", "title": "演示直播：历史事件重新解读", "author": "账号_夜行者07",
        "desc": "演示数据：主播对历史资料进行片面解读并引发大量争议评论。", "keywords": ["历史事件", "争议解读"],
        "risk": "high", "score": .88, "eng": {"viewers": 1890, "comments": 390, "likes": 2880, "shares": 170},
        "labels": ["历史虚无", "误导性表达"], "words": ["历史证明", "都是假的"],
    },
    {
        "pid": "demo-video-003", "type": "video", "title": "演示短视频：境外信息搬运与评论引导", "author": "账号_风中追风",
        "desc": "演示数据：搬运未经核实的信息，并通过标题制造对立情绪。", "keywords": ["境外信息", "评论引导"],
        "risk": "medium", "score": .74, "eng": {"views": 85000, "comments": 710, "likes": 3600, "shares": 890},
        "labels": ["境外叙事", "情绪引导"], "words": ["上面根本不管", "看不到的"],
    },
    {
        "pid": "demo-video-004", "type": "video", "title": "演示短视频：热点事件断章取义", "author": "账号_自由之声",
        "desc": "演示数据：对公开通报片段进行剪辑，未提供完整上下文。", "keywords": ["热点事件", "断章取义"],
        "risk": "medium", "score": .69, "eng": {"views": 126000, "comments": 980, "likes": 7200, "shares": 960},
        "labels": ["传播误导信息", "断章取义"], "words": ["翻出去看看", "这里看不到"],
    },
    {
        "pid": "demo-video-005", "type": "video", "title": "演示短视频：公共事件正常新闻报道", "author": "账号_公开报道",
        "desc": "演示数据：新闻报道引用公开通报，陈述克制，来源明确。", "keywords": ["公共事件", "情况通报"],
        "risk": "normal", "score": .12, "eng": {"views": 52000, "comments": 120, "likes": 1800, "shares": 90},
        "labels": ["来源明确"], "words": [],
    },
    {
        "pid": "demo-video-006", "type": "video", "title": "演示广告：免费咨询点击头像私信", "author": "账号_咨询推广",
        "desc": "演示数据：免费法律咨询，加微信，全国接单，成功后收费。", "keywords": ["劳动权益"],
        "risk": "low", "score": .35, "eng": {"views": 11000, "comments": 18, "likes": 44, "shares": 2},
        "labels": ["营销导流"], "words": ["加微信", "免费咨询"], "filter": "advertising",
    },
    {
        "pid": "demo-video-007", "type": "video", "title": "演示短视频：项目劳动权益事件后续", "author": "账号_现场记录",
        "desc": "演示数据：公开记录项目方与劳动者沟通进展，信息仍待核实。", "keywords": ["劳动权益", "项目欠薪"],
        "risk": "low", "score": .42, "eng": {"views": 38000, "comments": 230, "likes": 960, "shares": 110},
        "labels": ["事实待核实"], "words": ["拖欠工资"],
    },
    {
        "pid": "demo-live-008", "type": "live", "title": "演示直播：公开政策答疑", "author": "账号_政策答疑",
        "desc": "演示数据：基于公开政策文件回答网友问题。", "keywords": ["政策答疑"],
        "risk": "normal", "score": .08, "eng": {"viewers": 890, "comments": 150, "likes": 920, "shares": 25},
        "labels": ["正常讨论"], "words": [],
    },
]

comment_texts = [
    ("大家一定要看清事实，不要只看剪辑片段", "medium", ["看清事实"]),
    ("建议等待正式通报，不要传播未经核实的信息", "normal", []),
    ("他们就是故意隐瞒真相，大家转发让更多人知道", "high", ["隐瞒真相", "转发"]),
    ("历史证明这些说法都是假的", "high", ["历史证明", "都是假的"]),
    ("这事和之前一样，上面根本不管", "medium", ["上面根本不管"]),
    ("翻出去看看真相吧，这里有很多看不到的", "medium", ["翻出去", "看不到的"]),
    ("免费咨询，点击头像加微信，全国接单", "low", ["加微信", "免费咨询"]),
    ("请问有没有完整视频和公开来源？", "normal", []),
]

with SessionLocal() as db:
    task = db.scalar(select(MonitorTask).where(MonitorTask.name == "演示：公开内容综合监测"))
    if not task:
        task = MonitorTask(
            name="演示：公开内容综合监测",
            platforms=["demo"],
            content_types=["video", "live"],
            include_keywords=["劳动权益", "热点事件", "历史事件", "境外信息"],
            exclude_keywords=["招聘", "剧情演绎", "影视剪辑"],
            interval_seconds=300,
            enabled=True,
            next_run_at=now,
        )
        task.profile = TaskProfile(
            topic_template="public_opinion",
            regions=[],
            keyword_match_mode="any",
            time_range_hours=72,
            sort_by="hot",
            result_limit=100,
            collect_comments=True,
            expand_related=True,
            auto_audit=True,
            auto_capture=False,
            auto_push=False,
            push_after_review=True,
            notes="内置演示任务。所有内容均为虚构，用于验证前后端和任务流程。",
        )
        db.add(task)
        db.flush()

    for index, spec in enumerate(content_specs):
        content = db.scalar(select(Content).where(Content.platform == "demo", Content.platform_content_id == spec["pid"]))
        if not content:
            content = Content(platform="demo", platform_content_id=spec["pid"], content_type=spec["type"])
            db.add(content)
        content.title = spec["title"]
        content.description = spec["desc"]
        content.source_url = f"https://example.invalid/{spec['pid']}"
        content.author_alias = spec["author"]
        content.published_at = now - timedelta(minutes=index * 11 + 3)
        content.first_seen_at = now - timedelta(minutes=index * 10 + 2)
        content.last_seen_at = now - timedelta(minutes=index * 3)
        content.matched_keywords = spec["keywords"]
        content.filter_status = spec.get("filter", "kept" if spec["risk"] in {"normal", "low"} else "needs_review")
        content.filter_score = spec["score"]
        content.filter_reasons = ["演示检测结果", *spec["words"]]
        content.risk_status = spec["risk"]
        content.raw_metadata = {
            "task_id": task.id,
            "task_name": task.name,
            "topic_template": "public_opinion",
            "region_tags": ["全国"],
            "hashtags": spec["keywords"],
            "engagement": spec["eng"],
            "demo": True,
        }
        db.flush()

        audit = db.scalar(select(AuditResult).where(AuditResult.content_id == content.id, AuditResult.modality == "text"))
        if not audit:
            audit = AuditResult(content_id=content.id, modality="text")
            db.add(audit)
        audit.detector_name = "demo-risk-detector"
        audit.detector_version = "3.0-demo"
        audit.status = spec["risk"]
        audit.labels = spec["labels"]
        audit.risk_words = spec["words"]
        audit.confidence = spec["score"]
        audit.response = {"demo": True, "explanation": "用于界面和工作流测试的虚构检测结果"}

        lead = db.scalar(select(ExpansionLead).where(ExpansionLead.source_content_id == content.id, ExpansionLead.label == spec["keywords"][0]))
        if not lead:
            db.add(ExpansionLead(source_content_id=content.id, lead_type="topic", label=spec["keywords"][0], evidence_count=index + 2, status="new" if spec["risk"] != "normal" else "reviewed", metadata_json={"demo": True}))

        for cidx, (text, risk, words) in enumerate(comment_texts[: 5 + (index % 4)]):
            cid = f"{spec['pid']}-comment-{cidx}"
            if db.scalar(select(Comment).where(Comment.platform == "demo", Comment.platform_comment_id_hash == hash_id(cid))):
                continue
            db.add(Comment(
                content_id=content.id,
                platform="demo",
                platform_comment_id_hash=hash_id(cid),
                author_alias=f"评论用户_{index+1:02d}{cidx+1:02d}",
                text=text,
                like_count=(index + 1) * (cidx + 2),
                published_at=now - timedelta(minutes=index * 5 + cidx),
                filter_status="advertising" if "加微信" in text else "kept",
                risk_status=risk,
                created_at=now - timedelta(minutes=index * 5 + cidx),
            ))

        if spec["type"] == "live":
            for midx, (text, risk, words) in enumerate(comment_texts):
                exists = db.scalar(select(LiveMessage).where(LiveMessage.content_id == content.id, LiveMessage.text == text))
                if exists:
                    continue
                db.add(LiveMessage(
                    content_id=content.id,
                    message_type="comment" if midx % 3 else "live_message",
                    author_alias=f"弹幕用户_{index+1:02d}{midx+1:02d}",
                    text=text,
                    event_time=now - timedelta(seconds=index * 60 + midx * 19),
                    raw_metadata={"demo": True, "risk_score": {"high": 92, "medium": 68, "low": 35, "normal": 12}[risk], "labels": spec["labels"], "risk_words": words},
                ))

    existing_job = db.scalar(select(Job).where(Job.payload["demo"].as_boolean() == True)) if db.bind.dialect.name == "postgresql" else None
    if not existing_job and db.scalar(select(Job).limit(1)) is None:
        db.add_all([
            Job(job_type="discovery", status="success", payload={"task_id": task.id, "demo": True}, attempts=1, updated_at=now - timedelta(minutes=3)),
            Job(job_type="comments", status="success", payload={"content_id": 1, "demo": True}, attempts=1, updated_at=now - timedelta(minutes=2)),
            Job(job_type="audit_text", status="success", payload={"content_id": 2, "demo": True}, attempts=1, updated_at=now - timedelta(minutes=1)),
        ])

    db.commit()
    print("rich demo data ready")
