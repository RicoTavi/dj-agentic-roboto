"""Tests for the Last.fm source and multi-source merge (no network - cache only)."""

from pathlib import Path

from src.lastfm import build_lastfm_source, LastfmSource
from src.retrieval import CompositeSource, LocalCatalogSource, RetrievalQuery

CACHE = Path(__file__).resolve().parent.parent / "data" / "lastfm_cache.json"


def test_offline_build_reads_committed_cache():
    # No key, no network: results must come purely from the committed cache.
    _src, meta = build_lastfm_source("new jack swing", "happy", None,
                                     cache_path=CACHE, allow_network=False)
    assert meta["candidates"] > 0
    assert meta["network_used"] is False


def test_retrieved_tracks_have_no_fabricated_energy():
    src, _meta = build_lastfm_source("new jack swing", "happy", None,
                                     cache_path=CACHE, allow_network=False)
    # Honesty: a retrieved track carries the tag we queried but NO energy number.
    assert src.songs, "expected cached candidates"
    assert all(s["energy"] == "" for s in src.songs)
    assert all(s.get("source") == "last.fm" for s in src.songs)


def test_composite_merges_and_dedupes_local_winning():
    local = LocalCatalogSource([
        {"title": "X", "artist": "Y", "genre": "pop", "mood": "happy",
         "energy": 0.8, "mood_tags": ""}])
    remote = LastfmSource([
        {"title": "X", "artist": "Y", "genre": "pop", "mood": "",
         "energy": "", "mood_tags": "pop", "source": "last.fm"},
        {"title": "Z", "artist": "W", "genre": "pop", "mood": "",
         "energy": "", "mood_tags": "pop", "source": "last.fm"}])
    results = CompositeSource([local, remote]).search(RetrievalQuery(genre="pop"))
    by_title = {s["title"]: s for s in results}
    assert set(by_title) == {"X", "Z"}          # X de-duplicated, Z added
    assert by_title["X"]["energy"] == 0.8        # the local row won the tie
