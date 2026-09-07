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
