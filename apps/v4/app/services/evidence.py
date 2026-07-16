from pathlib import Path
from sqlalchemy.orm import Session
from app.db.models import EvidenceFile
from app.utils import sha256_file

def register_file(db:Session, content_id:int, file_type:str, path:Path, source_url="", history=None):
    obj=EvidenceFile(content_id=content_id,file_type=file_type,file_path=str(path),sha256=sha256_file(path),source_url=source_url,processing_history=history or [])
    db.add(obj); db.commit(); db.refresh(obj); return obj
