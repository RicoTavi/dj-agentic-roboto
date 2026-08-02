"""
Command-line entry point for the applied recommender system (DJ Agentic Roboto).

Pipeline:  seed songs -> derived taste profile -> agent (plan/retrieve/check/
refine) over the catalog -> ranked mixtape, with a confidence score and a
reasoning trace saved to a log file.

Usage:
    python -m src.app                                   # uses the example seeds
    python -m src.app --seeds data/seeds_example.csv
    python -m src.app --seeds my_songs.csv --k 8
    python -m src.app --trace logs/agent_run.md         # where to save the trace
"""

import argparse
from pathlib import Path

from src.agent import RecommenderAgent, format_trace
from src.guardrails import validate_seeds
from src.profile import derive_profile
from src.recommender import load_songs

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEEDS = ROOT / "data" / "seeds_example.csv"
DEFAULT_CATALOG = ROOT / "data" / "catalog.csv"
DEFAULT_TRACE = ROOT / "logs" / "agent_run.md"


def _build_source(profile, catalog, use_lastfm: bool):
    """Builds the retrieval source: local catalog alone, or local + Last.fm."""
    from src.retrieval import CompositeSource, LocalCatalogSource
    local = LocalCatalogSource(catalog)
    if not use_lastfm:
        return local

    from src.keys import load_lastfm_key
    from src.lastfm import build_lastfm_source
    key = load_lastfm_key()          # None -> cache-only (offline) mode
    lastfm, meta = build_lastfm_source(
        profile.dominant_genre, profile.dominant_mood, key,
        allow_network=key is not None)
    if meta["candidates"] == 0:
        print("(Last.fm added 0 candidates - no key and empty cache; "
              "using the local catalog only.)\n")
        return local
    mode = "live" if meta["network_used"] else "cached"
    print(f"Last.fm ({mode}) added {meta['candidates']} real candidate(s) to "
          "the pool.\n")
    return CompositeSource([local, lastfm])


def run(seeds_path: str, catalog_path: str, k: int, trace_path: str,
        voice: str = "baseline", use_lastfm: bool = True) -> int:
    """Runs one end-to-end recommendation and prints a readable report."""
    # --- Guardrail: seeds must be present and carry usable signals ------
    seeds = load_songs(seeds_path)
    ok, message = validate_seeds(seeds)
    if not ok:
        print(f"[guardrail] {message}")
        return 1

    catalog = load_songs(catalog_path)
    print(f"Loaded {len(seeds)} seed song(s) and {len(catalog)} catalog song(s).\n")

    # --- Derive taste + run the agent -----------------------------------
    profile = derive_profile(seeds)
    print("Your taste, learned from your seeds:")
    print(f"  {profile.explain()}\n")

    source = _build_source(profile, catalog, use_lastfm)
    agent = RecommenderAgent(source, profile, seeds, k=k)
    result = agent.run()

    # --- Report ---------------------------------------------------------
    print(f"Agent worked through {len(result.steps)} search step(s). "
          f"Confidence: {result.confidence_label.upper()} "
          f"({result.confidence:.2f}).")
    for note in result.notes:
        print(f"  ! {note}")
    print()

    if not result.recommendations:
        print("No recommendations: nothing in the catalog cleared the bar, so "
              "the agent declined rather than force a bad match.")
    else:
        from src.explain import dj_explanation
        print(f"Your mixtape (top {len(result.recommendations)}), "
              f"voice: {voice}:")
        for rank, (song, score, why) in enumerate(result.recommendations, 1):
            print(f"  {rank}. {song.get('title')} - {song.get('artist')} "
                  f"[{song.get('genre')}] (score {score:.2f})")
            reason = dj_explanation(song, seeds, why) if voice == "dj" else why
            print(f"       because: {reason}")

    # --- Save the reasoning trace ---------------------------------------
    trace = format_trace(result)
    Path(trace_path).parent.mkdir(parents=True, exist_ok=True)
    Path(trace_path).write_text(trace, encoding="utf-8")
    print(f"\nReasoning trace saved to {trace_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="DJ Agentic Roboto - agentic music recommender.")
    parser.add_argument("--seeds", default=str(DEFAULT_SEEDS),
                        help="CSV of songs you like (your library).")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG),
                        help="CSV catalog to recommend from.")
    parser.add_argument("--k", type=int, default=5,
                        help="How many songs to recommend (default: 5).")
    parser.add_argument("--trace", default=str(DEFAULT_TRACE),
                        help="Where to save the reasoning trace.")
    parser.add_argument("--voice", choices=["baseline", "dj"], default="baseline",
                        help="Explanation style (default: baseline).")
    parser.add_argument("--no-lastfm", action="store_true",
                        help="Use only the local catalog (skip Last.fm retrieval).")
    args = parser.parse_args()
    raise SystemExit(run(args.seeds, args.catalog, args.k, args.trace,
                         args.voice, use_lastfm=not args.no_lastfm))


if __name__ == "__main__":
    main()
