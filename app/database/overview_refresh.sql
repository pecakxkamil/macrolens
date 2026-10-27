-- Disposable published Overview snapshots; source observations and PIT caches are separate.
CREATE TABLE IF NOT EXISTS overview_publications (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    brief JSONB NOT NULL,
    histories JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS overview_refresh_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    job_id UUID,
    status TEXT NOT NULL DEFAULT 'idle',
    attempted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    next_check_at TIMESTAMPTZ,
    publication_id UUID REFERENCES overview_publications(id),
    source_versions JSONB NOT NULL DEFAULT '{}',
    results JSONB NOT NULL DEFAULT '[]'
);
INSERT INTO overview_refresh_state(id) VALUES (1) ON CONFLICT DO NOTHING;
