"""
Retrieval sources for the applied recommender system.

A retrieval source answers one question: "given this query, which candidate
songs from the corpus match?" The agent (src/agent.py) plans a query, reads the
results, and *widens* the query when the results are too thin — so the search
logic lives here, kept deliberately simple, while the decision-making lives in
the agent.

Phase 2 ships one source, LocalCatalogSource, over data/catalog.csv. Phase 5
adds a second (cached Last.fm) behind the same tiny interface.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


def norm(value) -> str:
    """Lower-cases and trims a categorical value; '' for anything non-string."""
    return value.strip().casefold() if isinstance(value, str) else ""


def _as_float(value) -> Optional[float]:
    """Returns value as a float, or None if missing/unparseable."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tag_set(value) -> set:
    """Normalises a semicolon-separated string (or list) into a set of tags."""
    if isinstance(value, str):
        parts = value.split(";")
    elif isinstance(value, (list, tuple, set)):
        parts = value
    else:
        return set()
    return {norm(p) for p in parts if norm(p)}


@dataclass
class RetrievalQuery:
    """
    A search request. Only the fields that are set act as constraints; leaving
    a field as None means "don't filter on this", which is how the agent widens
    a search (it drops constraints one by one).
    """
    genre: Optional[str] = None
    mood: Optional[str] = None
    tags: Optional[List[str]] = None          # matches if ANY tag overlaps
    energy: Optional[float] = None
    energy_tolerance: Optional[float] = None   # only used when energy is set
    label: str = ""                            # short human description

    def describe(self) -> str:
        """Human-readable summary of the active constraints, for traces."""
        if self.label:
            return self.label
        bits = []
        if self.genre:
            bits.append(f"genre={self.genre}")
        if self.mood:
            bits.append(f"mood={self.mood}")
        if self.energy is not None and self.energy_tolerance is not None:
            bits.append(f"energy={self.energy:.2f}±{self.energy_tolerance:.2f}")
        if self.tags:
            bits.append(f"tags~{self.tags[:3]}")
        return ", ".join(bits) if bits else "no filters (entire corpus)"


def _matches(song: Dict, query: RetrievalQuery) -> bool:
    """True when a song satisfies every active constraint in the query."""
    if query.genre and norm(song.get("genre")) != norm(query.genre):
        return False
    if query.mood and norm(song.get("mood")) != norm(query.mood):
        return False
    if query.energy is not None and query.energy_tolerance is not None:
        energy = _as_float(song.get("energy"))
        if energy is None or abs(energy - query.energy) > query.energy_tolerance:
            return False
    if query.tags:
        wanted = {norm(t) for t in query.tags}
        if not (wanted & _tag_set(song.get("mood_tags"))):
            return False
    return True


class LocalCatalogSource:
    """Retrieves candidate songs from an in-memory catalog (data/catalog.csv)."""

    name = "local-catalog"

    def __init__(self, songs: List[Dict]):
        self.songs = list(songs)

    def search(self, query: RetrievalQuery) -> List[Dict]:
        """Returns every catalog song that matches the query."""
        return [song for song in self.songs if _matches(song, query)]


class CompositeSource:
    """
    Merges several retrieval sources into one (RAG multi-source). Results from
    all sources are concatenated and de-duplicated by title+artist, with earlier
    sources winning ties - so the local catalog's richer rows are preferred over
    a thinner Last.fm entry for the same song.
    """

    name = "multi-source"

    def __init__(self, sources: List):
        self.sources = list(sources)

    def search(self, query: RetrievalQuery) -> List[Dict]:
        merged: List[Dict] = []
        seen = set()
        for source in self.sources:
            for song in source.search(query):
                key = (norm(song.get("title")), norm(song.get("artist")))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(song)
        return merged
