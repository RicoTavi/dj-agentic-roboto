# 🎧 Model Card: Music Recommender Simulation

> **This is a simplified educational simulation built for a course assignment.**
> It is not a production system, it was not evaluated against real users, and it
> should not be compared to a commercial recommender.

## 1. Model Name  

**VibeMatch 1.0** — a content-based music recommender.

<!-- Rename this if you'd prefer something else; the name is yours to pick. -->

---

## 2. Intended Use  

This model is for classroom exploration. It exists to demonstrate how a recommender
turns song attributes and a stated preference into a ranked list, and to make the
reasoning behind each recommendation visible.

It generates a top-k list of songs from a fixed 20-song catalog, with a numeric score
and a plain-English reason for every result.

It assumes the user can state their taste directly as one favourite genre, one
favourite mood, and one target energy level. It assumes those three fields are enough
to describe what someone wants to hear right now.

It is not built for real users and has no way to serve them.

---

## 3. How the Model Works  

Every song is described by a few labels and numbers: a genre, a mood, and an energy
rating from 0 to 1. A listener describes themselves the same way — one genre, one mood,
one energy level they are in the mood for.

The model compares the listener's description to each song, one song at a time, and
adds up points:

- The song's genre is the same as the listener's favourite genre: **2 points**
- The song's mood is the same as the listener's favourite mood: **1 point**
- The song's energy is close to the listener's target: **up to 1 point**, scaled by how
  close it is. Identical energy earns the full point; opposite extremes earn nothing.

The highest possible score is 4. Once every song has a score, they are sorted from
highest to lowest and the top five are shown, along with the reasons that produced each
score.

Genre is deliberately worth more than mood and energy combined. That makes the results
predictable and easy to explain, and it is also the model's biggest source of bias.

Two optional preferences can add to the score, but only when the listener states them:
a favourite decade (half a point) and a list of mood words that are checked against
each song's tags (up to half a point).

**Ranking modes.** The weighting above is the default, called *balanced*. The model
also offers three alternative strategies the user can switch to: *mood-first* (mood
outweighs genre), *energy* (only energy similarity counts), and *crowd-pleaser* (the
balanced recipe plus a bonus of up to 1.5 points for popular songs). Each mode is just
a different set of weights flowing through the same scoring logic.

**Fairness: the artist repetition penalty.** Without intervention, a strong artist can
occupy several slots of a five-song list — in testing, one artist held two of the top
four for the new jack swing profile. The model now subtracts 0.75 points from a song
for each track by the same artist already selected above it. This improves fairness in
two directions: listeners see more variety instead of a single artist's catalog, and
other artists are not crowded out of short lists by one dominant name. The deduction is
printed in the song's reasons whenever it fires, so the adjustment is visible rather
than silent. Its limits are noted in section 6.

**Changes from the starter logic:** the starter project contained only function
signatures and placeholder returns. All scoring, loading, and ranking behaviour
described here was added, along with ten additional songs.

---

## 4. Data  

The catalog is `data/songs.csv`: **20 songs, 12 genres, 7 moods**, with energy values
ranging from 0.28 to 0.95.

Ten songs came with the starter project and are fictional. Ten real songs were added,
mostly late-1980s and 1990s new jack swing, freestyle, hip hop, R&B, and eurodance.

Genre counts: new jack swing 4, lofi 3, pop 2, freestyle 2, eurodance 2, and one each of
rock, ambient, jazz, synthwave, indie pop, r&b, and hip hop.

Mood counts: happy 5, intense 4, chill 3, moody 3, and one each of relaxed, focused,
and sad.

Each song carries fifteen fields. Five were added as a stretch feature: release year,
decade, a 0–100 popularity estimate, a short list of mood tags, and language.

**Important caveat about the numbers.** The `energy`, `valence`, `danceability`, and
`acousticness` values imitate the audio-analysis features a streaming service computes
from a waveform. Here they were assigned by hand. Only the `tempo_bpm` values for the
real songs were looked up from public sources. Of the added fields, release years for
the ten real songs are real; years for the fictional songs are invented, and the
popularity values are estimates throughout — informed by chart performance for the real
songs, invented for the fictional ones. The mood tags were authored by hand. No audio was analysed.

**What is missing from the data:** release year, lyrics, language, popularity, listening
history, and any information about scenes, eras, or artist lineage.

---

## 5. Strengths  

The model behaves correctly and predictably when a profile lines up with a
well-represented part of the catalog:

- Profiles with several songs in their genre produce clean, defensible rankings. The
  NJS Party and Chill Lofi profiles each returned a perfect 4.00 top result — a song
  matching genre, mood, and energy exactly.
- **Every recommendation is explainable.** The score always decomposes into named
  reasons, so it is never unclear why a song appeared.
- **Conflicting preferences resolve sensibly.** A profile asking for a sad mood at 0.85
  energy correctly surfaced a heartbreak lyric at 119 BPM rather than defaulting to a
  slow song.
- **Bad input does not produce false confidence in scoring.** Missing, empty, or
  unparseable values earn zero points rather than accidentally counting as a match.

Adding real songs to the catalog made these strengths much easier to judge. With
fictional songs there was no way to tell whether a good-looking score corresponded to a
sensible recommendation.

---

## 6. Limitations and Bias

**Features it does not consider.** Lyrics, language, release year, popularity, artist
lineage, scene, and listening history. Four columns that exist in the data — `valence`,
`danceability`, `acousticness`, and `tempo_bpm` — are loaded but never scored.

**Uneven genre resolution.** The catalog treats `lofi`, `ambient`, `synthwave`, and
`indie pop` as four separate genres while asking a single `r&b` label to cover a much
broader range of music. Splitting one tradition finely while flattening another is a
bias in the labelling itself, before any code runs.

**Exact string matching.** Related genres score identically to unrelated ones. TLC's
"Creep" ranks 15th of 20 for a new jack swing profile, partly because `r&b` and
`new jack swing` are different strings.

**Genre overfitting.** At 2 points, genre outweighs a perfect mood and energy match
combined. A song in the right genre that matches nothing else still beats a song that
matches everything else.

**Underrepresentation.** Eight of twelve genres contain exactly one song. Only one song
in the entire catalog is labelled sad. Listeners whose taste falls in a thin part of the
catalog get worse results through no fault of their own.

**Filter bubbles by construction.** The fictional starter songs and the added real songs
share no genres. A profile aimed at one group can never surface the other.

**The diversity control is narrow.** The artist repetition penalty only sees artist
names. Repetition of genre, mood, or era is never penalised, the 0.75 deduction is a
hand-picked constant rather than a measured one, and an artist releasing under two
names would evade it entirely.

**Estimated values feed real rankings.** The popularity numbers that drive the
crowd-pleaser mode, and the mood tags that can add up to half a point, were both
authored by hand. Any bias in those estimates flows directly into the rankings.

**False confidence.** The model always returns five results, formatted identically,
whether the top score is 4.00 or 0.95. It has no way to say "I have nothing good for
this request." When asked for a genre absent from the catalog, it silently ranked on
mood and energy alone without reporting that the genre was never found.

**No understanding of meaning.** The model scores how a song is labelled, never what it
is about. A record can sound bright and be about betrayal; a novelty song and a sincere
one are indistinguishable if their attributes match.

**Cold start.** A new song can be recommended immediately from its attributes, but the
model learns nothing from behaviour, so it cannot improve as a listener uses it.

---

## 7. Evaluation  

Three user profiles and two edge cases were run, and the full output is reproduced in
the README.

| Profile | Preferences | Top result | Score |
| --- | --- | --- | --- |
| NJS Party | new jack swing / happy / 0.80 | On Our Own — Bobby Brown | 4.00 |
| Freestyle Heartbreak | freestyle / sad / 0.85 | No Reason to Cry — Judy Torres | 3.97 |
| Chill Lofi | lofi / chill / 0.35 | Library Rain — Paper Lanterns | 4.00 |
| EDGE: genre not in catalog | reggaeton / happy / 0.70 | Rooftop Lights — Indigo Parade | 1.94 |
| EDGE: max energy, no categorical prefs | "" / "" / 1.00 | Barbie Girl — Aqua | 0.95 |

What was checked: that scores descend, that reasons match their songs, that the top
result was defensible for the stated profile, and that edge cases degrade sensibly
rather than crashing.

Behaviour was also verified for an empty catalog, a `k` larger than the catalog, `k=0`,
missing and unparseable numeric values, out-of-range energy values, and case
differences in genre and mood strings. The original song list is never mutated by
ranking.

**One controlled experiment was run and reverted.** Awarding partial credit for related
genres was predicted to lift TLC's "Creep" into the top five. It did not — the song rose
only from 15th to 11th, because partial credit lifts every related song at once. A
follow-up sweep showed that even when a related genre earned as much as an exact match,
"Creep" never entered the top five: it misses on mood and energy as well as genre. The
experiment was reverted and documented in the README.

**Limits of this evaluation.** Five profiles is a demonstration, not a measurement.
There is no ground truth, no accuracy metric, and no real users. The profiles were
written by the same people who designed the scoring rules, so the evaluation partly
confirms that the system does what it was built to do. Half the catalog is fictional and
cannot be judged against real intuition at all.

Little in the evaluation was surprising, in part because the scoring rules were laid out
by the assignment rather than designed from scratch — the results largely matched what
the rules predicted.

---

## 8. Future Work  

- **Genre hierarchies** so related genres earn partial credit — but derived from a
  recognised music taxonomy rather than hand-written opinion, which is why the
  experimental version was reverted.
- **A confidence threshold**, so the model can return two results instead of padding to
  five, or state that it found no good match.
- **Multi-value profiles**, so a listener can like more than one genre or mood.
- **Use the still-unused columns** — `valence`, `danceability`, `acousticness`,
  `tempo_bpm`, `language`, and the `likes_acoustic` preference that is declared but
  never read.
- **Broaden the diversity penalty** beyond artist names, to genre, mood, or era
  repetition — and derive the penalty size from data instead of picking it by hand.
- **Era and scene as features**, which is the information the genre experiment showed
  the model was actually missing.
- **A larger, more balanced catalog**, ideally with feature values that were measured
  rather than assigned.

---

## 9. Personal Reflection  

The clearest thing I took from this project was how much the quality of the data affects
your ability to judge the system. Working with fictional songs, I had no way to tell
whether a recommendation was good. Once I added real songs, the connection between the
scoring rules and the output became much easier to see.

I was not especially surprised by the results, partly because I did not build the
scoring from scratch — the structure was already laid out by the assignment. Given the
option I would have approached it differently, and I would want to spend more time on
collecting real listening data rather than asking users to describe their own taste up
front.

---

# Project 4 Extension — DJ Agentic Roboto (Applied AI System)

This section documents the Module 4 extension that turns the base recommender into
an agentic, multi-source applied AI system. It answers the required reflection
prompts: limitations and biases, potential misuse, testing surprises, and AI
collaboration (one helpful and one flawed suggestion).

## 10. Data Provenance and Disclosure

The retrieval catalog (`data/catalog.csv`) is a **deliberate mix of real and
fictional tracks**. Roughly ten entries are real songs in the project's core genres
(new jack swing, freestyle, R&B — e.g. Bobby Brown, Bell Biv DeVoe, Exposé, Pajama
Party, Mary J. Blige); the rest are fictional placeholders that provide off-genre
variety. **All audio-feature values (energy, valence, danceability, acousticness)
are approximate and hand-labeled, not measured.** Tracks retrieved live from Last.fm
(`data/lastfm_cache.json`) are real, but carry only the genre/mood tag Last.fm
asserts — their energy and other numeric features are intentionally left blank
rather than fabricated.

## 11. Limitations and Bias (Extension)

- **Popularity bias.** Last.fm's `tag.getTopTracks` returns the *most-played* tracks
  for a tag, so live retrieval skews toward popular and recent music.
- **Noisy community tags.** Last.fm tags are crowd-sourced and unreliable: a query
  for "new jack swing" returns genuine tracks (Bobby Brown, Jade) alongside clear
  mistags (Sabrina Carpenter, NewJeans, PinkPantheress). The system trusts the tag,
  so this noise flows into candidates.
- **Sparse attributes for retrieved tracks.** Because Last.fm tracks have no energy
  value, they are scored on genre/mood alone and always rank below fully-attributed
  local songs — informative, but it caps how high a discovered track can rank.
- **No natural-language understanding.** Taste is derived by counting attributes, not
  by interpreting free-text mood. The system cannot respond to "music for a rainy
  Sunday" except through the tags already present.
- **Era / language skew.** Both the seed example and catalog lean late-80s/90s,
  English-language dance and R&B, so recommendations reflect that slice of music.
- **Small local catalog.** 38 songs is still tiny; the local half of the system
  inherits the original project's cold-start and coverage limits.

## 12. Could This Be Misused, and How We Prevent It

- **Taste narrowing / filter bubble.** A recommender that only reinforces existing
  taste can trap listeners. Mitigations already in the system: an artist-repetition
  penalty, staged widening (genre → mood → tags → whole catalog), and confidence
  scoring that flags thin or over-narrow results.
- **False authority.** The friendly "DJ voice" could make weak picks sound
  confident. It is constrained to name a *real* seed song and real shared attributes,
  and falls back to the mechanical explanation rather than invent a reason.
- **Data attribution.** Last.fm data is used read-only under a free API key, trimmed,
  and cached; no personal or user-identifying data is collected or stored.

## 13. Evaluation Summary (Extension)

- **Automated tests:** 24 passing (`python -m pytest -q`) covering taste derivation,
  the agent loop (widening, seed de-duplication, honest refusal), both explanation
  voices, the input guardrail, and offline Last.fm / multi-source merge.
- **Evaluation harness:** 6 of 6 behavior checks pass (`python -m src.evaluate`),
  including the two cases where the correct behavior is to refuse (empty input,
  nothing-fits) — see `logs/eval_report.md`.
- **Specialization, measured:** across a 5-song mixtape, the DJ voice names one of
  the listener's seed songs **100%** of the time versus **0%** for the baseline —
  same facts, measurably different, grounded style.
- **RAG multi-source, measured:** for an 8-song new jack swing mixtape, genre purity
  rises from **3/8 to 8/8** on-genre once Last.fm is added, with real discovered
  tracks (Janet Jackson, Jade, Soul for Real) replacing off-genre filler.

## 14. AI Collaboration During Development

This project was built in collaboration with an AI coding assistant (Claude). Two
concrete moments stand out.

- **A flawed AI suggestion (caught).** When first asked to build the larger catalog,
  the assistant generated an *entirely fabricated* 38-song dataset — invented artists
  and song titles paired with confident, precise-looking audio-feature numbers
  (e.g. "energy 0.81, valence 0.30") — while, in the same conversation, advising about
  keeping data honest. This is exactly the hallucination anti-pattern this course
  warns about: fluent, specific, and false. It was caught by spotting a fake row, and
  the data was switched to real tracks with a clear provenance disclosure (Section 10).
- **A helpful AI suggestion (kept).** The assistant proposed caching every Last.fm
  response to a committed JSON file so the system runs offline with no API key. This
  made the multi-source feature fully reproducible for grading and removed the network
  as a point of failure — a design decision that materially improved reliability.

## 15. Personal Reflection (Extension)

**Biggest takeaway.** My biggest takeaway was seeing what happens when you take
something you built yourself, add the power of AI and its loop of planning and
retrieving, and then connect it to a much larger data source. Putting my own handful
of songs up against a wider catalog let me see how something that feels small and
niche can actually connect into something much bigger. It showed me that the
possibilities are endless. The only real limitation is your mind.

**What surprised me.** What surprised me was the static and noise that came back from
Last.fm, like songs that clearly did not belong showing up tagged as new jack swing.
It goes to show that even an agentic system is not error-proof. Without curation, a
human in the loop, and quality-checking the work, letting AI run without guardrails
can pull flawed results straight into your process. That is something worth keeping in
mind whenever you work with AI tools.

**What this project says about me as an AI engineer.** It proved to me that I have the
capability and the know-how to use these tools to add real value, capability, and
functionality to whatever I put my effort into. And if I can do it, anyone can, as long
as they are willing to trust the process and step in to re-steer when it is needed.
