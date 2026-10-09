import { useEffect, useState } from "react";
import { fetchMacroState, type MacroStateReading, type MacroStateResponse } from "../api/macrolens";
import { formatClassification, formatDate, formatNumber } from "../format";
import { type MetricKey } from "../metricMetadata";

import { InfoTooltip } from "../components/InfoTooltip";

const order: Array<keyof MacroStateResponse["domains"]> = [
  "labor", "inflation", "growth", "consumer", "housing", "financial_conditions",
];
const detailRoutes: Record<typeof order[number], string> = {
  labor: "#/indicators/PAYEMS", inflation: "#/indicators/CPIAUCSL", growth: "#/indicators/GDPC1",
  consumer: "#/indicators/RSAFS", housing: "#/indicators/HOUST", financial_conditions: "#/indicators/NFCI",
};
const selectedKeys: Record<typeof order[number], string[]> = {
  labor: ["payrolls", "unemployment", "initial_claims", "job_openings", "average_hourly_earnings"],
  inflation: ["headline_cpi", "core_cpi", "headline_pce", "core_pce"],
  growth: ["real_gdp", "cfnai", "industrial_production", "capacity_utilization"],
  consumer: ["retail_sales", "real_consumption", "real_disposable_income", "saving_rate"],
  housing: ["housing_starts", "building_permits", "new_home_sales", "mortgage_rate"],
  financial_conditions: ["fed_funds_rate", "treasury_2y", "treasury_10y", "real_yield_10y", "yield_curve_2s10s", "nfci"],
};
const metadataKeys: Record<string, MetricKey> = {
  "labor.unemployment": "unemploymentRate", "labor.initial_claims": "initialClaimsLevel",
  "labor.job_openings": "jobOpeningsLevel", "labor.average_hourly_earnings": "earningsYoy",
  "inflation.headline_cpi": "headlineCpiYoy", "inflation.core_cpi": "coreCpiYoy",
  "inflation.headline_pce": "headlinePceYoy", "inflation.core_pce": "corePceYoy",
  "growth.real_gdp": "realGdpQoq", "growth.cfnai": "cfnaiLevel",
  "growth.industrial_production": "industrialYoy", "growth.capacity_utilization": "capacityLevel",
  "consumer.retail_sales": "retailYoy", "consumer.real_consumption": "consumptionYoy",
  "consumer.saving_rate": "savingRate", "housing.housing_starts": "housingStartsLevel",
  "housing.building_permits": "buildingPermitsLevel", "housing.new_home_sales": "newHomeSalesLevel",
  "housing.mortgage_rate": "mortgageRate", "financial_conditions.yield_curve_2s10s": "curveSpread",
  "financial_conditions.nfci": "nfciLevel",
};
const classificationMetadataKeys: Record<string, MetricKey> = {
  "labor.payrolls": "payrollMomentum", "labor.unemployment": "unemploymentMomentum",
  "labor.initial_claims": "initialClaimsMomentum", "inflation.headline_cpi": "headlineCpiMomentum",
  "inflation.core_cpi": "coreCpiMomentum", "inflation.core_pce": "corePceMomentum",
  "growth.real_gdp": "realGdpMomentum", "growth.cfnai": "cfnaiPosition",
  "growth.industrial_production": "industrialMomentum", "growth.capacity_utilization": "capacityDirection",
  "consumer.retail_sales": "retailMomentum", "consumer.real_consumption": "consumptionMomentum",
  "housing.housing_starts": "housingStartsDirection", "housing.building_permits": "permitsDirection",
  "housing.new_home_sales": "homeSalesDirection", "housing.mortgage_rate": "mortgageDirection",
  "financial_conditions.yield_curve_2s10s": "curveShape", "financial_conditions.nfci": "nfciPosition",
};
type LoadState = { status: "loading" } | { status: "error" } | { status: "ready"; data: MacroStateResponse };

function Classification({ value }: { value: string }) {
  const tone = value === "improving" ? "positive" : value === "weakening" ? "negative" : "context";
  return <span className={`classification-pill classification-pill--${tone}`}>{formatClassification(value)}</span>;
}

function Reading({ reading, domain }: { reading: MacroStateReading; domain: string }) {
  const key = `${domain}.${reading.key}`;
  const metadataKey = classificationMetadataKeys[key] ?? metadataKeys[key];
  const value = `${formatNumber(reading.value)}${reading.unit === "percent" ? "%" : ` ${reading.unit}`}`;
  return <div className="macro-state-reading">
    <span>{reading.label} {metadataKey ? <InfoTooltip metricKey={metadataKey} /> : null}</span>
    <strong>{value}</strong>
    {reading.classification ? <Classification value={reading.classification} /> : null}
  </div>;
}

export function MacroStatePage() {
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    fetchMacroState(controller.signal)
      .then((data) => { if (!controller.signal.aborted) setState({ status: "ready", data }); })
      .catch(() => { if (!controller.signal.aborted) setState({ status: "error" }); });
    return () => controller.abort();
  }, [retry]);

  return <main className="macro-state-page">
    <header className="macro-state-header">
      <p className="eyebrow">MacroLens</p>
      <h1>Macro State</h1>
      <p className="subtitle">Current US macroeconomic evidence across labor, inflation, growth, consumer, housing and financial conditions.</p>
    </header>
    {state.status === "loading" ? <div className="loading-panel">Loading Macro State...</div> : null}
    {state.status === "error" ? <div className="error-panel" role="alert">
      <p>Macro State is unavailable. Check the API and try again.</p>
      <button type="button" onClick={() => { setState({ status: "loading" }); setRetry((value) => value + 1); }}>Retry</button>
    </div> : null}
    {state.status === "ready" ? <>
      <section className="macro-state-freshness" aria-label="Component freshness">
        <strong>As of: {formatDate(state.data.as_of_date)}</strong>
        <div>{order.map((key) => <span key={key}>{state.data.domains[key].name}: {formatDate(state.data.component_as_of_dates[key])}</span>)}</div>
      </section>
      <section aria-label="Domain overview">
        <h2>Domain overview</h2>
        <div className="macro-state-grid">{order.map((key) => {
          const domain = state.data.domains[key];
          return <article className="macro-state-card" key={key} aria-label={`${domain.name} state`}>
            <div className="macro-state-card__header"><h3>{domain.name}</h3><span>As of {formatDate(domain.as_of_date)}</span></div>
            {key === "labor" ? <div className="macro-state-overall">Overall labor momentum <Classification value={domain.classifications.overall_momentum} /> <InfoTooltip metricKey="laborOverall" /></div> : null}
            <div className="macro-state-readings">{domain.readings.filter((reading) => selectedKeys[key].includes(reading.key)).map((reading) => <Reading key={reading.key} domain={key} reading={reading} />)}</div>
            <ul className="macro-state-evidence">{domain.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
            <a href={detailRoutes[key]}>View {domain.name} indicators</a>
          </article>;
        })}</div>
      </section>
      <section className="macro-state-cross-currents" aria-label="Cross-currents">
        <h2>Cross-currents</h2>
        <p>Cross-currents highlight indicators within the current macro picture that are moving in different directions. They are descriptive and are not forecasts.</p>
        {state.data.cross_currents.length ? <div className="macro-state-cross-grid">{state.data.cross_currents.map((item) => <article key={item.domain} className="macro-state-cross-card">
          <h3>{state.data.domains[item.domain].name}</h3>
          <div>{item.evidence.map((evidence) => <div key={evidence.label}><span>{evidence.label}</span><Classification value={evidence.classification} /></div>)}</div>
          <p>{item.summary}</p>
        </article>)}</div> : <p>No curated cross-currents match the current classifications.</p>}
      </section>
    </> : null}
  </main>;
}
