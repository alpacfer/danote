from __future__ import annotations

from pathlib import Path

from app.db.sqlite import get_connection

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations(db_path: Path) -> list[str]:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    applied_now: list[str] = []
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
            )
            """
        )

        applied_versions = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = migration_file.name
            if version in applied_versions:
                continue

            conn.executescript(migration_file.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,),
            )
            applied_now.append(version)

    return applied_now
