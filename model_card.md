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

**Important caveat about the numbers.** The `energy`, `valence`, `danceability`, and
`acousticness` values imitate the audio-analysis features a streaming service computes
from a waveform. Here they were assigned by hand. Only the `tempo_bpm` values for the
real songs were looked up from public sources. No audio was analysed.

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

**No diversity control.** One artist can occupy multiple slots in a five-song list.

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
- **Use the unused columns** — `valence`, `danceability`, `acousticness`, `tempo_bpm`,
  and the `likes_acoustic` preference that is currently declared but never read.
- **A diversity penalty**, so one artist cannot fill several slots.
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
