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
| **Essence / summary** | A compact narrative: "We learned X from trying Y."             |
| **Source links**      | IDs of events (or other memories) that birthed it.             |
| **Importance**        | Weight in recall, curation priority (0.0-1.0 float).           |
| **Confidence**        | How sure the system is about its correctness or stability (0.0-1.0 float). |
| **Recency**           | Pure temporal distance from occurrence (0.0-1.0 float, auto-computed). |
| **Decay**             | Composite fading score based on importance, confidence, and recency (0.0-1.0 float, auto-computed). |
| **Timespan**          | When the underlying events occurred (start–end).               |
| **Tags / topics**     | Semantic hooks: "shipping routes," "error handling," "ethics." |
| **State**             | Active → Decaying → Archived (controls recall frequency).      |
| **Curator signals**   | e.g. reinforcement, merges, splits, contradictions.            |

### Four-Factor Recall System

Memory recall is driven by an interplay of four floating-point scores (all 0.0-1.0):

1. **Importance** (static/semi-static): How significant the memory is. Set at creation, manually updated by curation.
2. **Confidence** (static/semi-static): How stable/certain the memory is. Set at creation, manually updated by curation.
3. **Recency** (auto-computed): Pure temporal distance. Fresh memories score high (1.0), old memories score low (→0.0).
4. **Decay** (auto-computed): Composite fading score. Memories fade over time, but importance and confidence provide resistance.

**Verbal Model**: We follow "high is good" semantics for positive signals:
- **High importance** → stronger recall (positive signal)
- **High confidence** → stronger recall (positive signal)
- **High recency** → stronger recall (positive signal)
- **High decay** → weaker recall (negative signal — memory has faded)

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

At runtime, the **pack compiler** pulls relevant Memories based on multi-factor scoring:

**Semantic Relevance**:
* Vector similarity (semantic search)
* Structured filters (topic, tags, state)
* Policy constraints (e.g., one per domain per session)

**Temporal & Salience Factors**:
* **Importance**: Intrinsic weight (how significant the memory is)
* **Confidence**: Trustworthiness (how stable/certain the memory is)
* **Recency**: Temporal freshness (prefer recent context when relevant)
* **Decay**: Fading resistance (penalize faded memories unless reinforced)

**Recall Scoring** combines all factors. Example weighted formula:
```
recall_weight = (
    semantic_relevance * 0.4 +     # How relevant to current query
    importance * 0.25 +             # How significant the memory is
    confidence * 0.15 +             # How trustworthy it is
    recency_score * 0.15 +          # How fresh it is
    (1.0 - decay_score) * 0.05      # Inverted decay (high decay = penalty)
)
```

Coefficients are tunable based on use case (e.g., emphasize recency for conversational agents, importance for strategic planning).

### d. **Reflection / Curation**

The **Dreamer** (curation loop) revisits Memories periodically to:

* merge near-duplicates,
* summarize clusters into higher-order Memories,
* decay low-importance or outdated ones,
* promote durable insights into Lessons.

### e. **Decay**

Decay is not deletion; it's gradual reduction of recall probability triggered by time, modulated by importance and confidence.

**Key Distinction**:
- **Recency** is objective/mechanical: pure temporal distance from occurrence
- **Decay** is cognitive/psychological: how much the memory has faded from active recall

**Mathematical Relationships** (initial hypothesis, tunable):

```python
# Recency Score: Fresh memories = 1.0, old memories → 0.0
age_days = (now - time_end).days
max_age_days = 365  # Configurable decay horizon (memories older than this → recency = 0)
recency_score = max(0.0, 1.0 - (age_days / max_age_days))

# Decay Score: Memories fade over time, but importance + confidence provide resistance
base_decay_rate = 0.01  # Per day (configurable)
resistance = sqrt(importance * confidence)  # Geometric mean as resistance factor
decay_score = 1.0 - exp(-base_decay_rate * age_days * (1.0 - resistance))

# Interpretation:
# - High importance + high confidence → high resistance → slow decay
# - Low importance or low confidence → low resistance → fast decay
# - decay_score starts at 0.0 (fresh) and approaches 1.0 (fully faded) over time
```

**Auto-Update Strategy**:
- **Option A**: Cached fields updated by Dreamer periodically (e.g., daily)
- **Option B**: Computed on-the-fly during pack compilation (more accurate, no storage)
- **Option C**: Hybrid—cache for performance, recompute when precision matters

**Supersession**: Decay can also be triggered by newer, conflicting memories (not just time).

---

## 5. Storage model (conceptually)

A lightweight schema suffices:

**memory**

* `id` - UUID primary key
* `spirit_id` - Owner/identity entity (FK to spirits.id)
* `summary` - TEXT, compact narrative essence
* `importance` - FLOAT (0.0–1.0), weight in recall/curation
* `confidence` - FLOAT (0.0–1.0), stability/certainty
* `recency_score` - FLOAT (0.0–1.0), cached temporal freshness (optional, auto-computed)
* `decay_score` - FLOAT (0.0–1.0), cached fading score (optional, auto-computed)
* `state` - ENUM (`active`, `decaying`, `archived`)
* `time_start`, `time_end` - TIMESTAMP, when underlying events occurred (nullable)
* `meta` - JSONB (topics, tags, curator signals)
* `created_at`, `updated_at` - Automatic timestamp management
* `is_deleted` - BOOLEAN, soft delete flag

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
