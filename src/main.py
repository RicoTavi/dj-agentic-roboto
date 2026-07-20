"""
Command line runner for the Music Recommender Simulation.

Runs the recommender against several user profiles and two edge cases so the
behaviour of the scoring rules can be compared side by side.

Usage:
    python -m src.main                    # default "balanced" ranking mode
    python -m src.main --mode mood-first  # switch ranking strategy
"""

import argparse
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple

from src.recommender import RANKING_MODES, load_songs, recommend_songs

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
        "80s Groove",
        {"genre": "new jack swing", "mood": "happy", "energy": 0.80,
         "decade": "1980s", "tags": ["funky", "romantic"]},
        "NJS Party plus the optional decade and mood-tag preferences.",
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

# Column widths for the results table.
WIDTHS = (3, 24, 14, 5, 44)
HEADERS = ("#", "Title", "Artist", "Score", "Because")


def _rule(sep: str = "-") -> str:
    return "+" + "+".join(sep * (w + 2) for w in WIDTHS) + "+"


def _row(cells: Tuple[str, ...]) -> str:
    """Renders one table row, wrapping any cell that is wider than its column."""
    wrapped = [textwrap.wrap(str(c), width=w) or [""] for c, w in zip(cells, WIDTHS)]
    height = max(len(col) for col in wrapped)
    lines = []
    for i in range(height):
        parts = [(col[i] if i < len(col) else "").ljust(w) for col, w in zip(wrapped, WIDTHS)]
        lines.append("| " + " | ".join(parts) + " |")
    return "\n".join(lines)


def show(name: str, prefs: Dict, note: str, songs: List[Dict], mode) -> None:
    """Prints the top recommendations for one profile as a table."""
    print(f"PROFILE: {name}")
    print(f"  Preferences: {prefs}")
    print(f"  Testing: {note}")

    recommendations = recommend_songs(prefs, songs, k=TOP_K, mode=mode)
    if not recommendations:
        print("  No recommendations available.\n")
        return

    print(_rule("="))
    print(_row(HEADERS))
    print(_rule("="))
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(_row((str(rank), song.get("title", "?"), song.get("artist", ""),
                    f"{score:.2f}", explanation)))
        print(_rule())
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the music recommender.")
    parser.add_argument(
        "--mode",
        choices=sorted(RANKING_MODES),
        default="balanced",
        help="ranking strategy to use (default: balanced)",
    )
    args = parser.parse_args()
    mode = RANKING_MODES[args.mode]

    songs = load_songs(str(SONGS_CSV))
    print(f"\nLoaded {len(songs)} songs from {SONGS_CSV.name}")
    print(f"Ranking mode: {mode.name} — {mode.description}\n")

    for name, prefs, note in PROFILES + EDGE_CASES:
        show(name, prefs, note, songs, mode)


if __name__ == "__main__":
    main()
