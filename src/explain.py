"""
Explanation renderers: baseline (mechanical) vs a specialized "DJ voice".

The original project always answered "why this song?" with a mechanical reason
list produced by the scorer: "genre match (+2.0), mood match (+1.0), energy
similarity (+0.85)". That stays as the BASELINE renderer.

Phase 3 adds a SPECIALIZED renderer with a deliberately constrained style:
  - it always anchors the pick to the closest seed song in the user's library,
  - it stays short and warm (DJ patter, not a spreadsheet),
  - it is grounded ONLY in real, matched attributes - it never invents a reason.

The rule that it must name a *real* seed song is what keeps the specialized
voice honest instead of a free-text hallucination. model_card.md reports the
measurable gap between the two styles (see compare_explanations).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.retrieval import norm, _tag_set, _as_float

# The specialized voice must stay short; this bounds the patter.
MAX_DJ_WORDS = 24

# Deterministic template bank (a few-shot style pattern set). Choice is keyed to
# the song title so a given song always gets the same line - reproducible.
_TEMPLATES = [
    "Cued up {title} because it rides the same {hook} as your {seed}.",
    "If {seed} is your thing, {title} sits right in that {hook} pocket.",
    "{title} lands next to your {seed} - same {hook} energy.",
    "Pulled {title} for you: it echoes the {hook} of {seed}.",
]


@dataclass
class SeedMatch:
    """The seed song a recommendation most resembles, and why."""
    seed: Dict
    similarity: float
    shared: List[str]  # real shared traits, most salient first (e.g. ["new jack swing", "happy"])


def _energy_word(energy: Optional[float]) -> Optional[str]:
    """A short human label for an energy value, or None if unknown."""
    if energy is None:
        return None
    if energy >= 0.66:
        return "high-energy"
    if energy <= 0.40:
        return "mellow"
    return "midtempo"


def closest_seed(song: Dict, seeds: List[Dict]) -> Optional[SeedMatch]:
    """
    Finds the seed song a recommendation most resembles, using the same signals
    as the scorer (genre, mood, energy, tags). Returns None if there are no
    seeds. Ties break on seed title so the result is deterministic.
    """
    best: Optional[SeedMatch] = None
    for seed in seeds:
        shared: List[str] = []
        similarity = 0.0

        if norm(song.get("genre")) and norm(song.get("genre")) == norm(seed.get("genre")):
            similarity += 2.0
            shared.append(str(seed.get("genre")))
        if norm(song.get("mood")) and norm(song.get("mood")) == norm(seed.get("mood")):
            similarity += 1.0
            shared.append(str(seed.get("mood")))

        song_e, seed_e = _as_float(song.get("energy")), _as_float(seed.get("energy"))
        if song_e is not None and seed_e is not None and abs(song_e - seed_e) <= 0.15:
            similarity += max(0.0, 1.0 - abs(song_e - seed_e))
            word = _energy_word(song_e)
            if word:
                shared.append(word)

        overlap = _tag_set(song.get("mood_tags")) & _tag_set(seed.get("mood_tags"))
        if overlap:
            similarity += min(0.5, 0.25 * len(overlap))
            shared.append(sorted(overlap)[0])

        candidate = SeedMatch(seed, similarity, shared)
        # Prefer higher similarity; break ties by seed title for stable output.
        if (best is None or candidate.similarity > best.similarity
                or (candidate.similarity == best.similarity
                    and str(seed.get("title")) < str(best.seed.get("title")))):
            best = candidate
    return best


def _pick_template(title: str) -> str:
    """Deterministically selects a template from the bank based on the title."""
    index = sum(ord(ch) for ch in title) % len(_TEMPLATES)
    return _TEMPLATES[index]


def dj_explanation(song: Dict, seeds: List[Dict], baseline_why: str = "") -> str:
    """
    Renders the specialized DJ-voice line for one recommendation.

    Falls back to the mechanical baseline when it cannot honestly anchor the
    pick to a real seed (no seeds, or nothing in common) - it will not fabricate
    a connection.
    """
    match = closest_seed(song, seeds)
    if match is None or not match.shared:
        return baseline_why or "recommended for you"

    hook = match.shared[0]
    line = _pick_template(str(song.get("title"))).format(
        title=song.get("title"), seed=match.seed.get("title"), hook=hook)

    # Enforce the "stay short" constraint.
    words = line.split()
    if len(words) > MAX_DJ_WORDS:
        line = " ".join(words[:MAX_DJ_WORDS]) + "..."
    return line


def _names_a_seed(text: str, seeds: List[Dict]) -> bool:
    """True if the explanation text mentions any seed song by title."""
    low = text.casefold()
    return any(str(seed.get("title", "")).casefold() in low
               for seed in seeds if seed.get("title"))


def compare_explanations(recommendations: List[Tuple[Dict, float, str]],
                         seeds: List[Dict]) -> Dict:
    """
    Measures the difference between the baseline and DJ-voice renderers over a
    set of recommendations. Returns aggregate metrics plus per-song lines, so
    model_card.md can show a concrete, measurable specialization effect.
    """
    rows = []
    for song, _score, baseline_why in recommendations:
        dj = dj_explanation(song, seeds, baseline_why)
        rows.append({
            "title": song.get("title"),
            "baseline": baseline_why,
            "dj": dj,
            "baseline_names_seed": _names_a_seed(baseline_why, seeds),
            "dj_names_seed": _names_a_seed(dj, seeds),
            "baseline_words": len(baseline_why.split()),
            "dj_words": len(dj.split()),
        })

    n = len(rows) or 1
    return {
        "count": len(rows),
        "baseline_seed_citation_rate": sum(r["baseline_names_seed"] for r in rows) / n,
        "dj_seed_citation_rate": sum(r["dj_names_seed"] for r in rows) / n,
        "baseline_avg_words": sum(r["baseline_words"] for r in rows) / n,
        "dj_avg_words": sum(r["dj_words"] for r in rows) / n,
        "rows": rows,
    }
