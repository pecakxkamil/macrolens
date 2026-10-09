# Methodology

MacroLens currently defines v1 mechanical feature calculations for configured economic series.

These are mechanical feature calculations only. Macro-state scoring and economic interpretation methodology are still not designed and should not be invented.

Methodology version: `v1`

## Macro Calendar

Calendar v1 maps active configured series to FRED economic releases and stores the release dates published by FRED and underlying sources. It includes scheduled dates without observations when FRED provides them. Dates are displayed without times or time zones. A source-published date does not necessarily mean the observations were available on FRED or ALFRED that day.

Release details may show latest stored and previous observations as current-vintage context. They do not reconstruct actual values at the historical release date. Consensus, surprises, and release-vintage comparisons are outside Calendar v1.

## Historical Chart Data

MacroLens chart history is **current-vintage history**. For each historical
`observation_date`, observation endpoints select the latest stored vintage and
feature endpoints select the latest stored feature `as_of_date`. This is suitable
for viewing how the latest available dataset evolves across observation dates.

Current-vintage history is not point-in-time historical reconstruction. Revised
economic series may differ from the values originally published, so these chart
endpoints must not be interpreted as showing what was known at each historical
date. True point-in-time reconstruction remains planned and will require
vintage-aware / ALFRED ingestion and feature computation.

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

Inflation state, hot/cold classification, and inflation scoring are not designed yet.

## GDPC1

- `qoq_annualized`: ((current value / previous quarter) ** 4 - 1) * 100
- `yoy`: ((current value / value 4 observations earlier) - 1) * 100

## CFNAI

- `level`: current value
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

CFNAI is an official index where zero indicates historical trend growth, positive values indicate above-average growth, and negative values indicate below-average growth. MacroLens does not create a Growth classification from CFNAI yet.

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

Growth state, growth scoring, strong/weak/recessionary classification, and investment signals are not designed yet.

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

Consumer state, consumer scoring, strong/weak classification, sentiment-based classification, and investment signals are not designed yet.

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

Housing state, housing scoring, strong/weak/hot/cold classification, affordability scoring, recession labels, and investment signals are not designed yet.

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

Financial Conditions State, financial conditions scoring, Fed-decision inference, bullish/bearish rate labels, recession predictions, and investment signals are not designed yet.

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

The current USA Economy Now snapshot is supported using the feature rows available in the current feature store. An explicit historical `as_of_date` is usable only when the required feature rows exist under that as-of constraint for all required domains. MacroLens storage is not yet a complete point-in-time vintage history. True historical reconstruction will require the planned vintage-aware / ALFRED layer; MacroLens must not substitute current revised data, forward-fill missing historical features, or recompute historical snapshots from today's revised data and call them point-in-time snapshots.

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
