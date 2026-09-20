import { createContext, useContext, useEffect, useId, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import {
  fetchDashboardHistory,
  fetchUsaEconomyNow,
  type DashboardHistory,
  type DashboardHistoryKey,
  type UsaEconomyNow,
} from "./api/macrolens";
import {
  formatClassification,
  formatCompactCount,
  formatDate,
  formatNumber,
  formatObservationDate,
  formatPercentagePoint,
  formatPercent,
  formatSaarThousands,
  formatThousandsAsMillions,
} from "./format";
import {
  metricMetadata,
  type MetricKey,
  type MetricMetadata,
} from "./metricMetadata";

const freshnessLabels: Array<[keyof UsaEconomyNow["component_as_of_dates"], string]> = [
  ["labor", "Labor"],
  ["inflation", "Inflation"],
  ["growth", "Growth"],
  ["consumer", "Consumer"],
  ["housing", "Housing"],
  ["financial_conditions", "Financial Conditions"],
];

type ViewMode = "all" | "key" | "custom";
type DomainKey = "labor" | "inflation" | "growth" | "consumer" | "housing" | "financial";

const VIEW_MODE_STORAGE_KEY = "macrolens.dashboard.viewMode";
const CUSTOM_METRICS_STORAGE_KEY = "macrolens.dashboard.customMetrics";

const domainMetricKeys: Record<DomainKey, MetricKey[]> = {
  labor: ["unemploymentRate", "unemploymentLevel", "payrollLevel", "initialClaimsLevel", "continuingClaimsLevel", "jobOpeningsLevel", "participationLevel", "earningsYoy", "laborOverall", "payrollMomentum", "unemploymentMomentum", "initialClaimsMomentum"],
  inflation: ["headlineCpiYoy", "coreCpiYoy", "headlinePceYoy", "corePceYoy", "eciYoy", "earningsYoy", "headlineCpiMomentum", "coreCpiMomentum", "corePceMomentum"],
  growth: ["realGdpQoq", "realGdpYoy", "cfnaiLevel", "industrialYoy", "capacityLevel", "durableGoodsYoy", "realGdpMomentum", "cfnaiPosition", "industrialMomentum", "capacityDirection"],
  consumer: ["retailYoy", "consumptionYoy", "disposableIncomeYoy", "savingRate", "retailMomentum", "consumptionMomentum"],
  housing: ["housingStartsLevel", "buildingPermitsLevel", "newHomeSalesLevel", "mortgageRate", "housingStartsDirection", "permitsDirection", "homeSalesDirection", "mortgageDirection"],
  financial: ["fedFunds", "treasury2y", "treasury10y", "realYield10y", "curveSpread", "nfciLevel", "curveShape", "nfciPosition", "nfciDirection"],
};

const domainLabels: Record<DomainKey, string> = {
  labor: "Labor",
  inflation: "Inflation",
  growth: "Growth",
  consumer: "Consumer",
  housing: "Housing",
  financial: "Financial Conditions",
};

const keyMetricIds = new Set([
  "labor.unemploymentRate", "labor.unemploymentLevel", "labor.payrollLevel", "labor.initialClaimsLevel", "labor.laborOverall",
  "inflation.headlineCpiYoy", "inflation.coreCpiYoy", "inflation.corePceYoy", "inflation.headlineCpiMomentum",
  "growth.realGdpQoq", "growth.realGdpYoy", "growth.cfnaiLevel", "growth.industrialYoy", "growth.realGdpMomentum",
  "consumer.retailYoy", "consumer.consumptionYoy", "consumer.disposableIncomeYoy", "consumer.savingRate",
  "housing.housingStartsLevel", "housing.buildingPermitsLevel", "housing.newHomeSalesLevel", "housing.mortgageRate",
  "financial.fedFunds", "financial.treasury2y", "financial.treasury10y", "financial.curveSpread", "financial.nfciLevel",
]);

const allMetricIds = Object.entries(domainMetricKeys).flatMap(([domain, keys]) =>
  keys.map((key) => `${domain}.${key}`),
);

const FilterContext = createContext<{
  mode: ViewMode;
  customMetrics: Set<string>;
}>({ mode: "all", customMetrics: new Set(allMetricIds) });
const DomainContext = createContext<DomainKey>("labor");

function metricIsVisible(mode: ViewMode, customMetrics: Set<string>, domain: DomainKey, key: MetricKey) {
  const id = `${domain}.${key}`;
  if (mode === "all") return true;
  if (mode === "key") return keyMetricIds.has(id);
  return customMetrics.has(id);
}

function storedViewMode(): ViewMode {
  const value = localStorage.getItem(VIEW_MODE_STORAGE_KEY);
  return value === "key" || value === "custom" ? value : "all";
}

function storedCustomMetrics(): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(CUSTOM_METRICS_STORAGE_KEY) ?? "null");
    return Array.isArray(value) ? value.filter((item) => typeof item === "string") : allMetricIds;
  } catch {
    return allMetricIds;
  }
}

function Badge({ value }: { value: string }) {
  return <span className="badge">{value}</span>;
}

export function classificationTone(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/[_-]+/g, " ");
  const tones: Record<string, string> = {
    improving: "positive",
    weakening: "negative",
    accelerating: "accelerating",
    decelerating: "decelerating",
    rising: "rising",
    falling: "falling",
    easing: "easing",
    tightening: "tightening",
    "above trend": "above-trend",
    "below trend": "below-trend",
    "looser than average": "looser",
    "tighter than average": "tighter",
    positive: "curve-positive",
    inverted: "inverted",
    flat: "flat",
    stable: "stable",
    mixed: "mixed",
  };
  return tones[normalized] ?? "context";
}

function ClassificationPill({ value }: { value: string }) {
  const tone = classificationTone(value);
  return (
    <span className={`classification-pill classification-pill--${tone}`}>
      {formatClassification(value)}
    </span>
  );
}

function InfoTooltip({ metricKey }: { metricKey: MetricKey }) {
  const [isOpen, setIsOpen] = useState(false);
  const tooltipId = useId();
  const metadata: MetricMetadata = metricMetadata[metricKey];

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "Escape") {
      setIsOpen(false);
      event.currentTarget.blur();
    }
  }

  return (
    <span className={`info-tooltip${isOpen ? " info-tooltip--open" : ""}`}>
      <button
        type="button"
        className="info-tooltip__trigger"
        aria-label={`About ${metadata.label}`}
        aria-describedby={tooltipId}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
        onKeyDown={handleKeyDown}
      >
        i
      </button>
      <span id={tooltipId} role="tooltip" className="info-tooltip__content">
        <span>{metadata.description}</span>
        {metadata.methodology ? <span>{metadata.methodology}</span> : null}
      </span>
    </span>
  );
}

interface PreviousValue {
  value: string;
  observationDate: string;
  frequency?: string;
}

interface HistoryReading {
  value: string;
  observationDate?: string;
  frequency?: string;
  previous: PreviousValue | null;
}

function previousValue(
  history: DashboardHistory,
  key: DashboardHistoryKey,
  currentObservationDate: string,
  formatter: (value?: number) => string,
): PreviousValue | null {
  const observations = (history[key]?.observations ?? [])
    .filter(
      (observation) =>
        typeof observation.value === "number" &&
        observation.observation_date < currentObservationDate,
    )
    .sort((left, right) => left.observation_date.localeCompare(right.observation_date));
  const previous = observations[observations.length - 1];

  return previous
    ? {
        value: formatter(previous.value ?? undefined),
        observationDate: previous.observation_date,
        frequency: history[key]?.frequency,
      }
    : null;
}

function latestHistoryReading(
  history: DashboardHistory,
  key: DashboardHistoryKey,
  formatter: (value?: number) => string,
): HistoryReading {
  const response = history[key];
  const observations = (response?.observations ?? [])
    .filter((observation) => typeof observation.value === "number")
    .sort((left, right) => left.observation_date.localeCompare(right.observation_date));
  const current = observations[observations.length - 1];
  const previous = observations[observations.length - 2];

  return {
    value: current ? formatter(current.value ?? undefined) : "-",
    observationDate: current?.observation_date,
    frequency: response?.frequency,
    previous: previous
      ? {
          value: formatter(previous.value ?? undefined),
          observationDate: previous.observation_date,
          frequency: response?.frequency,
        }
      : null,
  };
}

function Metric({
  metricKey,
  value,
  detail,
  type = "number",
  detailType = "metadata",
  previous,
  observationDate,
  observationFrequency,
}: {
  metricKey: MetricKey;
  value: string;
  detail?: string;
  type?: "number" | "category";
  detailType?: "metadata" | "category";
  previous?: PreviousValue | null;
  observationDate?: string;
  observationFrequency?: string;
}) {
  const domain = useContext(DomainContext);
  const filter = useContext(FilterContext);
  if (!metricIsVisible(filter.mode, filter.customMetrics, domain, metricKey)) {
    return null;
  }

  const label = metricMetadata[metricKey].label;
  return (
    <div className="metric">
      <dt className="metric-label">
        <span>{label}</span>
        <InfoTooltip metricKey={metricKey} />
      </dt>
      <dd className={`metric-value metric-value--${type}`}>
        {type === "category" ? <ClassificationPill value={value} /> : value}
      </dd>
      {observationDate ? (
        <span className="metric-observation">
          Observed {formatObservationDate(observationDate, observationFrequency)}
        </span>
      ) : null}
      {previous !== undefined ? (
        <span className="metric-previous">
          Previous: {previous?.value ?? "—"}
          {previous ? (
            <span>
              {" · "}
              {formatObservationDate(previous.observationDate, previous.frequency)}
            </span>
          ) : null}
        </span>
      ) : null}
      {detail ? (
        <span className={`metric-detail metric-detail--${detailType}`}>
          {detailType === "category" ? <ClassificationPill value={detail} /> : detail}
        </span>
      ) : null}
    </div>
  );
}

function DomainCard({
  domain,
  title,
  children,
}: {
  domain: DomainKey;
  title: string;
  children: ReactNode;
}) {
  const filter = useContext(FilterContext);
  const hasVisibleMetric = domainMetricKeys[domain].some((key) =>
    metricIsVisible(filter.mode, filter.customMetrics, domain, key),
  );
  if (!hasVisibleMetric) {
    return null;
  }

  return (
    <DomainContext.Provider value={domain}>
      <section className="domain-card" aria-labelledby={`${title}-heading`}>
        <h2 id={`${title}-heading`}>{title}</h2>
        {children}
      </section>
    </DomainContext.Provider>
  );
}

function DomainSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="domain-section">
      <h3>{title}</h3>
      <dl className="metric-grid">{children}</dl>
    </section>
  );
}

function ViewControl({
  mode,
  customMetrics,
  onModeChange,
  onCustomMetricsChange,
}: {
  mode: ViewMode;
  customMetrics: Set<string>;
  onModeChange: (mode: ViewMode) => void;
  onCustomMetricsChange: (metrics: Set<string>) => void;
}) {
  function toggleMetric(id: string) {
    const next = new Set(customMetrics);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onCustomMetricsChange(next);
  }

  return (
    <section className="view-control" aria-labelledby="view-control-heading">
      <div className="view-control__bar">
        <h2 id="view-control-heading">Data view</h2>
        <div className="segmented-control" role="group" aria-label="Dashboard data view">
          {(["all", "key", "custom"] as ViewMode[]).map((value) => (
            <button
              key={value}
              type="button"
              className={mode === value ? "segmented-control__button is-active" : "segmented-control__button"}
              aria-pressed={mode === value}
              onClick={() => onModeChange(value)}
            >
              {value === "all" ? "All data" : value === "key" ? "Key data" : "Custom"}
            </button>
          ))}
        </div>
      </div>
      {mode === "custom" ? (
        <div className="custom-metrics" role="group" aria-label="Custom metric selection">
          {(Object.keys(domainMetricKeys) as DomainKey[]).map((domain) => (
            <fieldset key={domain}>
              <legend>{domainLabels[domain]}</legend>
              <div className="custom-metrics__options">
                {domainMetricKeys[domain].map((key) => {
                  const id = `${domain}.${key}`;
                  return (
                    <label key={id}>
                      <input
                        type="checkbox"
                        checked={customMetrics.has(id)}
                        onChange={() => toggleMetric(id)}
                      />
                      <span>{metricMetadata[key].label}</span>
                    </label>
                  );
                })}
              </div>
            </fieldset>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function Dashboard({
  snapshot,
  history,
  viewMode,
  customMetrics,
  onViewModeChange,
  onCustomMetricsChange,
}: {
  snapshot: UsaEconomyNow;
  history: DashboardHistory;
  viewMode: ViewMode;
  customMetrics: Set<string>;
  onViewModeChange: (mode: ViewMode) => void;
  onCustomMetricsChange: (metrics: Set<string>) => void;
}) {
  const {
    labor,
    inflation,
    growth,
    consumer,
    housing,
    financial_conditions: financialConditions,
  } = snapshot;

  const unemploymentLevel = latestHistoryReading(
    history,
    "unemploymentLevel",
    formatThousandsAsMillions,
  );
  const payrollLevel = latestHistoryReading(
    history,
    "payrollLevel",
    formatThousandsAsMillions,
  );
  const initialClaimsLevel = latestHistoryReading(
    history,
    "initialClaimsLevel",
    formatCompactCount,
  );
  const continuingClaimsLevel = latestHistoryReading(
    history,
    "continuingClaimsLevel",
    formatCompactCount,
  );
  const laborVotes = [
    labor.payrolls.momentum,
    labor.unemployment.momentum,
    labor.initial_claims.momentum,
  ];
  const improvingVotes = laborVotes.filter((value) => value === "improving").length;
  const weakeningVotes = laborVotes.filter((value) => value === "weakening").length;

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">MacroLens</p>
          <h1>USA Economy Now</h1>
          <p className="subtitle">Current US macroeconomic conditions</p>
        </div>
        <div className="status-panel">
          <span>As of</span>
          <strong>{formatDate(snapshot.as_of_date)}</strong>
          <p>Current-state macro dashboard. No trading signals.</p>
        </div>
      </header>

      <ViewControl
        mode={viewMode}
        customMetrics={customMetrics}
        onModeChange={onViewModeChange}
        onCustomMetricsChange={onCustomMetricsChange}
      />

      <section className="freshness" aria-labelledby="freshness-heading">
        <h2 id="freshness-heading">Component Freshness</h2>
        <div className="freshness-grid">
          {freshnessLabels.map(([key, label]) => (
            <div key={key} className="freshness-item">
              <span>{label}</span>
              <strong>{formatDate(snapshot.component_as_of_dates[key])}</strong>
            </div>
          ))}
        </div>
      </section>

      <FilterContext.Provider value={{ mode: viewMode, customMetrics }}>
      <main className="domain-grid">
        <DomainCard domain="labor" title="LABOR">
          <DomainSection title="Key readings">
            <Metric metricKey="unemploymentRate" value={formatPercent(labor.unemployment.level)} observationDate={labor.unemployment.observation_date} observationFrequency="monthly" previous={previousValue(history, "unemploymentRate", labor.unemployment.observation_date, formatPercent)} />
            <Metric metricKey="unemploymentLevel" value={unemploymentLevel.value} observationDate={unemploymentLevel.observationDate} observationFrequency={unemploymentLevel.frequency} previous={unemploymentLevel.previous} />
            <Metric metricKey="payrollLevel" value={payrollLevel.value} observationDate={payrollLevel.observationDate} observationFrequency={payrollLevel.frequency} previous={payrollLevel.previous} />
            <Metric metricKey="initialClaimsLevel" value={initialClaimsLevel.value} observationDate={initialClaimsLevel.observationDate} observationFrequency={initialClaimsLevel.frequency} previous={initialClaimsLevel.previous} />
            <Metric metricKey="continuingClaimsLevel" value={continuingClaimsLevel.value} observationDate={continuingClaimsLevel.observationDate} observationFrequency={continuingClaimsLevel.frequency} previous={continuingClaimsLevel.previous} />
            <Metric metricKey="jobOpeningsLevel" value={formatThousandsAsMillions(labor.job_openings.level)} observationDate={labor.job_openings.observation_date} observationFrequency="monthly" previous={previousValue(history, "jobOpeningsLevel", labor.job_openings.observation_date, formatThousandsAsMillions)} />
            <Metric metricKey="participationLevel" value={formatPercent(labor.labor_force_participation.level)} observationDate={labor.labor_force_participation.observation_date} observationFrequency="monthly" previous={previousValue(history, "participationLevel", labor.labor_force_participation.observation_date, formatPercent)} />
            <Metric metricKey="earningsYoy" value={formatPercent(labor.average_hourly_earnings.yoy)} observationDate={labor.average_hourly_earnings.observation_date} observationFrequency="monthly" previous={previousValue(history, "earningsYoy", labor.average_hourly_earnings.observation_date, formatPercent)} />
          </DomainSection>
          <DomainSection title="Interpretation / momentum">
            <Metric metricKey="laborOverall" value={labor.overall_momentum} type="category" detail={`${improvingVotes} improving · ${weakeningVotes} weakening`} />
            <Metric metricKey="payrollMomentum" value={labor.payrolls.momentum} type="category" detail={`3M avg change: ${formatNumber(labor.payrolls.monthly_change_ma_3m, 0)}K · 6M: ${formatNumber(labor.payrolls.monthly_change_ma_6m, 0)}K`} />
            <Metric metricKey="unemploymentMomentum" value={labor.unemployment.momentum} type="category" detail={`Current: ${formatPercent(labor.unemployment.level)} · 3M change: ${formatPercentagePoint(labor.unemployment.change_3m)}`} />
            <Metric metricKey="initialClaimsMomentum" value={labor.initial_claims.momentum} type="category" detail={`4W avg: ${formatCompactCount(labor.initial_claims.moving_average_4w)} · 13W: ${formatCompactCount(labor.initial_claims.moving_average_13w)}`} />
          </DomainSection>
        </DomainCard>

        <DomainCard domain="inflation" title="INFLATION">
          <DomainSection title="Key readings">
            <Metric metricKey="headlineCpiYoy" value={formatPercent(inflation.headline_cpi.yoy)} observationDate={inflation.headline_cpi.observation_date} observationFrequency="monthly" previous={previousValue(history, "headlineCpiYoy", inflation.headline_cpi.observation_date, formatPercent)} />
            <Metric metricKey="coreCpiYoy" value={formatPercent(inflation.core_cpi.yoy)} observationDate={inflation.core_cpi.observation_date} observationFrequency="monthly" previous={previousValue(history, "coreCpiYoy", inflation.core_cpi.observation_date, formatPercent)} />
            <Metric metricKey="headlinePceYoy" value={formatPercent(inflation.headline_pce.yoy)} observationDate={inflation.headline_pce.observation_date} observationFrequency="monthly" previous={previousValue(history, "headlinePceYoy", inflation.headline_pce.observation_date, formatPercent)} />
            <Metric metricKey="corePceYoy" value={formatPercent(inflation.core_pce.yoy)} observationDate={inflation.core_pce.observation_date} observationFrequency="monthly" previous={previousValue(history, "corePceYoy", inflation.core_pce.observation_date, formatPercent)} />
            <Metric metricKey="eciYoy" value={formatPercent(inflation.employment_cost_index.yoy)} observationDate={inflation.employment_cost_index.observation_date} observationFrequency="quarterly" previous={previousValue(history, "eciYoy", inflation.employment_cost_index.observation_date, formatPercent)} />
            <Metric metricKey="earningsYoy" value={formatPercent(inflation.average_hourly_earnings.yoy)} observationDate={inflation.average_hourly_earnings.observation_date} observationFrequency="monthly" previous={previousValue(history, "earningsYoy", inflation.average_hourly_earnings.observation_date, formatPercent)} />
          </DomainSection>
          <DomainSection title="Interpretation / momentum">
            <Metric metricKey="headlineCpiMomentum" value={inflation.headline_cpi.momentum} type="category" detail={`3M ann.: ${formatPercent(inflation.headline_cpi.annualized_3m)} · YoY: ${formatPercent(inflation.headline_cpi.yoy)}`} />
            <Metric metricKey="coreCpiMomentum" value={inflation.core_cpi.momentum} type="category" detail={`3M ann.: ${formatPercent(inflation.core_cpi.annualized_3m)} · YoY: ${formatPercent(inflation.core_cpi.yoy)}`} />
            <Metric metricKey="corePceMomentum" value={inflation.core_pce.momentum} type="category" detail={`3M ann.: ${formatPercent(inflation.core_pce.annualized_3m)} · YoY: ${formatPercent(inflation.core_pce.yoy)}`} />
          </DomainSection>
        </DomainCard>

        <DomainCard domain="growth" title="GROWTH">
          <DomainSection title="Key readings">
            <Metric metricKey="realGdpQoq" value={formatPercent(growth.real_gdp.qoq_annualized)} observationDate={growth.real_gdp.observation_date} observationFrequency="quarterly" previous={previousValue(history, "realGdpQoq", growth.real_gdp.observation_date, formatPercent)} />
            <Metric metricKey="realGdpYoy" value={formatPercent(growth.real_gdp.yoy)} observationDate={growth.real_gdp.observation_date} observationFrequency="quarterly" previous={previousValue(history, "realGdpYoy", growth.real_gdp.observation_date, formatPercent)} />
            <Metric metricKey="cfnaiLevel" value={`${formatNumber(growth.cfnai.level)} / ${formatNumber(growth.cfnai.moving_average_3m)}`} observationDate={growth.cfnai.observation_date} observationFrequency="monthly" previous={previousValue(history, "cfnaiLevel", growth.cfnai.observation_date, formatNumber)} />
            <Metric metricKey="industrialYoy" value={formatPercent(growth.industrial_production.yoy)} observationDate={growth.industrial_production.observation_date} observationFrequency="monthly" previous={previousValue(history, "industrialYoy", growth.industrial_production.observation_date, formatPercent)} />
            <Metric metricKey="capacityLevel" value={formatPercent(growth.capacity_utilization.level)} observationDate={growth.capacity_utilization.observation_date} observationFrequency="monthly" previous={previousValue(history, "capacityLevel", growth.capacity_utilization.observation_date, formatPercent)} />
            <Metric metricKey="durableGoodsYoy" value={formatPercent(growth.durable_goods_orders.yoy)} observationDate={growth.durable_goods_orders.observation_date} observationFrequency="monthly" previous={previousValue(history, "durableGoodsYoy", growth.durable_goods_orders.observation_date, formatPercent)} />
          </DomainSection>
          <DomainSection title="Interpretation / momentum">
            <Metric metricKey="realGdpMomentum" value={growth.real_gdp.momentum} type="category" detail={`QoQ ann.: ${formatPercent(growth.real_gdp.qoq_annualized)} · YoY: ${formatPercent(growth.real_gdp.yoy)}`} />
            <Metric metricKey="cfnaiPosition" value={growth.cfnai.position} type="category" detail={`3M avg: ${formatNumber(growth.cfnai.moving_average_3m)} · reference: 0`} />
            <Metric metricKey="industrialMomentum" value={growth.industrial_production.momentum} type="category" detail={`3M ann.: ${formatPercent(growth.industrial_production.annualized_3m)} · YoY: ${formatPercent(growth.industrial_production.yoy)}`} />
            <Metric metricKey="capacityDirection" value={growth.capacity_utilization.direction} type="category" detail={`3M change: ${formatPercentagePoint(growth.capacity_utilization.change_3m)}`} />
          </DomainSection>
        </DomainCard>

        <DomainCard domain="consumer" title="CONSUMER">
          <DomainSection title="Key readings">
            <Metric metricKey="retailYoy" value={formatPercent(consumer.retail_sales.yoy)} detail="Nominal series" observationDate={consumer.retail_sales.observation_date} observationFrequency="monthly" previous={previousValue(history, "retailYoy", consumer.retail_sales.observation_date, formatPercent)} />
            <Metric metricKey="consumptionYoy" value={formatPercent(consumer.real_consumption.yoy)} observationDate={consumer.real_consumption.observation_date} observationFrequency="monthly" previous={previousValue(history, "consumptionYoy", consumer.real_consumption.observation_date, formatPercent)} />
            <Metric metricKey="disposableIncomeYoy" value={formatPercent(consumer.real_disposable_income.yoy)} observationDate={consumer.real_disposable_income.observation_date} observationFrequency="monthly" previous={previousValue(history, "disposableIncomeYoy", consumer.real_disposable_income.observation_date, formatPercent)} />
            <Metric metricKey="savingRate" value={formatPercent(consumer.saving_rate.level)} observationDate={consumer.saving_rate.observation_date} observationFrequency="monthly" previous={previousValue(history, "savingRate", consumer.saving_rate.observation_date, formatPercent)} />
          </DomainSection>
          <DomainSection title="Interpretation / momentum">
            <Metric metricKey="retailMomentum" value={consumer.retail_sales.momentum} type="category" detail={`3M ann.: ${formatPercent(consumer.retail_sales.annualized_3m)} · YoY: ${formatPercent(consumer.retail_sales.yoy)}`} />
            <Metric metricKey="consumptionMomentum" value={consumer.real_consumption.momentum} type="category" detail={`3M ann.: ${formatPercent(consumer.real_consumption.annualized_3m)} · YoY: ${formatPercent(consumer.real_consumption.yoy)}`} />
            <Metric metricKey="savingRate" value={consumer.saving_rate.direction} type="category" detail={`3M change: ${formatPercentagePoint(consumer.saving_rate.change_3m)}`} />
          </DomainSection>
        </DomainCard>

        <DomainCard domain="housing" title="HOUSING">
          <DomainSection title="Key readings">
            <Metric metricKey="housingStartsLevel" value={formatSaarThousands(housing.housing_starts.level)} observationDate={housing.housing_starts.observation_date} observationFrequency="monthly" previous={previousValue(history, "housingStartsLevel", housing.housing_starts.observation_date, formatSaarThousands)} />
            <Metric metricKey="buildingPermitsLevel" value={formatSaarThousands(housing.building_permits.level)} observationDate={housing.building_permits.observation_date} observationFrequency="monthly" previous={previousValue(history, "buildingPermitsLevel", housing.building_permits.observation_date, formatSaarThousands)} />
            <Metric metricKey="newHomeSalesLevel" value={formatSaarThousands(housing.new_home_sales.level)} observationDate={housing.new_home_sales.observation_date} observationFrequency="monthly" previous={previousValue(history, "newHomeSalesLevel", housing.new_home_sales.observation_date, formatSaarThousands)} />
            <Metric metricKey="mortgageRate" value={formatPercent(housing.mortgage_rate.level)} observationDate={housing.mortgage_rate.observation_date} observationFrequency="weekly" previous={previousValue(history, "mortgageRate", housing.mortgage_rate.observation_date, formatPercent)} />
          </DomainSection>
          <DomainSection title="Interpretation / momentum">
            <Metric metricKey="housingStartsDirection" value={housing.housing_starts.direction} type="category" detail={`MoM: ${formatPercent(housing.housing_starts.mom)} · YoY: ${formatPercent(housing.housing_starts.yoy)}`} />
            <Metric metricKey="permitsDirection" value={housing.building_permits.direction} type="category" detail={`MoM: ${formatPercent(housing.building_permits.mom)} · YoY: ${formatPercent(housing.building_permits.yoy)}`} />
            <Metric metricKey="homeSalesDirection" value={housing.new_home_sales.direction} type="category" detail={`MoM: ${formatPercent(housing.new_home_sales.mom)} · YoY: ${formatPercent(housing.new_home_sales.yoy)}`} />
            <Metric metricKey="mortgageDirection" value={housing.mortgage_rate.direction} type="category" detail={`4W change: ${formatPercentagePoint(housing.mortgage_rate.change_4w)}`} />
          </DomainSection>
        </DomainCard>

        <DomainCard domain="financial" title="FINANCIAL CONDITIONS">
          <DomainSection title="Key readings">
            <Metric metricKey="fedFunds" value={formatPercent(financialConditions.fed_funds_rate.level)} observationDate={financialConditions.fed_funds_rate.observation_date} observationFrequency="daily" previous={previousValue(history, "fedFunds", financialConditions.fed_funds_rate.observation_date, formatPercent)} />
            <Metric metricKey="treasury2y" value={formatPercent(financialConditions.treasury_2y.level)} observationDate={financialConditions.treasury_2y.observation_date} observationFrequency="daily" previous={previousValue(history, "treasury2y", financialConditions.treasury_2y.observation_date, formatPercent)} />
            <Metric metricKey="treasury10y" value={formatPercent(financialConditions.treasury_10y.level)} observationDate={financialConditions.treasury_10y.observation_date} observationFrequency="daily" previous={previousValue(history, "treasury10y", financialConditions.treasury_10y.observation_date, formatPercent)} />
            <Metric metricKey="realYield10y" value={formatPercent(financialConditions.real_yield_10y.level)} observationDate={financialConditions.real_yield_10y.observation_date} observationFrequency="daily" previous={previousValue(history, "realYield10y", financialConditions.real_yield_10y.observation_date, formatPercent)} />
            <Metric metricKey="curveSpread" value={formatPercentagePoint(financialConditions.yield_curve_2s10s.spread)} observationDate={financialConditions.yield_curve_2s10s.observation_date} observationFrequency="daily" previous={null} />
            <Metric metricKey="nfciLevel" value={formatNumber(financialConditions.nfci.level)} detail="Reference: 0" observationDate={financialConditions.nfci.observation_date} observationFrequency="weekly" previous={previousValue(history, "nfciLevel", financialConditions.nfci.observation_date, formatNumber)} />
          </DomainSection>
          <DomainSection title="Interpretation / momentum">
            <Metric metricKey="curveShape" value={financialConditions.yield_curve_2s10s.shape} type="category" detail={`Spread: ${formatPercentagePoint(financialConditions.yield_curve_2s10s.spread)}`} />
            <Metric metricKey="nfciPosition" value={financialConditions.nfci.position} type="category" detail={`Level: ${formatNumber(financialConditions.nfci.level)} · reference: 0`} />
            <Metric metricKey="nfciDirection" value={financialConditions.nfci.direction} type="category" detail={`4W change: ${formatNumber(financialConditions.nfci.change_4w)}`} />
          </DomainSection>
        </DomainCard>
      </main>
      </FilterContext.Provider>

      <div className="methodology-note">
        <Badge value="Deterministic classifications only" />
        <span>No forecasts or investment recommendations are generated.</span>
      </div>
    </>
  );
}

export default function App() {
  const [snapshot, setSnapshot] = useState<UsaEconomyNow | null>(null);
  const [history, setHistory] = useState<DashboardHistory>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>(storedViewMode);
  const [customMetrics, setCustomMetrics] = useState<Set<string>>(
    () => new Set(storedCustomMetrics()),
  );

  useEffect(() => {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode);
  }, [viewMode]);

  useEffect(() => {
    localStorage.setItem(CUSTOM_METRICS_STORAGE_KEY, JSON.stringify([...customMetrics]));
  }, [customMetrics]);

  useEffect(() => {
    let isActive = true;

    setIsLoading(true);
    setError(null);

    Promise.all([fetchUsaEconomyNow(), fetchDashboardHistory()])
      .then(([data, historyData]) => {
        if (isActive) {
          setSnapshot(data);
          setHistory(historyData);
        }
      })
      .catch(() => {
        if (isActive) {
          setError("MacroLens API is unavailable. Start the FastAPI server and try again.");
        }
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [requestId]);

  if (isLoading) {
    return (
      <div className="app-shell">
        <div className="loading-panel">Loading USA Economy Now...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-shell">
        <div className="error-panel" role="alert">
          <h1>MacroLens</h1>
          <p>{error}</p>
          <button type="button" onClick={() => setRequestId((current) => current + 1)}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {snapshot ? (
        <Dashboard
          snapshot={snapshot}
          history={history}
          viewMode={viewMode}
          customMetrics={customMetrics}
          onViewModeChange={setViewMode}
          onCustomMetricsChange={setCustomMetrics}
        />
      ) : null}
    </div>
  );
}
