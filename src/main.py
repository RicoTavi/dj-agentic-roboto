"""
Command line runner for the Music Recommender Simulation.

Runs the recommender against several user profiles and two edge cases so the
behaviour of the scoring rules can be compared side by side.
"""

from pathlib import Path
from typing import Dict, List, Tuple

from src.recommender import load_songs, recommend_songs

# Resolve the CSV relative to the project root so the program runs from any directory.
SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"

TOP_K = 5

# (name, preferences, what this profile is testing)
PROFILES: List[Tuple[str, Dict, str]] = [
    (
        "NJS Party",
        {"genre": "new jack swing", "mood": "happy", "energy": 0.80},
        "An upbeat late-80s new jack swing listener.",
    ),
    (
        "Freestyle Heartbreak",
        {"genre": "freestyle", "mood": "sad", "energy": 0.85},
        "Conflicting signals: a sad mood at dance-floor energy.",
    ),
    (
        "Chill Lofi",
        {"genre": "lofi", "mood": "chill", "energy": 0.35},
        "A low-energy study or background listener.",
    ),
]

EDGE_CASES: List[Tuple[str, Dict, str]] = [
    (
        "EDGE: Genre Not In Catalog",
        {"genre": "reggaeton", "mood": "happy", "energy": 0.70},
        "No song has this genre, so ranking falls back to mood and energy alone.",
    ),
    (
        "EDGE: Maximum Energy, No Categorical Preference",
        {"genre": "", "mood": "", "energy": 1.00},
        "Empty categorical preferences must earn nothing, leaving a pure energy ranking.",
    ),
]


def show(name: str, prefs: Dict, note: str, songs: List[Dict]) -> None:
    """Prints the top recommendations for one profile."""
    print("=" * 72)
    print(f"PROFILE: {name}")
    print(f"  Preferences: {prefs}")
    print(f"  Testing: {note}")
    print("-" * 72)

    recommendations = recommend_songs(prefs, songs, k=TOP_K)
    if not recommendations:
        print("  No recommendations available.")
        return

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        artist = song.get("artist")
        title = f"{song['title']} - {artist}" if artist else song["title"]
        print(f"  {rank}. {title}")
        print(f"     Score: {score:.2f}  |  Because: {explanation}")
    print()


def main() -> None:
    songs = load_songs(str(SONGS_CSV))
    print(f"\nLoaded {len(songs)} songs from {SONGS_CSV.name}\n")

    for name, prefs, note in PROFILES + EDGE_CASES:
        show(name, prefs, note, songs)


if __name__ == "__main__":
    main()
