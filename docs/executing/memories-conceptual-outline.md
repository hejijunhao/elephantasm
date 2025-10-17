Perfect — we’ve established **Events** as the raw, objective feed of “what happened.”
Now we move one layer up in the cognitive stack: **Memories** — where meaning and continuity start.

---

## 1. What a Memory *is*

A **Memory** is a *subjective interpretation or condensation* of one or more Events.
It transforms “what happened” into “what it meant.”

Think of it as:

> *a structured, human-like recollection—compressed, contextual, and perspectival.*

Each memory is:

* **Derived**, not raw — it’s synthesized from one or several Events (sometimes across time).
* **Subjective** — it reflects what *this spirit* considered meaningful.
* **Compact** — holds distilled understanding, not full transcripts.
* **Evolving** — it can merge, split, decay, or be promoted into Lessons or Knowledge.

---

## 2. Purpose

Memories serve as the **working long-term store** that bridges context windows and sessions.

They:

* Form the **narrative continuity** (“what I’ve done, seen, thought”).
* Enable **retrieval-augmented reasoning** without replaying raw events.
* Provide **summaries** that the agent can “reflect upon.”
* Act as **training material** for generating Lessons and Knowledge.
* Define a **semantic time-line** distinct from chronological time (because they can reorganize around themes, not dates).

---

## 3. Conceptual anatomy

Each Memory typically contains:

| Component             | Meaning                                                        |
| --------------------- | -------------------------------------------------------------- |
| **Essence / summary** | A compact narrative: “We learned X from trying Y.”             |
| **Source links**      | IDs of events (or other memories) that birthed it.             |
| **Importance**        | Weight in recall, curation priority.                           |
| **Confidence**        | How sure the system is about its correctness or stability.     |
| **Timespan**          | When the underlying events occurred (start–end).               |
| **Tags / topics**     | Semantic hooks: “shipping routes,” “error handling,” “ethics.” |
| **State**             | Active → Decaying → Archived (controls recall frequency).      |
| **Curator signals**   | e.g. reinforcement, merges, splits, contradictions.            |

---

## 4. How they function

### a. **Accumulation**

The *selector* monitors streams of Events and identifies clusters worth remembering:

* bursts of similar activity,
* completed tool-task cycles,
* repeated themes,
* emotional/salient signals.

### b. **Synthesis**

When a cluster is selected:

1. Extract the **content** (text from Events).
2. Identify **salient elements** (entities, outcomes, relationships).
3. Generate a **summary** — a natural-language condensation.
4. Store as a new **Memory** with metadata + event links.
5. Optionally embed it (for later semantic recall).

> In human terms: “Yesterday’s long debugging session” becomes
> “Found the root cause of recurring latency spikes in message ingestion.”

### c. **Recall**

At runtime, the **pack compiler** pulls relevant Memories based on:

* vector similarity (semantic search),
* structured filters (topic, importance, recency),
* policy (e.g., one per domain per session).

### d. **Reflection / Curation**

The **Dreamer** (curation loop) revisits Memories periodically to:

* merge near-duplicates,
* summarize clusters into higher-order Memories,
* decay low-importance or outdated ones,
* promote durable insights into Lessons.

### e. **Decay**

Decay is not deletion; it’s gradual reduction of recall probability or confidence.
You can model this with an exponential decay on “attention weight,” triggered by time or supersession.

---

## 5. Storage model (conceptually)

A lightweight schema suffices:

**memory**

* `id`
* `spirit_id` (or owner)
* `summary` (text)
* `importance` (0–5)
* `confidence` (0–1)
* `state` (`active|decaying|archived`)
* `time_start`, `time_end` (optional)
* `meta` (topics, tags)
* `created_at`, `updated_at`

**memory_event_link**

* `memory_id`
* `event_id`
* `weight`

Optionally:
**memory_embedding**

* `(memory_id, vector)`

This keeps Memories *semantic*, not transactional.

---

## 6. Synthesis strategies (how new memories arise)

You can model several creation paths:

| Strategy                     | Trigger                       | Example                                               |
| ---------------------------- | ----------------------------- | ----------------------------------------------------- |
| **Immediate synthesis**      | Salient event (strong signal) | Error or praise triggers instant memory               |
| **Windowed synthesis**       | End of session                | Summarize a chat/work block                           |
| **Retrospective synthesis**  | Periodic cron                 | Dreamer curates older events into fewer memories      |
| **Cross-episodic synthesis** | Thematic merge                | Merge all “shipping delay” memories into one summary  |
| **Reflective synthesis**     | Explicit self-reflection      | “I’ve been getting better at debugging async issues.” |

Each Memory thus exists in a **network**, not a strict timeline.

---

## 7. Relationship to Lessons & Knowledge

* **Lessons** = *meta-memories*: distilled “what/why/how/when” patterns from multiple related Memories.
* **Knowledge** = *stable truths* extracted from Lessons or cross-validated Memories.

So, **Memories** are *the substrate*—they feed upward into **Lessons** and **Knowledge** and downward back into future **context packs**.

---

## 8. Example lifecycle

1. *Event stream:*
   `[Tool.Call: query API] → [Tool.Result: error] → [Decision: retry with params] → [Tool.Result: success]`
2. *Synthesis:*
   → Memory: “Retrying the API with correct parameters fixed the timeout error.”
3. *Curation:*
   → Memory importance raised after repetition across sessions.
4. *Lesson formation:*
   → “When encountering timeout errors, check for missing params before retrying.”
5. *Knowledge consolidation:*
   → “Timeouts often stem from missing parameters in API calls.”

---

## 9. Philosophical framing

Memories are **the narrative glue** between experience (Events) and understanding (Knowledge).
They hold *subjectivity* and *temporality*: “what it felt like, what seemed important, what I concluded.”
Technically, they make context *continuous*; philosophically, they make the system *self-reflective.*

---
