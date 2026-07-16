from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from connector_service.drivers import DouyinDriver, KuaishouDriver
from connector_service.drivers.base import ProviderNotConfigured
from connector_service.models import (
    CommentsRequest,
    CommentsResponse,
    ResolveMediaRequest,
    ResolveMediaResponse,
    RelationsRequest,
    RelationsResponse,
    SearchRequest,
    SearchResponse,
)

PLATFORM = os.getenv("CONNECTOR_PLATFORM", "douyin").strip().lower()
INTERNAL_TOKEN = os.getenv("CONNECTOR_INTERNAL_TOKEN", "")

driver = DouyinDriver() if PLATFORM == "douyin" else KuaishouDriver() if PLATFORM == "kuaishou" else None
if driver is None:
    raise RuntimeError("CONNECTOR_PLATFORM must be douyin or kuaishou")

app = FastAPI(
    title=f"{PLATFORM} authorized connector",
    version="1.0.0",
    description="Authorized provider integration boundary for the social-media monitor task center.",
)


def authorize(authorization: str | None = Header(default=None)):
    if not INTERNAL_TOKEN:
        return
    if authorization != f"Bearer {INTERNAL_TOKEN}":
        raise HTTPException(401, "invalid connector token")


@app.exception_handler(ProviderNotConfigured)
def provider_not_configured(_, exc: ProviderNotConfigured):
    return JSONResponse(status_code=501, content={"detail": str(exc), "platform": PLATFORM})


@app.get("/health")
def health(_: None = Depends(authorize)):
    return driver.health()


@app.post("/v1/search", response_model=SearchResponse)
def search(body: SearchRequest, _: None = Depends(authorize)):
    return driver.search(body)


@app.post("/v1/comments", response_model=CommentsResponse)
def comments(body: CommentsRequest, _: None = Depends(authorize)):
    return driver.comments(body)


@app.post("/v1/media/resolve", response_model=ResolveMediaResponse)
def resolve_media(body: ResolveMediaRequest, _: None = Depends(authorize)):
    return driver.resolve_media(body)


@app.post("/v1/relations", response_model=RelationsResponse)
def relations(body: RelationsRequest, _: None = Depends(authorize)):
    return driver.relations(body)
