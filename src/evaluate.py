"""
Evaluation harness for the applied recommender system.

Runs the whole pipeline (guardrail -> profile -> agent) against a battery of
predefined inputs - the normal case plus the awkward ones (too few seeds, empty
input, garbage rows, a taste the catalog can't serve) - and prints a pass/fail
summary with each run's confidence. This is both the reliability evidence and
the test-harness stretch: it proves the system behaves as intended, including
when it should refuse.

Run it:
    python -m src.evaluate                 # prints a Markdown report, sets exit code
    python -m src.evaluate --out logs/eval_report.md
"""

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from src.agent import RecommenderAgent
from src.guardrails import validate_seeds
from src.profile import derive_profile
from src.recommender import load_songs
from src.retrieval import LocalCatalogSource

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog.csv"
DEFAULT_REPORT = ROOT / "logs" / "eval_report.md"


def _s(title, artist, genre, mood, energy, **extra) -> Dict:
    """Builds a seed/catalog song dict with sensible defaults."""
    base = dict(title=title, artist=artist, genre=genre, mood=mood,
                energy=energy, valence=0.6, tempo_bpm=112, danceability=0.82,
                acousticness=0.1, decade="1990s", popularity=50,
                mood_tags="dance", year=1990, language="english")
    base.update(extra)
    return base


@dataclass
class SystemOutcome:
    """Normalised result of running the pipeline once."""
    blocked: bool                 # guardrail refused the input before running
    block_reason: str
    recommendations: list
    confidence: float
    confidence_label: str         # 'none' when the agent honestly refused
    steps: int


def evaluate_seeds(seeds: List[Dict], catalog: List[Dict], k: int = 5) -> SystemOutcome:
    """Runs guardrail -> profile -> agent and returns a normalised outcome."""
    ok, reason = validate_seeds(seeds)
    if not ok:
        return SystemOutcome(True, reason, [], 0.0, "blocked", 0)
    profile = derive_profile(seeds)
    result = RecommenderAgent(LocalCatalogSource(catalog), profile, seeds, k=k).run()
    return SystemOutcome(False, "", result.recommendations, result.confidence,
                         result.confidence_label, len(result.steps))


@dataclass
class EvalCase:
    """One predefined test: an input, the behaviour we expect, and how to check it."""
    name: str
    input_desc: str
    expect_desc: str
    check: Callable[[SystemOutcome], bool]
    seeds: List[Dict]
    catalog: Optional[List[Dict]] = None   # None -> use the default catalog


# A tiny catalog with nothing near a high-energy dance taste, to test refusal.
_FARAWAY_CATALOG = [
    _s("Fog", "Drift", "ambient", "chill", 0.05, mood_tags="space",
       decade="2020s", tempo_bpm=58),
    _s("Haze", "Mist", "ambient", "chill", 0.08, mood_tags="calm",
       decade="2020s", tempo_bpm=60),
]

# A coherent, healthy taste (mirrors the real example library).
_HEALTHY_SEEDS = [
    _s("Weekend Kind of Love", "Andre Sotto", "new jack swing", "happy", 0.80),
    _s("Cassette Crush", "Ronnie Blaze", "new jack swing", "happy", 0.82),
    _s("Payday Swing", "The Fresh Committee", "new jack swing", "happy", 0.84),
    _s("Club Lights Fade", "Lisette Cruz", "freestyle", "sad", 0.83,
       mood_tags="heartbreak"),
    _s("Boulevard Beat", "Q-Town Crew", "freestyle", "intense", 0.87,
       mood_tags="club"),
]


def build_cases() -> List[EvalCase]:
    return [
        EvalCase(
            "typical_taste",
            "5 coherent new jack swing / freestyle seeds",
            "returns a full set with medium/high confidence",
            lambda o: (not o.blocked and len(o.recommendations) == 5
                       and o.confidence_label in {"high", "medium"}),
            _HEALTHY_SEEDS,
        ),
        EvalCase(
            "too_few_seeds",
            "only 2 seeds",
            "still answers, but flags low/medium confidence",
            lambda o: (not o.blocked and len(o.recommendations) >= 1
                       and o.confidence_label in {"low", "medium"}),
            _HEALTHY_SEEDS[:2],
        ),
        EvalCase(
            "empty_input",
            "no seed songs at all",
            "guardrail blocks with a clear message",
            lambda o: o.blocked,
            [],
        ),
        EvalCase(
            "garbage_rows",
            "rows with no genre, mood, or energy",
            "guardrail blocks (can't learn a taste from noise)",
            lambda o: o.blocked,
            [dict(title="???", artist="???", genre="", mood="", energy="")],
        ),
        EvalCase(
            "genre_not_in_catalog",
            "a cumbia taste (catalog has almost none)",
            "widens past genre (2+ steps) and still answers",
            lambda o: not o.blocked and o.steps >= 2 and len(o.recommendations) >= 1,
            [_s("Mi Cumbia", "Fan", "cumbia", "happy", 0.72, mood_tags="festive",
                decade="2020s")] * 3,
        ),
        EvalCase(
            "nothing_fits",
            "high-energy dance taste vs an ambient-only crate",
            "honestly refuses rather than force a weak match",
            lambda o: (not o.blocked and o.recommendations == []
                       and o.confidence_label == "none"),
            _HEALTHY_SEEDS,
            _FARAWAY_CATALOG,
        ),
    ]


def run_report(catalog_path: str, out_path: Optional[str]) -> int:
    """Runs every case, prints a Markdown report, returns process exit code."""
    default_catalog = load_songs(catalog_path)
    cases = build_cases()

    lines = ["# Evaluation Report", "",
             "| Case | Input | Expected behavior | Confidence | Result |",
             "| --- | --- | --- | --- | --- |"]
    passed = 0
    for case in cases:
        catalog = case.catalog if case.catalog is not None else default_catalog
        outcome = evaluate_seeds(case.seeds, catalog)
        ok = bool(case.check(outcome))
        passed += ok
        conf = ("blocked" if outcome.blocked
                else f"{outcome.confidence_label} ({outcome.confidence:.2f})")
        verdict = "PASS" if ok else "FAIL"
        lines.append(f"| {case.name} | {case.input_desc} | {case.expect_desc} "
                     f"| {conf} | {verdict} |")

    total = len(cases)
    summary = f"**{passed} of {total} checks passed.**"
    lines += ["", summary, ""]
    report = "\n".join(lines)

    print(report)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(report + "\n", encoding="utf-8")
        print(f"Report written to {out_path}")
    return 0 if passed == total else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the recommender system.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--out", default=str(DEFAULT_REPORT),
                        help="Where to write the Markdown report (default: logs/).")
    args = parser.parse_args()
    raise SystemExit(run_report(args.catalog, args.out))


if __name__ == "__main__":
    main()
