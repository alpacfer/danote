from __future__ import annotations

from dataclasses import dataclass, replace

from app.core.config import Settings
from app.db.migrations import apply_migrations
from app.db.repositories.user_api_keys import SUPPORTED_PROVIDERS
from app.db.repositories.user_trial import UserTrialRepository
from app.services.use_cases.trial import TrialUseCase

_USER = 1


@dataclass(frozen=True)
class _Meta:
    is_set: bool


class _FakeKeysRepo:
    def __init__(self, *, all_set: bool) -> None:
        self._all_set = all_set

    def status(self, *, user_id: int):
        return {p: _Meta(is_set=self._all_set) for p in SUPPORTED_PROVIDERS}


def _settings(db_path, **overrides) -> Settings:
    base = Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model="retired-dacy-disabled",
        gemini_api_key="host-key",
    )
    return replace(base, **overrides)


def _use_case(tmp_path, *, keys_all_set=False, **setting_overrides) -> TrialUseCase:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    return TrialUseCase(
        settings=_settings(db_path, **setting_overrides),
        trial_repository=UserTrialRepository(db_path),
        api_keys_repository=_FakeKeysRepo(all_set=keys_all_set),
    )


def test_distinct_words_allowed_then_blocked_at_limit(tmp_path) -> None:
    uc = _use_case(tmp_path, trial_daily_search_limit=2)

    a = uc.check_and_consume(_USER, "house")
    assert a.allowed and a.metered and a.used == 1

    b = uc.check_and_consume(_USER, "car")
    assert b.allowed and b.used == 2

    blocked = uc.check_and_consume(_USER, "tree")
    assert blocked.allowed is False
    assert blocked.used == 2


def test_repeat_word_is_free_and_normalized(tmp_path) -> None:
    uc = _use_case(tmp_path, trial_daily_search_limit=1)

    first = uc.check_and_consume(_USER, "House")
    assert first.allowed and first.used == 1

    # Different casing / surrounding whitespace is the same word.
    repeat = uc.check_and_consume(_USER, "  house ")
    assert repeat.allowed is True

    blocked = uc.check_and_consume(_USER, "different")
    assert blocked.allowed is False


def test_unmetered_when_all_keys_configured(tmp_path) -> None:
    uc = _use_case(tmp_path, keys_all_set=True, trial_daily_search_limit=1)

    for word in ("one", "two", "three"):
        decision = uc.check_and_consume(_USER, word)
        assert decision.allowed is True
        assert decision.metered is False


def test_unmetered_when_trial_disabled(tmp_path) -> None:
    uc = _use_case(tmp_path, trial_enabled=False, trial_daily_search_limit=0)

    decision = uc.check_and_consume(_USER, "anything")
    assert decision.allowed is True
    assert decision.metered is False


def test_status_shape_for_trial_user(tmp_path) -> None:
    uc = _use_case(tmp_path, trial_daily_search_limit=50)
    uc.check_and_consume(_USER, "hello")

    status = uc.status(_USER)
    assert status.enabled is True
    assert status.available is True  # host gemini key present
    assert status.keys_configured is False
    assert status.opted_in is False
    assert status.limit == 50
    assert status.used == 1
    assert status.remaining == 49
    assert len(status.resets_on) == 10  # YYYY-MM-DD


def test_opt_in_marks_opted_in(tmp_path) -> None:
    uc = _use_case(tmp_path)
    assert uc.status(_USER).opted_in is False

    after = uc.opt_in(_USER)
    assert after.opted_in is True
    assert uc.status(_USER).opted_in is True


def test_status_available_false_without_host_key(tmp_path) -> None:
    uc = _use_case(tmp_path, gemini_api_key=None)
    assert uc.status(_USER).available is False


def test_guest_quota_persists_by_browser_hash(tmp_path) -> None:
    uc = _use_case(tmp_path, guest_daily_search_limit=2)
    browser_hash = "browser-hash"

    first = uc.check_and_consume_guest(browser_hash, "House")
    assert first.allowed and first.used == 1

    repeat = uc.check_and_consume_guest(browser_hash, " house ")
    assert repeat.allowed and repeat.used == 1

    second = uc.check_and_consume_guest(browser_hash, "car")
    assert second.allowed and second.used == 2

    blocked = uc.check_and_consume_guest(browser_hash, "tree")
    assert blocked.allowed is False
    assert blocked.used == 2

    status = uc.guest_status(browser_hash)
    assert status.limit == 2
    assert status.used == 2
    assert status.remaining == 0
