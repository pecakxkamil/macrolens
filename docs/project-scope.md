# Project Scope

MacroLens is a US macroeconomic analytics portfolio project: collect and validate source data, calculate transparent indicators, explain the current economic picture and inspect documented historical relationships.

## Implemented product

- **Overview:** six compact domains with 17 latest/previous/three-period comparisons, same-month YoY context for seven MoM measures and an official Fed target-range block, exact observation periods, numerical arrows and source links; seven-day release preview, next FOMC/CME link and Markdown export. Classifications and technical evidence remain in backend products and the report audit appendix; additional readings remain in Explore Data.
- **Explore Data:** the single-indicator explorer and curated historical charts, using existing series, transformations, ranges, definitions and sources.
- **Research:** experimental Macro Conditions Index (PIT and current-vintage, decomposition, coverage and audit), Macro-Market Analysis (Nasdaq/Bitcoin comparison and lead/lag), and Indicator Relationships with its own synchronization method.
- **Auxiliary calendar:** the existing full release view, accessed from Overview rather than a fourth main tab.
- FRED ingestion and validation, PostgreSQL observations/features/releases, separate ALFRED vintage backfill, deterministic analytics and read-only FastAPI endpoints support these views.

The three-section structure relocates existing functionality. It does not change ingestion, schema, vintage selection, feature formulas, MCI components/weights/normalization or correlation/alignment rules. Legacy UI hashes remain compatible; APIs are retained.

## Limitations and future ideas

There are no AI integrations, new assets/indicators, consensus/surprise feeds, diagnostics workspace, accounts, schedules/notifications, report archive, PDF export or additional deployment infrastructure in this scope. Such ideas are not implemented commitments.

Overview and ordinary histories remain current-vintage; only the explicitly labeled PIT MCI reconstructs historical information availability. Data may be missing or lag publishers. Experimental scores and correlations are descriptive rather than forecasts or investment guidance. See the [README](../README.md) for setup and [methodology](methodology.md) for the analytical rules.
