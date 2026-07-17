import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "Documents" / "Codex" / "danote" / "backend"))

from app.db.migrations import apply_migrations, get_connection
from app.services.typo.typo_engine import TypoEngine, _load_decision_thresholds
from app.services.typo.candidates import CandidateProvider
from app.services.typo.ranking import rank_candidates
from app.services.typo.decision import decide_status

db_path = Path("/tmp/debug_typo.sqlite3")
if db_path.exists():
    db_path.unlink()

apply_migrations(db_path)
with get_connection(db_path) as conn:
    for lemma in ["bog", "spise", "sensor"]:
        conn.execute(
            "INSERT OR IGNORE INTO lexemes (lemma, source) VALUES (?, 'manual')",
            (lemma.lower(),),
        )

dictionary_path = Path("/tmp/debug_da_words.txt")
dictionary_path.write_text("\n".join(["bog", "spise", "spiser", "sensor"]) + "\n", encoding="utf-8")

engine = TypoEngine(db_path=db_path, dictionary_path=dictionary_path)
result = engine.classify_unknown(token="spisrr")

print("Status:", result.status)
print("Confidence:", result.confidence)
print("Reason tags:", result.reason_tags)
print("Suggestions:")
for sug in result.suggestions:
    print(f"  {sug.value}: score={sug.score}, source_flags={sug.source_flags}")

print("\nDetail candidates:")
forms = engine.candidates.suggest("spisrr")
ranked = rank_candidates(token="spisrr", candidates=forms, known_lemmas={"bog", "spise", "sensor"})
for item in ranked:
    print(f"  {item.value}: score={item.score}, distance={item.distance}, prior_score={item.prior_score}, error_likelihood={item.error_likelihood}")
