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
