import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {fetchSeriesHistory,fetchFeatureHistory,type CalendarMeasure} from '../api/macrolens';
import {formatObservationDate} from '../format';
import {et} from './earningsPresentation';
import {compactMeasureValue} from './calendarPresentation';
import {blsTrend,comparableTrend,trendGeometry,trendRequest,type TrendPoint} from './macroTrendData';

export function MacroTrend({measure}:{measure:CalendarMeasure}){
 const container=useRef<HTMLElement>(null),[width,setWidth]=useState(540);
 useLayoutEffect(()=>{const node=container.current;if(!node)return;const resize=()=>setWidth(Math.max(240,node.clientWidth||540));resize();if(typeof ResizeObserver==='undefined')return;const observer=new ResizeObserver(resize);observer.observe(node);return()=>observer.disconnect();});
 const request=trendRequest(measure),key=JSON.stringify({request,actual:measure.actual,vintage:measure.vintage_date}),[state,setState]=useState<{key:string;points:TrendPoint[]}>();
 useEffect(()=>{
  if(!request||measure.selected_source==='bls:employment')return;
  const abort=new AbortController(),options={startDate:request.startDate,endDate:request.endDate,signal:abort.signal};
  const promise=request.feature?fetchFeatureHistory(request.series,request.feature,options):fetchSeriesHistory(request.series,options);
  promise.then(data=>{if(!abort.signal.aborted)setState({key,points:comparableTrend(measure,data)});}).catch(()=>{if(!abort.signal.aborted)setState({key,points:[]});});
  return()=>abort.abort();
 },[key]);
 const fromBls=blsTrend(measure);const points=fromBls.length?fromBls:state?.key===key?state.points:[];if(!points.length)return null;
 const geometry=trendGeometry(points,measure.frequency,width),title=et(`Trend · ${points.length} observations`,`Trend · ${points.length} odczytów`);
 return <section ref={container} className="macro-insight-trend" aria-label={title}><h4>{title}</h4>
 <svg viewBox={`0 0 ${width} 198`} role="img" aria-label={title}><title>{title}</title><desc>{measure.selected_source==='bls:employment'?et('BLS history from one captured response; includes revisions.','Historia BLS z jednej pobranej odpowiedzi; obejmuje rewizje.'):request?.documentHash?et('History from the selected report.','Historia z wybranego raportu.'):et('Current-vintage history; may include revisions.','Historia w bieżącej wersji; może zawierać rewizje.')}</desc>
 <g className="macro-trend-axis">{geometry.ticks.map(t=><g key={t.value}><line x1={geometry.left} x2={geometry.right} y1={t.y} y2={t.y}/><text x={geometry.left-8} y={t.y+4} textAnchor="end">{compactMeasureValue(t.value,measure.unit)}</text></g>)}
 <line className="macro-trend-baseline" x1={geometry.left} x2={geometry.left} y1={geometry.top} y2={geometry.bottom}/>
 {geometry.xTicks.map((p,i)=><text key={p.period} x={p.x} y={166} textAnchor={i===0?'start':i===geometry.xTicks.length-1?'end':'middle'}>{formatObservationDate(p.period,measure.frequency)}</text>)}
 <text x={(geometry.left+geometry.right)/2} y={190} textAnchor="middle">{et('Reference period · fitted value scale','Okres odczytu · dopasowana skala wartości')}</text></g>
 <path d={geometry.path}/>{geometry.dots.map(p=><circle key={p.period} cx={p.x} cy={p.y} r="2.5"><title>{formatObservationDate(p.period,measure.frequency)}: {compactMeasureValue(p.value,measure.unit)}</title></circle>)}</svg>
 <ol className="visually-hidden" aria-label={et('Trend values','Wartości trendu')}>{points.map(p=><li key={p.period}><time dateTime={p.period}>{formatObservationDate(p.period,measure.frequency)}</time>: {compactMeasureValue(p.value,measure.unit)}</li>)}</ol>
 </section>;
}
