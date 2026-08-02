"""Tests for the guardrail and the evaluation harness."""

from src.guardrails import validate_seeds
from src.evaluate import build_cases, evaluate_seeds
from src.recommender import load_songs
from pathlib import Path

CATALOG = load_songs(str(Path(__file__).resolve().parent.parent / "data" / "catalog.csv"))


def test_validate_rejects_empty():
    ok, _msg = validate_seeds([])
    assert ok is False


def test_validate_rejects_signalless_rows():
    ok, _msg = validate_seeds([dict(title="x", artist="y", genre="", mood="", energy="")])
    assert ok is False


def test_validate_accepts_usable_seed():
    ok, _msg = validate_seeds([dict(title="x", artist="y", genre="pop",
                                    mood="happy", energy=0.5)])
    assert ok is True


def test_every_eval_case_passes():
    """The harness's own expectations must all hold (meta-check)."""
    for case in build_cases():
        catalog = case.catalog if case.catalog is not None else CATALOG
        outcome = evaluate_seeds(case.seeds, catalog)
        assert case.check(outcome), f"eval case failed: {case.name}"
