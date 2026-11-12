import type {CalendarMeasure,HistoryResponse} from '../api/macrolens';

type Rule={frequency:string;unit:string;sourceUnit:string;feature?:string;document?:boolean};
const rules:Record<string,Rule>={
 'JTSJOL:raw':{frequency:'monthly',unit:'thousand openings',sourceUnit:'thousands'},
 'UNRATE:raw':{frequency:'monthly',unit:'percent',sourceUnit:'percent'},
 'ICSA:raw':{frequency:'weekly',unit:'claims',sourceUnit:'number'},
 'CCSA:raw':{frequency:'weekly',unit:'claims',sourceUnit:'number'},
 'PAYEMS:monthly_change':{frequency:'monthly',unit:'thousand jobs',sourceUnit:'thousands of persons',feature:'monthly_change'},
 'GDPC1:qoq_annualized':{frequency:'quarterly',unit:'percent',sourceUnit:'billions of chained 2017 dollars',feature:'qoq_annualized'},
 'ISM_MANUFACTURING_PMI:raw':{frequency:'monthly',unit:'index points',sourceUnit:'index',document:true},
 'ISM_SERVICES_PMI:raw':{frequency:'monthly',unit:'index points',sourceUnit:'index',document:true},
};
for(const series of ['CPIAUCSL','CPILFESL','PCEPI','PCEPILFE'])for(const feature of ['mom','yoy'])rules[`${series}:${feature}`]={frequency:'monthly',unit:'percent',sourceUnit:'index',feature};

export function blsTrend(m:CalendarMeasure):TrendPoint[]{
 if(m.selected_source==='bls:cpi'){
  if(!m.cpi_history||!m.actual_provenance?.raw_hash||m.cpi_rate_kind!=='derived_index_rate')return [];
  return Object.entries(m.cpi_history).filter(([period,value])=>validDate(period)&&period<=(m.reference_period??'')&&Number.isFinite(Number(value))).sort(([a],[b])=>a.localeCompare(b)).slice(-12).map(([period,value])=>({period,value:Number(value)}));
 }
 if(m.selected_source!=='bls:employment'||!m.bls_history||!m.actual_provenance?.raw_hash)return [];
 return Object.entries(m.bls_history).filter(([period,value])=>validDate(period)&&period<=(m.reference_period??'')&&Number.isFinite(Number(value))).sort(([a],[b])=>a.localeCompare(b)).slice(-12).map(([period,value])=>({period,value:Number(value)}));
}

export type TrendPoint={period:string;value:number};
export type TrendRequest={series:string;feature?:string;startDate:string;endDate:string;rule:Rule;documentHash?:string};
const validDate=(value:string)=>/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
export function trendRequest(m:CalendarMeasure):TrendRequest|null {
 const rule=rules[`${m.series_id}:${m.feature_name}`];
 if(!rule||rule.frequency!==m.frequency||rule.unit!==m.unit||m.mapping_status!=='confirmed'||m.actual===null||!Number.isFinite(m.actual)||!m.reference_period||!validDate(m.reference_period)||m.source_comparison==='conflict')return null;
 if(m.seasonal_adjustment&&/not seasonally|NSA/i.test(m.seasonal_adjustment))return null;
 const documentHash=rule.document?m.actual_provenance?.raw_hash:undefined;
 if(rule.document&&(typeof documentHash!=='string'||!documentHash))return null;
 const start=new Date(m.reference_period+'T00:00:00Z');
 if(rule.frequency==='weekly')start.setUTCDate(start.getUTCDate()-7*15);
 else start.setUTCMonth(start.getUTCMonth()-(rule.frequency==='quarterly'?45:15));
 return {series:m.series_id,feature:rule.feature,startDate:start.toISOString().slice(0,10),endDate:m.reference_period,rule,documentHash:typeof documentHash==='string'?documentHash:undefined};
}

export function comparableTrend(m:CalendarMeasure,data:unknown):TrendPoint[]{
 const request=trendRequest(m);if(!request||!data||typeof data!=='object')return [];
 const d=data as HistoryResponse&{unit?:string;feature_name?:string;methodology_version?:string;source?:string};
 if(d.series_id!==request.series||d.frequency!==request.rule.frequency||d.unit!==request.rule.sourceUnit||d.history_type!=='current_vintage'||!Array.isArray(d.observations))return [];
 if(request.feature?(d.feature_name!==request.feature||d.methodology_version!=='v1'):d.feature_name!==undefined)return [];
 if(request.rule.document&&d.source!=='ism')return [];
 const points=new Map<string,number>();
 for(const row of d.observations){
  if(!row||typeof row!=='object')continue;
  const r=row as typeof row&{raw_hash?:string};
  if(request.documentHash&&r.raw_hash!==request.documentHash)continue;
  if(!validDate(r.observation_date)||typeof r.value!=='number'||!Number.isFinite(r.value)||r.observation_date>request.endDate||r.observation_date<request.startDate)continue;
  const day=r.observation_date;
  if(m.frequency==='monthly'&&!day.endsWith('-01'))return [];
  if(m.frequency==='quarterly'&&!/^\d{4}-(01|04|07|10)-01$/.test(day))return [];
  if(points.has(day)&&points.get(day)!==r.value)return [];
  points.set(day,r.value);
 }
 const result=[...points].sort(([a],[b])=>a.localeCompare(b)).slice(-12).map(([period,value])=>({period,value}));
 return result.length>=3?result:[];
}

export function trendGeometry(points:TrendPoint[],frequency:string,width=540){
 const times=points.map(p=>Date.parse(p.period+'T00:00:00Z')),values=points.map(p=>p.value),min=Math.min(...values),max=Math.max(...values);
 const padding=(max-min||Math.abs(max)*0.1||1)*0.08,span=max-min+2*padding,rough=span/3,power=10**Math.floor(Math.log10(rough));
 const step=([1,2,2.5,5,10].find(n=>n*power>=rough)??10)*power;
 const low=Math.floor((min-padding)/step)*step,high=Math.ceil((max+padding)/step)*step;
 const left=78,right=width-16,top=18,bottom=146,y=(value:number)=>bottom-(value-low)/(high-low)*(bottom-top);
 const ticks=Array.from({length:Math.round((high-low)/step)+1},(_,i)=>{const value=Number((low+i*step).toPrecision(12));return {value,y:y(value)};});
 const dots=points.map((p,i)=>({...p,x:left+(times[i]-times[0])/(times[times.length-1]-times[0]||1)*(right-left),y:y(p.value)}));
 const path=dots.map((p,i)=>{
  if(!i)return `M${p.x},${p.y}`;
  const expected=new Date(times[i-1]);
  if(frequency==='weekly')expected.setUTCDate(expected.getUTCDate()+7);else expected.setUTCMonth(expected.getUTCMonth()+(frequency==='quarterly'?3:1));
  return `${expected.getTime()===times[i]?'L':'M'}${p.x},${p.y}`;
 }).join(' ');
 const indices=width<370?[0,points.length-1]:[0,Math.floor((points.length-1)/2),points.length-1];
 return {dots,path,ticks,left,right,top,bottom,xTicks:[...new Set(indices)].map(i=>dots[i])};
}
