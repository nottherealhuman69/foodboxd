"""Shared input validation helpers."""


def valid_rating(r: float) -> bool:
    """Ratings run 0.5–5 in half-star steps."""
    return r is not None and 0.5 <= r <= 5 and (r * 2) == int(r * 2)
