from app.core.config import settings
from app.adapters.demo import DemoAdapter
from app.adapters.http_authorized import AuthorizedHTTPAdapter


def get_adapter(name: str):
    if name == "demo" and settings.demo_provider_enabled:
        return DemoAdapter()
    if name == "douyin":
        return AuthorizedHTTPAdapter(
            "douyin",
            settings.douyin_connector_url,
            settings.douyin_connector_token,
            settings.http_timeout_seconds,
        )
    if name == "kuaishou":
        return AuthorizedHTTPAdapter(
            "kuaishou",
            settings.kuaishou_connector_url,
            settings.kuaishou_connector_token,
            settings.http_timeout_seconds,
        )
    raise KeyError(f"unknown or disabled platform: {name}")


def _authorized_status(name: str, url: str, token: str) -> dict:
    return {
        "enabled": bool(url),
        "configured": bool(url),
        "mode": "authorized-http",
        "base_url": url or "",
        "token_configured": bool(token),
        "required_endpoints": [
            "GET /health",
            "POST /v1/search",
            "POST /v1/comments",
            "POST /v1/media/resolve",
            "POST /v1/relations",
        ],
    }


def statuses():
    return {
        "demo": {
            "enabled": settings.demo_provider_enabled,
            "configured": settings.demo_provider_enabled,
            "mode": "built-in-demo",
            "base_url": "built-in",
            "token_configured": True,
            "required_endpoints": [],
        },
        "douyin": _authorized_status(
            "douyin", settings.douyin_connector_url, settings.douyin_connector_token
        ),
        "kuaishou": _authorized_status(
            "kuaishou", settings.kuaishou_connector_url, settings.kuaishou_connector_token
        ),
    }
