from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.db.session import Base, engine
from app.db import models  # noqa: F401

Base.metadata.create_all(engine)
Path(settings.storage_root).mkdir(parents=True, exist_ok=True)
Path("./data/logs").mkdir(parents=True, exist_ok=True)

if settings.demo_provider_enabled and os.getenv("SKIP_DEMO_SEED", "0") != "1":
    runpy.run_path(str(Path(__file__).with_name("seed_demo.py")), run_name="__main__")
else:
    print("database initialized; demo seed skipped")
