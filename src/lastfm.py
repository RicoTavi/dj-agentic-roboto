"""
Last.fm as a second retrieval source (RAG multi-source).

The local catalog is small and fixed. Last.fm adds a live corpus of *real*
tracks tagged with the listener's dominant genre and mood. Because Last.fm only
gives us tags (not the energy/tempo/valence the scorer reads), retrieved tracks
are tagged with just what Last.fm actually asserts - the genre or mood we
queried - and their energy is left blank. The scorer already ignores missing
signals, so these tracks are scored honestly on what we know, never on invented
numbers.

Reproducibility: every response is trimmed and cached to a committed JSON file
(data/lastfm_cache.json). With a key, a cache miss fetches live and updates the
cache; without a key (or offline), the source reads the cache only. Grading
therefore needs no key and no network. The API key is read via src/keys.py and
never logged or stored in the cache.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.retrieval import RetrievalQuery, _matches

API_ROOT = "http://ws.audioscrobbler.com/2.0/"
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE = ROOT / "data" / "lastfm_cache.json"
REQUEST_TIMEOUT = 10
DEFAULT_LIMIT = 30


# -- Cache helpers --------------------------------------------------------
def load_cache(path: Path) -> Dict[str, list]:
    """Loads the trimmed-response cache, or an empty cache if none exists."""
    if Path(path).exists():
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def save_cache(path: Path, cache: Dict[str, list]) -> None:
    """Writes the cache back as pretty JSON (committed reproducibility evidence)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")


# -- Fetch ----------------------------------------------------------------
def _fetch_tag_top_tracks(tag: str, key: Optional[str], limit: int) -> List[Dict]:
    """Calls Last.fm tag.getTopTracks and returns trimmed {title, artist} dicts.

    Returns [] on any error or when no key is available - a missing/empty
    result is a supported state, not a crash. The key is never logged.
    """
    if not key:
        return []
    params = urllib.parse.urlencode({
        "method": "tag.gettoptracks", "tag": tag, "api_key": key,
        "format": "json", "limit": limit,
    })
    try:
        with urllib.request.urlopen(f"{API_ROOT}?{params}", timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    tracks = data.get("tracks", {}).get("track", []) if isinstance(data, dict) else []
    trimmed = []
    for track in tracks:
        title = track.get("name")
        artist = (track.get("artist") or {}).get("name")
        if title and artist:
            trimmed.append({"title": title, "artist": artist})
    return trimmed


def tag_top_tracks(tag: str, key: Optional[str], cache: Dict[str, list],
                   limit: int = DEFAULT_LIMIT, allow_network: bool = True) -> List[Dict]:
    """Cache-first lookup of top tracks for a tag. Fetches live only on a miss."""
    cache_key = f"tag.gettoptracks::{tag.strip().casefold()}::{limit}"
    if cache_key in cache:
        return cache[cache_key]
    if not allow_network:
        return []
    fetched = _fetch_tag_top_tracks(tag, key, limit)
    if fetched:                       # only cache real results, so a transient
        cache[cache_key] = fetched    # empty fetch can be retried later
    return fetched


# -- Source ---------------------------------------------------------------
def _to_candidate(title: str, artist: str, field: str, tag: str) -> Dict:
    """Builds a catalog-shaped song dict, tagging ONLY the field Last.fm asserts."""
    song = {"title": title, "artist": artist, "genre": "", "mood": "",
            "energy": "", "tempo_bpm": "", "valence": "", "danceability": "",
            "acousticness": "", "decade": "", "popularity": "",
            "mood_tags": tag, "language": "", "source": "last.fm"}
    song[field] = tag                 # 'genre' or 'mood' = the tag we queried
    return song


class LastfmSource:
    """A retrieval source backed by pre-fetched Last.fm candidates."""

    name = "last.fm"

    def __init__(self, candidates: List[Dict]):
        self.songs = list(candidates)

    def search(self, query: RetrievalQuery) -> List[Dict]:
        return [song for song in self.songs if _matches(song, query)]


def build_lastfm_source(genre: Optional[str], mood: Optional[str],
                        key: Optional[str], cache_path: Path = DEFAULT_CACHE,
                        allow_network: bool = True, limit: int = DEFAULT_LIMIT
                        ) -> Tuple[LastfmSource, Dict]:
    """
    Builds a LastfmSource for a taste by fetching (or reading cached) top tracks
    for the dominant genre and mood. Returns the source plus a small meta dict
    for reporting (how many candidates, whether the network was used).
    """
    cache = load_cache(cache_path)
    before = json.dumps(cache, sort_keys=True)

    candidates: List[Dict] = []
    seen = set()
    # (tag, which scorer field the tag maps to). Genre first so a track tagged
    # both genre and mood keeps its stronger genre attribution.
    queries = [(genre, "genre"), (mood, "mood")]
    for tag, field in queries:
        if not tag:
            continue
        for row in tag_top_tracks(tag, key, cache, limit, allow_network):
            dedupe_key = (row["title"].casefold(), row["artist"].casefold())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            candidates.append(_to_candidate(row["title"], row["artist"], field, tag))

    if json.dumps(cache, sort_keys=True) != before:
        save_cache(cache_path, cache)

    meta = {"candidates": len(candidates),
            "network_used": bool(key) and allow_network,
            "cache_path": str(cache_path)}
    return LastfmSource(candidates), meta
