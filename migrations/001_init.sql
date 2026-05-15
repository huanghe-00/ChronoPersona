-- ChronoPersona MVA v1.4 PostgreSQL Schema
-- 6 core tables + sync_operation_logs
-- insights / embodied_interactions marked as [FUTURE]

-- 1. 概念层级表（自引用 IS_A）
CREATE TABLE IF NOT EXISTS concepts (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    concept_type TEXT NOT NULL
        CHECK (concept_type IN ('food','emotion','person','event','object','abstract')),
    parent_id UUID REFERENCES concepts(id),
    embedding VECTOR(1024),
    branch_id TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_concepts_branch ON concepts(branch_id);
CREATE INDEX IF NOT EXISTS idx_concepts_type ON concepts(concept_type);

-- 2. 记忆实体节点（桥接 L2/L3）
CREATE TABLE IF NOT EXISTS memory_nodes (
    id UUID PRIMARY KEY,
    memory_type TEXT NOT NULL
        CHECK (memory_type IN ('episodic','semantic','insight')),
    ref_id TEXT NOT NULL,
    content_summary TEXT,
    branch_id TEXT NOT NULL DEFAULT 'main',
    session_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memory_nodes_branch ON memory_nodes(branch_id);
CREATE INDEX IF NOT EXISTS idx_memory_nodes_session ON memory_nodes(session_id);
CREATE INDEX IF NOT EXISTS idx_memory_nodes_type ON memory_nodes(memory_type);

-- 3. 语义边（8 类）
CREATE TABLE IF NOT EXISTS semantic_edges (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL,
    target_id UUID NOT NULL,
    edge_type TEXT NOT NULL CHECK (edge_type IN (
        'IS_A','MENTIONS','TEMPORAL_NEXT','CAUSED',
        'CONTRADICTS','BELONGS_TO','SIMILAR_TO','TRIGGERED_BY'
    )),
    weight FLOAT DEFAULT 1.0,
    metadata JSONB,
    branch_id TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_edges_type ON semantic_edges(edge_type, branch_id);
CREATE INDEX IF NOT EXISTS idx_edges_source ON semantic_edges(source_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_edges_target ON semantic_edges(target_id, edge_type);

-- 4. 意图导航策略
CREATE TABLE IF NOT EXISTS intent_patterns (
    id UUID PRIMARY KEY,
    intent_type TEXT NOT NULL CHECK (intent_type IN (
        'retrieve','vertical_generalize','vertical_specify',
        'parallel_compare','temporal_trace','causal_explore',
        'empathize','persona_switch'
    )),
    trigger_keywords TEXT[],
    trigger_regex TEXT,
    entry_edge_types TEXT[] NOT NULL DEFAULT '{}',
    max_hops INT DEFAULT 3,
    target_memory_types TEXT[] DEFAULT '{episodic,semantic}',
    priority_score FLOAT DEFAULT 1.0,
    branch_scope TEXT DEFAULT 'current',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. MVCC 版本链（L3 Entity 级细粒度）
CREATE TABLE IF NOT EXISTS entity_versions (
    id UUID PRIMARY KEY,
    entity_id TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    version TEXT NOT NULL,
    parent_version TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    vector_clock JSONB,
    content_hash TEXT,
    diff JSONB,
    provenance_op TEXT,
    UNIQUE(entity_id, branch_id, version)
);
CREATE INDEX IF NOT EXISTS idx_entity_versions_lookup ON entity_versions(entity_id, branch_id, version);

-- 6. MVCC Session 快照（L2 粗粒度）
CREATE TABLE IF NOT EXISTS session_snapshots (
    id UUID PRIMARY KEY,
    branch_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    version TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    lww_state JSONB,
    qdrant_metadata JSONB,
    UNIQUE(branch_id, session_id, version)
);

-- 7. 同步操作日志（W1 冻结：CRDT 操作落盘与故障恢复）
CREATE TABLE IF NOT EXISTS sync_operation_logs (
    id UUID PRIMARY KEY,
    device_id TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    operation_type TEXT NOT NULL CHECK (operation_type IN ('set', 'delete', 'merge')),
    key TEXT NOT NULL,
    value_hash TEXT,
    hlc_timestamp JSONB NOT NULL,
    vector_clock JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sync_logs_device ON sync_operation_logs(device_id, branch_id, created_at);

-- MVO 种子（最小可行本体）
INSERT INTO concepts (id, name, concept_type, parent_id) VALUES
('c_food', '食物', 'abstract', NULL),
('c_cuisine', '菜系', 'abstract', 'c_food'),
('c_sichuan', '川菜', 'food', 'c_cuisine'),
('c_cantonese', '粤菜', 'food', 'c_cuisine'),
('c_emotion', '情绪', 'abstract', NULL),
('c_anxiety', '焦虑', 'emotion', 'c_emotion'),
('c_joy', '喜悦', 'emotion', 'c_emotion'),
('c_person', '人物', 'abstract', NULL),
('c_family', '家人', 'relation', 'c_person')
ON CONFLICT DO NOTHING;

INSERT INTO intent_patterns (intent_type, trigger_keywords, entry_edge_types, max_hops) VALUES
('temporal_trace', ARRAY['后来','之后','然后','接着','现在怎样','结果如何'], ARRAY['TEMPORAL_NEXT','MENTIONS'], 3),
('causal_explore', ARRAY['为什么','怎么回事','原因','怎么会'], ARRAY['CAUSED','MENTIONS'], 3),
('vertical_generalize', ARRAY['种类','类型','还有哪些','类似的','同类的'], ARRAY['IS_A'], 2),
('vertical_specify', ARRAY['具体','哪种','什么样的','举例'], ARRAY['IS_A'], 2),
('parallel_compare', ARRAY['和','相比','哪个','还是','或者'], ARRAY['SIMILAR_TO'], 2),
('empathize', ARRAY['难过','开心','生气','担心','害怕'], ARRAY['MENTIONS'], 2)
ON CONFLICT DO NOTHING;
