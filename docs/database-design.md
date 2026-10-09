# Database Design

MacroLens uses PostgreSQL 17 for local development.

The current database schema stores configured economic series, point-in-time observation vintages, and derived analytical features.

## series

Stores metadata for each configured economic data series.

Key fields:

- `series_id`: stable external series identifier, such as `PAYEMS`, `UNRATE`, or `ICSA`.
- `name`: full series name.
- `short_name`: concise display name.
- `category`: macroeconomic category, such as `labor`.
- `frequency`: release frequency, such as `monthly` or `weekly`.
- `unit`: reported unit for the series.
- `revision_tracking`: whether vintages should be tracked for the series.
- `active`: whether the series is currently included in MacroLens workflows.

## observation_vintages

Stores raw normalized observations by vintage. The uniqueness constraint on `series_id`, `observation_date`, and `vintage_date` preserves point-in-time semantics and prevents duplicate rows for the same reported value vintage.

Key fields:

- `series_id`: economic series identifier.
- `observation_date`: the economic observation period.
- `vintage_date`: the realtime/vintage date associated with the reported value.
- `value`: numeric observation value, or null for source missing values.
- `source`: `fred_snapshot` for ordinary snapshot ingestion, or `alfred` for validated real-time interval backfills. Snapshot vintage dates do not establish historical publication availability.
- `realtime_end`: inclusive source validity end for trusted ALFRED intervals; null for snapshot rows.
- `ingested_at`: timestamp when the row was loaded.

## computed_features

Stores calculated analytical features such as moving averages, period changes, growth rates, and future derived metrics. This table is storage only; feature calculations are not implemented yet.

Key fields:

- `series_id`: economic series identifier.
- `observation_date`: the economic observation period the calculated feature refers to.
- `as_of_date`: the date of the data snapshot/vintage used to calculate the feature.
- `feature_name`: feature identifier such as `monthly_change`, `moving_average_3m`, `moving_average_4w`, `yoy`, etc.
- `feature_value`: numeric calculated feature value.
- `methodology_version`: version of the feature calculation methodology, allowing calculations to evolve later without losing reproducibility.
- `computed_at`: timestamp when the feature row was calculated.

The uniqueness constraint on `series_id`, `observation_date`, `as_of_date`, `feature_name`, and `methodology_version` prevents duplicate calculations for the same point-in-time feature while allowing new methodology versions to coexist with prior results.

## economic_releases, series_release_map, release_dates

Calendar v1 persists FRED release metadata in `economic_releases`, links configured series to releases through `series_release_map`, and stores source-published dates in `release_dates`. The mapping and dates tables use composite primary keys to make repeated syncs idempotent. `release_last_updated` is retained only when FRED provides it; the Calendar does not treat it as a release time.

Calendar queries join these tables to active configured `series` rows. A release date appears once with all linked MacroLens indicators. The schema has no consensus, actual-at-release, surprise, or release-time fields. A small official-source time mapping in the API adds scheduled time metadata for supported release names without changing stored FRED dates; unknown times remain null.

## alfred_backfills (PIT MCI infrastructure v1)

Records each MCI series' fully completed ALFRED real-time window, source interval
row count, and completion timestamp. Incomplete transactions never advance this
ledger. PIT loaders use only `source=alfred` rows and verify common completed
coverage; the ledger also invalidates optional local history caches. The existing
observation/vintage key is reused, with a partial index for ALFRED lookups.

Apply the additive schema with `python -m app.database.init_db`. No index score
table is added. PIT features are reconstructed from raw selected vintages using
the shared pure formulas; the `computed_features` table remains the separate
current-vintage feature store and is never used to recreate PIT history.
