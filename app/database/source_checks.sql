-- Additive availability-check provenance. No historical timestamps are inferred.
CREATE TABLE IF NOT EXISTS source_check_runs (
    id UUID PRIMARY KEY,
    resource TEXT NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'partial', 'error')),
    scope JSONB NOT NULL DEFAULT '{}',
    error_code TEXT
);
CREATE INDEX IF NOT EXISTS source_check_runs_resource_attempt_idx
    ON source_check_runs (resource, attempted_at DESC);
CREATE INDEX IF NOT EXISTS source_check_runs_success_idx
    ON source_check_runs (resource, finished_at DESC) WHERE status = 'success';
