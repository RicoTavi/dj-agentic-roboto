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
from src.profile import derive_profile
from src.recommender import load_songs

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEEDS = ROOT / "data" / "seeds_example.csv"
DEFAULT_CATALOG = ROOT / "data" / "catalog.csv"
DEFAULT_TRACE = ROOT / "logs" / "agent_run.md"


def run(seeds_path: str, catalog_path: str, k: int, trace_path: str) -> int:
    """Runs one end-to-end recommendation and prints a readable report."""
    # --- Guardrail: seeds must load and be non-empty --------------------
    seeds = load_songs(seeds_path)
    if not seeds:
        print(f"[guardrail] No seed songs found in {seeds_path}. "
              "Give me a few songs you like and I'll learn your taste.")
        return 1

    catalog = load_songs(catalog_path)
    print(f"Loaded {len(seeds)} seed song(s) and {len(catalog)} catalog song(s).\n")

    # --- Derive taste + run the agent -----------------------------------
    profile = derive_profile(seeds)
    print("Your taste, learned from your seeds:")
    print(f"  {profile.explain()}\n")

    from src.retrieval import LocalCatalogSource
    agent = RecommenderAgent(LocalCatalogSource(catalog), profile, seeds, k=k)
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
        print(f"Your mixtape (top {len(result.recommendations)}):")
        for rank, (song, score, why) in enumerate(result.recommendations, 1):
            print(f"  {rank}. {song.get('title')} - {song.get('artist')} "
                  f"[{song.get('genre')}] (score {score:.2f})")
            print(f"       because: {why}")

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
    args = parser.parse_args()
    raise SystemExit(run(args.seeds, args.catalog, args.k, args.trace))


if __name__ == "__main__":
    main()
