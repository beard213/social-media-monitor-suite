from __future__ import annotations
import httpx
from pathlib import Path
from typing import Any
from app.core.config import settings

def _walk(obj):
    if isinstance(obj,dict):
        for k,v in obj.items(): yield k,v; yield from _walk(v)
    elif isinstance(obj,list):
        for v in obj: yield from _walk(v)

def normalize_response(raw:dict[str,Any]):
    status="unknown"; labels=[]; words=[]; confidence=None
    for k,v in _walk(raw):
        if k in {"content_category","suggestion","conclusion","status","risk_level"}:
            s=str(v).lower()
            if str(v) in {"合规","疑似","违规"}: status=str(v)
            elif s in {"pass","safe","normal","allow"}: status="合规"
            elif s in {"review","suspect","warning"}: status="疑似"
            elif s in {"block","reject","illegal","risk"}: status="违规"
        if k in {"label","category","risk_label","type"} and isinstance(v,str) and v not in labels: labels.append(v)
        if k in {"risk_words","keywords","risk_word"}:
            vals=v if isinstance(v,list) else [v]
            for x in vals:
                x=str(x)
                if x and x not in words: words.append(x)
        if k in {"confidence","score","probability"} and isinstance(v,(int,float)): confidence=max(confidence or 0,float(v))
    return {"status":status,"labels":labels,"risk_words":words,"confidence":confidence,"response":raw}

class DetectorClient:
    def health(self):
        if not settings.detector_enabled: return {"enabled":False,"ok":False,"message":"检测服务未启用"}
        try:
            with httpx.Client(timeout=10) as c:
                r=c.get(settings.detector_base_url.rstrip('/')+"/health")
                return {"enabled":True,"ok":r.is_success,"status_code":r.status_code}
        except Exception as e: return {"enabled":True,"ok":False,"error":str(e)}
    def text(self, text:str):
        if not settings.detector_enabled: return {"status":"skipped","labels":[],"risk_words":[],"confidence":None,"response":{"reason":"disabled"}}
        with httpx.Client(timeout=settings.http_timeout_seconds) as c:
            r=c.post(settings.detector_base_url.rstrip('/')+"/api/v1/detect/text",json={"content":text}); r.raise_for_status(); return normalize_response(r.json())
    def file(self, modality:str, path:Path):
        if not settings.detector_enabled: return {"status":"skipped","labels":[],"risk_words":[],"confidence":None,"response":{"reason":"disabled"}}
        with path.open('rb') as f, httpx.Client(timeout=max(settings.http_timeout_seconds,300)) as c:
            r=c.post(settings.detector_base_url.rstrip('/')+f"/api/v1/detect/{modality}",files={"file":(path.name,f,"application/octet-stream")}); r.raise_for_status(); return normalize_response(r.json())

detector=DetectorClient()
