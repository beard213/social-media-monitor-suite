from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from typing import Any
from app.core.config import settings

def utcnow(): return datetime.now(timezone.utc)

def anonymize(value: str, prefix="user") -> str:
    raw = f"{settings.anonymization_salt}:{value or 'anonymous'}".encode()
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:12]}"

def hash_id(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def sha256_file(path) -> str:
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def stable_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
