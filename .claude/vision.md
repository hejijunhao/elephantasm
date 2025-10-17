# 🐘 Elephantasm — Long-Term Agentic Memory (LTAM)

## Overview

Elephantasm is a modular, open-source Long-Term Agentic Memory (LTAM) framework designed to give AI agents continuity, self-awareness, and evolution over time.

Unlike typical "memory" systems that simply log interactions or retrieve nearest neighbors from a vector store, Elephantasm is a structured cognitive substrate — a framework for how agents remember, learn, and become.

It treats memory not as a cache, but as a living system of Events, Memories, Lessons, Knowledge, and Identity — each transforming into the next through deterministic, auditable processes.

The goal is simple but ambitious:

**To give agents the ability to retain and evolve context — continuously, coherently, and controllably.**

## Core Principles

### Continuity in addition to Context

Context represents short-term awareness — what the agent knows right now (its active thread, cache, and immediate focus).
Continuity, by contrast, preserves what the agent has experienced before.
Elephantasm unifies both. Context gives responsiveness; continuity gives identity. Together, they enable agents that both think and remember.

### Structure in addition to Similarity

Vector search remains vital for fast, associative recall — but it's only one layer.
Elephantasm builds structured metadata and relational links on top of embeddings, allowing hybrid retrieval that's both efficient and semantically meaningful.
Structured logic governs relationships; vector math accelerates discovery.

### Determinism as a Guiding Frame, not a Cage

Determinism defines how memories are organized, stored, and retrieved — but within that structure, each agent retains self-determination.
The LLM's own reasoning still plays a role in which memories to surface or prioritize, balancing structure with adaptive intelligence.

### Curation post-Accumulation

Every experience is first recorded. Nothing is lost by default.
Curation happens after accumulation: a reflective process that distills relevance, merges overlaps, and retires noise.
This loop — guided by the Dreamer — is self-reinforcing: the more an agent curates, the better it understands what matters.

### Composability over Complexity

The LTAM should integrate easily into any agentic system, framework, or runtime — whether you're building in LangChain, LlamaIndex, FastAPI, or raw Python.

### Identity as Emergence

Over time, the aggregation of Lessons and Knowledge defines an agent's evolving Identity — its behavioral fingerprint, biases, and worldview.

## System Architecture

At a high level:

```
Incoming Event
      ↓
[Cortex] — selects what matters
      ↓
[Pack Compiler] — builds a memory pack (deterministic)
      ↓
[Planner / Tools] — executes, updates, learns
      ↓
[Dreamer] — curates and evolves memory layers
```

### Core Objects

| Layer         | Purpose                                                                | Persistence        |
| ------------- | ---------------------------------------------------------------------- | ------------------ |
| **Event**     | Raw interaction or signal (e.g., user input, tool call, API response). | Ephemeral + Stored |
| **Memory**    | Structured reflection or encoding of one or more events.               | Stored             |
| **Lesson**    | Extracted insight or rule from patterns across memories.               | Stored             |
| **Knowledge** | Canonicalized truths — the agent's "understanding" of the world.       | Stored             |
| **Identity**  | The agent's accumulated disposition, tone, and preferences.            | Stored             |

### The Dreamer Loop

A scheduled or triggered background process:

- Reviews stored memories periodically.
- Clusters and promotes relevant insights.
- Merges duplicates and archives stale content.
- Refines Lessons → Knowledge → Identity.

The Dreamer ensures the system doesn't just remember, but evolves.

## Technical Philosophy

**FastAPI-first:** Elephantasm starts as a clean, modular backend microservice.
The API provides structured endpoints for ingesting events, compiling memory packs, retrieving curated context, and triggering curation cycles.

**Minimal UI:** A simple dashboard will visualize memory creation, evolution, and lineage — useful for introspection and debugging.

**Multi-Tenant Ready:** Inspired by your Supabase + RLS patterns — each app or agent instance will have its own isolated namespace and identity.

**SDKs:**
- `elephantasm-py` for Python/LLM applications
- `@elephantasm/client` for TypeScript/Node environments

**Storage Layer:** PostgreSQL (with JSONB for schema flexibility).
Vector search optional, not central — recall is structured and deterministic.

## Development Philosophy

**Start small, think big.**
The first milestone is a minimal working LTAM pipeline: ingest events, generate memories, and retrieve deterministic packs.

**Simplicity as strategy.**
Avoid over-engineering early. Each component should be explainable, testable, and replaceable.

**Transparency as a feature.**
Every memory, transformation, and pack assembly should be observable and traceable.

**Open collaboration.**
This will evolve through community input and experimental feedback loops — the system itself will, one day, use its own memory to guide its improvement.

## Roadmap (Very Broad/High-Level)

### Phase 1 — Core Service (v0.1)

- FastAPI skeleton
- Event ingestion + memory creation
- Pack compiler + deterministic retrieval
- Basic Dreamer cron job
- Simple UI (memory stream visualization)
- Python/TS SDKs (capture & retrieve)

### Phase 2 — Growth & Intelligence (v1)

- Layered promotion (Memory → Lesson → Knowledge)
- Identity layer
- Provenance tracking
- Evaluation tools (memory quality, drift)
- Configurable curation rules

### Phase 3 — Ecosystem (v2+)

- Self-hosted + managed cloud mode
- Rich observability dashboard
- Multi-agent shared memory networks
- Memory pack marketplace (export/import trained packs)
- Integrations with OpenAI, Anthropic, HuggingFace models

---

*"Memory is not what happened. It's the story we tell ourselves about what mattered."*
