"""
The recommender agent: a deterministic plan -> retrieve -> check -> refine loop.

This is the project's "AI feature". Instead of scoring a fixed 20-song list, the
agent *reasons about its own search*:

  1. PLAN     - turn the derived taste profile into a retrieval query.
  2. RETRIEVE - ask a source for candidate songs (excluding the user's seeds).
  3. SCORE    - rank candidates with the ORIGINAL scorer (unchanged - still the
                brain of the system).
  4. CHECK    - critique the result: enough songs? good enough?
  5. REFINE   - if not, widen the query and try again; otherwise stop.

Every iteration records a trace (plan/action/observation/decision) so the
reasoning can be saved to a log and audited. The loop is fully deterministic, so
the same seeds always produce the same trace - which makes it reproducible
evidence for grading, not a black box.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.profile import TasteProfile
from src.recommender import recommend_songs
from src.retrieval import RetrievalQuery, norm

# A recommendation must clear this score to count as a genuinely good match.
# Below it, the agent would rather widen the search than serve a weak pick.
MIN_SCORE = 2.0
# Absolute floor: if even the best-effort pick (after widening to the whole
# catalog) scores below this, the agent declines entirely rather than force a
# bad match. This is the honest-AI guardrail: "I've got nothing good for you."
REFUSE_BELOW = 1.0
DEFAULT_K = 5
MAX_ENERGY_TOLERANCE = 0.15

Ranked = Tuple[Dict, float, str]  # (song, score, why) as returned by the scorer


@dataclass
class AgentStep:
    """One iteration of the loop, captured for the reasoning trace."""
    iteration: int
    plan: str
    action: str
    observation: str
    decision: str


@dataclass
class AgentResult:
    """The outcome of a full agent run."""
    recommendations: List[Ranked]
    steps: List[AgentStep]
    confidence: float
    confidence_label: str
    notes: List[str] = field(default_factory=list)
    profile: Optional[TasteProfile] = None


class RecommenderAgent:
    """Plans, retrieves, checks, and refines to build a recommendation set."""

    def __init__(self, source, profile: TasteProfile, seed_songs: List[Dict],
                 k: int = DEFAULT_K, min_score: float = MIN_SCORE):
        self.source = source
        self.profile = profile
        self.seed_songs = seed_songs
        self.k = k
        self.min_score = min_score

    # -- Planning: the widening ladder -----------------------------------
    def _stages(self) -> List[RetrievalQuery]:
        """
        Ordered queries from most specific to most general. The agent starts at
        the top and steps down only when a stage's results are too thin. Stages
        that the profile can't support (e.g. no dominant genre) are skipped.
        """
        p = self.profile
        stages: List[RetrievalQuery] = []
        if p.dominant_genre and p.mean_energy is not None:
            stages.append(RetrievalQuery(
                genre=p.dominant_genre, energy=p.mean_energy,
                energy_tolerance=MAX_ENERGY_TOLERANCE,
                label=f"{p.dominant_genre} near energy {p.mean_energy:.2f}"))
        if p.dominant_genre:
            stages.append(RetrievalQuery(
                genre=p.dominant_genre, label=f"any {p.dominant_genre}"))
        if p.dominant_mood:
            stages.append(RetrievalQuery(
                mood=p.dominant_mood, label=f"any {p.dominant_mood} song"))
        if p.top_tags:
            stages.append(RetrievalQuery(
                tags=p.top_tags, label=f"tag overlap with {p.top_tags[:3]}"))
        stages.append(RetrievalQuery(label="entire catalog (last resort)"))
        return stages

    # -- The loop --------------------------------------------------------
    def run(self) -> AgentResult:
        seed_keys = {(norm(s.get("title")), norm(s.get("artist")))
                     for s in self.seed_songs}
        prefs = self.profile.to_prefs()
        stages = self._stages()

        steps: List[AgentStep] = []
        best: Optional[Tuple[List[Ranked], int]] = None  # (ranked, stage_index)
        accepted = False

        for i, query in enumerate(stages):
            last_stage = (i == len(stages) - 1)
            plan = f"Search for {query.describe()}."

            candidates = [s for s in self.source.search(query)
                          if (norm(s.get("title")), norm(s.get("artist"))) not in seed_keys]
            action = (f"Retrieved {len(candidates)} candidate(s) from "
                      f"{self.source.name} (after removing your seeds).")

            if not candidates:
                observation = "Nothing matched this query."
                decision = ("Widen the search." if not last_stage
                            else "Out of options: recommend nothing.")
                steps.append(AgentStep(i, plan, action, observation, decision))
                continue

            ranked = recommend_songs(prefs, candidates, k=self.k)
            top_score = ranked[0][1] if ranked else 0.0
            distinct_artists = len({norm(r[0].get("artist")) for r in ranked})
            enough = len(ranked) >= self.k
            good = top_score >= self.min_score

            observation = (f"Top score {top_score:.2f}; {len(ranked)} ranked; "
                           f"{distinct_artists} distinct artist(s).")

            # Track the strongest result seen so far as a fallback.
            if best is None or top_score > best[0][0][1]:
                best = (ranked, i)

            if good and enough:
                decision = "Accept: strong matches and a full set."
                steps.append(AgentStep(i, plan, action, observation, decision))
                best = (ranked, i)
                accepted = True
                break

            reasons = []
            if not good:
                reasons.append(f"top score {top_score:.2f} < {self.min_score}")
            if not enough:
                reasons.append(f"only {len(ranked)} of {self.k} slots filled")
            joined = "; ".join(reasons)
            decision = (f"Widen the search ({joined})." if not last_stage
                        else f"Last resort reached; return best effort ({joined}).")
            steps.append(AgentStep(i, plan, action, observation, decision))

        # Decide the final set, applying the honest-refusal floor.
        refusal_note = None
        if best is None:
            recommendations, stage_index = [], len(stages)
            refusal_note = "No candidate matched any query."
        else:
            ranked, stage_index = best
            if ranked[0][1] < REFUSE_BELOW:
                recommendations = []
                refusal_note = (f"Best possible match scored only "
                                f"{ranked[0][1]:.2f} (< {REFUSE_BELOW}); too "
                                "weak to recommend honestly.")
            else:
                recommendations = ranked[:self.k]

        confidence, label, notes = self._confidence(
            recommendations, stage_index, accepted, len(stages), refusal_note)
        return AgentResult(recommendations, steps, confidence, label, notes,
                           self.profile)

    # -- Confidence scoring ----------------------------------------------
    def _confidence(self, recs: List[Ranked], stage_index: int,
                    accepted: bool, num_stages: int,
                    refusal_note: Optional[str] = None):
        """Rates how much to trust the result (an honest-AI signal)."""
        notes: List[str] = []
        if not recs:
            reason = refusal_note or "No song cleared the bar."
            return 0.0, "none", [
                f"{reason} The agent returned nothing rather than force a bad "
                "match."]

        # Earlier (more specific) stages mean a more on-target match.
        confidence = max(0.2, 1.0 - 0.2 * stage_index)
        if not self.profile.is_confident:
            confidence *= 0.6
            notes.append(f"Only {self.profile.seed_count} seed song(s) - the "
                         "taste profile itself is low-confidence.")
        if not accepted:
            confidence *= 0.7
            notes.append("No stage fully cleared the bar; these are best-effort "
                         "picks from a widened search.")

        confidence = round(confidence, 2)
        label = ("high" if confidence >= 0.75
                 else "medium" if confidence >= 0.45 else "low")
        return confidence, label, notes


# -- Trace rendering ------------------------------------------------------
def format_trace(result: AgentResult, title: str = "Agent Reasoning Trace") -> str:
    """Renders an AgentResult as a Markdown reasoning trace."""
    lines = [f"# {title}", ""]
    if result.profile is not None:
        lines += [f"**Derived taste:** {result.profile.explain()}", ""]
    lines += [f"**Confidence:** {result.confidence_label} "
              f"({result.confidence:.2f})", ""]
    for note in result.notes:
        lines.append(f"> {note}")
    if result.notes:
        lines.append("")

    lines.append("## Reasoning steps")
    for step in result.steps:
        lines += [
            f"### Iteration {step.iteration}",
            f"- **Plan:** {step.plan}",
            f"- **Action:** {step.action}",
            f"- **Observation:** {step.observation}",
            f"- **Decision:** {step.decision}",
            "",
        ]

    lines.append("## Final recommendations")
    if not result.recommendations:
        lines.append("_None - the agent declined to recommend._")
    else:
        for rank, (song, score, why) in enumerate(result.recommendations, 1):
            lines.append(f"{rank}. **{song.get('title')}** - "
                         f"{song.get('artist')} "
                         f"(score {score:.2f}) - {why}")
    lines.append("")
    return "\n".join(lines)
