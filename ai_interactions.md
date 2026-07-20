# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agentic Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

The whole project was built collaboratively with Claude Code (Anthropic's coding
agent), working from a written instruction file that defined when the agent could act
independently (implementing starter functions, running tests, fixing import errors)
and when it had to stop for a decision (scoring weights, dataset changes, experiments,
git operations, anything reflective or first-person).

For the stretch features specifically, the agent was asked to add five new song
attributes (`year`, `decade`, `popularity`, `mood_tags`, `language`) across all 20
songs, wire the new attributes into the scoring logic, implement an artist repetition
penalty, build four switchable ranking modes, and replace the plain CLI output with a
formatted table — then update every affected document so the README output stayed
byte-identical to a live program run.

**Prompts used:**

Representative prompts from the sessions (paraphrased where long):

- "Take a look at assignment.md and let me know if you understand the asks there."
- "For the scoring recipe... let's take it as is... what options could there be?" —
  which led the agent to run four candidate recipes against the real catalog and show
  the ranking differences before locking the weights.
- "Where do we get the data for the dataset you'd like to expand?" — which surfaced
  that the agent would otherwise have invented songs, and led to real tracks being
  supplied by me instead.
- "R&B is fine but NGL... for African American music I feel like it's too broad" —
  which changed the genre labelling from one broad `r&b` bucket to precise labels
  (`new jack swing`, `freestyle`, `hip hop`), and later became the basis of the
  controlled experiment.
- "Here is the rubric... can you act as a grader and see if full points are present" —
  which caught a missing requirement (the explanation of how real-world recommenders
  work) that was then written.

**What did the agent generate or change?**

- `src/recommender.py` — all core functions (`load_songs`, `score_song`,
  `recommend_songs`, the `Recommender` class), later the `RankingMode` strategy
  objects, the optional decade/tag/popularity signals, and the artist penalty.
- `src/main.py` — profile/edge-case runner, `--mode` command-line switch, ASCII table.
- `data/songs.csv` — the agent added the rows and new columns; the ten real songs were
  chosen by me, and the agent looked up tempos and release years from public sources.
- `README.md` and `model_card.md` — drafted by the agent from actual program output
  and observed results, reviewed by me.
- A controlled experiment (genre-family partial credit) that was implemented, measured,
  shown to change almost nothing, and reverted on my decision.

**What did you verify or fix manually?**

- The agent's prediction for the experiment was wrong: it predicted TLC's "Creep"
  would reach roughly rank 5 with partial genre credit; the song only moved from 15th
  to 11th, because partial credit lifted every related song at once. The agent flagged
  its own error, but the lesson stands — agent predictions needed checking against
  actual runs.
- The agent initially proposed labelling all the added songs as one broad `r&b`
  genre. I pushed back that the label was too broad for Black American music, and the
  labelling was corrected to `new jack swing` / `r&b` / `freestyle` / `hip hop`.
- The agent mis-cited a ranking (13th vs 15th) in one draft — a stale number from an
  earlier, smaller version of the catalog — and corrected it on re-verification.
- I supplied a release year of 1988 for one song; the agent verified it against public
  sources and corrected it to 1989.
- All decision points (scoring weights, keeping vs reverting the experiment, commits
  and pushes, which stretch features to attempt) were decided by me, with the agent
  providing a recommendation and the measured evidence for it.

---

## Design Pattern (SF10)

> Document how AI helped you choose or implement a design pattern.

**Which design pattern did you use?**

The **Strategy pattern**, for the ranking modes.

**How did AI help you brainstorm or implement it?**

The groundwork came from an earlier design conversation: before implementing anything,
the agent ran four candidate scoring recipes (balanced, flat weights, mismatch
penalties, energy-first) against the real catalog and showed how each one ranked the
same profiles. That comparison established that a "scoring recipe" is really just a
set of weights flowing through identical logic — which is exactly the insight the
Strategy pattern captures.

When the stretch feature asked for multiple ranking modes, the agent proposed
formalising that insight: each mode became a named, frozen `RankingMode` object
holding its weights, registered in a `RANKING_MODES` dictionary, with `score_song`
consulting whichever mode is active. Adding a new mode requires no new scoring code —
only a new entry with different numbers.

**How does the pattern appear in your final code?**

- `src/recommender.py` — the `RankingMode` dataclass and the `RANKING_MODES` registry
  (`balanced`, `mood-first`, `energy`, `crowd-pleaser`), with `DEFAULT_MODE` pointing
  at `balanced`. `score_song(user_prefs, song, mode)` reads every weight from the
  active strategy.
- `src/main.py` — the `--mode` command-line argument selects a strategy by name, so a
  user can switch ranking behaviour without touching any code:
  `python -m src.main --mode crowd-pleaser`.
