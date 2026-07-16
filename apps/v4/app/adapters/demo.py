from datetime import datetime, timezone
from app.adapters.base import PlatformAdapter, AdapterItem


class DemoAdapter(PlatformAdapter):
    name = "demo"

    def search(self, keywords, content_types, limit=20, **options):
        k = keywords[0] if keywords else "示例"
        regions = options.get("regions") or ["全国"]
        region_name = "雄安新区" if any(x in {"xiongan", "雄安新区"} for x in regions) or "雄安" in k else "河北省"
        items = []
        common = {
            "published_at": datetime.now(timezone.utc),
            "matched_keywords": [k],
        }
        if "video" in content_types:
            items += [
                AdapterItem(
                    platform="demo",
                    platform_content_id=f"video-event-{k}-{region_name}",
                    content_type="video",
                    title=f"{region_name}某项目工人反映{k}问题",
                    description="公开视频记录现场情况，包含事实陈述和多条公众评论，等待进一步核实。",
                    source_url="https://example.invalid/video/event",
                    author_id="demo-author-1",
                    metadata={
                        "region": region_name,
                        "hashtags": [k, region_name, "劳动权益"],
                        "engagement": {"comments": 182, "likes": 630},
                        "related_public_content": [
                            {"title": f"{region_name}同类项目情况说明", "url": "https://example.invalid/related/1"}
                        ],
                    },
                    **common,
                ),
                AdapterItem(
                    platform="demo",
                    platform_content_id=f"video-ad-{k}",
                    content_type="video",
                    title=f"{k}律师免费咨询",
                    description="点击头像私信，加微信，全国接单，成功后收费。",
                    source_url="https://example.invalid/video/ad",
                    author_id="demo-author-2",
                    metadata={
                        "region": "全国",
                        "hashtags": [k, "法律咨询"],
                        "engagement": {"comments": 17, "likes": 25},
                    },
                    **common,
                ),
                AdapterItem(
                    platform="demo",
                    platform_content_id=f"video-news-{k}",
                    content_type="video",
                    title=f"媒体核实：{k}事件后续进展",
                    description="新闻报道引用律师对劳动法规的解释，不含联系方式和咨询导流。",
                    source_url="https://example.invalid/video/news",
                    author_id="demo-news",
                    metadata={
                        "region": region_name,
                        "hashtags": [k, "情况通报"],
                        "engagement": {"comments": 68, "likes": 410},
                    },
                    **common,
                ),
            ]
        if "live" in content_types:
            items += [
                AdapterItem(
                    platform="demo",
                    platform_content_id=f"live-{k}-{region_name}",
                    content_type="live",
                    title=f"{region_name}{k}事件现场公开直播",
                    description="演示直播条目；真实环境需授权连接器提供直播地址和互动消息。",
                    source_url="https://example.invalid/live",
                    author_id="demo-live",
                    metadata={
                        "region": region_name,
                        "hashtags": [k, region_name, "现场直播"],
                        "engagement": {"viewers": 328, "comments": 96},
                    },
                    **common,
                )
            ]
        return items[:limit]

    def comments(self, platform_content_id, limit=100):
        return [
            {
                "platform_comment_id": f"{platform_content_id}-c1",
                "author_id": "viewer-1",
                "text": "希望尽快核实项目工资发放情况",
                "like_count": 27,
            },
            {
                "platform_comment_id": f"{platform_content_id}-c2",
                "author_id": "viewer-2",
                "text": "雄安新区相关部门是否已经发布情况说明",
                "like_count": 15,
            },
            {
                "platform_comment_id": f"{platform_content_id}-c3",
                "author_id": "ad-account",
                "text": "免费法律咨询，点击头像加微信，全国接单",
                "like_count": 0,
            },
        ][:limit]

    def relations(self, author_id: str, limit: int = 100):
        return [
            {
                "account_id": f"{author_id}-friend-1",
                "account_alias": "公开关联账号甲",
                "relation_type": "friend",
                "profile_url": "https://example.invalid/account/1",
                "evidence_count": 3,
                "metadata": {"demo": True},
            },
            {
                "account_id": f"{author_id}-commenter-1",
                "account_alias": "高频评论账号乙",
                "relation_type": "frequent_commenter",
                "profile_url": "https://example.invalid/account/2",
                "evidence_count": 6,
                "metadata": {"demo": True},
            },
        ][:limit]

