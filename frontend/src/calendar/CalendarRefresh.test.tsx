import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,beforeEach,expect,test,vi} from 'vitest';
import type {CalendarResponse,CalendarMeasure,OverviewRefreshState} from '../api/macrolens';
import {CalendarPage} from './CalendarPage';
import {setLanguage} from '../i18n/language';

const NOW=new Date('2026-10-29T12:52:00Z');
const base:CalendarMeasure={series_id:'GDPC1',label:'Real GDP QoQ, annualized',feature_name:'qoq_annualized',frequency:'quarterly',unit:'percent',reference_period:'2026-07-01',previous_period:'2026-04-01',previous_kind:'previous_period',actual:null,previous:2.22,forecast:null,consensus_status:'not_integrated',data_version:null,revision_confirmed:false,binding_method:'official_schedule',vintage_date:null,realtime_end:null,result_status:'awaiting_data',mapping_status:'confirmed',source_url:'https://fred.stlouisfed.org/series/GDPC1',missing_reason:{actual:'observation_missing',previous:null}};
beforeEach(()=>{vi.useFakeTimers();vi.setSystemTime(NOW);Object.defineProperty(document,'visibilityState',{configurable:true,value:'visible'});});
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();setLanguage('en');});
async function flush(){await act(async()=>{for(let n=0;n<12;n++)await Promise.resolve();});}

test.each(['en','pl'] as const)('visible Calendar keeps GDP blank until committed generation, then reloads automatically in %s',language=>{
 // The async assertions run in the returned promise so fake timers remain active.
 return (async()=>{
 setLanguage(language);let committed=false;const requests:string[]=[];
 const refresh=():OverviewRefreshState=>({status:committed?'partial':'running',publication_id:committed?'published-q3':'stored-q2',next_check_at:new Date(+NOW+900_000).toISOString(),results:[]});
 const snapshot=(start:string,end:string):CalendarResponse=>({start_date:start,end_date:end,category:null,data_revision:committed?'published-q3':'stored-q2',automatic_refresh_supported:true,refresh:refresh(),events:[{release_id:53,release_name:'Gross Domestic Product',release_date:'2026-10-29',release_time:'08:30:00',source_timezone:'America/New_York',release_datetime_utc:'2026-10-29T12:30:00Z',importance:'high',source_link:null,date_precision:'date',series:[{series_id:'GDPC1',name:'Real GDP',short_name:'Real GDP',frequency:'quarterly',unit:'index',category:'growth'}],measures:[committed?{...base,actual:3.37,data_version:'current_vintage',result_status:'available',missing_reason:{actual:null,previous:null}}:base]}]});
 vi.stubGlobal('fetch',vi.fn(async(input:string|URL,init?:RequestInit)=>{
  const u=new URL(String(input));requests.push(`${init?.method??'GET'} ${u.pathname}`);
  if(u.pathname.endsWith('/brief/refresh'))return {ok:true,json:async()=>refresh()};
  if(u.pathname==='/api/v1/calendar')return {ok:true,json:async()=>snapshot(u.searchParams.get('start_date')!,u.searchParams.get('end_date')!)};
  throw new Error('Unexpected request');
 }));
 render(<CalendarPage/>);await flush();
 expect(document.querySelector('.agenda-actual')).toHaveTextContent('—');
 expect(document.querySelector('.agenda-secondary:last-child')).toHaveTextContent(language==='en'?'2.22%':'2,22%');
 await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});
 expect(document.querySelector('.agenda-actual')).toHaveTextContent('—');
 committed=true;
 await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});await flush();
 expect(document.querySelector('.agenda-actual')).toHaveTextContent(language==='en'?'3.37%':'3,37%');
 fireEvent.click(document.querySelector('.agenda-measure-name')!);
 expect(document.querySelector('.agenda-detail')).toHaveTextContent(language==='en'?'Current-vintage':'Bieżąca');
 fireEvent.keyDown(document.querySelector('.agenda-detail')!,{key:'Escape'});
 expect(document.querySelector('.agenda-detail')).toBeNull();
 expect(document.querySelector('.agenda-measure-name')).toHaveFocus();
 expect(requests.filter(r=>r.startsWith('POST'))).toHaveLength(0); // Entry saw an already-running job.
 expect(requests.filter(r=>r==='GET /api/v1/calendar')).toHaveLength(2);
 expect(screen.getByRole('main')).toBeInTheDocument();
 })();
});
