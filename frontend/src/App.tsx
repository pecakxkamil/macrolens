import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { fetchUsaEconomyNow, type UsaEconomyNow } from "./api/macrolens";
import {
  formatClassification,
  formatDate,
  formatNumber,
  formatPercentagePoint,
  formatPercent,
} from "./format";

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

function ClassificationPill({ value }: { value: string }) {
  return <span className="classification-pill">{formatClassification(value)}</span>;
}

function Metric({
  label,
  value,
  detail,
  type = "number",
  detailType = "metadata",
}: {
  label: string;
  value: string;
  detail?: string;
  type?: "number" | "category";
  detailType?: "metadata" | "category";
}) {
  return (
    <div className="metric">
      <dt>{label}</dt>
      <dd className={`metric-value metric-value--${type}`}>
        {type === "category" ? <ClassificationPill value={value} /> : value}
      </dd>
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

function Dashboard({ snapshot }: { snapshot: UsaEconomyNow }) {
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
          <Metric label="Overall momentum" value={labor.overall_momentum} type="category" />
          <Metric
            label="Payrolls momentum"
            value={labor.payrolls.momentum}
            type="category"
            detail={`obs ${formatDate(labor.payrolls.observation_date)}`}
          />
          <Metric
            label="Unemployment momentum"
            value={labor.unemployment.momentum}
            type="category"
            detail={`obs ${formatDate(labor.unemployment.observation_date)}`}
          />
          <Metric
            label="Initial claims momentum"
            value={labor.initial_claims.momentum}
            type="category"
            detail={`obs ${formatDate(labor.initial_claims.observation_date)}`}
          />
        </DomainCard>

        <DomainCard title="INFLATION">
          <Metric label="Headline CPI YoY" value={formatPercent(inflation.headline_cpi.yoy)} />
          <Metric label="Headline CPI momentum" value={inflation.headline_cpi.momentum} type="category" />
          <Metric label="Core CPI YoY" value={formatPercent(inflation.core_cpi.yoy)} />
          <Metric label="Core CPI momentum" value={inflation.core_cpi.momentum} type="category" />
          <Metric label="Core PCE YoY" value={formatPercent(inflation.core_pce.yoy)} />
          <Metric label="Core PCE momentum" value={inflation.core_pce.momentum} type="category" />
        </DomainCard>

        <DomainCard title="GROWTH">
          <Metric label="Real GDP QoQ annualized" value={formatPercent(growth.real_gdp.qoq_annualized)} />
          <Metric label="Real GDP momentum" value={growth.real_gdp.momentum} type="category" />
          <Metric label="CFNAI position" value={growth.cfnai.position} type="category" />
          <Metric
            label="Industrial Production momentum"
            value={growth.industrial_production.momentum}
            type="category"
          />
          <Metric
            label="Capacity Utilization direction"
            value={growth.capacity_utilization.direction}
            type="category"
          />
        </DomainCard>

        <DomainCard title="CONSUMER">
          <Metric label="Retail Sales momentum" value={consumer.retail_sales.momentum} type="category" />
          <Metric label="Retail Sales YoY" value={formatPercent(consumer.retail_sales.yoy)} />
          <Metric label="Real Consumption momentum" value={consumer.real_consumption.momentum} type="category" />
          <Metric label="Real Consumption YoY" value={formatPercent(consumer.real_consumption.yoy)} />
          <Metric
            label="Saving Rate"
            value={formatPercent(consumer.saving_rate.level)}
            detail={consumer.saving_rate.direction}
            detailType="category"
          />
        </DomainCard>

        <DomainCard title="HOUSING">
          <Metric label="Housing Starts direction" value={housing.housing_starts.direction} type="category" />
          <Metric label="Housing Starts YoY" value={formatPercent(housing.housing_starts.yoy)} />
          <Metric label="Building Permits direction" value={housing.building_permits.direction} type="category" />
          <Metric label="New Home Sales direction" value={housing.new_home_sales.direction} type="category" />
          <Metric label="30Y Mortgage Rate" value={formatPercent(housing.mortgage_rate.level)} />
          <Metric label="Mortgage Rate direction" value={housing.mortgage_rate.direction} type="category" />
        </DomainCard>

        <DomainCard title="FINANCIAL CONDITIONS">
          <Metric label="Effective Fed Funds Rate" value={formatPercent(financialConditions.fed_funds_rate.level)} />
          <Metric label="2Y Treasury" value={formatPercent(financialConditions.treasury_2y.level)} />
          <Metric label="10Y Treasury" value={formatPercent(financialConditions.treasury_10y.level)} />
          <Metric label="10Y Real Yield" value={formatPercent(financialConditions.real_yield_10y.level)} />
          <Metric label="2s10s spread" value={formatPercentagePoint(financialConditions.yield_curve_2s10s.spread)} />
          <Metric label="2s10s shape" value={financialConditions.yield_curve_2s10s.shape} type="category" />
          <Metric label="NFCI level" value={formatNumber(financialConditions.nfci.level)} />
          <Metric label="NFCI position" value={financialConditions.nfci.position} type="category" />
          <Metric label="NFCI direction" value={financialConditions.nfci.direction} type="category" />
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
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState(0);

  useEffect(() => {
    let isActive = true;

    setIsLoading(true);
    setError(null);

    fetchUsaEconomyNow()
      .then((data) => {
        if (isActive) {
          setSnapshot(data);
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

  return <div className="app-shell">{snapshot ? <Dashboard snapshot={snapshot} /> : null}</div>;
}
