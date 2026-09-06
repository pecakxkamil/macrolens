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
