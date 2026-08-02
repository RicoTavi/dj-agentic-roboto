"""Unit tests for the explanation renderers (src/explain.py)."""

from src.explain import (closest_seed, dj_explanation, compare_explanations,
                         MAX_DJ_WORDS)


def _song(title, artist, genre, mood, energy, tags="dance"):
    return dict(title=title, artist=artist, genre=genre, mood=mood,
                energy=energy, mood_tags=tags)


SEEDS = [
    _song("Cassette Crush", "Ronnie Blaze", "new jack swing", "happy", 0.82),
    _song("Two Left Feelings", "Ivory Lane", "r&b", "sad", 0.46, tags="smooth"),
]


def test_closest_seed_matches_on_genre_and_mood():
    pick = _song("Poison", "Bell Biv DeVoe", "new jack swing", "happy", 0.85)
    match = closest_seed(pick, SEEDS)
    assert match.seed["title"] == "Cassette Crush"       # same genre+mood
    assert "new jack swing" in match.shared


def test_dj_line_names_a_seed_and_is_short():
    pick = _song("Poison", "Bell Biv DeVoe", "new jack swing", "happy", 0.85)
    line = dj_explanation(pick, SEEDS)
    assert "Cassette Crush" in line                        # anchored to a real seed
    assert len(line.split()) <= MAX_DJ_WORDS               # stays short


def test_dj_falls_back_when_no_seeds():
    pick = _song("Poison", "Bell Biv DeVoe", "new jack swing", "happy", 0.85)
    # With no seeds it must NOT invent a connection - it uses the baseline text.
    assert dj_explanation(pick, [], baseline_why="genre match") == "genre match"


def test_comparison_shows_measurable_gap():
    recs = [
        (_song("Poison", "BBD", "new jack swing", "happy", 0.85), 4.6,
         "genre match (+2.0), mood match (+1.0)"),
        (_song("Just Got Paid", "Kemp", "new jack swing", "happy", 0.83), 4.2,
         "genre match (+2.0), mood match (+1.0)"),
    ]
    metrics = compare_explanations(recs, SEEDS)
    # The whole point: DJ voice cites a seed every time, baseline never does.
    assert metrics["dj_seed_citation_rate"] == 1.0
    assert metrics["baseline_seed_citation_rate"] == 0.0
