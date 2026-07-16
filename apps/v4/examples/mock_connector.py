import os
from datetime import datetime, timezone
from fastapi import FastAPI
from pydantic import BaseModel

platform = os.getenv("MOCK_PLATFORM", "douyin")
app = FastAPI(title=f"{platform} authorized connector mock")


class Search(BaseModel):
    keywords: list[str]
    content_types: list[str]
    limit: int = 20
    regions: list[str] = []
    time_range_hours: int = 24
    sort_by: str = "latest"
    keyword_match_mode: str = "any"


class Comments(BaseModel):
    platform_content_id: str
    limit: int = 100


@app.get("/health")
def health():
    return {"ok": True, "platform": platform, "mock": True}


@app.post("/v1/search")
def search(body: Search):
    keyword = body.keywords[0] if body.keywords else "示例"
    region = "雄安新区" if any(x in {"xiongan", "雄安新区"} for x in body.regions) else "河北省"
    now = datetime.now(timezone.utc).isoformat()
    common_metadata = {
        "mock": True,
        "region": region,
        "hashtags": [keyword, region],
        "search_echo": {
            "regions": body.regions,
            "time_range_hours": body.time_range_hours,
            "sort_by": body.sort_by,
            "keyword_match_mode": body.keyword_match_mode,
        },
    }
    items = []
    if "video" in body.content_types:
        items += [
            {
                "platform_content_id": f"{platform}-event-{keyword}-{region}",
                "content_type": "video",
                "title": f"{platform} {region}某项目工人反映{keyword}问题",
                "description": "公开事实陈述，等待进一步核实",
                "source_url": f"https://example.invalid/{platform}/event",
                "media_url": "",
                "stream_url": "",
                "cover_url": "",
                "author_id": f"{platform}-author-1",
                "published_at": now,
                "matched_keywords": [keyword],
                "metadata": {
                    **common_metadata,
                    "engagement": {"comments": 103, "likes": 420},
                    "related_public_content": [
                        {"title": f"{region}同类公开情况说明", "url": "https://example.invalid/related/1"}
                    ],
                },
            },
            {
                "platform_content_id": f"{platform}-ad-{keyword}",
                "content_type": "video",
                "title": f"{keyword}律师免费咨询",
                "description": "点击头像私信，加微信，全国接单，成功后收费",
                "source_url": f"https://example.invalid/{platform}/ad",
                "media_url": "",
                "stream_url": "",
                "cover_url": "",
                "author_id": f"{platform}-author-ad",
                "published_at": now,
                "matched_keywords": [keyword],
                "metadata": {**common_metadata, "region": "全国", "engagement": {"comments": 8, "likes": 14}},
            },
        ]
    if "live" in body.content_types:
        items.append(
            {
                "platform_content_id": f"{platform}-live-{keyword}-{region}",
                "content_type": "live",
                "title": f"{platform} {region}{keyword}公开直播",
                "description": "模拟授权直播发现结果",
                "source_url": f"https://example.invalid/{platform}/live",
                "media_url": "",
                "stream_url": "",
                "cover_url": "",
                "author_id": f"{platform}-live-author",
                "published_at": now,
                "matched_keywords": [keyword],
                "metadata": {**common_metadata, "engagement": {"viewers": 256, "comments": 81}},
            }
        )
    return {"items": items[: body.limit]}


@app.post("/v1/comments")
def comments(body: Comments):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "comments": [
            {
                "platform_comment_id": body.platform_content_id + "-1",
                "author_id": "viewer-a",
                "text": "希望有关方面核实项目工资发放情况",
                "like_count": 19,
                "published_at": now,
            },
            {
                "platform_comment_id": body.platform_content_id + "-2",
                "author_id": "viewer-b",
                "text": "雄安新区是否已经发布相关情况说明",
                "like_count": 11,
                "published_at": now,
            },
            {
                "platform_comment_id": body.platform_content_id + "-3",
                "author_id": "ad-a",
                "text": "免费咨询，点击头像加微信，全国接单",
                "like_count": 0,
                "published_at": now,
            },
        ][: body.limit]
    }
