import sys
from pathlib import Path
import shutil
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.adapters.registry import statuses
from app.services.detector import detector

print(
    json.dumps(
        {
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "database": settings.database_url,
            "storage": str(settings.storage_root),
            "platforms": statuses(),
            "detector": detector.health(),
        },
        ensure_ascii=False,
        indent=2,
    )
)
