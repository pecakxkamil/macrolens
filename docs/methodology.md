# Methodology

MacroLens currently defines v1 mechanical feature calculations for configured economic series.

These are mechanical feature calculations only. Macro-state scoring and economic interpretation methodology are still not designed and should not be invented.

Methodology version: `v1`

## PAYEMS

- `monthly_change`: value[t] - value[t-1]
- `monthly_change_ma_3m`: arithmetic mean of the latest 3 valid `monthly_change` values
- `monthly_change_ma_6m`: arithmetic mean of the latest 6 valid `monthly_change` values

## UNRATE

- `level`: current value
- `change_3m`: current value - value 3 observations earlier
- `change_6m`: current value - value 6 observations earlier
- `moving_average_3m`: arithmetic mean of current and previous 2 observations

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
