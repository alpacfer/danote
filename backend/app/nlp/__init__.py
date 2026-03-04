from __future__ import annotations

from typing import TYPE_CHECKING

from app.nlp.adapter import NLPAdapter, NLPToken

if TYPE_CHECKING:
    from app.nlp.danish import DaCyLemmyNLPAdapter as DaCyLemmyNLPAdapter


__all__ = [
    "NLPAdapter",
    "NLPToken",
    "DaCyLemmyNLPAdapter",
    "load_danish_nlp_adapter",
]


def load_danish_nlp_adapter(*args, **kwargs):
    from app.nlp.danish import load_danish_nlp_adapter as _load

    return _load(*args, **kwargs)


def __getattr__(name: str):
    if name == "DaCyLemmyNLPAdapter":
        from app.nlp.danish import DaCyLemmyNLPAdapter

        return DaCyLemmyNLPAdapter
    raise AttributeError(name)
