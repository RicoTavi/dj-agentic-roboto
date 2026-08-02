"""
Taste-profile derivation for the applied recommender system.

The original Week-6 project asked the user to *describe* their taste by hand
(a preferences dictionary). This module instead *learns* the same kind of
profile from a set of seed songs the user already likes, so the taste that
drives ranking is grounded in real listening rather than a guess.

The derived profile stays transparent: it can explain exactly which seeds
produced each preference (e.g. "dominant genre new jack swing (4/12)"), which
keeps the project's original promise that you can always answer "why?".
"""

from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Dict, List, Optional

from src.recommender import load_songs  # reuse the existing CSV loader

# Numeric attributes we average across the seed set to characterise taste.
MEAN_FIELDS = ("energy", "valence", "tempo_bpm", "acousticness")

# A seed set smaller than this is flagged low-confidence (an honest-AI guardrail
# used later by the agent: "you only gave me 3 songs, trust this less").
MIN_CONFIDENT_SEEDS = 5

# Average acousticness at or above this marks a listener who leans acoustic.
ACOUSTIC_THRESHOLD = 0.5

# How many mood tags to surface as the profile's signature tags.
TOP_TAG_COUNT = 5


def _as_float(value) -> Optional[float]:
    """Returns value as a float, or None if it is missing or unparseable."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean(value) -> str:
    """Lower-cases and trims a categorical string; '' for anything else."""
    return value.strip().casefold() if isinstance(value, str) else ""


def _tags(value) -> List[str]:
    """Splits a semicolon-separated mood_tags value into normalised tags."""
    if isinstance(value, str):
        return [t.strip().casefold() for t in value.split(";") if t.strip()]
    if isinstance(value, (list, tuple)):
        return [_clean(t) for t in value if _clean(t)]
    return []


def _dominant(counter: Counter) -> str:
    """Most common key, breaking ties alphabetically so results are stable."""
    if not counter:
        return ""
    most = max(counter.values())
    return sorted(key for key, count in counter.items() if count == most)[0]


@dataclass
class TasteProfile:
    """A taste profile learned from a set of seed songs."""
    seed_count: int
    dominant_genre: str
    genre_distribution: Dict[str, int]
    dominant_mood: str
    mood_distribution: Dict[str, int]
    mean_energy: Optional[float]
    mean_valence: Optional[float]
    mean_tempo: Optional[float]
    dominant_decade: Optional[str]
    top_tags: List[str]
    likes_acoustic: bool

    @property
    def is_confident(self) -> bool:
        """True when there are enough seeds to trust the profile."""
        return self.seed_count >= MIN_CONFIDENT_SEEDS

    def to_prefs(self) -> Dict:
        """Converts the profile into the preferences dict score_song expects."""
        prefs: Dict = {}
        if self.dominant_genre:
            prefs["genre"] = self.dominant_genre
        if self.dominant_mood:
            prefs["mood"] = self.dominant_mood
        if self.mean_energy is not None:
            prefs["energy"] = round(self.mean_energy, 3)
        if self.dominant_decade:
            prefs["decade"] = self.dominant_decade
        if self.top_tags:
            prefs["tags"] = list(self.top_tags)
        return prefs

    def explain(self) -> str:
        """One human-readable paragraph on how the taste was derived."""
        genre_n = self.genre_distribution.get(self.dominant_genre, 0)
        mood_n = self.mood_distribution.get(self.dominant_mood, 0)
        parts = [
            f"Derived from {self.seed_count} seed song(s).",
            f"Dominant genre: {self.dominant_genre or '-'} ({genre_n}/{self.seed_count}).",
            f"Dominant mood: {self.dominant_mood or '-'} ({mood_n}/{self.seed_count}).",
        ]
        if self.mean_energy is not None:
            parts.append(f"Average energy: {self.mean_energy:.2f}.")
        if self.dominant_decade:
            parts.append(f"Leans {self.dominant_decade}.")
        if self.top_tags:
            parts.append(f"Signature tags: {', '.join(self.top_tags)}.")
        if not self.is_confident:
            parts.append(
                f"Low confidence: fewer than {MIN_CONFIDENT_SEEDS} seeds, "
                "so recommendations may be unreliable."
            )
        return " ".join(parts)


def derive_profile(seeds: List[Dict]) -> TasteProfile:
    """Learns a TasteProfile from a list of seed song dicts."""
    if not seeds:
        raise ValueError("Cannot derive a taste profile from zero seed songs.")

    genres: Counter = Counter()
    moods: Counter = Counter()
    decades: Counter = Counter()
    tags: Counter = Counter()
    numeric: Dict[str, List[float]] = {field: [] for field in MEAN_FIELDS}

    for song in seeds:
        if _clean(song.get("genre")):
            genres[_clean(song.get("genre"))] += 1
        if _clean(song.get("mood")):
            moods[_clean(song.get("mood"))] += 1
        if _clean(song.get("decade")):
            decades[_clean(song.get("decade"))] += 1
        for tag in _tags(song.get("mood_tags")):
            tags[tag] += 1
        for field in MEAN_FIELDS:
            value = _as_float(song.get(field))
            if value is not None:
                numeric[field].append(value)

    averages = {f: (mean(vals) if vals else None) for f, vals in numeric.items()}

    return TasteProfile(
        seed_count=len(seeds),
        dominant_genre=_dominant(genres),
        genre_distribution=dict(genres),
        dominant_mood=_dominant(moods),
        mood_distribution=dict(moods),
        mean_energy=averages["energy"],
        mean_valence=averages["valence"],
        mean_tempo=averages["tempo_bpm"],
        dominant_decade=_dominant(decades) or None,
        top_tags=[tag for tag, _count in tags.most_common(TOP_TAG_COUNT)],
        likes_acoustic=(averages["acousticness"] or 0.0) >= ACOUSTIC_THRESHOLD,
    )


def load_seed_profile(csv_path: str) -> TasteProfile:
    """Loads seed songs from a CSV file and returns the derived taste profile."""
    return derive_profile(load_songs(csv_path))
