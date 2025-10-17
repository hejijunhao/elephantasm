/**
 * Core TypeScript types for Elephantasm LTAM System
 *
 * These types represent the five layers of the memory hierarchy:
 * Event → Memory → Lesson → Knowledge → Identity
 */

/**
 * Base interface for all memory objects
 */
interface BaseMemoryObject {
  id: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

/**
 * Event - Raw interaction or signal
 * The foundational layer that captures everything that happens
 */
export interface Event extends BaseMemoryObject {
  type: 'user_input' | 'tool_call' | 'api_response' | 'system_event' | 'custom';
  content: string;
  source?: string;
  agent_id?: string;
  session_id?: string;
  context?: Record<string, unknown>;
}

/**
 * Memory - Structured reflection or encoding of one or more events
 * The first level of abstraction from raw events
 */
export interface Memory extends BaseMemoryObject {
  event_ids: string[];
  summary: string;
  embedding?: number[];
  importance_score?: number;
  tags?: string[];
  category?: string;
  agent_id: string;
}

/**
 * Lesson - Extracted insight or rule from patterns across memories
 * The second level of abstraction - what the agent learns
 */
export interface Lesson extends BaseMemoryObject {
  memory_ids: string[];
  insight: string;
  confidence_score?: number;
  application_count?: number;
  category?: string;
  agent_id: string;
}

/**
 * Knowledge - Canonicalized truths - the agent's understanding
 * The third level - consolidated, verified understanding
 */
export interface Knowledge extends BaseMemoryObject {
  lesson_ids: string[];
  truth: string;
  domain?: string;
  reliability_score?: number;
  last_validated?: string;
  agent_id: string;
}

/**
 * Identity - The agent's accumulated disposition and worldview
 * The highest level - who the agent has become
 */
export interface Identity extends BaseMemoryObject {
  knowledge_ids: string[];
  trait_name: string;
  trait_value: string | number | boolean;
  strength?: number;
  evolution_history?: Array<{
    timestamp: string;
    previous_value: string | number | boolean;
    trigger?: string;
  }>;
  agent_id: string;
}

/**
 * Memory Pack - Deterministic compilation of relevant context
 * Used for retrieval and providing context to agents
 */
export interface MemoryPack {
  id: string;
  created_at: string;
  query?: string;
  events: Event[];
  memories: Memory[];
  lessons: Lesson[];
  knowledge: Knowledge[];
  identity_traits: Identity[];
  compilation_strategy: string;
  relevance_scores?: Record<string, number>;
}

/**
 * Agent - Represents an AI agent using the LTAM system
 */
export interface Agent {
  id: string;
  name: string;
  created_at: string;
  description?: string;
  config?: Record<string, unknown>;
}

/**
 * Dreamer Job - Background curation process
 */
export interface DreamerJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at?: string;
  completed_at?: string;
  operation_type: 'cluster' | 'promote' | 'merge' | 'archive';
  agent_id: string;
  results?: {
    items_processed: number;
    items_created?: number;
    items_updated?: number;
    items_archived?: number;
  };
  error?: string;
}

/**
 * API Response Types
 */
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

/**
 * Request Types
 */
export interface CreateEventRequest {
  type: Event['type'];
  content: string;
  source?: string;
  agent_id?: string;
  session_id?: string;
  context?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface CompilePackRequest {
  agent_id: string;
  query?: string;
  event_ids?: string[];
  strategy?: 'recent' | 'relevant' | 'comprehensive';
  max_items?: {
    events?: number;
    memories?: number;
    lessons?: number;
    knowledge?: number;
    identity?: number;
  };
}

export interface TriggerDreamerRequest {
  agent_id: string;
  operation_type: DreamerJob['operation_type'];
  config?: Record<string, unknown>;
}
