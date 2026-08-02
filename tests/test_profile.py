"""Unit tests for taste-profile derivation (src/profile.py)."""

import pytest

from src.profile import derive_profile, MIN_CONFIDENT_SEEDS


def _song(**overrides) -> dict:
    """Builds a seed-song dict with blank defaults, overridden as needed."""
    base = dict(genre="", mood="", energy="", valence="", tempo_bpm="",
                danceability="", acousticness="", decade="", mood_tags="")
    base.update(overrides)
    return base


def test_dominant_genre_and_mood():
    seeds = [
        _song(genre="new jack swing", mood="happy", energy=0.80),
        _song(genre="new jack swing", mood="happy", energy=0.82),
        _song(genre="freestyle", mood="sad", energy=0.83),
    ]
    profile = derive_profile(seeds)
    assert profile.dominant_genre == "new jack swing"
    assert profile.dominant_mood == "happy"
    assert profile.seed_count == 3


def test_mean_energy_is_averaged():
    seeds = [_song(genre="pop", mood="happy", energy=0.40),
             _song(genre="pop", mood="happy", energy=0.60)]
    assert derive_profile(seeds).mean_energy == pytest.approx(0.50)


def test_to_prefs_has_expected_keys():
    seeds = [_song(genre="lofi", mood="chill", energy=0.35,
                   decade="2020s", mood_tags="chill;study")]
    prefs = derive_profile(seeds).to_prefs()
    assert prefs["genre"] == "lofi"
    assert prefs["mood"] == "chill"
    assert prefs["energy"] == 0.35
    assert prefs["decade"] == "2020s"
    assert "chill" in prefs["tags"]


def test_empty_seeds_raises():
    with pytest.raises(ValueError):
        derive_profile([])


def test_small_seed_set_is_low_confidence():
    profile = derive_profile([_song(genre="pop", mood="happy", energy=0.5)])
    assert profile.is_confident is False
    assert profile.seed_count < MIN_CONFIDENT_SEEDS


def test_unparseable_numbers_are_ignored():
    seeds = [_song(genre="pop", mood="happy", energy="n/a"),
             _song(genre="pop", mood="happy", energy=0.60)]
    # The bad value is skipped, so the mean is just the one real number.
    assert derive_profile(seeds).mean_energy == pytest.approx(0.60)
