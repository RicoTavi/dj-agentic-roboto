"""Unit tests for the recommender agent (src/agent.py)."""

from src.agent import RecommenderAgent
from src.profile import derive_profile
from src.retrieval import LocalCatalogSource


def _song(id, title, artist, genre, mood, energy, **extra):
    base = dict(id=id, title=title, artist=artist, genre=genre, mood=mood,
                energy=energy, valence=0.6, tempo_bpm=110, danceability=0.8,
                acousticness=0.1, decade="1990s", mood_tags="dance", year=1990)
    base.update(extra)
    return base


def _agent(seeds, catalog, k=5):
    profile = derive_profile(seeds)
    return RecommenderAgent(LocalCatalogSource(catalog), profile, seeds, k=k)


def test_happy_path_accepts_early_and_excludes_seeds():
    seeds = [_song(1, "A", "Artist One", "new jack swing", "happy", 0.80),
             _song(2, "B", "Artist Two", "new jack swing", "happy", 0.80)]
    catalog = [_song(101, "C", "Nova", "new jack swing", "happy", 0.80),
               _song(102, "D", "Vega", "new jack swing", "happy", 0.78),
               _song(103, "E", "Rigel", "new jack swing", "happy", 0.82)]
    result = _agent(seeds, catalog, k=2).run()
    titles = [song["title"] for song, _s, _w in result.recommendations]
    assert len(result.recommendations) == 2
    assert "A" not in titles and "B" not in titles      # seeds excluded
    assert result.confidence_label in {"high", "medium"}


def test_dedupes_seed_that_also_appears_in_catalog():
    shared = _song(1, "Shared", "Same Artist", "new jack swing", "happy", 0.80)
    seeds = [shared, _song(2, "S2", "Other", "new jack swing", "happy", 0.80)]
    catalog = [dict(shared),  # same title+artist as a seed -> must be dropped
               _song(101, "New", "Fresh", "new jack swing", "happy", 0.80)]
    titles = [s["title"] for s, _sc, _w in _agent(seeds, catalog).run().recommendations]
    assert "Shared" not in titles
    assert "New" in titles


def test_widens_when_genre_is_sparse():
    # Taste is new jack swing, but the catalog has only ONE such song and lots
    # of same-mood songs -> the agent must widen past genre to fill the set.
    seeds = [_song(i, f"S{i}", f"A{i}", "new jack swing", "happy", 0.80)
             for i in range(1, 6)]
    catalog = [_song(101, "NJS", "Only NJS", "new jack swing", "happy", 0.80)]
    catalog += [_song(200 + i, f"P{i}", f"Pop{i}", "pop", "happy", 0.80)
                for i in range(4)]  # same mood, different genre
    result = _agent(seeds, catalog, k=5).run()
    assert len(result.recommendations) == 5           # set got filled
    assert len(result.steps) >= 2                      # it actually widened
    assert result.confidence_label in {"medium", "low"}  # not a clean match


def test_refuses_when_nothing_fits():
    # Taste is high-energy dance; catalog is only far-away low-energy ambient in
    # an unrelated genre/mood -> best match is too weak, so the agent declines.
    seeds = [_song(i, f"S{i}", f"A{i}", "eurodance", "intense", 0.95,
                   mood_tags="club", decade="1990s") for i in range(1, 6)]
    catalog = [_song(300 + i, f"Q{i}", f"Amb{i}", "ambient", "chill", 0.05,
                     mood_tags="space", decade="2020s") for i in range(3)]
    result = _agent(seeds, catalog, k=5).run()
    assert result.recommendations == []
    assert result.confidence_label == "none"


def test_empty_catalog_refuses():
    seeds = [_song(1, "A", "One", "pop", "happy", 0.8)]
    result = _agent(seeds, [], k=5).run()
    assert result.recommendations == []
    assert result.confidence == 0.0
