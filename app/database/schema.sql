CREATE TABLE IF NOT EXISTS series (
    series_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    short_name VARCHAR,
    category VARCHAR NOT NULL,
    frequency VARCHAR NOT NULL,
    unit VARCHAR,
    revision_tracking BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS observation_vintages (
    id BIGSERIAL PRIMARY KEY,
    series_id VARCHAR NOT NULL REFERENCES series(series_id),
    observation_date DATE NOT NULL,
    vintage_date DATE NOT NULL,
    value NUMERIC,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (series_id, observation_date, vintage_date)
);

CREATE TABLE IF NOT EXISTS computed_features (
    id BIGSERIAL PRIMARY KEY,
    series_id VARCHAR NOT NULL REFERENCES series(series_id),
    observation_date DATE NOT NULL,
    as_of_date DATE NOT NULL,
    feature_name VARCHAR NOT NULL,
    feature_value NUMERIC,
    methodology_version VARCHAR NOT NULL DEFAULT 'v1',
    computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (
        series_id,
        observation_date,
        as_of_date,
        feature_name,
        methodology_version
    )
);

CREATE TABLE IF NOT EXISTS economic_releases (
    release_id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    source_link VARCHAR,
    press_release BOOLEAN,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS series_release_map (
    series_id VARCHAR NOT NULL REFERENCES series(series_id),
    release_id INTEGER NOT NULL REFERENCES economic_releases(release_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (series_id, release_id)
);

CREATE TABLE IF NOT EXISTS release_dates (
    release_id INTEGER NOT NULL REFERENCES economic_releases(release_id),
    release_date DATE NOT NULL,
    release_last_updated VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (release_id, release_date)
);

CREATE INDEX IF NOT EXISTS release_dates_date_idx ON release_dates (release_date);

-- Snapshot requests do not establish historical availability. Only verified
-- ALFRED interval downloads are used by PIT loaders.
ALTER TABLE observation_vintages ADD COLUMN IF NOT EXISTS source VARCHAR NOT NULL DEFAULT 'fred_snapshot';
ALTER TABLE observation_vintages ADD COLUMN IF NOT EXISTS realtime_end DATE;

CREATE TABLE IF NOT EXISTS alfred_backfills (
    series_id VARCHAR PRIMARY KEY REFERENCES series(series_id),
    realtime_start DATE NOT NULL,
    realtime_end DATE NOT NULL,
    rows_downloaded BIGINT NOT NULL,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS observation_vintages_alfred_idx
    ON observation_vintages (series_id, vintage_date, observation_date)
    WHERE source = 'alfred';

-- Local ISM document versions; never part of the trusted FRED/ALFRED store.
CREATE TABLE IF NOT EXISTS ism_documents (
    id BIGSERIAL PRIMARY KEY,
    series_id VARCHAR NOT NULL,
    report_month DATE NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    raw_hash VARCHAR(64) NOT NULL,
    raw_path TEXT NOT NULL,
    UNIQUE (series_id, raw_hash)
);
CREATE TABLE IF NOT EXISTS ism_observations (
    document_id BIGINT NOT NULL REFERENCES ism_documents(id),
    observation_date DATE NOT NULL,
    value NUMERIC NOT NULL CHECK (value >= 0 AND value <= 100),
    PRIMARY KEY (document_id, observation_date)
);

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

-- Immutable direct-publisher receipts. Existing observation keys and FRED/PIT
-- semantics stay unchanged; RAW retains intraday versions of a daily snapshot.
CREATE TABLE IF NOT EXISTS publisher_documents (
    id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    http_status INTEGER NOT NULL,
    raw_hash VARCHAR(64) NOT NULL,
    raw_path TEXT NOT NULL,
    metadata JSONB NOT NULL,
    UNIQUE (source, kind, raw_hash)
);
ALTER TABLE observation_vintages ADD COLUMN IF NOT EXISTS source_document_id UUID
    REFERENCES publisher_documents(id);
ALTER TABLE observation_vintages ADD COLUMN IF NOT EXISTS publication_document_id UUID
    REFERENCES publisher_documents(id);
CREATE INDEX IF NOT EXISTS publisher_documents_source_retrieved_idx
    ON publisher_documents (source, retrieved_at, id);
CREATE INDEX IF NOT EXISTS observation_vintages_source_document_idx
    ON observation_vintages (source_document_id) WHERE source_document_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS observation_vintages_publication_document_idx
    ON observation_vintages (publication_document_id) WHERE publication_document_id IS NOT NULL;
