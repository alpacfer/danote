from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import load_settings
from app.db.migrations import apply_migrations
from app.db.seed import seed_starter_data


if __name__ == "__main__":
    settings = load_settings()
    applied = apply_migrations(settings.db_path)
    seeded = seed_starter_data(settings.db_path)

    print(
        json.dumps(
            {
                "db_path": str(settings.db_path),
                "applied_migrations": applied,
                **seeded,
            },
            ensure_ascii=True,
        )
    )
