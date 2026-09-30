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
