import { fetchBriefHistory } from "../api/macrolens";
import { lazy, Suspense, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { ChartDefinition } from "../charts/chartDefinitions";
import { combineChartData, fetchChartHistory, rangeStartDate, requestKey, type ChartRow } from "../charts/chartData";
import { getLocale, tLabel, tText } from "../i18n/language";
import { compactReadingValue, readingNumber, readingUnit, type PreparedReading } from "./readingComparisons";

const TimeSeriesChart = lazy(() => import("../charts/TimeSeriesChart").then(module => ({default:module.TimeSeriesChart})));
export type PreviewChart = { definition: ChartDefinition; unit: string; sources?: PreparedReading["sources"]; attribution?: string };
export function readingPreview(reading: PreparedReading): PreviewChart | null {
  const raw = reading.raw;
  if (!raw) return null;
  return {unit:raw.unit, sources:reading.sources, attribution:raw.attribution, definition:{id:`preview-${raw.component}`,title:reading.label,description:"Current-vintage history.",
    domain:raw.domain === "financial_conditions" ? "financial" : raw.domain,
    frequency:raw.frequency as ChartDefinition["frequency"],unit:"index",
    series:[{id:"value",label:reading.label,color:"#83a9d5",seriesId:raw.series_id,
      ...(raw.feature_name === "spread" ? {derived:"2s10s" as const} : raw.feature_name === "raw" ? {} : {featureName:raw.feature_name})}]} };
}
export const fedPreview: PreviewChart = {unit:"percent", sources:["DFEDTARL","DFEDTARU"].map(id=>({label:id,url:`https://fred.stlouisfed.org/series/${id}`})), definition:{id:"preview-fed-target",title:"Fed target range",description:"Current-vintage history.",domain:"financial",frequency:"daily",unit:"percent",
  series:[{id:"lower",label:"Lower bound",seriesId:"DFEDTARL",color:"#83a9d5"},{id:"upper",label:"Upper bound",seriesId:"DFEDTARU",color:"#d9af75"}]}};

export function ReadingChartDialog({ chart, title, onClose, publicationId }: {chart:PreviewChart|null;title:string;onClose:()=>void;publicationId?:string}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const previousFocus = useRef(document.activeElement as HTMLElement|null);
  const [range,setRange] = useState<number|null>(3);
  const [retry,setRetry] = useState(0);
  const [state,setState] = useState<{status:"loading"|"error"|"ready";rows:ChartRow[]}>({status:"loading",rows:[]});
  useEffect(() => {
    const node=dialog.current!;
    const previousOverflow=document.body.style.overflow;
    node.showModal();document.body.style.overflow="hidden";
    return () => {node.close();document.body.style.overflow=previousOverflow;previousFocus.current?.focus({preventScroll:true});};
  },[]);
  useEffect(() => {
    if (!chart) return;
    const controller=new AbortController();setState({status:"loading",rows:[]});
    Promise.all(chart.definition.series.map(async series => [requestKey(series),await (publicationId ? fetchBriefHistory(publicationId,requestKey(series),{startDate:range ? rangeStartDate(range) : undefined,signal:controller.signal}) : fetchChartHistory(series,{startDate:range ? rangeStartDate(range) : undefined,signal:controller.signal}))] as const))
      .then(histories=>{if(!controller.signal.aborted)setState({status:"ready",rows:combineChartData(chart.definition,Object.fromEntries(histories))});})
      .catch(()=>{if(!controller.signal.aborted)setState({status:"error",rows:[]});});
    return ()=>controller.abort();
  },[chart,range,retry,publicationId]);
  const hasData = chart && state.rows.some(row=>chart.definition.series.some(series=>typeof row[series.id]==="number"));
  const formatValue = (value:number, compact=false) => {
    if (!chart) return "";
    if (compact && ["claims","persons"].includes(chart.unit)) return new Intl.NumberFormat(getLocale(),{notation:"compact",maximumFractionDigits:1}).format(value);
    if (compact) return compactReadingValue(readingNumber(value,chart.unit),chart.unit);
    return `${readingNumber(value,chart.unit)}${chart.unit === "percent" ? "%" : ` ${tText(readingUnit(chart.unit))}`}`;
  };
  return createPortal(<dialog ref={dialog} className="overview-chart-dialog" aria-labelledby={titleId} onCancel={event=>{event.preventDefault();onClose();}} onClick={event=>{if(event.target===event.currentTarget)onClose();}}>
    <div className="overview-chart-dialog__panel">
      <header><h2 id={titleId}>{tText(title)}</h2><button type="button" onClick={onClose} autoFocus>{tText("Close chart")}</button></header>
      <p className="market-note">{tText("Current-vintage history.")} {chart ? tText(readingUnit(chart.unit)) : null}</p>
      {chart ? <>
        <div className="charts-range" role="group" aria-label={tLabel("Chart time range")}>{[1,3,5,null].map(years=><button type="button" key={years ?? "max"} aria-pressed={range===years} onClick={()=>setRange(years)}>{tText(years ? `${years}Y` : "Max")}</button>)}</div>
        {state.status==="loading" ? <p role="status">{tText("Loading indicator history...")}</p> : null}
        {state.status==="error" ? <div role="alert">{tText("Unable to load indicator history.")} <button onClick={()=>setRetry(value=>value+1)}>{tText("Retry")}</button></div> : null}
        {state.status==="ready" && !hasData ? <p>{tText("No history available for this range.")}</p> : null}
        {state.status==="ready" && hasData ? <Suspense fallback={<p role="status">{tText("Loading indicator history...")}</p>}><TimeSeriesChart definition={chart.definition} rows={state.rows} valueFormatter={formatValue} /></Suspense> : null}
        <footer className="market-note">{chart.attribution ? <p>{tText(chart.attribution)}</p> : null}{chart.sources?.map(source=><a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.label}</a>)}</footer>
      </> : <p>{tText("Chart unavailable for this reading.")}</p>}
    </div>
  </dialog>,document.body);
}
