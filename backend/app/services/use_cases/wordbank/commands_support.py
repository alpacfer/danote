from __future__ import annotations

from app.api.schemas.v1.wordbank import ResetDatabaseResponse
from app.db.migrations import apply_migrations, get_connection
from app.services.token_classifier import normalize_token


class WordbankCommandsSupportMixin:
    def _invalidate_pos_cache(self, lemma: str, surface: str | None) -> None:
        values = {normalize_token(lemma)}
        if surface:
            values.add(normalize_token(surface))
        keys_to_delete = [key for key in self._pos_morph_cache if key[0] in values]
        for key in keys_to_delete:
            self._pos_morph_cache.pop(key, None)




    def _store_lexeme_metadata(self, lexeme_id: int, pos_tag: str | None, morphology: str | None) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = ?, morphology = ?
                WHERE id = ?
                """,
                (pos_tag, morphology, lexeme_id),
            )




    def _store_surface_form_metadata(
        self,
        lexeme_id: int,
        form: str,
        pos_tag: str | None,
        morphology: str | None,
    ) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE surface_forms
                SET pos_tag = ?, morphology = ?
                WHERE lexeme_id = ? AND form = ?
                """,
                (pos_tag, morphology, lexeme_id, form),
            )




    def reset_database(self) -> ResetDatabaseResponse:
        if self._db_path.exists():
            os.remove(self._db_path)
        apply_migrations(self._db_path)
        if self._typo_engine is not None:
            self._typo_engine.invalidate_cache()

        return ResetDatabaseResponse(
            status="reset",
            message="Database reset complete.",
        )
