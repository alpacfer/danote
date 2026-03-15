from __future__ import annotations


class ConflictError(RuntimeError):
    """Represents a user-facing conflict such as a gated workflow prerequisite."""
