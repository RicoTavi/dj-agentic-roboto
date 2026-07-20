from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import csv

# --- Scoring recipe -------------------------------------------------------
# Kept as named constants so a single edit changes the whole system, and so
# the weighting experiment has exactly one place to touch. These are the
# weights of the default "balanced" ranking mode.
GENRE_WEIGHT = 2.0
MOOD_WEIGHT = 1.0
ENERGY_WEIGHT = 1.0

# Optional signals, scored only when the user profile asks for them.
DECADE_WEIGHT = 0.5     # exact decade match, e.g. "1980s"
TAG_WEIGHT = 0.25       # per overlapping mood tag...
TAG_CAP = 0.5           # ...up to this much in total

# Diversity: each song already picked by the same artist subtracts this much
# from a candidate's score during selection, so one artist cannot quietly
# fill several slots in a short list.
ARTIST_PENALTY = 0.75

# Fields that must be converted out of CSV strings, and the type to use.
NUMERIC_FIELDS = {
    "id": int,
    "tempo_bpm": int,
    "energy": float,
    "valence": float,
    "danceability": float,
    "acousticness": float,
    "year": int,
    "popularity": int,
}


# --- Ranking modes (Strategy pattern) -------------------------------------
# Each mode is a named weighting strategy. score_song consults the active
# mode for its weights, so switching strategy never means new scoring code —
# only different numbers flowing through the same logic.

@dataclass(frozen=True)
class RankingMode:
    """A named weighting strategy for the scorer."""
    name: str
    description: str
    genre_weight: float
    mood_weight: float
    energy_weight: float
    popularity_weight: float = 0.0


RANKING_MODES: Dict[str, RankingMode] = {
    "balanced": RankingMode(
        "balanced",
        "The default recipe: genre dominates, mood and energy refine.",
        genre_weight=GENRE_WEIGHT, mood_weight=MOOD_WEIGHT, energy_weight=ENERGY_WEIGHT,
    ),
    "mood-first": RankingMode(
        "mood-first",
        "Mood dominates; genre becomes a small nudge.",
        genre_weight=0.5, mood_weight=2.0, energy_weight=1.0,
    ),
    "energy": RankingMode(
        "energy",
        "Pure energy similarity; categorical labels are ignored.",
        genre_weight=0.0, mood_weight=0.0, energy_weight=3.0,
    ),
    "crowd-pleaser": RankingMode(
        "crowd-pleaser",
        "The balanced recipe plus a bonus for popular songs.",
        genre_weight=GENRE_WEIGHT, mood_weight=MOOD_WEIGHT, energy_weight=ENERGY_WEIGHT,
        popularity_weight=1.5,
    ),
}

DEFAULT_MODE = RANKING_MODES["balanced"]


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

    def to_prefs(self) -> Dict:
        """Converts the profile into the preference dict that score_song expects."""
        return {
            "genre": self.favorite_genre,
            "mood": self.favorite_mood,
            "energy": self.target_energy,
        }


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Returns the top k Songs for a user, ranked by score_song."""
        ranked = recommend_songs(user.to_prefs(), [asdict(s) for s in self.songs], k)
        by_id = {s.id: s for s in self.songs}
        return [by_id[song["id"]] for song, _score, _why in ranked]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns a human-readable explanation of why a song fits a user."""
        _score, reasons = score_song(user.to_prefs(), asdict(song))
        return format_reasons(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            song = dict(row)
            for field, cast in NUMERIC_FIELDS.items():
                value = song.get(field)
                # Leave unparseable values as-is; score_song refuses to score them.
                if value not in (None, ""):
                    try:
                        song[field] = cast(value)
                    except ValueError:
                        pass
            songs.append(song)
    return songs

def _matches(preferred, actual) -> bool:
    """Compares two categorical values, ignoring case and surrounding whitespace."""
    if not isinstance(preferred, str) or not isinstance(actual, str):
        return False
    if not preferred.strip() or not actual.strip():
        return False
    return preferred.strip().casefold() == actual.strip().casefold()


def _tag_set(value) -> set:
    """Normalises a semicolon-separated string or a list into a set of tags."""
    if isinstance(value, str):
        parts = value.split(";")
    elif isinstance(value, (list, tuple, set)):
        parts = value
    else:
        return set()
    return {p.strip().casefold() for p in parts if isinstance(p, str) and p.strip()}


def score_song(user_prefs: Dict, song: Dict,
               mode: Optional[RankingMode] = None) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences under a ranking mode.
    Required by recommend_songs() and src/main.py
    """
    if mode is None:
        mode = DEFAULT_MODE

    score = 0.0
    reasons: List[str] = []

    if mode.genre_weight > 0 and _matches(user_prefs.get("genre"), song.get("genre")):
        score += mode.genre_weight
        reasons.append(f"genre match (+{mode.genre_weight:.1f})")

    if mode.mood_weight > 0 and _matches(user_prefs.get("mood"), song.get("mood")):
        score += mode.mood_weight
        reasons.append(f"mood match (+{mode.mood_weight:.1f})")

    target_energy = user_prefs.get("energy")
    song_energy = song.get("energy")
    # Only score energy when both sides are real numbers, so a missing or
    # unparseable value earns nothing instead of silently counting as 0.0.
    if (mode.energy_weight > 0
            and isinstance(target_energy, (int, float))
            and isinstance(song_energy, (int, float))):
        # Clamped at 0.0 so out-of-range data can never subtract from the score.
        similarity = max(0.0, 1.0 - abs(float(song_energy) - float(target_energy)))
        points = mode.energy_weight * similarity
        if points > 0:
            score += points
            reasons.append(f"energy similarity (+{points:.2f})")

    # Optional signals: these score only when the profile asks for them, so
    # profiles that do not mention them are completely unaffected.
    if _matches(user_prefs.get("decade"), song.get("decade")):
        score += DECADE_WEIGHT
        reasons.append(f"decade match (+{DECADE_WEIGHT:.1f})")

    wanted_tags = _tag_set(user_prefs.get("tags"))
    if wanted_tags:
        overlap = wanted_tags & _tag_set(song.get("mood_tags"))
        if overlap:
            points = min(TAG_CAP, TAG_WEIGHT * len(overlap))
            score += points
            reasons.append(f"mood tags {sorted(overlap)} (+{points:.2f})")

    # Popularity is a property of the song, not a match against a preference;
    # it only contributes in modes that weight it (e.g. crowd-pleaser).
    popularity = song.get("popularity")
    if mode.popularity_weight > 0 and isinstance(popularity, (int, float)):
        points = mode.popularity_weight * max(0.0, min(100.0, float(popularity))) / 100.0
        if points > 0:
            score += points
            reasons.append(f"popularity (+{points:.2f})")

    return score, reasons


def format_reasons(reasons: List[str]) -> str:
    """Joins scoring reasons into one readable sentence."""
    return ", ".join(reasons) if reasons else "no matching features"


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5,
                    mode: Optional[RankingMode] = None,
                    artist_penalty: float = ARTIST_PENALTY) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    if k <= 0:
        return []

    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, mode)
        scored.append((song, score, reasons))

    # Greedy selection with a diversity penalty: each round, every candidate's
    # score is reduced by ARTIST_PENALTY for each song already picked from the
    # same artist, then the best remaining candidate is taken. Ties fall back
    # to title so the same catalog always produces the same order.
    picked: List[Tuple[Dict, float, str]] = []
    artist_counts: Dict[str, int] = {}
    remaining = list(scored)

    while remaining and len(picked) < k:
        def adjusted(item):
            song, score, _reasons = item
            artist = str(song.get("artist", "")).casefold()
            return score - artist_penalty * artist_counts.get(artist, 0)

        best = min(remaining, key=lambda item: (-adjusted(item), str(item[0].get("title", ""))))
        remaining.remove(best)

        song, score, reasons = best
        artist = str(song.get("artist", "")).casefold()
        hits = artist_counts.get(artist, 0)
        final_score = score
        final_reasons = list(reasons)
        if hits and artist_penalty > 0:
            penalty = artist_penalty * hits
            final_score = score - penalty
            final_reasons.append(f"artist repetition penalty (-{penalty:.2f})")
        artist_counts[artist] = hits + 1

        picked.append((song, final_score, format_reasons(final_reasons)))

    return picked
