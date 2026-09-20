import { useEffect, useId, useState } from "react";
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
  formatDate,
  formatNumber,
  formatObservationDate,
  formatPercentagePoint,
  formatPercent,
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

function Badge({ value }: { value: string }) {
  return <span className="badge">{value}</span>;
}

export function classificationTone(value: string): "positive" | "negative" | "neutral" | "context" {
  const normalized = value.trim().toLowerCase();
  if (normalized === "improving") return "positive";
  if (normalized === "weakening") return "negative";
  if (normalized === "mixed" || normalized === "stable") return "neutral";
  return "context";
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

function Metric({
  metricKey,
  value,
  detail,
  type = "number",
  detailType = "metadata",
  previous,
}: {
  metricKey: MetricKey;
  value: string;
  detail?: string;
  type?: "number" | "category";
  detailType?: "metadata" | "category";
  previous?: PreviousValue | null;
}) {
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
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="domain-card" aria-labelledby={`${title}-heading`}>
      <h2 id={`${title}-heading`}>{title}</h2>
      <dl className="metric-grid">{children}</dl>
    </section>
  );
}

function Dashboard({
  snapshot,
  history,
}: {
  snapshot: UsaEconomyNow;
  history: DashboardHistory;
}) {
  const {
    labor,
    inflation,
    growth,
    consumer,
    housing,
    financial_conditions: financialConditions,
  } = snapshot;

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

      <main className="domain-grid">
        <DomainCard title="LABOR">
          <Metric metricKey="laborOverall" value={labor.overall_momentum} type="category" />
          <Metric
            metricKey="payrollMomentum"
            value={labor.payrolls.momentum}
            type="category"
            detail={`obs ${formatDate(labor.payrolls.observation_date)}`}
          />
          <Metric
            metricKey="unemploymentMomentum"
            value={labor.unemployment.momentum}
            type="category"
            detail={`obs ${formatDate(labor.unemployment.observation_date)}`}
          />
          <Metric
            metricKey="initialClaimsMomentum"
            value={labor.initial_claims.momentum}
            type="category"
            detail={`obs ${formatDate(labor.initial_claims.observation_date)}`}
          />
        </DomainCard>

        <DomainCard title="INFLATION">
          <Metric metricKey="headlineCpiYoy" value={formatPercent(inflation.headline_cpi.yoy)} previous={previousValue(history, "headlineCpiYoy", inflation.headline_cpi.observation_date, formatPercent)} />
          <Metric metricKey="headlineCpiMomentum" value={inflation.headline_cpi.momentum} type="category" />
          <Metric metricKey="coreCpiYoy" value={formatPercent(inflation.core_cpi.yoy)} previous={previousValue(history, "coreCpiYoy", inflation.core_cpi.observation_date, formatPercent)} />
          <Metric metricKey="coreCpiMomentum" value={inflation.core_cpi.momentum} type="category" />
          <Metric metricKey="corePceYoy" value={formatPercent(inflation.core_pce.yoy)} previous={previousValue(history, "corePceYoy", inflation.core_pce.observation_date, formatPercent)} />
          <Metric metricKey="corePceMomentum" value={inflation.core_pce.momentum} type="category" />
        </DomainCard>

        <DomainCard title="GROWTH">
          <Metric metricKey="realGdpQoq" value={formatPercent(growth.real_gdp.qoq_annualized)} previous={previousValue(history, "realGdpQoq", growth.real_gdp.observation_date, formatPercent)} />
          <Metric metricKey="realGdpMomentum" value={growth.real_gdp.momentum} type="category" />
          <Metric metricKey="cfnaiPosition" value={growth.cfnai.position} type="category" />
          <Metric
            metricKey="industrialMomentum"
            value={growth.industrial_production.momentum}
            type="category"
          />
          <Metric
            metricKey="capacityDirection"
            value={growth.capacity_utilization.direction}
            type="category"
          />
        </DomainCard>

        <DomainCard title="CONSUMER">
          <Metric metricKey="retailMomentum" value={consumer.retail_sales.momentum} type="category" />
          <Metric metricKey="retailYoy" value={formatPercent(consumer.retail_sales.yoy)} previous={previousValue(history, "retailYoy", consumer.retail_sales.observation_date, formatPercent)} />
          <Metric metricKey="consumptionMomentum" value={consumer.real_consumption.momentum} type="category" />
          <Metric metricKey="consumptionYoy" value={formatPercent(consumer.real_consumption.yoy)} previous={previousValue(history, "consumptionYoy", consumer.real_consumption.observation_date, formatPercent)} />
          <Metric
            metricKey="savingRate"
            value={formatPercent(consumer.saving_rate.level)}
            detail={consumer.saving_rate.direction}
            detailType="category"
            previous={previousValue(history, "savingRate", consumer.saving_rate.observation_date, formatPercent)}
          />
        </DomainCard>

        <DomainCard title="HOUSING">
          <Metric metricKey="housingStartsDirection" value={housing.housing_starts.direction} type="category" />
          <Metric metricKey="housingStartsYoy" value={formatPercent(housing.housing_starts.yoy)} previous={previousValue(history, "housingStartsYoy", housing.housing_starts.observation_date, formatPercent)} />
          <Metric metricKey="permitsDirection" value={housing.building_permits.direction} type="category" />
          <Metric metricKey="homeSalesDirection" value={housing.new_home_sales.direction} type="category" />
          <Metric metricKey="mortgageRate" value={formatPercent(housing.mortgage_rate.level)} previous={previousValue(history, "mortgageRate", housing.mortgage_rate.observation_date, formatPercent)} />
          <Metric metricKey="mortgageDirection" value={housing.mortgage_rate.direction} type="category" />
        </DomainCard>

        <DomainCard title="FINANCIAL CONDITIONS">
          <Metric metricKey="fedFunds" value={formatPercent(financialConditions.fed_funds_rate.level)} previous={previousValue(history, "fedFunds", financialConditions.fed_funds_rate.observation_date, formatPercent)} />
          <Metric metricKey="treasury2y" value={formatPercent(financialConditions.treasury_2y.level)} previous={previousValue(history, "treasury2y", financialConditions.treasury_2y.observation_date, formatPercent)} />
          <Metric metricKey="treasury10y" value={formatPercent(financialConditions.treasury_10y.level)} previous={previousValue(history, "treasury10y", financialConditions.treasury_10y.observation_date, formatPercent)} />
          <Metric metricKey="realYield10y" value={formatPercent(financialConditions.real_yield_10y.level)} previous={previousValue(history, "realYield10y", financialConditions.real_yield_10y.observation_date, formatPercent)} />
          <Metric metricKey="curveSpread" value={formatPercentagePoint(financialConditions.yield_curve_2s10s.spread)} previous={null} />
          <Metric metricKey="curveShape" value={financialConditions.yield_curve_2s10s.shape} type="category" />
          <Metric metricKey="nfciLevel" value={formatNumber(financialConditions.nfci.level)} previous={previousValue(history, "nfciLevel", financialConditions.nfci.observation_date, formatNumber)} />
          <Metric metricKey="nfciPosition" value={financialConditions.nfci.position} type="category" />
          <Metric metricKey="nfciDirection" value={financialConditions.nfci.direction} type="category" />
        </DomainCard>
      </main>

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
      {snapshot ? <Dashboard snapshot={snapshot} history={history} /> : null}
    </div>
  );
}
