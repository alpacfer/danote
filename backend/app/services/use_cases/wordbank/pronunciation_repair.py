from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.db.repositories import WordbankBackgroundJobRepository
from app.db.sqlite import get_connection


@dataclass(frozen=True, slots=True)
class QueuedPronunciationRepairSummary:
    lemma_count: int
    form_count: int
    enqueued_jobs: int
    unchanged_jobs: int
    queued_forms_by_lemma: dict[str, list[str]]


def find_missing_pronunciation_forms(db_path: Path) -> dict[str, list[str]]:
    queued_forms_by_lemma: dict[str, set[str]] = defaultdict(set)
    with get_connection(db_path, read_only=True) as conn:
        root_rows = conn.execute(
            """
            SELECT
                l.lemma,
                COUNT(
                    CASE
                        WHEN sf.meaning_id IS NULL AND sf.form = l.lemma THEN 1
                    END
                ) AS root_row_count,
                SUM(
                    CASE
                        WHEN sf.meaning_id IS NULL
                         AND sf.form = l.lemma
                         AND sf.pronunciation_audio IS NOT NULL THEN 1
                        ELSE 0
                    END
                ) AS root_audio_count
            FROM lexemes l
            LEFT JOIN surface_forms sf ON sf.lexeme_id = l.id
            GROUP BY l.id, l.lemma
            ORDER BY l.lemma ASC
            """
        ).fetchall()
        for row in root_rows:
            root_row_count = int(row["root_row_count"] or 0)
            root_audio_count = int(row["root_audio_count"] or 0)
            if root_row_count == 0 or root_audio_count == 0:
                queued_forms_by_lemma[str(row["lemma"])].add(str(row["lemma"]))

        surface_rows = conn.execute(
            """
            SELECT
                l.lemma,
                sf.form,
                COUNT(*) AS row_count,
                SUM(CASE WHEN sf.pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END) AS audio_count
            FROM surface_forms sf
            JOIN lexemes l ON l.id = sf.lexeme_id
            GROUP BY l.id, l.lemma, sf.form
            HAVING COUNT(*) > SUM(CASE WHEN sf.pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END)
            ORDER BY l.lemma ASC, sf.form ASC
            """
        ).fetchall()
        for row in surface_rows:
            queued_forms_by_lemma[str(row["lemma"])].add(str(row["form"]))

    return {
        lemma: sorted(forms)
        for lemma, forms in sorted(queued_forms_by_lemma.items())
        if forms
    }


def queue_missing_pronunciations(
    db_path: Path,
    *,
    dry_run: bool = False,
) -> QueuedPronunciationRepairSummary:
    queued_forms_by_lemma = find_missing_pronunciation_forms(db_path)
    if dry_run:
        return QueuedPronunciationRepairSummary(
            lemma_count=len(queued_forms_by_lemma),
            form_count=sum(len(forms) for forms in queued_forms_by_lemma.values()),
            enqueued_jobs=0,
            unchanged_jobs=0,
            queued_forms_by_lemma=queued_forms_by_lemma,
        )

    repository = WordbankBackgroundJobRepository(db_path)
    enqueued_jobs = 0
    unchanged_jobs = 0
    for lemma, forms in queued_forms_by_lemma.items():
        if repository.enqueue_pronunciation_job(
            stored_lemma=lemma,
            requested_forms=forms,
            force=False,
        ):
            enqueued_jobs += 1
        else:
            unchanged_jobs += 1
    return QueuedPronunciationRepairSummary(
        lemma_count=len(queued_forms_by_lemma),
        form_count=sum(len(forms) for forms in queued_forms_by_lemma.values()),
        enqueued_jobs=enqueued_jobs,
        unchanged_jobs=unchanged_jobs,
        queued_forms_by_lemma=queued_forms_by_lemma,
    )
