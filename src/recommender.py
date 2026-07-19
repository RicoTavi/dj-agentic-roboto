from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import csv

# --- Scoring recipe -------------------------------------------------------
# Kept as named constants so a single edit changes the whole system, and so
# the Stage 7 weighting experiment has exactly one place to touch.
GENRE_WEIGHT = 2.0
MOOD_WEIGHT = 1.0
ENERGY_WEIGHT = 1.0

# Fields that must be converted out of CSV strings, and the type to use.
NUMERIC_FIELDS = {
    "id": int,
    "tempo_bpm": int,
    "energy": float,
    "valence": float,
    "danceability": float,
    "acousticness": float,
}


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


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py
    """
    score = 0.0
    reasons: List[str] = []

    if _matches(user_prefs.get("genre"), song.get("genre")):
        score += GENRE_WEIGHT
        reasons.append(f"genre match (+{GENRE_WEIGHT:.1f})")

    if _matches(user_prefs.get("mood"), song.get("mood")):
        score += MOOD_WEIGHT
        reasons.append(f"mood match (+{MOOD_WEIGHT:.1f})")

    target_energy = user_prefs.get("energy")
    song_energy = song.get("energy")
    # Only score energy when both sides are real numbers, so a missing or
    # unparseable value earns nothing instead of silently counting as 0.0.
    if isinstance(target_energy, (int, float)) and isinstance(song_energy, (int, float)):
        # Clamped at 0.0 so out-of-range data can never subtract from the score.
        similarity = max(0.0, 1.0 - abs(float(song_energy) - float(target_energy)))
        points = ENERGY_WEIGHT * similarity
        if points > 0:
            score += points
            reasons.append(f"energy similarity (+{points:.2f})")

    return score, reasons


def format_reasons(reasons: List[str]) -> str:
    """Joins scoring reasons into one readable sentence."""
    return ", ".join(reasons) if reasons else "no matching features"


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    if k <= 0:
        return []

    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored.append((song, score, format_reasons(reasons)))

    # sorted() leaves the caller's list untouched; ties fall back to title so
    # the same catalog always produces the same order.
    ranked = sorted(scored, key=lambda item: (-item[1], str(item[0].get("title", ""))))
    return ranked[:k]
