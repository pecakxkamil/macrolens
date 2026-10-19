# Methodology

MacroLens currently defines v1 mechanical feature calculations for configured economic series.

Existing deterministic domain classifications and Macro State evidence interpret these mechanical features. Economy Brief reuses that logic; it adds no classification system or composite score. MCI methodology is documented separately below.

Methodology version: `v1`

## Product organization

Overview combines Economy Brief and Macro State; Explore Data contains the single-indicator explorer and curated charts; Research contains Macro Conditions Index, Macro-Market Analysis (including lead/lag) and Indicator Relationships. The full calendar is an auxiliary Overview view. This presentation structure changes no formulas, weights, vintage rules, normalization, correlations or synchronization methods. See [architecture](architecture.md) for routing and [README](../README.md) for setup.

## Macro Calendar

Calendar v1 maps active configured series to FRED economic releases and stores the release dates published by FRED and underlying sources. It includes scheduled dates without observations when FRED provides them. Known publisher-convention release times are represented with source timezone America/New_York and displayed in Europe/Warsaw; unknown times remain unavailable. A source-published date does not necessarily mean the observations were available on FRED or ALFRED that day.

Release details may show latest stored and previous observations as current-vintage context. They do not reconstruct actual values at the historical release date. Consensus, surprises, and release-vintage comparisons are outside Calendar v1.

## Historical Chart Data

MacroLens chart history is **current-vintage history**. For each historical
`observation_date`, observation endpoints select the latest stored vintage and
feature endpoints select the latest stored feature `as_of_date`. This is suitable
for viewing how the latest available dataset evolves across observation dates.

Current-vintage history is not point-in-time historical reconstruction. Revised
economic series may differ from the values originally published, so these chart
endpoints must not be interpreted as showing what was known at each historical
date. The separate PIT MCI reconstructs its own 15 components from ALFRED;
this does not make these chart endpoints or other snapshots point-in-time.

## PAYEMS

- `monthly_change`: value[t] - value[t-1]
- `monthly_change_ma_3m`: arithmetic mean of the latest 3 valid `monthly_change` values
- `monthly_change_ma_6m`: arithmetic mean of the latest 6 valid `monthly_change` values

## UNRATE

- `level`: current value
- `change_3m`: current value - value 3 observations earlier
- `change_6m`: current value - value 6 observations earlier
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

## UNEMPLOY

- `level`: current number of unemployed persons, published in thousands

UNEMPLOY is a count of unemployed people. It is distinct from UNRATE, which is
the unemployment rate expressed as a percentage.

## ICSA

- `moving_average_4w`: arithmetic mean of current and previous 3 observations
- `moving_average_13w`: arithmetic mean of current and previous 12 observations
- `yoy`: ((current value / value 52 observations earlier) - 1) * 100

## CCSA

- `moving_average_4w`: arithmetic mean of current and previous 3 observations
- `moving_average_13w`: arithmetic mean of current and previous 12 observations
- `yoy`: ((current value / value 52 observations earlier) - 1) * 100

## JTSJOL

- `level`: current value
- `change_3m`: current value - value 3 observations earlier
- `change_6m`: current value - value 6 observations earlier
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100

## CIVPART

- `level`: current value
- `change_3m`: current value - value 3 observations earlier
- `change_6m`: current value - value 6 observations earlier
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

## CES0500000003

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

## CPIAUCSL

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

## CPILFESL

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

## PCEPI

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

## PCEPILFE

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

## ECIALLCIV

- `qoq`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 4 observations earlier) - 1) * 100

This module supplies existing inflation momentum classifications. It adds no hot/cold label; separate MCI component scoring is documented below.

## GDPC1

- `qoq_annualized`: ((current value / previous quarter) ** 4 - 1) * 100
- `yoy`: ((current value / value 4 observations earlier) - 1) * 100

## CFNAI

- `level`: current value
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

CFNAI is an official index where zero indicates historical trend growth, positive values indicate above-average growth, and negative values indicate below-average growth. MacroLens classifies CFNAI position from its three-month average relative to zero, as documented under CFNAI Position below.

## INDPRO

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

## TCU

- `level`: current value
- `change_3m`: current value - value 3 observations earlier
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

## DGORDER

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

This module supplies existing growth momentum and trend classifications. It adds no strong/weak/recessionary label or investment signal; separate MCI scoring is documented below.

## RSAFS

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

Retail Sales is a nominal series. MacroLens does not interpret higher nominal retail sales automatically as stronger real consumption.

## PCEC96

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

PCEC96 is a real consumption series.

## DSPIC96

- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `annualized_3m`: ((current value / value 3 observations earlier) ** 4 - 1) * 100

DSPIC96 is a real disposable-income series.

## PSAVERT

- `level`: current value
- `change_3m`: current value - value 3 observations earlier
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

PSAVERT is a saving-rate level, not a growth series.

This module supplies existing consumer momentum classifications. It adds no strong/weak or sentiment label and no investment signal; separate MCI scoring is documented below.

## HOUST

- `level`: current published SAAR level
- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

Housing Starts is a seasonally adjusted annual rate level series. `mom` and `yoy` describe percentage changes in the published SAAR level. The 3M moving average smooths volatile monthly housing activity.

## PERMIT

- `level`: current published SAAR level
- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

Building Permits is a seasonally adjusted annual rate level series. `mom` and `yoy` describe percentage changes in the published SAAR level. The 3M moving average smooths volatile monthly housing activity.

## HSN1F

- `level`: current published SAAR level
- `mom`: ((current value / previous observation) - 1) * 100
- `yoy`: ((current value / value 12 observations earlier) - 1) * 100
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

New Home Sales is a seasonally adjusted annual rate level series. `mom` and `yoy` describe percentage changes in the published SAAR level. The 3M moving average smooths volatile monthly housing activity.

## MORTGAGE30US

- `level`: current value
- `change_4w`: current mortgage rate - rate 4 weekly observations earlier
- `change_13w`: current mortgage rate - rate 13 weekly observations earlier
- `moving_average_4w`: arithmetic mean of current and previous 3 observations

Mortgage-rate changes are expressed in percentage points, not relative percentage changes. These features are descriptive only and are not interpreted as automatically good or bad.

This module supplies existing housing direction classifications. It adds no strong/weak/hot/cold label, affordability score, recession label or investment signal; separate MCI scoring is documented below.

## DFF

- `level`: current Effective Federal Funds Rate

DFF is a rate level. Values are percentages and are not classified as good or bad.

## DGS2

- `level`: current 2Y Treasury yield

DGS2 is a yield level. Values are percentages and are not classified as good or bad.

## DGS10

- `level`: current 10Y Treasury yield

DGS10 is a yield level. Values are percentages and are not classified as good or bad.

## DFII10

- `level`: current 10Y real Treasury yield

DFII10 is a real yield level. Values are percentages and are not classified as good or bad.

## NFCI

- `level`: current Chicago Fed National Financial Conditions Index value
- `change_4w`: current NFCI - NFCI 4 weekly observations earlier
- `moving_average_4w`: arithmetic mean of current and previous 3 observations

NFCI zero is the historical-average reference. Positive NFCI indicates tighter-than-average financial conditions, and negative NFCI indicates looser-than-average financial conditions. `change_4w` is an absolute index-point difference.

The 2s10s Treasury spread will later be calculated as `DGS10 - DGS2` using synchronized observations with identical `observation_date`. MacroLens does not subtract independently selected latest DGS10 and DGS2 observations, does not forward-fill either Treasury series to force alignment, and does not use a separate FRED yield-spread series.

This module supplies existing curve-shape and NFCI position/direction classifications. It adds no Fed-decision inference, bullish/bearish label, recession prediction or investment signal; separate MCI scoring is documented below.

## Financial Conditions Snapshot

The Financial Conditions Snapshot is a transparent current-state view using existing computed features. It does not create an overall Financial Conditions score, does not infer future Fed decisions, does not classify rates as bullish or bearish, does not create recession predictions, and does not create investment or trading signals.

Each snapshot component includes `observation_date` and `feature_as_of_date` so data freshness is visible.

### Rate And Yield Levels

DFF, DGS2, DGS10, and DFII10 expose `level` only. These are rate or yield levels expressed in percent and are descriptive only.

### 2s10s Yield Curve

The 2s10s spread is calculated inside the snapshot:

- `spread`: DGS10 - DGS2

The calculation uses DGS10 and DGS2 observations with exactly the same `observation_date`. The snapshot chooses the latest common `observation_date` available under the requested as-of constraint. It does not subtract independently selected latest observations if their dates differ, does not forward-fill, and does not use a separate FRED spread series.

The spread `feature_as_of_date` is the maximum of the synchronized DGS2 and DGS10 `feature_as_of_date` values.

The curve-shape label is purely mathematical:

- `spread` > 0: `positive`
- `spread` < 0: `inverted`
- `spread` == 0: `flat`

This is not a recession classification, investment signal, or good/bad label.

### NFCI Position And Direction

NFCI position is based on `level` relative to zero:

- `level` > 0: `tighter_than_average`
- `level` < 0: `looser_than_average`
- `level` == 0: `average`

NFCI direction is based on `change_4w`:

- `change_4w` > 0: `tightening`
- `change_4w` < 0: `easing`
- `change_4w` == 0: `stable`

These labels describe NFCI mechanically and are not trading signals.

### Snapshot Components

- DFF: Effective Fed Funds Rate includes `level`.
- DGS2: 2Y Treasury Yield includes `level`.
- DGS10: 10Y Treasury Yield includes `level`.
- DFII10: 10Y Real Yield includes `level`.
- 2s10s: includes synchronized `dgs2`, `dgs10`, `spread`, and curve shape.
- NFCI: includes `level`, `change_4w`, `moving_average_4w`, position, and direction.

## USA Economy Now

USA Economy Now v1 is an aggregation and view layer over the six existing domain snapshots:

- Labor Market Snapshot
- Inflation Snapshot
- Growth Snapshot
- Consumer Snapshot
- Housing Snapshot
- Financial Conditions Snapshot

All domain methodologies remain unchanged. USA Economy Now does not average domain classifications, vote across components, create an overall economy score, produce strong/weak labels, create expansion/recession labels, create risk-on/risk-off labels, generate trading signals, predict markets, or infer future Fed decisions.

Economic domains have different release schedules. For that reason, USA Economy Now exposes `component_as_of_dates` for every domain. The top-level `as_of_date` is a view/reference date: when a date is requested explicitly, it is that requested date; otherwise, it is the maximum top-level `as_of_date` across the component snapshots. It is not a claim that every underlying observation shares the same date.

The current USA Economy Now snapshot is supported using the feature rows available in the current feature store. An explicit historical `as_of_date` is usable only when the required feature rows exist under that as-of constraint for all required domains. The current feature store is not a complete historical USA Economy Now reconstruction. The existing ALFRED layer reconstructs the separate PIT MCI components only; MacroLens must not substitute current revised data, forward-fill missing historical features, or recompute historical snapshots from today's revised data and call them point-in-time snapshots.

## Housing Snapshot

The Housing Snapshot is a transparent current-state view using existing computed features. It does not create an overall Housing score, does not classify housing as strong/weak/hot/cold, does not create affordability scores, does not create recession labels, and does not create investment or trading signals.

Each snapshot component includes `observation_date` and `feature_as_of_date` so data freshness is visible.

### Housing Starts Direction

Housing Starts direction is based on `mom`:

- `mom` > 0: `rising`
- `mom` < 0: `falling`
- `mom` == 0: `stable`

### Building Permits Direction

Building Permits direction is based on `mom`:

- `mom` > 0: `rising`
- `mom` < 0: `falling`
- `mom` == 0: `stable`

### New Home Sales Direction

New Home Sales direction is based on `mom`:

- `mom` > 0: `rising`
- `mom` < 0: `falling`
- `mom` == 0: `stable`

### Mortgage Rate Direction

30-Year Mortgage Rate direction is based on `change_4w`:

- `change_4w` > 0: `rising`
- `change_4w` < 0: `falling`
- `change_4w` == 0: `stable`

Mortgage-rate changes are absolute percentage-point changes. Rising/falling is descriptive only and is not treated as good or bad.

### Snapshot Components

- HOUST: Housing Starts includes `level`, `mom`, `yoy`, `moving_average_3m`, and direction.
- PERMIT: Building Permits includes `level`, `mom`, `yoy`, `moving_average_3m`, and direction.
- HSN1F: New Home Sales includes `level`, `mom`, `yoy`, `moving_average_3m`, and direction.
- MORTGAGE30US: 30-Year Mortgage Rate includes `level`, `change_4w`, `change_13w`, `moving_average_4w`, and direction.

## Consumer Snapshot

The Consumer Snapshot is a transparent current-state view using existing computed features. It does not create an overall Consumer State, does not create a Consumer score, does not classify consumers as strong or weak, does not create recession or business-cycle labels, and does not create investment or trading signals.

Each snapshot component includes `observation_date` and `feature_as_of_date` so data freshness is visible.

### Retail Sales Momentum

Retail Sales uses a mechanical nominal growth momentum comparison:

- `annualized_3m` > `yoy`: `accelerating`
- `annualized_3m` < `yoy`: `decelerating`
- Equal values: `stable`

Retail Sales is nominal. The acceleration/deceleration label describes nominal retail-sales growth only and is not interpreted as real consumer strength.

### Real Consumption Momentum

Real Personal Consumption Expenditures uses a mechanical real growth momentum comparison:

- `annualized_3m` > `yoy`: `accelerating`
- `annualized_3m` < `yoy`: `decelerating`
- Equal values: `stable`

### Real Disposable Income Momentum

Real Disposable Personal Income uses a mechanical real growth momentum comparison:

- `annualized_3m` > `yoy`: `accelerating`
- `annualized_3m` < `yoy`: `decelerating`
- Equal values: `stable`

### Saving-Rate Direction

Personal Saving Rate direction is based on `change_3m`:

- `change_3m` > 0: `rising`
- `change_3m` < 0: `falling`
- `change_3m` == 0: `stable`

Saving-rate direction is descriptive only and is not treated as good or bad.

### Snapshot Components

- RSAFS: Retail Sales includes `mom`, `yoy`, `annualized_3m`, and nominal growth momentum.
- PCEC96: Real Personal Consumption Expenditures includes `mom`, `yoy`, `annualized_3m`, and real consumption momentum.
- DSPIC96: Real Disposable Personal Income includes `mom`, `yoy`, `annualized_3m`, and real income momentum.
- PSAVERT: Personal Saving Rate includes `level`, `change_3m`, `moving_average_3m`, and descriptive direction.

## Growth Snapshot

The Growth Snapshot is a transparent current-state view using existing computed features. It does not create an overall Growth score, does not classify the economy as strong/weak/recessionary, does not create business-cycle regime labels, and does not create investment or trading signals.

Each snapshot component includes `observation_date` and `feature_as_of_date` so data freshness is visible.

### GDP Momentum

Real GDP uses a mechanical momentum comparison:

- `qoq_annualized` > `yoy`: `accelerating`
- `qoq_annualized` < `yoy`: `decelerating`
- Equal values: `stable`

### CFNAI Position

CFNAI position is based on `moving_average_3m` relative to the official zero trend reference:

- `moving_average_3m` > 0: `above_trend`
- `moving_average_3m` < 0: `below_trend`
- `moving_average_3m` == 0: `at_trend`

This is mechanical and reflects the official meaning of zero in CFNAI. It is not a strong/weak or recession classification.

### Industrial Production Momentum

Industrial Production uses the same mechanical momentum comparison as Real GDP:

- `annualized_3m` > `yoy`: `accelerating`
- `annualized_3m` < `yoy`: `decelerating`
- Equal values: `stable`

### Capacity Utilization Direction

Capacity Utilization direction is based on `change_3m`:

- `change_3m` > 0: `rising`
- `change_3m` < 0: `falling`
- `change_3m` == 0: `stable`

### Durable Goods Orders Latest Direction

Durable Goods Orders latest direction is based only on `mom`:

- `mom` > 0: `rising`
- `mom` < 0: `falling`
- `mom` == 0: `stable`

This direction is not treated as a good/bad classification.

### Snapshot Components

- GDPC1: Real GDP includes `qoq_annualized`, `yoy`, and GDP momentum.
- CFNAI: Chicago Fed National Activity Index includes `level`, `moving_average_3m`, and position relative to trend.
- INDPRO: Industrial Production includes `mom`, `yoy`, `annualized_3m`, and industrial-production momentum.
- TCU: Capacity Utilization includes `level`, `change_3m`, `moving_average_3m`, and direction.
- DGORDER: Durable Goods Orders includes `mom`, `yoy`, `moving_average_3m`, and latest direction.

## Inflation Snapshot

The Inflation Snapshot is a transparent current-state view using existing computed features. It does not create an overall inflation score, does not classify inflation as hot/cold/high/low, does not compare inflation to a policy target, and does not create investment or trading signals.

Each snapshot component includes `observation_date` and `feature_as_of_date` so data freshness is visible.

### Price Index Momentum

Headline CPI, Core CPI, Headline PCE, and Core PCE use the same mechanical momentum rule:

- `annualized_3m` > `yoy`: `accelerating`
- `annualized_3m` < `yoy`: `decelerating`
- Equal values: `stable`

### Snapshot Components

- CPIAUCSL: Headline CPI includes `mom`, `yoy`, `annualized_3m`, and price-index momentum.
- CPILFESL: Core CPI includes `mom`, `yoy`, `annualized_3m`, and price-index momentum.
- PCEPI: Headline PCE includes `mom`, `yoy`, `annualized_3m`, and price-index momentum.
- PCEPILFE: Core PCE includes `mom`, `yoy`, `annualized_3m`, and price-index momentum.
- ECIALLCIV: Employment Cost Index includes `qoq` and `yoy` values only.
- CES0500000003: Average Hourly Earnings includes `mom`, `yoy`, and `annualized_3m` as wage-pressure context only.

## Labor Market Momentum

This is momentum classification only. It is not an absolute strong/weak labor-market classification, it is not an investment signal, and there is no numeric labor score yet.

Methodology version: `v1`

### Payroll Momentum

Compare `monthly_change_ma_3m` with `monthly_change_ma_6m`.

- `monthly_change_ma_3m` > `monthly_change_ma_6m`: `improving`
- `monthly_change_ma_3m` < `monthly_change_ma_6m`: `weakening`
- Equal values: `stable`

Rationale: the recent average pace of job creation is compared with the longer six-month average.

### Unemployment Momentum

Use `change_3m`.

- `change_3m` < 0: `improving`
- `change_3m` > 0: `weakening`
- `change_3m` == 0: `stable`

### Claims Momentum

Compare `moving_average_4w` with `moving_average_13w`.

- `moving_average_4w` < `moving_average_13w`: `improving`
- `moving_average_4w` > `moving_average_13w`: `weakening`
- Equal values: `stable`

### Overall Labor Momentum

Using payroll, unemployment, and claims component classifications:

- At least 2 `improving`: `improving`
- At least 2 `weakening`: `weakening`
- Otherwise: `mixed`

## Labor Market Snapshot

The Labor Market Snapshot is a transparent current-state view using all configured labor-market series. It preserves the existing Labor Market Momentum v1 methodology exactly: overall momentum is still based only on PAYEMS, UNRATE, and ICSA.

The snapshot does not create a numeric labor score, does not classify the labor market as strong or weak, does not treat JTSJOL or CIVPART direction as good or bad, and does not classify wage growth as good or bad.

Each snapshot component includes `observation_date` and `feature_as_of_date` so data freshness is visible.

### Snapshot Components

- PAYEMS: includes `monthly_change`, `monthly_change_ma_3m`, `monthly_change_ma_6m`, and the existing payroll momentum classification.
- UNRATE: includes `level`, `change_3m`, and the existing unemployment momentum classification.
- ICSA: includes `moving_average_4w`, `moving_average_13w`, and the existing claims momentum classification.
- CCSA: includes `moving_average_4w`, `moving_average_13w`, and uses the same directional logic as ICSA: 4W lower than 13W is `improving`, 4W higher than 13W is `weakening`, equal values are `stable`.
- JTSJOL: includes `level`, `change_3m`, and `yoy`; `change_3m` > 0 is `rising`, `change_3m` < 0 is `falling`, and `change_3m` == 0 is `stable`.
- CIVPART: includes `level`, `change_3m`, and `moving_average_3m`; `change_3m` > 0 is `rising`, `change_3m` < 0 is `falling`, and `change_3m` == 0 is `stable`.
- CES0500000003: includes `mom`, `yoy`, and `annualized_3m` values only.

## Macro Relationships v1

Relationships uses the existing raw observation and computed-feature history loaders. Both provide the latest stored value for each observation date (`history_type = current_vintage`), so revised values can differ from those available at the time. The comparison does not reconstruct historical vintages.

For two or three selected histories, the backend chooses the lowest frequency: quarterly before monthly, monthly before weekly, weekly before daily. It groups observation dates into calendar quarters, calendar months, ISO weeks, or exact days at that frequency. Within each period and each history, it takes the latest dated non-null finite observation. No missing period is filled, and each aligned period appears once. Alignment uses economic observation dates, not publication dates; it applies no lead, lag, or causal interpretation.

The response keeps periods with at least one selected value. Each pair's `overlapping_observation_count` counts only periods with both values. Pearson correlation is computed from those paired values only; it is null with fewer than three pairs or if either side has zero variance. With three indicators, the API reports all three pairwise comparisons. Date filters are passed to the existing history loaders before grouping.

Actual-value mode uses separate chart axes for differing units. Indexed mode uses 100 at the first period where all selected values are present and nonzero; every displayed value is divided by its own baseline value and multiplied by 100. If no shared nonzero baseline exists, indexed mode is unavailable. The index is a visual comparison of relative changes, not a measure of economic strength. Correlation describes historical co-movement, not causation or future market moves.

## Macro State v1

Macro State is a descriptive synthesis of the six existing USA Economy Now domain
snapshots. It projects their stored feature readings and classifications without
recomputing economic features or changing domain methodology. The API preserves
the top-level date, component dates, and each selected reading's observation and
feature dates. Domain as-of dates describe snapshot freshness; they are not a shared
publication date for all underlying observations.

Labor retains its existing overall momentum based on payrolls, unemployment, and
initial claims. Other domains receive no overall classification. Retail sales
remains explicitly nominal. Inflation, growth, housing, and financial directions
retain their original meaning; rising, falling, accelerating, and decelerating
receive contextual styling rather than a good/bad judgment.

Evidence statements are fixed templates over existing classifications. The three
curated cross-current rules require both classifications to match exactly:

- Labor overall momentum is `improving` and payroll momentum is `weakening`.
- Real GDP momentum is `decelerating` and industrial production momentum is `accelerating`.
- Housing starts direction is `falling` and building permits direction is `rising`.

No other combinations trigger these rules, including stable states or the
reverse combination. Each detected cross-current returns its domain, descriptive
summary, and both underlying classifications as structured evidence. An empty
list means none of these curated rules matched; it does not establish agreement
across all macro indicators.

Macro State creates no single economic score, recession probability, economic
regime, trading signal, or forecast. Cross-currents highlight conflicting
directional evidence without causal interpretation or market predictions.
Current-vintage limitations continue to apply: stored values may include
revisions, and this view does not reconstruct what was known at a historical
date. Macro State v1 has no historical or ALFRED reconstruction.

## Macro Conditions Index v1

### Definition and interpretation

The Macro Conditions Index (MCI) is a monthly, descriptive 0-100 composite of six
domain subindices. Its methodology version is `v1`. The 50 reference denotes
historically typical activity conditions or the specified inflation-stability
reference distance; above 50 indicates broader relatively favorable/strong
conditions, and below 50 broader relatively weak conditions. These are
analytical comparisons, not economy regime classifications, economic welfare
measures, or predictions.

MCI does not model recession probability, market returns, or trading decisions.
No parameters are fitted, optimized, or chosen using asset performance. No
market asset overlays are included.

### Explicit components and orientation

Only the following 15 components are included. Inputs are existing stored
MacroLens v1 computed features; the index does not recompute their methodology.

| Domain | Component / source | Raw component value | Orientation | Within-domain weight |
| --- | --- | --- | --- | --- |
| Labor | PAYEMS payroll momentum | monthly_change_ma_3m - monthly_change_ma_6m | Higher | 1/3 |
| Labor | UNRATE unemployment change | change_3m (percentage points) | Lower | 1/3 |
| Labor | ICSA initial claims momentum | moving_average_4w - moving_average_13w | Lower | 1/3 |
| Inflation | CPIAUCSL headline CPI | yoy (%) | Distance from 2% | 1/3 |
| Inflation | CPILFESL core CPI | yoy (%) | Distance from 2% | 1/3 |
| Inflation | PCEPILFE core PCE | yoy (%) | Distance from 2% | 1/3 |
| Growth | GDPC1 real GDP | qoq_annualized (%) | Higher | 1/3 |
| Growth | CFNAI activity | moving_average_3m | Higher | 1/3 |
| Growth | INDPRO production | annualized_3m (%) | Higher | 1/3 |
| Consumer | PCEC96 real consumption | annualized_3m (%) | Higher | 1/2 |
| Consumer | DSPIC96 real disposable income | annualized_3m (%) | Higher | 1/2 |
| Housing | HOUST housing starts | yoy (%) | Higher | 1/3 |
| Housing | PERMIT building permits | yoy (%) | Higher | 1/3 |
| Housing | HSN1F new home sales | yoy (%) | Higher | 1/3 |
| Financial Conditions | NFCI | level | Lower | 1 |

The two labor differences preserve the existing payroll/claims momentum
comparisons. A declining unemployment-rate change has the same orientation as
existing unemployment momentum. Higher real output, consumption, income, and
housing activity growth describes expansion in those particular activities.
Housing uses growth rather than trending raw levels; it does not score prices,
affordability, housing welfare, or whether increasing construction is desirable.
NFCI's lower orientation means looser conditions relative to history; it does
not assert that ever-looser finance improves economic welfare. Policy rates,
Treasury yields, yield-curve shape, and mortgage rates are omitted because their
orientation is ambiguous. Nominal retail sales is omitted from consumer scoring.

### Historical activity normalization

For each non-inflation component, first form one valid component observation per
eligible calendar month (quarterly GDP is the exception described below). Let
`x_t` be the current raw component and `H_t` the expanding reference containing
only component observations through that eligible month, including `x_t`.
There are no future observations in this reference.

With `N = size(H_t)`, the midrank percentile is:

`P_t = 100 * (count(x in H_t where x < x_t) + 0.5 * count(x in H_t where x = x_t)) / N`

Higher-oriented components use `S_t = P_t`; lower-oriented components use
`S_t = 100 - P_t`. Scores are bounded to 0-100. A tied constant history and a
symmetric median observation score 50. The inclusion of half the tied values
avoids assigning an extreme score to a constant history.

Require at least **60 distinct eligible monthly component observations**, or
**20 distinct eligible quarterly GDP observations**, before an activity score
is available. These fixed v1 warm-up requirements approximate five years of
reference observations; gaps can lengthen the calendar period. Carried GDP
values do not increase the quarterly reference count. Earlier warm-up scores
are null. The expanding reference starts at the first stored valid component
observation, so differing stored history coverage can affect normalization.

### Inflation stability reference

Inflation is not assigned a simple lower-is-better orientation. For each of
headline CPI YoY, core CPI YoY, and core PCE YoY:

`S_t = max(0, 100 * (1 - abs(inflation_yoy_t - 2) / 4))`

The fixed analytical reference is **2%** and the zero-score distance is **4
percentage points**. Thus 2% scores 100; 0% and 4% score 50; -2% and 6% score 0.
Larger deviations also score 0. Both deflation and inflation above the reference
reduce stability scores. The 4pp scale is an explicit v1 design constant,
not an estimated economic boundary or a parameter fitted to market outcomes.
The 2% reference is applied consistently for comparison across these measures;
it is not a claim that CPI and core measures share an official policy target.

Inflation needs a finite current value but no historical warm-up. Its score of
50 is a specified reference distance, not an empirical median. Consequently the
overall index is not forced to have a historical median of exactly 50.

### Equal domains, contributions, and missing data

Components are equally weighted within their domain. Every domain weight is
**1/6**, regardless of its number of components:

`Domain_d = sum_i(component_score_i / component_count_d)`

`MCI = sum_d(Domain_d / 6)`

A component's domain contribution is `score * within_domain_weight`; its MCI
contribution is `score * within_domain_weight / 6`. A domain's MCI contribution
is `domain_score / 6`. The current API returns raw values, source inputs,
orientations, reference sample counts/dates, weights, and these contributions.
Scores are calculated with full numerical precision; display rounding does not
change the calculation.

All configured components are required for a domain score; all six domains are
required for MCI. Missing, nonfinite, unmatched, or insufficient-history inputs
produce null scores. Existing weights remain fixed. No components/domains are
dropped, reweighted, interpolated, or imputed as 50. Available component/domain
scores remain visible even when their containing composite is unavailable.

### Frequency alignment and GDP carry-forward

Output rows use **calendar month-end observation dates** and include completed
months only. For monthly sources, use the latest finite observation within that
month. For weekly claims and NFCI, select the latest finite component observation
within that month, not an average of weekly percentiles. Components needing two
features require an exact shared source observation date before subtraction.
There is one normalization sample per month, not one per week. Monthly and
weekly components are never carried into a later month.

FRED GDP observation dates denote quarter starts. A quarterly GDP feature is
eligible in the month immediately **after the quarter ends**: January-quarter
GDP first enters April, April-quarter GDP enters July, and so on. Normalize each
new GDP observation against eligible quarterly observations and then carry
**both its raw value and its score** for that month and at most two subsequent
months. Carry does not create extra reference observations. This is an explicit,
conservative period-alignment convention, not reconstructed publication timing
or interpolation. If a subsequent quarter is missing, the older value expires
after its three-month eligibility window and the growth score becomes null.

The current response chooses the most recent complete MCI month. It also exposes
`latest_evaluated_month` and the selected `observation_date` so an older complete
month cannot silently appear current. If no complete MCI exists, return the latest
evaluated row with null MCI and its available decomposition. Empty histories
return null current scores and an empty history.

History range filters are applied after building the full expanding reference.
Changing `start_date` therefore does not reset normalization. `end_date` limits
eligible month-end rows, and future dates are capped at today's calculation
cutoff. A mid-month endpoint does not include that incomplete endpoint month.

### Current-vintage limitations and API

Both endpoints expose `history_type = "current_vintage"` and
`methodology_version = "v1"`:

- `GET /api/v1/economy/us/mci`
- `GET /api/v1/economy/us/mci/history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

These endpoints are read-only and accept no methodology tuning parameters.
History reads the latest stored feature value for each economic observation
date. Revisions can change earlier raw values and their expanding reference
distribution, so historical index values may differ from real-time calculations.
Economic observation periods, not actual historical publication availability,
drive alignment. Feature freshness dates can be later than an index observation
month because of revisions.

The calculation excludes future economic observations from each row's expanding
reference; it does **not** reconstruct historical vintages or all release lags.
The historical index must not be presented as an investable/backtest signal.
ALFRED reconstruction and market overlays remain outside MCI v1.

## Point-in-Time Macro Conditions Index infrastructure v1

### Products and source provenance

The existing `history_type=current_vintage` MCI remains unchanged. Its historical
rows use today's stored revised values. The separate `history_type=point_in_time`,
`methodology_version=v1` product reconstructs only vintages known by each as-of
date. Point-in-time MCI is designed to reduce look-ahead bias. It is not a
validated trading or forecasting model.

The separate backfill uses the official
[FRED/ALFRED series observations API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html)
with `output_type=1` (observations by real-time period), `units=lin`, and the
inclusive real-time window `1776-07-04` through the requested cutoff. Paginated
change intervals preserve repeated observation dates across different vintages.
An observation date describes the economic period; `vintage_date` is the returned
`realtime_start`, meaning when that version became available in the source's
real-time history. `realtime_end` is its inclusive validity end, not an ingestion
timestamp. See [real-time period semantics](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).
Existing FRED snapshot rows are excluded unless the authoritative backfill
promotes the same key. Null source values remain null; expiration never revives
an earlier value. All source payloads are stored immutably and series coverage
is verified only after a complete successful transaction.

### Reconstruction and alignment

For T, select each observation's latest vintage with `vintage_date <= T` and
`observation_date <= T`. Recompute the required features on that selected dataset
with the existing pure feature formulas. Never read `computed_features` for PIT.
Missing monthly, quarterly, or weekly periods are explicit nulls, so rolling and
shift operations cannot compress gaps. An expanding normalization reference is
reconstructed from the history known at T; revisions may change later as-of
scores but cannot change earlier as-of scores. Existing v1 orientations,
inflation target scoring, warmups (60 monthly / 20 quarterly), equal component
weights within domains, and six equal domain weights are preserved.

Rows use calendar month-end as-of dates. At each date use the latest finite
component feature actually known then. Monthly source periods may be carried
until their age exceeds three calendar months. Weekly ICSA/NFCI periods expire
after 35 days. GDP quarters must actually be known and have ended; they expire
six months after their quarter-start observation date. Carry is explicit in
component responses. Missing/unverified/expired inputs keep fixed weights and
make their domain and the full index unavailable; no future values or
interpolation fill them. The latest endpoint evaluates the latest completed
month-end within common completed-backfill coverage, even if its score is null.

### Coverage and audit

No common vintage start is assumed. History starts at the first month-end within
all 15 series' known vintage coverage; early rows may have null scores while
warmups or missing values prevent a full index. `coverage.first_valid_as_of_date`
is derived from the earliest actual valid full-index history row, including when
served from cache. It is calculated before applying the display start-date filter;
a historical cutoff excludes later valid rows. Current and audit responses use
the same history-derived date, rather than leaving it null. Per-series metadata reports first
observation/vintage dates, stored vintage row counts, completed coverage cutoff,
and missing series. This date is derived from the local backfill, not fabricated
or hardcoded; inspect the rebuild output/API for the current coverage.

The exact-date audit returns each component's raw transformed value, score,
weights/contributions, source observation, raw dependencies and their vintage
dates and real-time interval ends. Its concise normalization summary reports the
method, reference count, range, and below/equal/above rank counts (or the inflation
target and distance). Full reference distributions and selected raw input grids
remain internal for regression tests and are omitted from the normal API response.
This lets an auditor verify feature dependencies and the normalization result
using only data known at T. History uses two bulk vintage/coverage reads, an ordered
vintage sweep, and per-series feature reuse when its known inputs do not change.
An optional local JSON history cache is invalidated by completed backfills.

### Date-level limitation

ALFRED's real-time date does not establish precise intraday availability. An
as-of date includes vintages dated that day. PIT v1 therefore uses monthly
month-end analysis and makes no minute-level availability claim. Calendar
scheduled release times are not used to infer when ALFRED had the observations.

## Market Comparison Lab v1

### Universe and provenance

The separate `config/market_assets.yaml` explicitly configures NASDAQCOM
(Nasdaq Composite, equity index, index points) and CBBTCUSD (Coinbase Bitcoin,
cryptocurrency, USD). It defines provider, frequency, source links, observation
conventions, and attribution so additional providers/assets can be introduced
without changing alignment/scoring logic. V1's sole provider is FRED; arbitrary
series IDs, gold, and other assets are not accepted.

NASDAQCOM observations are daily market closes from Nasdaq, Inc.; the source
unit is Index Feb 5, 1971=100. CBBTCUSD is a daily seven-day Coinbase price series;
its official notes specify observations as of 5 PM PST. The API/UI preserve
these descriptions without claiming matching intraday timestamps. See official
[Nasdaq source notes](https://fred.stlouisfed.org/series/NASDAQCOM) and
[Coinbase source notes](https://fred.stlouisfed.org/series/CBBTCUSD). These datasets
are copyrighted by their source organizations; source terms govern reproduction.
MacroLens does not claim ownership. Only monthly aligned values needed for the
comparison are exposed, rather than redistributing complete raw daily responses.

The explicit refresh path uses ordinary FRED observations with the existing key,
validation, raw storage, and database upsert. Source `.` values are stored as null,
never zero prices. Nonpositive numeric prices and incomplete responses are
rejected. Both v1 series fit FRED's 100000-row snapshot cap; truncation is an
error, not a silently accepted refresh. Unique raw filenames with exclusive
creation preserve every original response. Composite observation/vintage keys
make repeated refreshes idempotent. Market histories use the latest stored values
for each price observation date; they are not full ALFRED vintage histories.
Market storage uses category `market` and is excluded from active macro workflows.

### Macro history and alignment

The default macro product is Point-in-Time MCI v1, using only economic vintages
known by each historical month-end. Explicit current-vintage mode uses today's
stored revised macro values, and is clearly labeled. Neither macro product's
calculation, weights, or scores are modified by market comparison.

For each completed MCI month-end T, select the latest finite positive market price
whose observation date is on or before T. Nasdaq weekends/holidays therefore
use the preceding available close; Bitcoin can use an exact weekend date. Future
prices, nearest future dates, and interpolation are never used. Before an asset's
first observation, its value and date are null. Missing dates are skipped when
finding the last available price; there is no age-based expiry. Actual market
dates and source coverage remain visible so carried prices can be identified.
Monthly MCI gaps remain null and are not interpolated or reweighted.

### Display modes and shared base

The first selected-range month-end with a finite MCI and a positive aligned price
for every selected asset is the common `base_date`. Each original price is
reported in `base_values`. Indexed asset values at/after that date are
`100 * price / base_price`; assets never use independent base dates. Missing
prices stay null. No shared base returns a structured `insufficient_overlap`
result, explanation, and null indexed values. Max starts at the first shared
valid date. Explicit ranges may include unavailable periods before their base.
Full common coverage metadata lets the default 5Y UI fall back to Max when
less than five calendar years are available, without treating isolated macro
score gaps as shorter coverage.

MCI is a bounded state score, not a price. It remains on its native 0-100 axis
in both modes and is never ratio-rebased. Indexed assets share a distinct,
clearly labeled base-100 axis. Actual assets use separate index-points and USD
axes. Numeric magnitudes on these different scales are not directly comparable.
Only overall MCI is shown, without domain overlays.

### Monthly returns and correlation

Aligned monthly price return is `100 * (P_t / P_(t-1) - 1)`. MCI change is
`MCI_t - MCI_(t-1)` in points. Both require consecutive calendar month-end rows
and valid inputs; gaps in the calendar or required inputs produce null changes.
The preceding month may lie outside the display range, because it is required to
calculate the first selected month's actual monthly change/return. Returns are
calculated from actual aligned prices regardless of chart display mode.

Each asset has two contemporaneous Pearson correlations over the selected range:
MCI level versus that month's asset return, and MCI monthly change versus that
month's asset return. Each correlation uses only its own finite paired rows and
reports its overlapping observation count and variable definitions. Fewer than
three pairs or zero variance yields null. For pairs `(x_i,y_i)`, Pearson is
`sum((x_i-mean(x))*(y_i-mean(y))) / sqrt(sum((x_i-mean(x))^2)*sum((y_i-mean(y))^2))`.
This reuses the existing pure correlation function; no lead/lag analysis is added.

Correlation describes historical co-movement. It does not imply causation or
predictive power. NASDAQCOM price-index changes exclude dividends and are not
total returns; Coinbase Bitcoin represents one venue. Market observations can
be corrected by sources; PIT macro availability is date-level rather than
intraday. The workspace provides no forecasts, expected returns, targets,
trading signals, optimized weights, or strategy P&L.


## Macro?Market Lead/Lag Analysis v1

The separate Lead / Lag Analysis section of `#/research/macro-market` uses existing
Nasdaq Composite (`NASDAQCOM`) and Bitcoin (`CBBTCUSD`) observations only. PIT
MCI is the default; current-vintage is explicitly optional. No MCI construction,
weights, ingestion or original Market Comparison alignment is changed.

Definitions: `delta_MCI_t = MCI_t - MCI_(t-1)` in index points;
`R_asset_t = 100 * (P_t / P_(t-1) - 1)` in percent, where `P_t` is the last
finite positive observed price on or before calendar month-end. This analysis
rejects that price if it is more than **7 calendar days** old. This permits
ordinary weekends/holidays while preventing indefinite stale-price carry.
This freshness rule applies only to the new analysis.

For each integer `k = -6,...,+6`, compute
`Corr(delta_MCI_t, R_asset_(t+k))`. Positive k means MCI change precedes the
return; negative k means return precedes MCI change; zero is contemporaneous.
Pairs use exact calendar-month dictionary keys, never row-index shifts,
nearest-month matches, interpolation or multi-month returns. Missing/null MCI
at t or the immediately preceding month invalidates the change. An unavailable
price at either consecutive month-end invalidates the return. Dates and price
observation dates are included in each scatter-ready pair.

Only the MCI anchor month-end t is restricted by start_date/end_date (inclusive).
Full prior stored history is loaded for deltas, negative lags, returns and rolling
windows. Prices are loaded through up to six months after end_date, capped at
today; incomplete calendar months are excluded. Positive-lag return months may
therefore fall outside the reporting range. Missing actual observations remain
unavailable, including at the dataset boundary. The API exposes its loading
window and reporting/coverage metadata.

Pearson r uses finite valid pairs; N and first/last valid MCI anchor dates are
reported for every lag. Fewer than three pairs or zero variance returns null,
never zero. There are no p-values, optimized lags or regression forecasts.
Rolling windows cover exactly 24 or 36 calendar anchor months ending at t and
require every paired month to be valid. A missing month makes r null; windows
never compress to the last N available observations. Rolling windows can begin
before the reporting range. Positive k uses later returns relative to the
rolling anchor: these diagnostics are retrospective, not investable signals.

All 13 lags remain visible with sample counts, a rolling stability chart and
scatter tooltips identifying anchor month, return month, units and asset.
Correlation is descriptive, not causal or predictive. Same-month correlation
is not a prediction. Multiple testing and unstable correlations limit
interpretation. PIT availability is date-level, not intraday; market histories
are latest stored observations rather than vintage market histories.

Read-only endpoint: `GET /api/v1/market-comparison/lead-lag` with `assets`,
`start_date`, `end_date`, `macro_history_type=point_in_time|current_vintage`,
and `rolling_window=24|36`. Both existing assets are returned by default;
the UI requests its selected analysis asset. Asset whitelist, dates, history
mode and rolling window are validated. No schema change or data sync is needed.


## Economy Brief v1

Overview (`#/`) presents 17 current-vintage comparison rows and an official Fed target-range block in six compact domain cards,
with at most three explicitly selected indicators per domain. It retains the
Overview / Explore Data / Research navigation and EN/PL switch. Cards show
numbers and comparisons, without domain interpretations, momentum tags, repeated
comparison summaries or per-indicator methodology panels. Broader series and
transformation details remain in Explore Data; MCI and historical analyses remain
in Research. Indicator names link to exploration and source links expose series
definitions. Calendar and next FOMC/CME context remain below the cards.

`GET /api/v1/economy/us/brief` still aggregates the existing snapshot and projects
Macro State from it. These classifications are unchanged and retained for audit.
The `reading_comparisons` section supplies the 17 main comparisons using one
shared query over existing stored features. Current-vintage selection preserves
`as_of_date DESC, computed_at DESC, id DESC` for each observation and methodology
v1. The database returns only the required windows/four daily observations and
an optional newer null-period marker, not full histories. The existing six-item
`changes` section is retained, deriving its YoY entries from same-period contexts without another history query.

Every comparison uses the same series and transformation throughout: payroll
monthly change, claims 4W average, CPI/PCE MoM, GDP QoQ annualized, CFNAI 3M
average, industrial-production/consumption/income/nominal-retail MoM and the
existing rates/levels. The seven monthly MoM rows include smaller YoY context
joined by the same series ID and exact observation month for each column.
Missing context remains missing, without falling back to a different month.
The existing stored MoM calculation is used directly; no MoM is derived from YoY.
Official FRED metadata confirms SA monthly CPIAUCSL/CPILFESL/PCEPILFE/INDPRO/RSAFS
and SAAR monthly PCEC96/DSPIC96 levels. Annual-rate level scaling does not add
a second annualization to the existing MoM ratio. See README for source links
and metadata verification/refresh instructions. Selection anchors to the latest finite stored observation
of each measure, independently of the page date:

| Frequency | Previous | Three periods earlier | Missing periods |
| --- | --- | --- | --- |
| Monthly | Exact prior calendar month | Exact third prior calendar month | Missing; no substitution |
| Quarterly | Exact prior quarter | Exact third prior quarter | Missing; no substitution |
| Weekly | Seven days earlier | 21 days earlier | Missing; no substitution |
| Daily | Previous available finite observation | Third earlier available finite observation | Count available observations; show exact dates |

Daily offsets are neither calendar-day nor business-day offsets: for example,
DFF in Explore Data can contain weekend observations while Treasury yields may not. The curve
uses synchronized same-date DGS10 minus DGS2 observations before selecting its
previous/third-prior observations. Missing or nonfinite values are never zero;
calendar gaps are never compressed or interpolated. A newer stored missing
period does not replace a finite reading; its date remains in audit metadata.

Changes are arithmetic differences in the displayed measure, not additional
growth-rate calculations. Percentage rates/growth use percentage points, index
levels use index points, and other levels retain their units. The shared unit
beside an indicator applies to its three values and same-unit difference;
percentage-point differences are labeled separately from percent readings.
Older values are current-vintage revisions, not original values known at release.

The arrow always follows the numerical sign, including for indicators where a
rise is conventionally unfavorable. Only the arrow/difference is colored by a
small explicit presentation map: unemployment/claims rises red and falls green;
employment/real activity/real spending rises green and falls red; inflation
MoM direction stays neutral for all signs; lower monthly inflation alone is
not assigned an improved classification. Fed/mortgage rates, spreads, nominal retail sales and NFCI are
neutral. Unchanged and unavailable changes are neutral. There are no economic
thresholds, new classifications, scores or trading signals in this display.

The Fed target block uses only official DFEDTARL/DFEDTARU raw stored histories,
with both values joined on their observation date and lower <= upper validated.
It does not derive a target from DFF. A server-side cursor stops consuming paired
history at the latest contiguous range transition or a gap. An adjacent valid
previous pair is required to establish **Effective since** and **Last rate change**.
Changes are calculated in basis points for each bound, with separate moves if
the range width changes. An unchanged daily range is not a new decision; no last
FOMC decision date is inferred. A gap or incomplete regime history leaves the
change/effective date unknown. Invalid latest bounds do not fall back to older
ranges or DFF. Observation cutoffs and source ingestion timestamps remain separate
from the effective date and current page assembly time; no uniform age threshold
or freshness guarantee is added. New target-bound series are ordinary data inputs
for this block and Explore Data, not MCI/PIT components. No schema change is needed.

The next seven calendar days include today in Europe/Warsaw and the following
six dates. Existing release importance, supported time metadata and low-importance
grouping remain unchanged. FOMC uses the separately stored official Federal
Reserve schedule, with the next decision independent of the seven-day window.
Known UTC instants use standard Europe/Warsaw conversion, including US/Polish
DST mismatches; unknown times remain explicit. An unavailable calendar differs
from a successful empty stored calendar. FedWatch remains an external link.

**Download report** creates a UTF-8 Markdown file from the same prepared comparison
objects used by the screen, including all three values, periods and differences.
Its short main section contains the six domains and upcoming releases/FOMC.
Source details, full comparison metadata, snapshot/classification evidence and
limitations follow in the audit appendix. No PIT request is made by Overview;
PIT MCI remains in Research. Downloading never refetches data or recalculates PIT.
The existing optional external-AI instruction is text only; there is no AI
integration, model configuration, report archive or scheduler.

Report preparation time and data assembly time remain separate from observation
periods, publication dates, vintage dates and feature calculation dates. No
publication date is inferred and no common freshness threshold is introduced.
Section failures remain explicit and isolated: history comparisons/calendar can
remain usable when snapshot/state is unavailable. A failed comparison section
shows missing cells, never snapshot values with fabricated earlier readings.
Transport failure shows the existing error/retry state. No ingestion, database
schema, backend classification, MCI/PIT or Research methodology was changed.

For setup and local review commands see the [README](../README.md). Check the six
cards, calendar and downloaded report using `/api/v1/economy/us/brief`, including
exact expected periods for missing cells, at desktop and narrow widths.

### Economy Brief presentation and classification context

The backend Macro State synthesis/evidence and classification bases are preserved
in the API and report audit appendix. They are not shown on the numeric cards or
at the start of the report. A numerical period-to-period arrow does not inherit
an unrelated momentum classification. Calculation metadata and complete ISO
timestamps remain available for audit. Availability and recency are distinct;
snapshot/calculation dates do not prove publication dates or newer releases.

The brief API also projects `classification_basis` from the existing snapshot,
without querying more observations or recomputing any classification. It includes
the actual inputs, feature names, observation period, calculation date and rule:

- Payroll momentum compares 3-month with 6-month average job gains.
- Unemployment momentum uses the 3-month rate change, not the latest monthly change.
- Claims momentum compares 4-week with 13-week averages; lower is improving.
- Inflation, consumer and industrial-production momentum compare the current
  3-month annualized pace with YoY for the same ending observation period.
- GDP momentum compares the current quarter's QoQ annualized rate with that
  quarter's YoY rate, not with the prior quarter's annualized rate.
- CFNAI position uses its 3-month average relative to zero.
- Capacity utilization and saving-rate directions use 3-month changes;
  housing activity uses month-to-month changes; mortgage direction uses 4 weeks.
- Yield-curve shape is the sign of the 10Y-minus-2Y spread. NFCI position uses
  its level relative to zero and NFCI direction uses its 4-week change.
- Overall labor momentum retains the existing rule: at least two improving
  components means improving, at least two weakening means weakening, else mixed.

Thus a higher successive CPI YoY reading can coexist with decelerating momentum;
a lower successive GDP quarterly rate can coexist with accelerating momentum.
These describe different comparisons. The report keeps their actual values and
rules separate; displayed readings do not inherit unrelated classification tags.
Classification calculations use the original unrounded features.

Repeated low-importance calendar releases are grouped on Overview with all dates
and expandable entries. Source events and the full calendar are unchanged, and
the report retains every event. Identical source URLs are listed once. Markdown
uses blank-separated headings, paragraphs and lists, literal date brackets and
intra-word underscores, without redundant escaping. Download still uses only
the loaded data and makes no additional request.


## Interface languages (EN / PL)

The upper-right EN / PL switch changes the interface language across Overview,
Macro State, Macro Index, Market Comparison (including lead/lag), Charts,
Indicators and Calendar. It includes controls, accessibility labels, chart labels,
tooltips, indicator descriptions, classifications, API evidence and methodology
text. The initial language remains English; preference is stored locally under
`macrolens.language`, restored after reload and synchronized between browser tabs.

Switching preserves the current route, selected indicators, ranges and other
controls; it does not fetch the same data again. Polish formatting uses `pl-PL`
for numbers/dates and Polish large-number abbreviations. Release times still use
Europe/Warsaw with timezone-aware DST handling. Indicator search accepts both
Polish displayed names and original English names/series IDs.

Economy Brief Markdown follows the selected language and the same loaded data.
Technical series IDs, raw feature identifiers, API parameters, formulas and
source URLs remain unchanged; backend data and classification/MCI calculations
are not translated or modified. Translation is local and deterministic, with no
translation service or AI integration. Unknown externally supplied names retain
their source spelling until a translation is added to the bundled dictionary.
