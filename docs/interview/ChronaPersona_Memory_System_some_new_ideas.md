# ChronaPersona Memory System — Enhanced Design Document v1.0
**Document Role**: System-level knowledge base for Kimi 2.6 model consumption.  
**Scope**: Long-term memory architecture, retrieval scoring, engram schema, consolidation pipeline, and biomimetic mechanisms.  
**Reading Guide**: This document uses structured tags `[ARCH]`, `[ALGO]`, `[SCHEMA]`, `[FLOW]`, `[BIO]` to enable fast semantic indexing. All formulas are production-oriented pseudocode.

---

## 0. Meta-Architecture: The Penta-Layer Engram Stack

`[ARCH]` ChronaPersona implements a **Penta-Layer Memory Stack** mapped to neurocognitive counterparts. Information flows upward through consolidation gates, never downward without explicit de-archival.

| Layer | Neuro-Cognitive Analog | Storage Medium | Time Scale | Access Latency | Capacity Model |
|-------|------------------------|----------------|------------|----------------|----------------|
| **L1 Working Memory** | Prefrontal Cortex | In-context window (sliding) | Seconds–Minutes | <10 ms | Fixed (128K tokens budget) |
| **L2 Episodic Memory** | Hippocampus | Vector DB (Qdrant/FAISS) + Engram Graph | Hours–Months | 20–100 ms | Unbounded, filtered by admission |
| **L3 Semantic Memory** | Neocortex | Knowledge Graph (Neo4j/Custom) + Structured Store | Weeks–Permanent | 50–200 ms | Unbounded, hierarchical |
| **L4 Procedural Memory** | Basal Ganglia / Cerebellum | Executable DSL / State Machine / YAML Rules | Permanent | <5 ms (hot) | Bounded, curated |
| **L5 Meta-Memory** | Prefrontal Monitoring Layer | Index tables + Worth matrices + Strategy params | Continuous | <1 ms | Grows sub-linearly |

**Consolidation Flow** (upward only):
```
L1 (session) --[Admit Gate]--> L2 (episodic)
L2 --[Dream Job]--> L3 (semantic abstraction)
L3 --[Maturity Gate]--> L4 (procedural固化)
L5 monitors all layers and adjusts gate thresholds
```

---

## 1. Memory Admission & Retrieval Scoring

`[ALGO]` All engrams entering L2+ must pass an **Adaptive Memory Admission Control (A-MAC)**. This prevents noise accumulation at the source.

### 1.1 Admission Score (pre-storage gate)
```python
AdmissionScore(engram) = 
    w1 * Utility(e) + 
    w2 * Confidence(e) + 
    w3 * Novelty(e) + 
    w4 * Recency(e) + 
    w5 * TypePrior(e)

# Weights (empirically tuned, model-adjustable)
# TypePrior is the dominant factor per ablation studies.
```

**Component Definitions**:
- **Utility**: LLM-predicted future task contribution (0–1). Prompt: "How likely is this fact to be needed in the next 30 days?"
- **Confidence**: ROUGE-L overlap between engram claim and source evidence; penalizes hallucinations.
- **Novelty**: `1 - max_cosine_similarity(engram.vector, existing_L2_vectors)`. If < 0.15, flag for merge rather than insert.
- **Recency**: Time-decay kernel `exp(-λ * Δt)`.
- **TypePrior**: Hard-coded tier weights `[procedural: 1.0, preference: 0.9, fact: 0.6, chitchat: 0.1]`.

**Gate Rule**:
```
IF AdmissionScore >= 0.65 AND Confidence >= 0.75:
    route_to_L2_and_L3
ELIF AdmissionScore >= 0.40:
    route_to_L2_only (episodic buffer)
ELSE:
    discard_or_archive_to_cold_storage
```

### 1.2 Retrieval Ranking Formula (post-retrieval, pre-injection)
```python
FinalScore(engram, query, session_context) = 
    SemanticSim(query.vector, engram.vector) 
    * DynamicImportance(engram) 
    * RecencyDecay(engram.last_access, engram.access_count) 
    * EmotionalBoost(engram.valence, engram.arousal)
    * Confidence(engram)
    + ContextualBias(session_context, engram.cluster)

# Where:
# - DynamicImportance = base_importance * (1 + 0.1 * successful_uses - 0.3 * failed_uses)
# - RecencyDecay = exp(-base_decay * Δt / (1 + 0.5 * access_count))  # FadeMem modulation
# - EmotionalBoost = 1 + (valence * 0.2) + (arousal * 0.1)
#   Special rule: if valence < -0.5, EmotionalBoost clamps to 1.5 (negative lessons prioritized)
# - ContextualBias = cluster_coherence_score if engram.cluster matches session topic
```

**Context Budget Allocation** (L1 injection policy):
```
Total L1 Budget: 128K tokens
├── Current Session History: 40% (sliding window + key turn summaries)
├── Retrieved L2/L3 Memories: 30% (Top-K from ranked pool)
├── L4 Procedural Memory: 20% (always-hot rules)
└── Scratchpad / CoT: 10% (reserved for reasoning)

Hard constraint: Any engram with FinalScore < 0.35 is excluded from L1 injection.
```

---

## 2. Engram Schema: LLM-Generated Structured Output

`[SCHEMA]` After every agent execution turn, the executor LLM emits a **hidden Engram JSON** (not shown to user). This schema is designed to feed L2 (vector), L3 (graph), and L5 (meta) simultaneously.

### 2.1 Engram Schema Definition
```json
{
  "$schema": "chronapersona.engram.v1",
  "engram_id": "uuid_v7_time_ordered",
  "timestamp_utc": "2026-06-03T08:45:00Z",
  "user_id": "user_fingerprint",
  "session_id": "sess_uuid",

  "content_layers": {
    "raw_observation": "Verbatim or lightly cleaned user utterance / system action trace",
    "abstracted_fact": "Generalized declarative statement. Example: 'User prefers env vars over config files for deployment tasks.'",
    "procedural_rule": "IF-THEN-ELSE abstraction if pattern detected. Null if not procedural.",
    "embedding_text": "Concatenation of raw + abstracted, used for vectorization."
  },

  "metadata": {
    "importance_score": 7.5,
    "confidence_score": 0.92,
    "novelty_score": 0.34,
    "memory_type": "procedural_preference | factual | episodic | social",
    "maturity_tier": "hot | warm | stable | archived",
    "source_turn_index": 12
  },

  "affective_signal": {
    "valence": 0.7,
    "arousal": 0.3,
    "dominance": 0.5,
    "user_satisfaction_hint": "positive | neutral | negative | frustrated",
    "success_boost": 0.0,
    "frustration_mark": false
  },

  "relation_graph": {
    "entities": [
      {"entity_id": "e1", "label": "部署脚本", "type": "artifact", "role": "object"},
      {"entity_id": "e2", "label": "环境变量", "type": "method", "role": "preferred_by"}
    ],
    "triples": [
      {"subject": "e1", "predicate": "involved_in", "object": "e2", "confidence": 0.95}
    ],
    "logical_cluster": "devops_deployment_patterns",
    "supersedes": ["mem_abc_123"],
    "conflicts_with": ["mem_xyz_789"],
    "symbiotic_with": []
  },

  "retrieval_hints": {
    "trigger_keywords": ["部署", "配置", "环境变量", "脚本"],
    "contextual_prerequisites": ["user_engaged_in_deployment_task"],
    "ltm_index_anchor": "用户技术偏好:部署方式",
    "expected_query_clusters": ["devops", "ci_cd", "configuration_management"]
  },

  "provenance": {
    "model_version": "kimi-2.6",
    "extraction_prompt_hash": "sha256:...",
    "human_verified": false
  }
}
```

### 2.2 Routing Logic from Schema to Layers
```python
def route_engram(e):
    # L2 Episodic (Vector)
    vector_db.upsert(
        id=e.engram_id,
        vector=embed(e.content_layers.embedding_text),
        payload=e  # full JSON as metadata
    )

    # L3 Semantic (Graph)
    if e.relation_graph.triples:
        kg.merge_triples(e.relation_graph.triples, source=e.engram_id)

    # L4 Procedural (Rule Engine)
    if e.metadata.memory_type == "procedural_preference" 
       and e.metadata.maturity_tier == "stable"
       and e.affective_signal.valence > 0.5:
        rule_engine.stage_for_activation(e.content_layers.procedural_rule)

    # L5 Meta-Memory
    meta.index_cluster(e.relation_graph.logical_cluster, e.engram_id)
    meta.update_type_distribution(e.metadata.memory_type)
```

---

## 3. Dual-Phase Consolidation & The Dream Mechanism

`[FLOW]` ChronaPersona uses **Dual-Phase Consolidation**: online fast-write vs. offline deep-consolidation (Dream).

### 3.1 Phase 1: Online Fast Write (Hot Path)
- **Latency Budget**: < 100 ms total (async where possible).
- **Actions**:
  1. LLM emits Engram Schema.
  2. A-MAC gate evaluates AdmissionScore.
  3. Passed engrams are written to L2 (vector) and L3 (graph) **without deduplication**.
  4. Raw session logs appended to time-series buffer.
- **Acceptable Redundancy**: 15–30% temporary duplication is expected and tolerated.

### 3.2 Phase 2: Offline Dream (Cold Path)
- **Trigger**: Cron-scheduled during low-load window (e.g., 02:00 UTC) or when L2 size delta > 10% since last Dream.
- **Executor**: Dedicated background LLM (higher context, lower speed priority) or distilled consolidation model.
- **Input Window**: Last N sessions (max 100) + current L2/L3 snapshot.
- **Dream Tasks** (ordered):

| Task | Biomimetic Analog | Output |
|------|-------------------|--------|
| **T1: Semantic Deduplication** | Hippocampal pattern completion | Merge redundant engrams; keep superseded IDs in `replaced_by` chain |
| **T2: Conflict Resolution** | Prefrontal arbitration | Detect `conflicts_with` edges; LLM judges winner by confidence + valence + recency |
| **T3: Pattern Separation** | Sleep spindle orthogonalization | For high-similarity pairs (cos > 0.85), generate discriminative features and re-embed |
| **T4: Systems Consolidation** | Hippocampal-neocortical transfer | Abstract episodic clusters into semantic nodes; downgrade source episodic engrams to "warm" |
| **T5: Procedural Crystallization** | Basal ganglia habit formation | Promote procedural candidates to L4 if frequency >= 3, mean valence > 0.5, no valence < -0.3 |
| **T6: Meta-Memory Update** | Prefrontal self-monitoring | Recalculate Memory Worth for all touched clusters; update retrieval strategy priors |

**Dream Output Format**: A transaction log of mutations (insert/update/delete/mark) applied atomically to L2–L5.

### 3.3 Relationship: Dual-Phase vs. Dream
```
Dual-Phase Consolidation = Architecture Pattern
    ├── Online Phase: fast, rule-based or light-LLM
    └── Offline Phase: slow, heavy-LLM (Dream)

Dream = The semantic-intelligent implementation of the Offline Phase.
If your data is fully structured (JSON logs), Offline Phase can be rule-based.
If your data is natural language experience, Offline Phase MUST be Dream (LLM-driven).
```

---

## 4. Engram Cascade Update (Localized Vector Mutation)

`[ALGO]` Traditional vector DBs suffer from the **re-embedding problem**: updating one fact requires rebuilding the document chunk and its neighbors. Engram Cascade Update solves this via graph-activated local propagation.

### 4.1 Data Structure
```python
class EngramNode:
    node_id: str
    vector: List[float]           # semantic embedding
    activation_level: float       # 0.0–1.0, analogous to membrane potential
    engram_cluster: str           # e.g., "devops_deployment_patterns"
    synaptic_edges: List[{
        "target_id": str,
        "relation_type": "contradicts | supports | generalizes | specializes | co_occurs",
        "weight": float
    }]
    consolidation_state: float    # 0.0–1.0, how crystallized this memory is
    version: int
```

### 4.2 Cascade Trigger & Propagation
When a node A is updated (e.g., user preference changed from "env vars" to "config files"):

```python
def cascade_update(A, delta_vector, hop_limit=2, decay=0.5):
    # A.delta_vector = A.new_vector - A.old_vector
    queue = [(A, 0, 1.0)]  # (node, hop, signal_strength)
    visited = {A.node_id}

    while queue:
        node, hop, strength = queue.pop(0)
        if hop > hop_limit:
            continue

        # 1. Local vector微调 (only for 1-hop neighbors)
        if hop == 1:
            node.vector += learning_rate * strength * delta_vector
            node.version += 1
            vector_db.partial_update(node.node_id, node.vector)

        # 2. Activation boost & relation marking
        node.activation_level = min(1.0, node.activation_level + 0.3 * strength)

        # 3. Special handling for contradictions
        for edge in node.synaptic_edges:
            if edge.relation_type == "contradicts" and hop == 1:
                kg.flag_for_dream_resolution(A.node_id, node.node_id)

        # 4. Propagate to next hop
        for edge in node.synaptic_edges:
            if edge.target_id not in visited:
                visited.add(edge.target_id)
                next_node = kg.get(edge.target_id)
                queue.append((next_node, hop + 1, strength * decay * edge.weight))

    # 5. Cluster-level metadata update
    meta.mark_cluster_for_rebalance(A.engram_cluster)
```

**Complexity**: O(k) where k = cluster size (typically < 100), vs. O(N) global rebuild.

---

## 5. Biomimetic Extensions for Dream Phase

`[BIO]` Beyond basic deduplication and LLM summarization, the Dream phase can incorporate deeper neurocognitive mechanisms.

### 5.1 Pattern Separation (Hippocampal Orthogonalization)
**Problem**: Similar engrams (cos > 0.85) interfere during retrieval (catastrophic forgetting / aliasing).  
**Dream Action**:
1. Identify high-similarity pairs in the same cluster.
2. Prompt LLM: "Given these two similar memories, generate a distinguishing feature for each that makes them semantically separable."
3. Append discriminative features to `content_layers.embedding_text`.
4. Re-embed and verify cosine drops to < 0.75.

### 5.2 Stochastic Replay with Counterfactuals
**Biomimetic Basis**: Sleep replay is not verbatim; it includes stochastic variations for generalization.  
**Dream Action**:
1. Select high-Worth episodic engrams (success or failure).
2. LLM generates 2–3 counterfactual variants: "What if the user had chosen the alternative path?"
3. Variants are NOT stored as canonical memories.
4. They are used to **stress-test the causal structure** of the original engram; if contradictions found, downgrade confidence.

### 5.3 Systems Consolidation (Hippocampal → Neocortical Transfer)
**Dream Action**:
1. For each cluster with > 5 episodic engrams sharing the same abstract pattern:
   - LLM synthesizes a single semantic node (L3) capturing the invariant.
   - Episodic sources are demoted: `maturity_tier` → "warm", `retrieval_priority` → "on-demand only".
2. Semantic node inherits the union of entity graph edges, deduplicated.

### 5.4 Spindle Gating (Sleep Spindle Thresholding)
**Biomimetic Basis**: Sleep spindles gate which memories enter long-term consolidation.  
**Dream Action**:
1. Pre-filter engrams by composite score before any LLM processing.
2. Threshold: `importance_score > 7.0 AND confidence > 0.85 AND |valence| > 0.2`.
3. Engrams below threshold are marked `consolidation_state = 0.2` (latent) and skipped in this Dream cycle.

---

## 6. Affective Signal Processing (Emotional Valence)

`[ALGO]` Emotional scoring is not sentiment analysis for UI display; it is a **memory modulation signal**.

### 6.1 Three-Dimensional Affective Vector
```python
@dataclass
class AffectiveSignal:
    valence: float      # -1.0 (very negative) to +1.0 (very positive)
    arousal: float      # 0.0 (calm) to 1.0 (excited/urgent)
    dominance: float    # 0.0 (submissive/user-controlled) to 1.0 (agent-controlled/successful)
```

**Extraction Heuristics**:
- **Valence**: +0.7 on task success (user confirms), -1.0 on explicit frustration ("不对", "错了", "重新来"), 0.0 neutral.
- **Arousal**: Detect urgency markers (ALL CAPS, multiple "!", words like "紧急", "立刻", "马上").
- **Dominance**: Detect user control phrases ("必须按我说的", "不要改我的") vs. agent autonomy success.

### 6.2 Usage in Retrieval & Consolidation
```python
# Retrieval modulation
if engram.affective.valence < -0.5:
    engram.retrieval_boost *= 1.5       # Negative lessons are high-priority
    engram.retrieval_flag = "anti_pattern"
elif engram.affective.valence > 0.5 and engram.affective.arousal > 0.7:
    engram.retrieval_boost *= 1.3       # Peak positive experiences reinforced

# Procedural crystallization gate
if (engram.memory_type == "procedural" 
    and engram.affective.valence > 0.5 
    and not any(e.affective.valence < -0.3 for e in pattern_history)):
    trigger_L4_promotion(engram)
```

---

## 7. Meta-Memory: The Memory of Memory

`[ARCH]` L5 Meta-Memory is ChronaPersona's **self-model**. It does not contain user facts; it contains "what the system knows about its own knowledge."

### 7.1 Three Tiers of Meta-Memory

**Tier 1: Index Layer (What do we know?)**
```json
{
  "cluster_index": {
    "devops_deployment_patterns": {
      "engram_count": 47,
      "last_dream_cycle": "2026-06-03T02:00:00Z",
      "dominant_entities": ["部署脚本", "Docker", "环境变量"],
      "avg_importance": 6.8
    }
  },
  "type_distribution": {
    "procedural_preference": 0.12,
    "factual": 0.55,
    "episodic": 0.28,
    "social": 0.05
  }
}
```

**Tier 2: Quality Layer (What is useful?)**
- **Memory Worth**: `Worth(m) = Σ outcomes_after_retrieving(m) / retrieval_count(m)`
  - If `Worth < 0.3` despite high retrieval frequency: mark as **misleading engram**, suppress from Top-K.
  - If `Worth > 0.9` but retrieval frequency low: mark as **hidden gem**, force-inject when cluster is active.
- **Co-occurrence Matrix**: Which engrams are retrieved together? Used for pre-fetching.

**Tier 3: Strategy Layer (How should we retrieve?)**
```python
class RetrievalStrategy:
    # Dynamically adjusted per user/cluster
    semantic_weight: float        # default 1.0
    recency_weight: float         # default 0.8
    importance_weight: float      # default 0.6
    emotional_weight: float       # default 0.4

    # Updated by meta-learning from session outcomes
    def update(self, session_outcome: float, retrieved_engrams: List[Engram]):
        # Gradient descent on strategy weights to maximize session_outcome
        pass
```

### 7.2 Meta-Memory Driven Adaptive Retrieval
```python
def chrona_retrieve(query, user_id, session_context):
    # 1. Meta-memory selects strategy
    strategy = meta.get_strategy(user_id, query.cluster_hint)

    # 2. Hidden gems injection
    gems = meta.hidden_gems(query.domain, threshold=0.85)

    # 3. Primary vector search
    candidates = vector_db.search(query.vector, top_k=50)

    # 4. Rerank with strategy-weighted formula
    candidates = rerank(candidates, strategy.weights)

    # 5. Inject gems if not already present
    candidates = merge_gems(candidates, gems, max_gems=2)

    # 6. Final cut to L1 budget
    final = candidates[:budget_allowance]

    # 7. Log outcome for meta-memory update
    meta.log_retrieval_outcome(query.id, final, session_outcome)
    return final
```

### 7.3 Recursive Refinement (Meta-Memory of Meta-Memory)
When Meta-Memory itself exceeds scale thresholds, ChronaPersona triggers **Meta-Dream**:
- Consolidate cluster indices into higher-order topic indices.
- Prune obsolete strategy parameters (those not updated in 90 days).
- Rebalance Worth matrices using approximate algorithms (sampling).

---

## 8. Implementation Roadmap for ChronaPersona

`[FLOW]` Suggested build order, from MVP to full stack.

### Phase 0: Foundation (Week 1–2)
1. Implement **L1 Sliding Window** with turn summarization.
2. Implement **Engram Schema** and LLM hidden output pipeline.
3. Set up **L2 Vector DB** (Qdrant recommended for metadata filtering).

### Phase 1: Admission & Retrieval (Week 3–4)
1. Build **A-MAC** gate with static TypePrior weights.
2. Implement **FinalScore** ranking with Recency + SemanticSim.
3. Build **L3 Light Graph** (even Markdown link graph is sufficient initially).

### Phase 2: Dream & Consolidation (Week 5–8)
1. Build **Dream Job** runner (async, scheduled).
2. Implement T1 (Deduplication) + T4 (Systems Consolidation).
3. Add **Affective Signal** extraction and EmotionalBoost.

### Phase 3: Advanced Mechanisms (Week 9–12)
1. Implement **Engram Cascade Update** for localized vector mutation.
2. Build **L4 Procedural Memory** staging and rule engine.
3. Deploy **L5 Meta-Memory** with Worth tracking and adaptive retrieval.

### Phase 4: Biomimetic Polish (Ongoing)
1. Add **Pattern Separation** to Dream.
2. Experiment with **Stochastic Replay** for robustness testing.
3. Fine-tune Spindle Gating thresholds per user segment.

---

## 9. Quick Reference: Decision Trees

`[FLOW]`

### Engram Routing Decision
```
LLM outputs Engram Schema
|
+- AdmissionScore < 0.40 ----------> DISCARD (log to cold archive)
|
+- AdmissionScore 0.40–0.65 ------> L2 ONLY (episodic buffer)
|   +- Await next Dream cycle for promotion
|
+- AdmissionScore >= 0.65 --------> L2 + L3
    |
    +- memory_type == procedural --> Stage for L4 (pending maturity)
    |   +- maturity_gate: freq>=3 AND valence>0.5 AND no_negative --> PROMOTE to L4
    |
    +- relation_graph.non_empty ---> MERGE into L3 Knowledge Graph
```

### Context Injection Decision
```
Retrieval pool generated (Top-50 from L2/L3)
|
+- FinalScore < 0.35 ------------> EXCLUDE from L1
|
+- FinalScore 0.35–0.60 --------> SECONDARY pool (inject only if L1 budget remains)
|
+- FinalScore > 0.60 ------------> PRIMARY pool
    +- Sort by FinalScore descending
        +- Fill L1 budget: 40% session / 30% primary memories / 20% L4 rules / 10% scratchpad
```

### Dream Cycle Decision
```
Trigger: Cron @ 02:00 UTC OR L2 delta > 10%
|
+- Spindle Gate: importance < 7.0 --> SKIP (mark latent)
|
+- Pass Spindle Gate
    +- T1: Deduplicate (cos > 0.95) --> MERGE
    +- T2: Resolve conflicts --> LLM arbitration
    +- T3: Pattern Separation (cos > 0.85) --> DISCRIMINATE & RE-EMBED
    +- T4: Systems Consolidation (cluster size > 5) --> ABSTRACT to L3
    +- T5: Procedural Crystallization --> PROMOTE to L4
    +- T6: Meta-Memory Update --> RECALCULATE Worth & Strategy
```

---

**Document End**.  
**ChronaPersona Memory System v1.0 — Designed for Kimi 2.6 consumption and iterative refinement.**
