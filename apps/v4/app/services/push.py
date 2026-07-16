import httpx
from pathlib import Path
from app.core.config import settings
from app.utils import stable_hash

def _headers():
    return {"Authorization":f"Bearer {settings.push_bearer_token}"} if settings.push_bearer_token else {}

def push_event(payload:dict):
    if not settings.push_enabled or not settings.push_events_url: return {"status":"skipped","reason":"not configured"}
    with httpx.Client(timeout=settings.http_timeout_seconds) as c:
        r=c.post(settings.push_events_url,json=payload,headers=_headers()); r.raise_for_status(); data=r.json() if r.headers.get('content-type','').startswith('application/json') else {"text":r.text}
    return {"status":"success","payload_hash":stable_hash(payload),"response":data}

def push_media(content_id:int,path:Path):
    if not settings.push_enabled or not settings.push_media_url: return {"status":"skipped","reason":"not configured"}
    with path.open('rb') as f, httpx.Client(timeout=max(settings.http_timeout_seconds,300)) as c:
        r=c.post(settings.push_media_url,headers=_headers(),data={"content_id":str(content_id)},files={"file":(path.name,f,"video/mp4")});r.raise_for_status();data=r.json() if r.headers.get('content-type','').startswith('application/json') else {"text":r.text}
    return {"status":"success","response":data}
