import { useEffect, useState } from "react";
import { fetchRelationshipComparison, type RelationshipKey, type RelationshipResponse } from "../api/macrolens";
import { rangeStartDate } from "../charts/chartData";
import { RelationshipChart, type ComparisonMode } from "./RelationshipChart";
import { relationshipChoice, relationshipChoices, relationshipPresets } from "./relationshipDefinitions";

const ranges = ["1Y", "3Y", "5Y", "10Y", "Max"] as const;
type Range = typeof ranges[number];
type LoadState = { status: "loading" } | { status: "error" } | { status: "ready"; data: RelationshipResponse };

function IndicatorSelect({ label, value, onChange, unavailable, optional = false }: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  unavailable: string[];
  optional?: boolean;
}) {
  const domains = [...new Set(relationshipChoices.map((choice) => choice.domain))];
  return <label className="relationship-select">
    <span>{label}</span>
    <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
      {optional ? <option value="">No third indicator</option> : null}
      {domains.map((domain) => <optgroup key={domain} label={domain}>
        {relationshipChoices.filter((choice) => choice.domain === domain).map((choice) => <option
          key={choice.id} value={choice.id} disabled={unavailable.includes(choice.id)}
        >{choice.label}</option>)}
      </optgroup>)}
    </select>
  </label>;
}

export function RelationshipsPage() {
  const [leftId, setLeftId] = useState("CPIAUCSL:yoy");
  const [rightId, setRightId] = useState("DFF:raw");
  const [thirdId, setThirdId] = useState("");
  const [range, setRange] = useState<Range>("3Y");
  const [mode, setMode] = useState<ComparisonMode>("indexed");
  const [retry, setRetry] = useState(0);
  const [response, setResponse] = useState<{ key: string; state: LoadState }>({ key: "", state: { status: "loading" } });
  const requestKey = `${leftId}|${rightId}|${thirdId}|${range}|${retry}`;

  useEffect(() => {
    const controller = new AbortController();
    setResponse({ key: requestKey, state: { status: "loading" } });
    const left = relationshipChoice(leftId);
    const right = relationshipChoice(rightId);
    const third = thirdId ? relationshipChoice(thirdId) : undefined;
    fetchRelationshipComparison({
      left, right, third,
      startDate: range === "Max" ? undefined : rangeStartDate(Number(range.slice(0, -1))),
      signal: controller.signal,
    }).then((data) => { if (!controller.signal.aborted) setResponse({ key: requestKey, state: { status: "ready", data } }); })
      .catch(() => { if (!controller.signal.aborted) setResponse({ key: requestKey, state: { status: "error" } }); });
    return () => controller.abort();
  }, [requestKey]);

  const state = response.key === requestKey ? response.state : { status: "loading" } as const;
  const labels: Record<RelationshipKey, string> = {
    left: relationshipChoice(leftId).label,
    right: relationshipChoice(rightId).label,
    third: thirdId ? relationshipChoice(thirdId).label : "Third indicator",
  };

  return <main className="relationships-page">
    <header className="relationships-header">
      <p className="eyebrow">MacroLens</p>
      <h1>Macro Relationships</h1>
      <p className="subtitle">Compare the history of two or three US macroeconomic indicators.</p>
    </header>
    <div className="charts-notice">
      <strong>Current-vintage history.</strong> Historical observations use the latest stored values and may include revisions. This is not point-in-time historical reconstruction.
      <span>Correlation describes how two historical series moved together over the selected period. It does not establish causation or predict future market moves.</span>
      <span>Quick comparisons are examples, not recommendations. No trading signals.</span>
    </div>
    <section className="relationship-controls" aria-label="Relationship controls">
      <div className="relationship-presets" role="group" aria-label="Quick comparisons">
        <span>Quick comparisons</span>
        {relationshipPresets.map((preset) => <button key={preset.label} type="button" onClick={() => {
          setLeftId(preset.left); setRightId(preset.right); setThirdId("");
        }}>{preset.label}</button>)}
      </div>
      <div className="relationship-selectors">
        <IndicatorSelect label="First indicator" value={leftId} onChange={setLeftId} unavailable={[rightId, thirdId]} />
        <IndicatorSelect label="Second indicator" value={rightId} onChange={setRightId} unavailable={[leftId, thirdId]} />
        <IndicatorSelect label="Third indicator (optional)" value={thirdId} onChange={setThirdId} unavailable={[leftId, rightId]} optional />
      </div>
      <div className="relationship-options">
        <div className="charts-range" role="group" aria-label="Relationship time range">
          {ranges.map((item) => <button key={item} type="button" aria-pressed={range === item} className={range === item ? "is-active" : ""} onClick={() => setRange(item)}>{item}</button>)}
        </div>
        <div className="charts-range" role="group" aria-label="Comparison scale">
          <button type="button" aria-pressed={mode === "actual"} className={mode === "actual" ? "is-active" : ""} onClick={() => setMode("actual")}>Actual values</button>
          <button type="button" aria-pressed={mode === "indexed"} className={mode === "indexed" ? "is-active" : ""} onClick={() => setMode("indexed")}>Indexed comparison</button>
        </div>
      </div>
    </section>
    <section className="relationship-panel" aria-label="Relationship results">
      <div className="relationship-panel__header">
        <h2>Historical comparison</h2>
        <p>{mode === "indexed" ? "Indexed comparison: 100 at the first shared nonzero period. Values show relative change, not economic strength." : "Actual values share an axis when display units are compatible; different units use separate axes."}</p>
      </div>
      {state.status === "loading" ? <p className="relationship-state" role="status">Loading relationship data...</p> : null}
      {state.status === "error" ? <div className="relationship-state" role="alert">Unable to load relationship data. <button type="button" onClick={() => setRetry((value) => value + 1)}>Retry</button></div> : null}
      {state.status === "ready" && !state.data.observations.length ? <p className="relationship-state">No aligned history available for this range.</p> : null}
      {state.status === "ready" && state.data.observations.length && mode === "indexed" && state.data.normalization_base_period === null ? <p className="relationship-state">Indexed comparison is unavailable because there is no shared nonzero baseline.</p> : null}
      {state.status === "ready" && state.data.observations.length && (mode === "actual" || state.data.normalization_base_period !== null) ? <RelationshipChart response={state.data} labels={labels} mode={mode} /> : null}
    </section>
    {state.status === "ready" ? <section className="relationship-summary" aria-label="Relationship summary">
      <h2>Relationship summary</h2>
      <p>Comparison frequency: {state.data.comparison_frequency}. {state.data.alignment_methodology}</p>
      <div className="relationship-summary__grid">{state.data.comparisons.map((comparison) => <article key={`${comparison.left_key}-${comparison.right_key}`}>
        <h3>{labels[comparison.left_key]} / {labels[comparison.right_key]}</h3>
        <dl>
          <div><dt>Overlapping observations</dt><dd>{comparison.overlapping_observation_count}</dd></div>
          <div><dt>Pearson correlation</dt><dd>{comparison.correlation === null ? "Unavailable" : comparison.correlation.toFixed(2)}</dd></div>
        </dl>
      </article>)}</div>
      <p className="relationship-summary__note">Correlation is unavailable with fewer than three overlapping periods or no variation.</p>
    </section> : null}
  </main>;
}
