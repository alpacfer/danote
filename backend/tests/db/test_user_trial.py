from __future__ import annotations

from app.db.migrations import apply_migrations
from app.db.repositories.user_trial import UserTrialRepository

_USER = 1  # seeded local user from migration 027


def _repo(tmp_path) -> UserTrialRepository:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    return UserTrialRepository(db_path)


def test_opt_in_is_idempotent(tmp_path) -> None:
    repo = _repo(tmp_path)
    assert repo.is_opted_in(user_id=_USER) is False

    repo.opt_in(user_id=_USER)
    assert repo.is_opted_in(user_id=_USER) is True

    # Calling again must not raise and must stay opted in.
    repo.opt_in(user_id=_USER)
    assert repo.is_opted_in(user_id=_USER) is True


def test_reserve_counts_distinct_words_and_repeats_are_free(tmp_path) -> None:
    repo = _repo(tmp_path)

    first = repo.reserve(user_id=_USER, usage_date="2026-05-18", query_key="hus", limit=2)
    assert first.allowed is True
    assert first.used == 1

    # Same word again the same day is free and does not increment.
    repeat = repo.reserve(user_id=_USER, usage_date="2026-05-18", query_key="hus", limit=2)
    assert repeat.allowed is True
    assert repeat.used == 1

    second = repo.reserve(user_id=_USER, usage_date="2026-05-18", query_key="bil", limit=2)
    assert second.allowed is True
    assert second.used == 2

    assert repo.count_for_day(user_id=_USER, usage_date="2026-05-18") == 2


def test_reserve_blocks_new_word_at_limit(tmp_path) -> None:
    repo = _repo(tmp_path)
    repo.reserve(user_id=_USER, usage_date="2026-05-18", query_key="a", limit=1)

    blocked = repo.reserve(user_id=_USER, usage_date="2026-05-18", query_key="b", limit=1)
    assert blocked.allowed is False
    assert blocked.used == 1
    assert blocked.limit == 1

    # An already-counted word still works even once the cap is hit.
    repeat = repo.reserve(user_id=_USER, usage_date="2026-05-18", query_key="a", limit=1)
    assert repeat.allowed is True


def test_usage_resets_on_a_new_day(tmp_path) -> None:
    repo = _repo(tmp_path)
    repo.reserve(user_id=_USER, usage_date="2026-05-18", query_key="a", limit=1)

    blocked = repo.reserve(user_id=_USER, usage_date="2026-05-18", query_key="b", limit=1)
    assert blocked.allowed is False

    next_day = repo.reserve(user_id=_USER, usage_date="2026-05-19", query_key="b", limit=1)
    assert next_day.allowed is True
    assert next_day.used == 1
    assert repo.count_for_day(user_id=_USER, usage_date="2026-05-18") == 1
