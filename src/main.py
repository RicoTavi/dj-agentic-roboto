"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from pathlib import Path

from src.recommender import load_songs, recommend_songs

# Resolve the CSV relative to the project root so the program runs from any directory.
SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"


def main() -> None:
    songs = load_songs(str(SONGS_CSV))

    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    profile_name = "High-Energy Pop"

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print(f"\nProfile: {profile_name}")
    print(f"Preferences: {user_prefs}")
    print(f"\nTop {len(recommendations)} recommendations:\n")
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        artist = song.get("artist")
        title = f"{song['title']} - {artist}" if artist else song["title"]
        print(f"{rank}. {title}")
        print(f"   Score: {score:.2f}")
        print(f"   Because: {explanation}")
        print()


if __name__ == "__main__":
    main()
