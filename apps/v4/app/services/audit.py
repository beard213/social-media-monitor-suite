from pathlib import Path
from sqlalchemy.orm import Session
from app.db.models import Content, AuditResult
from app.services.detector import detector

def save_result(db, content_id, modality, result):
    obj=AuditResult(content_id=content_id,modality=modality,status=result.get('status','unknown'),labels=result.get('labels',[]),risk_words=result.get('risk_words',[]),confidence=result.get('confidence'),response=result.get('response',{}))
    db.add(obj); db.commit(); return obj

def audit_text(db:Session, content:Content, text:str, modality='text'):
    return save_result(db,content.id,modality,detector.text(text))

def audit_file(db:Session, content:Content, modality:str, path:Path):
    return save_result(db,content.id,modality,detector.file(modality,path))

def merge_status(statuses):
    if '违规' in statuses: return '违规'
    if '疑似' in statuses: return '疑似'
    if '合规' in statuses: return '合规'
    if 'skipped' in statuses: return 'skipped'
    return 'unknown'
