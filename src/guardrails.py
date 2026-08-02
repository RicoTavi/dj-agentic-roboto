"""
Input guardrails for the applied recommender system.

The system learns taste from user-supplied seed songs, so the first place it can
go wrong is bad input: no songs at all, or rows with none of the signals the
scorer needs. Rather than derive a meaningless profile and recommend confidently
from noise, the guardrail refuses early with a clear message.

validate_seeds is used by both the live app (src/app.py) and the evaluation
harness (src/evaluate.py), so the same check protects real runs and is exercised
by the test suite.
"""

from typing import Dict, List, Tuple

# A seed is only useful if it carries at least one signal the scorer reads.
SIGNAL_FIELDS = ("genre", "mood", "energy")


def _has_signal(song: Dict, field: str) -> bool:
    """True if a song carries a usable value for the given signal field."""
    value = song.get(field)
    if field == "energy":
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False
    return isinstance(value, str) and value.strip() != ""


def _is_usable(song: Dict) -> bool:
    """True if a seed song has at least one signal (genre, mood, or energy)."""
    return any(_has_signal(song, field) for field in SIGNAL_FIELDS)


def validate_seeds(seeds: List[Dict]) -> Tuple[bool, str]:
    """
    Checks that a seed set can produce a meaningful taste profile.

    Returns (ok, message). ok is False when the input should be refused; the
    message explains why (or, when ok, how many seeds were usable).
    """
    if not seeds:
        return False, "No seed songs provided - give me a few songs you like."
    usable = [s for s in seeds if _is_usable(s)]
    if not usable:
        return False, ("No seed song has a usable genre, mood, or energy value - "
                       "I can't learn a taste from this.")
    return True, f"{len(usable)} of {len(seeds)} seed song(s) usable."
