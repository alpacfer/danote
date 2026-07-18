from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.api.auth import CurrentUser
from app.api.routes import _use_case_factories, sentencebank, wordbank_audio, wordbank_search
from app.db.migrations import apply_migrations, get_connection
from app.db.repositories import WordbankRepository
from app.db.repositories.sentencebank import SentencebankRepository, SentenceTokenWriteRecord
from app.db.repositories.users import AppUserRepository
from app.main import create_app
from tests.api.wordbank_test_support import build_test_settings


@dataclass
class CurrentUserSwitcher:
    current: CurrentUser


def _current_user(user_id: int, subject: str) -> CurrentUser:
    return CurrentUser(
        id=user_id,
        email=f"{subject}@example.com",
        auth_provider="clerk",
        auth_subject=subject,
        display_name=subject,
        created_at="2026-01-01 00:00:00",
        last_seen_at="2026-01-01 00:00:00",
    )


def _install_current_user_switch(monkeypatch, switcher: CurrentUserSwitcher) -> None:
    def require_current_user(_request):
        return switcher.current

    for module in (_use_case_factories, sentencebank, wordbank_audio, wordbank_search):
        monkeypatch.setattr(module, "require_current_user", require_current_user)


def _create_test_users(db_path) -> tuple[CurrentUser, CurrentUser]:
    repo = AppUserRepository(db_path)
    first = repo.upsert_user(
        auth_provider="clerk",
        auth_subject="user-a",
        email="user-a@example.com",
        display_name="User A",
    )
    second = repo.upsert_user(
        auth_provider="clerk",
        auth_subject="user-b",
        email="user-b@example.com",
        display_name="User B",
    )
    return _current_user(first.id, "user-a"), _current_user(second.id, "user-b")


def _build_isolation_app(db_path, stub_nlp_adapter_factory):
    apply_migrations(db_path)
    return create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)


def _add_word(client: TestClient, surface: str, lemma: str) -> dict:
    response = client.post(
        "/api/wordbank/lexemes",
        json={"surface_token": surface, "lemma_candidate": lemma},
    )
    assert response.status_code == 200
    return response.json()


def _add_sentence(client: TestClient, source_text: str) -> dict:
    response = client.post(
        "/api/sentencebank/sentences",
        json={"source_text": source_text, "english_translation": f"translation for {source_text}"},
    )
    assert response.status_code == 200
    return response.json()


def test_wordbank_endpoints_scope_duplicate_lemmas_by_current_user(
    tmp_path,
    monkeypatch,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = _build_isolation_app(db_path, stub_nlp_adapter_factory)
    user_a, user_b = _create_test_users(db_path)
    switcher = CurrentUserSwitcher(user_a)
    _install_current_user_switch(monkeypatch, switcher)

    with TestClient(app) as client:
        switcher.current = user_a
        word_a = _add_word(client, "Bogen", "bog")
        meaning_a = word_a["meaning"]["id"]

        switcher.current = user_b
        word_b = _add_word(client, "Bogen", "bog")
        meaning_b = word_b["meaning"]["id"]

        assert meaning_a != meaning_b
        with get_connection(db_path) as conn:
            conn.execute(
                "UPDATE lexeme_meanings SET english_translation = 'book-a' WHERE id = ?",
                (meaning_a,),
            )
            conn.execute(
                "UPDATE lexeme_meanings SET english_translation = 'book-b' WHERE id = ?",
                (meaning_b,),
            )

        switcher.current = user_a
        list_a = client.get("/api/wordbank/lemmas")
        detail_a = client.get("/api/wordbank/lemmas/bog")
        search_a = client.get("/api/wordbank/search", params={"query": "bog"})

        switcher.current = user_b
        list_b = client.get("/api/wordbank/lemmas")
        detail_b = client.get("/api/wordbank/lemmas/bog")
        search_b = client.get("/api/wordbank/search", params={"query": "bog"})

        assert list_a.status_code == 200
        assert list_b.status_code == 200
        assert [item["lemma"] for item in list_a.json()["items"]] == ["bog"]
        assert [item["lemma"] for item in list_b.json()["items"]] == ["bog"]
        assert list_a.json()["items"][0]["translation_groups"][0]["english_translation"] == "book-a"
        assert list_b.json()["items"][0]["translation_groups"][0]["english_translation"] == "book-b"

        assert detail_a.status_code == 200
        assert detail_b.status_code == 200
        assert {item["id"] for item in detail_a.json()["meaning_sections"]} == {meaning_a}
        assert {item["id"] for item in detail_b.json()["meaning_sections"]} == {meaning_b}

        assert search_a.status_code == 200
        assert search_b.status_code == 200
        assert {item["meaning_id"] for item in search_a.json()["items"]} == {meaning_a}
        assert {item["meaning_id"] for item in search_b.json()["items"]} == {meaning_b}

        switcher.current = user_b
        blocked_delete = client.delete(f"/api/wordbank/meanings/{meaning_a}")
        assert blocked_delete.status_code == 404

        switcher.current = user_a
        own_delete = client.delete(f"/api/wordbank/meanings/{meaning_a}")
        assert own_delete.status_code == 200
        assert client.get("/api/wordbank/lemmas/bog").status_code == 404

        switcher.current = user_b
        assert client.get("/api/wordbank/lemmas/bog").status_code == 200


def test_sentencebank_endpoints_scope_duplicate_sentences_and_linked_word_cards(
    tmp_path,
    monkeypatch,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = _build_isolation_app(db_path, stub_nlp_adapter_factory)
    user_a, user_b = _create_test_users(db_path)
    switcher = CurrentUserSwitcher(user_a)
    _install_current_user_switch(monkeypatch, switcher)

    with TestClient(app) as client:
        switcher.current = user_a
        word_a = _add_word(client, "Bogen", "bog")
        sentence_a = _add_sentence(client, "Jeg laeser en bog")
        meaning_a = word_a["meaning"]["id"]

        switcher.current = user_b
        word_b = _add_word(client, "Bogen", "bog")
        sentence_b = _add_sentence(client, "Jeg laeser en bog")
        meaning_b = word_b["meaning"]["id"]

        assert sentence_a["id"] != sentence_b["id"]
        assert meaning_a != meaning_b

        repo_a = WordbankRepository(db_path, owner_user_id=user_a.id)
        repo_b = WordbankRepository(db_path, owner_user_id=user_b.id)
        lexeme_a = repo_a.get_lexeme("bog")
        lexeme_b = repo_b.get_lexeme("bog")
        assert lexeme_a is not None
        assert lexeme_b is not None
        token_a = SentenceTokenWriteRecord(
            token_index=0,
            surface_form="bog",
            normalized_surface="bog",
            lemma_candidate="bog",
            stored_lemma="bog",
            lexeme_id=lexeme_a.id,
            meaning_id=meaning_a,
            cor_id=None,
            pos_tag="NOUN",
            morphology=None,
            gloss=None,
            english_translation="book",
            gloss_translation=None,
        )
        token_b = SentenceTokenWriteRecord(
            token_index=0,
            surface_form="bog",
            normalized_surface="bog",
            lemma_candidate="bog",
            stored_lemma="bog",
            lexeme_id=lexeme_b.id,
            meaning_id=meaning_b,
            cor_id=None,
            pos_tag="NOUN",
            morphology=None,
            gloss=None,
            english_translation="bookcase",
            gloss_translation=None,
        )
        SentencebankRepository(db_path, owner_user_id=user_a.id).replace_sentence_tokens(
            sentence_id=sentence_a["id"],
            tokens=[token_a],
        )
        SentencebankRepository(db_path, owner_user_id=user_b.id).replace_sentence_tokens(
            sentence_id=sentence_b["id"],
            tokens=[token_b],
        )

        switcher.current = user_a
        sentences_a = client.get("/api/sentencebank/sentences")
        detail_a = client.get("/api/wordbank/lemmas/bog")

        switcher.current = user_b
        sentences_b = client.get("/api/sentencebank/sentences")
        detail_b = client.get("/api/wordbank/lemmas/bog")

        assert sentences_a.status_code == 200
        assert sentences_b.status_code == 200
        assert [item["id"] for item in sentences_a.json()["items"]] == [sentence_a["id"]]
        assert [item["id"] for item in sentences_b.json()["items"]] == [sentence_b["id"]]
        assert [item["id"] for item in detail_a.json()["linked_sentences"]] == [sentence_a["id"]]
        assert [item["id"] for item in detail_b.json()["linked_sentences"]] == [sentence_b["id"]]

        switcher.current = user_b
        blocked_delete = client.delete(f"/api/sentencebank/sentences/{sentence_a['id']}")
        assert blocked_delete.status_code == 404

        switcher.current = user_a
        own_delete = client.delete(f"/api/sentencebank/sentences/{sentence_a['id']}")
        assert own_delete.status_code == 200
        assert client.get("/api/sentencebank/sentences").json()["items"] == []

        switcher.current = user_b
        assert [item["id"] for item in client.get("/api/sentencebank/sentences").json()["items"]] == [
            sentence_b["id"]
        ]


def test_verification_change_history_is_owner_scoped(
    tmp_path,
    monkeypatch,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = _build_isolation_app(db_path, stub_nlp_adapter_factory)
    user_a, user_b = _create_test_users(db_path)
    switcher = CurrentUserSwitcher(user_a)
    _install_current_user_switch(monkeypatch, switcher)

    with TestClient(app) as client:
        switcher.current = user_a
        _add_word(client, "Bogen", "bog")
        change_a = WordbankRepository(db_path, owner_user_id=user_a.id).insert_change_log_entry(
            stored_lemma="bog",
            stored_surface_form=None,
            meaning_id=None,
            action_type="fix_translation",
            before_json={"english_translation": "old-a"},
            after_json={"english_translation": "new-a"},
            applied_at="2026-01-01 00:00:00",
            provider="test",
        )

        switcher.current = user_b
        _add_word(client, "Bogen", "bog")
        change_b = WordbankRepository(db_path, owner_user_id=user_b.id).insert_change_log_entry(
            stored_lemma="bog",
            stored_surface_form=None,
            meaning_id=None,
            action_type="fix_translation",
            before_json={"english_translation": "old-b"},
            after_json={"english_translation": "new-b"},
            applied_at="2026-01-01 00:00:00",
            provider="test",
        )

        switcher.current = user_a
        history_a = client.get("/api/wordbank/lexemes/verification-changes", params={"stored_lemma": "bog"})

        switcher.current = user_b
        history_b = client.get("/api/wordbank/lexemes/verification-changes", params={"stored_lemma": "bog"})

        assert history_a.status_code == 200
        assert history_b.status_code == 200
        assert [item["id"] for item in history_a.json()["items"]] == [change_a]
        assert [item["id"] for item in history_b.json()["items"]] == [change_b]
