from __future__ import annotations

from app.services.use_cases.wordbank.queries_cor import WordbankQueriesCorMixin
from app.services.use_cases.wordbank.queries_details import WordbankQueriesDetailsMixin
from app.services.use_cases.wordbank.queries_lemmas import WordbankQueriesLemmasMixin


class WordbankQueriesMixin(
    WordbankQueriesLemmasMixin,
    WordbankQueriesCorMixin,
    WordbankQueriesDetailsMixin,
):
    pass
