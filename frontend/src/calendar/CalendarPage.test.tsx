import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,beforeEach,expect,test,vi} from 'vitest';
import App from '../App';
import {CalendarPage} from './CalendarPage';
import {setLanguage,tText} from '../i18n/language';
import type {CalendarEvent,CalendarMeasure,CalendarResponse} from '../api/macrolens';
import {formatPolandTime,weekRange,todayIso} from './calendarDates';
import {compactMeasureName,compactPeriod,compactMeasureValue} from './calendarPresentation';
import {countdown,filterEvents,groupAgenda,nextInstant,presetRange,rangeError,resultPending} from './calendarAgenda';
const NOW='2026-10-26T10:00:00Z';
const cpi={series_id:'CPIAUCSL',name:'Consumer Price Index',short_name:'CPI',frequency:'monthly',unit:'index',category:'inflation'};
function measure(label='CPI MoM'):CalendarMeasure{return {series_id:'CPIAUCSL',label,feature_name:'mom',frequency:'monthly',unit:'percent',reference_period:'2026-09-01',previous_period:'2026-08-01',previous_kind:'previous_period',actual:.3,previous:.2,forecast:null,consensus_status:'not_integrated',data_version:'stored_date_vintage',revision_confirmed:false,binding_method:'alfred_release_date',vintage_date:'2026-10-26',realtime_end:'9999-12-31',result_status:'available',mapping_status:'confirmed',source_url:'https://fred.stlouisfed.org/series/CPIAUCSL'};}

test.each(['en','pl'] as const)('BEA release checks show durable limits and partial coverage in %s',async language=>{
 setLanguage(language);const item={...events()[0],release_id:53,estimate_stage:'advance',measures:[{...measure('Real GDP'),series_id:'GDPC1',reference_period:'2026-07-01'}]};
 const refresh={status:'partial',publication_id:'saved',next_check_at:'2026-10-26T10:02:00Z',results:[],refresh_mode:'bea_release_aware',bea_release_checks:[{id:'synthetic-gdp',release_id:53,release_date:item.release_date,reference_period:'2026-07-01',estimate_stage:'advance',scheduled_at:'2026-10-26T10:00:00Z',expires_at:'2026-10-26T10:30:00Z',attempts:2,max_attempts:5,status:'partial',next_check_at:'2026-10-26T10:05:00Z',confirmed_measures:0,expected_measures:1}]};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[item],automatic_refresh_supported:false,refresh})})));
 render(<CalendarPage/>);fireEvent.click(await screen.findByRole('button',{name:new RegExp(tText('Real GDP'))}));
 const section=screen.getByRole('region',{name:tText('BEA publication check')});
 expect(section).toHaveTextContent('2/5');expect(section).toHaveTextContent('0/1');expect(section).toHaveTextContent(tText('BEA report partially confirmed'));
 expect(section).toHaveTextContent(tText('Next permitted source check'));
});

test.each(['en','pl'] as const)('FT900 signed billion-dollar balance, neutral difference and sources in %s',async language=>{
 setLanguage(language);
 const rights={source:'U.S. Census Bureau / U.S. Bureau of Economic Analysis',copyright:'Source: U.S. Census Bureau and U.S. Bureau of Economic Analysis.',original_title:'U.S. International Trade in Goods and Services',terms_url:'https://www.bea.gov/help/faq/147',original_url:'https://www.census.gov/foreign-trade/Press-Release/current_press_release/exh1.xlsx',modifications:'MacroLens converts millions to billions of USD and computes signed differences. Current-vintage values may include revisions; negative balances are deficits. No publisher endorsement is implied.',redistribution_conditions:'BEA public-domain policy with exceptions.'};
 const m:CalendarMeasure={...measure('Trade Balance — SA'),series_id:'CENSUS_FT900_TOTAL',feature_name:'raw',unit:'USD bn',actual:-105.572,previous:-92.826,reference_period:'2026-08-01',previous_period:'2026-07-01',data_version:'current_vintage',source_url:rights.original_url,source_value_millions:'-105572'};
 const item:CalendarEvent={...events()[0],release_id:null,event_id:'ft900:2026-08:monthly',event_type:'ft900',release_name:'U.S. Trade Balance — Goods and Services',importance:'medium',category:'growth',reference_period:'2026-08-01',usage_rights:rights,document_url:'https://www.census.gov/foreign-trade/Press-Release/ft900/ft900_2608.pdf',document_status:'available',series:[{...cpi,series_id:m.series_id,category:'growth'}],measures:[m]};
 const next:CalendarEvent={...item,event_id:'ft900:2026-09:monthly',reference_period:'2026-09-01',release_date:'2026-11-04',release_datetime_utc:'2026-11-04T13:30:00Z',measures:[{...m,reference_period:'2026-09-01',previous_period:'2026-08-01',actual:null,previous:-105.572,result_status:'scheduled'}]};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-04',events:[item,next],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);const button=await screen.findByRole('button',{name:tText('Trade Balance — SA')+(language==='en'?' (Aug)':' (sie)')});
 const row=button.closest('tr')!;expect(row.querySelector('.agenda-actual')).toHaveTextContent(language==='en'?'-105.572':'-105,572');
 expect(row).toHaveTextContent(language==='en'?'USD bn':'mld USD');expect(row).toHaveTextContent(language==='en'?'12.746':'12,746');expect(row).not.toHaveTextContent('%');
 expect(row.querySelector('.favorable,.unfavorable')).toBeNull();
 expect(filterEvents([item,next],new Set([3]),false,new Set())).toHaveLength(0);expect(filterEvents([item,next],new Set([2]),false,new Set(['activity']))).toHaveLength(2);
 expect(nextInstant([next],new Date('2026-11-04T13:16:00Z'))).toBe(new Date('2026-11-04T13:30:00Z').getTime());
 expect(countdown(nextInstant([next],new Date('2026-11-04T13:16:00Z')),new Date('2026-11-04T13:16:00Z'))).toBeTruthy();
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent('U.S. Census Bureau');expect(detail).toHaveTextContent('U.S. Bureau of Economic Analysis');
 expect(within(detail).getByRole('link',{name:tText('Official Exhibit 1 XLSX')})).toHaveAttribute('href',rights.original_url);
 expect(within(detail).getByRole('link',{name:tText('BEA data use policy')})).toHaveAttribute('href',rights.terms_url);
 expect(within(detail).queryByRole('link',{name:tText('View indicator')})).not.toBeInTheDocument();
 fireEvent.keyDown(detail,{key:'Escape'});expect(button).toHaveFocus();
 expect(document.querySelectorAll('.agenda-entry')[1].querySelector('.agenda-actual')).toHaveTextContent('—');
});
function events():CalendarEvent[]{return [
 {release_id:10,release_name:'Consumer Price Index',release_date:'2026-10-26',release_time:'08:30:00',source_timezone:'America/New_York',release_datetime_utc:'2026-10-26T12:30:00Z',importance:'high',source_link:'https://www.bls.gov/cpi/',date_precision:'date',series:[cpi],measures:[measure(),{...measure('Core CPI MoM'),series_id:'CPILFESL'}]},
 {release_id:50,release_name:'Employment Situation',release_date:'2026-10-26',release_time:'08:30:00',source_timezone:'America/New_York',release_datetime_utc:'2026-10-26T12:30:00Z',importance:'high',source_link:null,date_precision:'date',series:[{...cpi,series_id:'UNRATE',category:'labor'}],measures:[{...measure('Unemployment rate'),series_id:'UNRATE',feature_name:'raw'}]},
 {release_id:180,release_name:'Unemployment Insurance Weekly Claims Report',release_date:'2026-10-29',release_time:null,source_timezone:null,release_datetime_utc:null,importance:'high',source_link:null,date_precision:'date',series:[{...cpi,series_id:'ICSA',category:'labor'}],measures:[{...measure('Initial jobless claims'),series_id:'ICSA',feature_name:'raw',unit:'claims',actual:null,previous:null,reference_period:null,previous_period:null,mapping_status:'reference_period_unconfirmed',data_version:null}]},
 {release_id:18,release_name:'H.15 Selected Interest Rates',release_date:'2026-10-26',release_time:null,source_timezone:null,release_datetime_utc:null,importance:'low',source_link:null,date_precision:'date',series:[{...cpi,series_id:'DFF',name:'Effective Fed Funds Rate',short_name:'Effective Fed Funds Rate',category:'financial_conditions'}]},
 {release_id:999,release_name:'Unclassified release',release_date:'2026-10-26',release_time:null,source_timezone:null,release_datetime_utc:null,importance:undefined as unknown as CalendarEvent['importance'],source_link:null,date_precision:'date',series:[{...cpi,series_id:'UNKNOWN',name:'Unclassified indicator',short_name:'Unclassified indicator'}]},
 ];}
function mockApi(mode='ready',automatic=false){
 const fetch=vi.fn(async(input:string|URL,init?:RequestInit)=>{const url=new URL(String(input));if(url.pathname.endsWith('/brief/refresh'))return {ok:true,json:async()=>({status:'complete',publication_id:'saved',next_check_at:'2026-10-26T10:15:00Z',results:[]})};
 if(url.pathname==='/api/v1/calendar'){
  if(mode==='loading')return new Promise(()=>{});if(mode==='error')return {ok:false};
  const start=url.searchParams.get('start_date')!,end=url.searchParams.get('end_date')!;
  return {ok:true,json:async()=>({start_date:start,end_date:end,events:mode==='empty'?[]:events().filter(e=>e.release_date>=start&&e.release_date<=end),data_revision:'saved',automatic_refresh_supported:automatic,check:{status:'complete',checked_at:'2026-10-26T09:00:00Z',start_date:start,end_date:end,sources:[],required_resources:[]}})};
 }return new Promise(()=>{});});vi.stubGlobal('fetch',fetch);return fetch;
}
test.each(['en','pl'] as const)('PPI keeps three monthly rows and independent NSA annual context in %s',async language=>{
 setLanguage(language);
 const ids=['PPIFIS','PPIFES','WPSFD49116'],annualIds=['PPIFID','PPICOR','WPUFD49116'];
 const readings=ids.map<CalendarMeasure>((sid,i)=>({...measure(),series_id:sid,actual:.68,previous:.25,data_version:'current_vintage',input_unit:'Index Apr 2010=100',seasonal_adjustment:'Seasonally Adjusted',transform_formula:'100 * (I[t] / I[t-1] - 1)',year_over_year:{...measure(),series_id:annualIds[i],feature_name:'yoy',actual:i===2?null:4.97,previous:4.81,data_version:'current_vintage',source_url:`https://fred.stlouisfed.org/series/${annualIds[i]}`,input_unit:'Index Apr 2010=100',seasonal_adjustment:'Not Seasonally Adjusted',transform_formula:'100 * (I[t] / I[t-12] - 1)',missing_reason:{actual:i===2?'ppi_publication_not_confirmed':null,previous:null}}}));
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[{...events()[0],release_id:46,release_name:'Producer Price Index',measures:readings}],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);await waitFor(()=>expect(document.querySelectorAll('.agenda-entry')).toHaveLength(3));
 const rows=[...document.querySelectorAll('.agenda-entry')];
 expect(rows[0].querySelector('.agenda-actual')).toHaveTextContent(language==='en'?'4.97%':'4,97%');
 expect(rows[2].querySelector('.agenda-actual')).toHaveTextContent(language==='en'?'0.68%':'0,68%');
 expect(rows[2].querySelector('.agenda-actual small')).toHaveTextContent('\u2014');
 fireEvent.click(rows[2].querySelector('.agenda-measure-name')!);
 const details=document.querySelector('.agenda-detail')!;
 expect(details).toHaveTextContent('WPUFD49116');expect(details).toHaveTextContent('I[t-12]');
 expect(details.querySelector('a[href="https://fred.stlouisfed.org/series/WPUFD49116"]')).toBeInTheDocument();
 expect(details).toHaveTextContent(language==='en'?'Current-vintage':'Bieżąca');
});
beforeEach(()=>{vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date(NOW));});
test.each(['en','pl'] as const)('Employment levels use CPS/CES and neutral pp/hours in %s',async language=>{
 setLanguage(language);
 const ids=['CIVPART','U6RATE','AWHAETP'],labels=['Labor Force Participation Rate','U-6 Labor Underutilization Rate','Average Weekly Hours — Total Private'];
 const levels=ids.map<CalendarMeasure>((sid,i)=>({...measure(labels[i]),series_id:sid,feature_name:'raw',actual:[61.8,7.6,34.4][i],previous:[61.6,7.7,34.3][i],unit:i===2?'hours':'percent',data_version:'current_vintage',survey:i===2?'CES':'CPS',source_series_id:i===2?'CES0500000002':i===1?'LNS13327709':'LNS11300000',seasonal_adjustment:'Seasonally Adjusted',source_url:`https://fred.stlouisfed.org/series/${sid}`}));
 const e={...events()[1],measures:[...events()[1].measures!,...levels]};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[e],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);const b=await screen.findByRole('button',{name:new RegExp(language==='en'?'Average Weekly Hours':'Średni tygodniowy czas pracy')});
 const rows=[...document.querySelectorAll('.agenda-entry')];expect(rows).toHaveLength(4);
 expect(rows[1].children[6]).toHaveTextContent(language==='en'?'0.2 pp':'0,2 pkt proc.');
 expect(rows[2].children[6]).toHaveTextContent(language==='en'?'0.1 pp':'0,1 pkt proc.');
 expect(rows[3].children[6]).toHaveTextContent(language==='en'?'0.1 hours':'0,1 godz.');
 expect(rows[3].querySelector('.agenda-actual')).toHaveTextContent(language==='en'?'34.4 hours':'34,4 godz.');
 expect(rows[1].querySelector('.agenda-comparison--favorable')).toBeNull();expect(rows[2].querySelector('.agenda-comparison--unfavorable')).toBeNull();
 fireEvent.click(b);expect(document.querySelector('.agenda-detail')).toHaveTextContent('CES0500000002');expect(document.querySelector('.agenda-detail')).toHaveTextContent('CES');
});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();vi.unstubAllGlobals();setLanguage('en');location.hash='';});

test.each(['en','pl'] as const)('Retail stays one report with three neutral percent measures and component details in %s',async language=>{
 setLanguage(language);
 const labels=['Nominal retail sales MoM','Retail Sales ex Autos MoM','Retail Sales Control Group MoM'];
 const ids=['RSAFS','RSFSXMV','RETAIL_CONTROL'];
 const part={observation_period:'2026-09-01',vintage_date:'2026-10-28',level:400184,unit:'millions of dollars',components:{RSFSXMV:605188,RSGASS:68021,RSBMGESD:44077,RSFSDP:92906},source_urls:Object.fromEntries(['RSFSXMV','RSGASS','RSBMGESD','RSFSDP'].map(sid=>[sid,`https://fred.stlouisfed.org/series/${sid}`]))};
 const readings=ids.map<CalendarMeasure>((sid,i)=>({...measure(labels[i]),series_id:sid,actual:i===2?.135621381:0.9,previous:i===2?1.18979194:1.4,forecast:null,data_version:'current_vintage',calculation_provenance:i===2?{actual:{current:part,previous:{...part,observation_period:'2026-08-01',level:399642},formula:'100 * (current / previous - 1)'}}:undefined}));
 const retail:CalendarEvent={...events()[0],release_id:9,event_id:'release:9:2026-09-01:advance',release_name:'Advance Monthly Sales for Retail and Food Services',importance:'medium',series:[{...cpi,series_id:'RSAFS',category:'consumer'}],measures:readings};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[retail],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);
 const name=language==='en'?'Retail Sales Control Group':'Sprzedaż detaliczna — grupa kontrolna';
 const button=await screen.findByRole('button',{name:new RegExp(name)});
 expect(document.querySelectorAll('.agenda-entry')).toHaveLength(3);
 const row=button.closest('tr')!;
 expect(row.querySelector('.agenda-actual')).toHaveTextContent(language==='en'?'0.14%':'0,14%');
 expect(row.textContent).toContain(language==='en'?'pp':'pkt proc.');
 expect(row.querySelector('.agenda-comparison')).toHaveClass('agenda-comparison--neutral');
 fireEvent.click(button);
 expect(screen.getByText(tText('Control Group calculation uses a common current-vintage snapshot, not historical first prints.'))).toBeInTheDocument();
 for(const sid of ['RSFSXMV','RSGASS','RSBMGESD','RSFSDP'])expect(screen.getAllByRole('link',{name:sid})).toHaveLength(2);
 expect(screen.queryByRole('link',{name:tText('View indicator')})).not.toBeInTheDocument();
 fireEvent.keyDown(document.querySelector('.agenda-detail')!,{key:'Escape'});
 expect(button).toHaveFocus();
});

test.each(['en','pl'] as const)('January publisher-only rows retain cross-year periods, zero previous and one-time provenance in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2027-01-11T12:00:00Z'));
 const reading={...measure(),reference_period:'2026-12-01',previous_period:'2026-11-01',actual:null,previous:0,forecast:null};
 const item:CalendarEvent={...events()[0],event_id:'release:10:2026-12-01:main',release_date:'2027-01-13',release_time:'08:30:00',source_timezone:'America/New_York',release_datetime_utc:'2027-01-13T13:30:00Z',measures:[reading],schedule_status:'confirmed',schedule_provenance:{source_url:'https://www.bls.gov/schedule/news_release/cpi.htm',retrieved_at:'2026-10-27T19:56:05Z',confirmation_type:'one_time_official_review'}};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2027-01-11',end_date:'2027-01-17',events:[item],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);
 const button=await screen.findByRole('button',{name:/2026/});
 const row=button.closest('tr')!;
 expect(row.querySelector('.agenda-time')).toHaveTextContent('14:30');
 expect(row.querySelector('.agenda-actual')).toHaveTextContent('—');
 expect(row.querySelector('td:last-child')).toHaveTextContent(language==='en'?'0.00%':'0,00%');
 fireEvent.click(button);
 expect(screen.getByText(tText('This schedule was confirmed by a one-time review of the official publisher page; automatic access remains unavailable.'))).toBeInTheDocument();
});

test.each(['en','pl'] as const)('Fed nonnumeric events retain separate rows, details, filters and unknown-time countdown exclusion in %s',async language=>{
 setLanguage(language);
 const kinds=['fomc_press_conference','fomc_minutes','fomc_sep'] as const;
 const names=['FOMC Press Conference','FOMC Meeting Minutes','Fed Economic Projections (SEP)'];
 const fed:CalendarEvent[]=kinds.map((kind,i)=>({...events()[0],release_id:null,event_id:`meeting:${kind}`,event_type:kind,release_name:names[i],series:[],measures:[],expects_numeric_result:false,release_date:'2026-10-28',release_time:i===2?null:'14:30:00',release_datetime_utc:i===2?null:'2026-10-28T18:30:00Z',source_timezone:'America/New_York',meeting_start_date:'2026-10-27',meeting_end_date:'2026-10-28',date_status:'confirmed',time_status:i===2?'unconfirmed':'confirmed',source_link:'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',document_status:'not_available',document_url:null}));
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:fed,automatic_refresh_supported:false})})));
 render(<CalendarPage/>);
 const button=await screen.findByRole('button',{name:tText(names[0])});
 expect(screen.getByRole('button',{name:tText(names[1])})).toBeInTheDocument();
 expect(screen.getByRole('button',{name:tText(names[2])})).toBeInTheDocument();
 expect(nextInstant([fed[2]],new Date(NOW))).toBe(Infinity);
 expect(filterEvents(fed,new Set([3]),false,new Set(['financial']))).toHaveLength(2);
 fireEvent.click(button);
 expect(screen.getByText(tText('Actual, Previous, Forecast and numerical comparisons do not apply to this event.'))).toBeInTheDocument();
 expect(screen.getByText(tText('No official document is linked yet. Document availability does not determine whether the event took place.'))).toBeInTheDocument();
 expect(screen.queryByText(tText('Awaiting data'))).not.toBeInTheDocument();
 expect(screen.getByText(/2026-10-27.*2026-10-28/)).toBeInTheDocument();
 fireEvent.keyDown(document.querySelector('.agenda-detail')!,{key:'Escape'});
 expect(button).toHaveFocus();
 fireEvent.click(screen.getByLabelText(/Only|Tylko/));
 expect(screen.queryByRole('button',{name:tText(names[1])})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:tText(names[2])})).toBeInTheDocument();
});


test('main Calendar and old route keep the Monday-Sunday range with one shared column header',async()=>{
 mockApi();location.hash='#/overview/calendar';render(<App/>);await screen.findByRole('button',{name:'CPI MoM (Sep)'});
 expect(location.hash).toBe('#/calendar');expect(screen.getByRole('link',{name:'Calendar'})).toHaveAttribute('aria-current','page');
 expect(screen.getByRole('button',{name:'This week'})).toHaveAttribute('aria-pressed','true');expect(screen.getAllByRole('columnheader',{name:'Event'})).toHaveLength(1);
 expect(screen.getByRole('rowgroup',{name:'Monday, October 26, 2026'})).toBeInTheDocument();expect(screen.getByRole('rowgroup',{name:'Thursday, October 29, 2026'})).toBeInTheDocument();
});

test('default importance, quick filter, categories and clear remain local',async()=>{
 const fetch=mockApi();render(<CalendarPage/>);await screen.findByRole('button',{name:'CPI MoM (Sep)'});
 expect(screen.queryByRole('button',{name:'Effective Fed Funds Rate'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Unclassified indicator'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByLabelText(/Only/));expect(screen.queryByRole('button',{name:'Initial jobless claims'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Clear filters'}));expect(screen.getByRole('button',{name:'Effective Fed Funds Rate'})).toBeInTheDocument();expect(screen.getByRole('button',{name:'Unclassified indicator'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Filters'}));fireEvent.click(screen.getByLabelText('Housing'));expect(screen.getByText('No events match the selected filters.')).toBeInTheDocument();expect(fetch).toHaveBeenCalledTimes(1);
});

test('each measure has one ordinary row with its own unchanged time, importance and neutral values',async()=>{
 mockApi();render(<CalendarPage/>);const row=(await screen.findByRole('button',{name:'CPI MoM (Sep)'})).closest('tr')!;
 expect(row).toHaveTextContent('13:30');expect(row).not.toHaveTextContent('PL');expect(within(row).getByRole('img',{name:'Importance 3 of 3'})).toBeInTheDocument();
 expect(row).toHaveTextContent('0.30%');expect(row).toHaveTextContent('0.20%');expect(screen.getByRole('button',{name:'Core CPI MoM (Sep)'}).closest('tr')).toHaveTextContent('13:30');
 expect(screen.queryByRole('button',{name:/Consumer Price Index/})).not.toBeInTheDocument();expect(screen.queryByText('Stored date-level vintage')).not.toBeInTheDocument();
 expect(document.querySelectorAll('.agenda-entry')).toHaveLength(4);expect(row.querySelectorAll('.agenda-number')).toHaveLength(3);expect(row.querySelector('.overview-interpretation')).toBeNull();
});

test('details preserve the publication relationship, full units, provenance, definition and exact Explore link',async()=>{
 const fetch=mockApi();render(<CalendarPage/>);const button=await screen.findByRole('button',{name:'CPI MoM (Sep)'});fireEvent.click(button);
 expect(button).toHaveAttribute('aria-expanded','true');const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent('Consumer Price Index');expect(detail).toHaveTextContent('ALFRED establishes date-level availability');expect(detail).toHaveTextContent('2026-10-26');expect(detail).toHaveTextContent('mom');
 expect(within(detail).getByRole('link',{name:'View indicator'})).toHaveAttribute('href','#/explore/indicators/CPIAUCSL');expect(fetch).toHaveBeenCalledTimes(1);
 fireEvent.keyDown(button,{key:'Escape'});expect(button).toHaveAttribute('aria-expanded','false');expect(button).toHaveFocus();
});

test('row clicks and a single selected measure open details without duplicate publication panels',async()=>{
 mockApi();render(<CalendarPage/>);const first=await screen.findByRole('button',{name:'CPI MoM (Sep)'});fireEvent.click(first.closest('tr')!);
 expect(first).toHaveAttribute('aria-expanded','true');const second=screen.getByRole('button',{name:'Core CPI MoM (Sep)'});fireEvent.click(second);
 expect(first).toHaveAttribute('aria-expanded','false');expect(second).toHaveAttribute('aria-expanded','true');expect(document.querySelectorAll('.agenda-detail')).toHaveLength(1);
});

test('missing values, unknown periods, unknown times and consensus stay as dashes with explanations in details',async()=>{
 mockApi();render(<CalendarPage/>);const button=await screen.findByRole('button',{name:'Initial jobless claims'}),row=button.closest('tr')!;
 expect(row).not.toHaveTextContent('Reference period');expect(row).not.toHaveTextContent('Awaiting');expect(row.querySelectorAll('.agenda-number')).toHaveLength(3);
 expect([...row.querySelectorAll('.agenda-number')].every(x=>x.textContent==='—')).toBe(true);expect(row.querySelector('.agenda-time')).toHaveTextContent('—');expect(row).not.toHaveTextContent('00:00');
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent('Reference period unconfirmed');expect(detail).toHaveTextContent('publication date does not confirm');expect(detail).toHaveTextContent('No integrated consensus source');expect(detail).toHaveTextContent('no midnight time is inferred');
});

test('only the closest time group has one compact countdown; simultaneous rows retain the same time',async()=>{
 mockApi();render(<CalendarPage/>);const first=await screen.findByRole('button',{name:'CPI MoM (Sep)'}),second=screen.getByRole('button',{name:'Unemployment rate (Sep)'});
 expect(first.closest('tr')).not.toHaveClass('is-next');expect(second.closest('tr')).not.toHaveClass('is-next');expect(screen.getAllByText('In 2 hours 30 minutes')).toHaveLength(1);
 expect(second.closest('tr')).toHaveTextContent('13:30');expect(screen.getByRole('button',{name:'Initial jobless claims'}).closest('tr')).not.toHaveClass('is-next');
});

test.each(['en','pl'] as const)('revised permits explain a published result pending in FRED and the previous-month basis in %s',async language=>{
 setLanguage(language);
 const source='https://www.census.gov/construction/bps/permitsbyusreg_cust.xls';
 const permit:CalendarMeasure={...measure('Building permits'),series_id:'PERMIT',feature_name:'raw',unit:'thousand homes/year (SAAR)',actual:null,previous:1403,data_version:null,result_status:'awaiting_data',source_url:'https://fred.stlouisfed.org/series/PERMIT',period_provenance:{source_url:'https://www.census.gov/construction/soc/schedule.html',reference_period:'2026-09-01',binding_method:'official_schedule',estimate_stage:'revised_permits'},publication_provenance:{source_url:source,release_date:'2026-10-27',reference_period:'2026-09-01',estimate_stage:'revised_permits'},missing_reason:{actual:'revised_permits_provider_pending',previous:null}};
 const event:CalendarEvent={...events()[0],release_id:27,release_name:'New Residential Construction',release_date:'2026-10-27',release_datetime_utc:'2026-10-27T12:00:00Z',measures:[permit]};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[event]})})));
 render(<CalendarPage/>);const button=await screen.findByRole('button',{name:language==='en'?'Building permits (Sep)':'Pozwolenia na budowę (wrz)'});
 expect(button.closest('tr')!.querySelector('.agenda-actual')).toHaveTextContent('—');
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent(tText('Census has published the revised permits, but a matching result has not yet been confirmed in FRED.'));
 expect(detail).toHaveTextContent(tText('This is a revision of the same month. Previous remains the preceding month, not the earlier estimate of this month.'));
 expect(detail.textContent).not.toContain('..');expect(within(detail).getByRole('link',{name:tText('Confirmed publisher release')})).toHaveAttribute('href',source);
});

test.each(['en','pl'] as const)('ISM future rows keep stars, exact months, no consensus and raw index units in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2026-11-02T08:00:00Z'));
 const ismEvents:CalendarEvent[]=['manufacturing','services'].map((kind,i)=>{
  const sid=i?'ISM_SERVICES_PMI':'ISM_MANUFACTURING_PMI',day=i?'2026-11-04':'2026-11-02';
  return {...events()[0],release_id:null,event_id:`ism:${kind}:2026-10-01`,event_type:'ism_report',release_name:i?'ISM Services PMI':'ISM Manufacturing PMI',release_date:day,release_time:'10:00:00',release_datetime_utc:day+'T15:00:00Z',measures:[{...measure(i?'ISM Services PMI':'ISM Manufacturing PMI'),series_id:sid,feature_name:'raw',unit:'index points',reference_period:'2026-10-01',previous_period:'2026-09-01',actual:null,previous:i?54.9:54.5,data_version:null,source_url:'https://www.ismworld.org/'}]};
 });
 const fetch=vi.fn(async()=>({ok:true,json:async()=>({events:ismEvents,start_date:'2026-11-02',end_date:'2026-11-08'})}));vi.stubGlobal('fetch',fetch);
 render(<CalendarPage/>);const name=language==='en'?'ISM Manufacturing PMI (Oct)':'ISM PMI przemysłu (paź)';
 const button=await screen.findByRole('button',{name}),row=button.closest('tr')!;
 expect(row).toHaveTextContent('16:00');expect(within(row).getByRole('img',{name:tText('Importance 3 of 3')})).toBeInTheDocument();
 expect(row.querySelector('.agenda-actual')).toHaveTextContent('—');expect(row.querySelector('.agenda-secondary')).toHaveTextContent('—');
 expect(row.querySelector('.agenda-secondary:last-child')).toHaveTextContent(language==='en'?'54.5':'54,5');expect(row.textContent).not.toContain('%');
 expect(screen.getByRole('link',{name:'ISM'})).toHaveAttribute('href','https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/');
 fireEvent.click(screen.getByLabelText(/Only|Tylko/));expect(screen.getByRole('button',{name})).toBeInTheDocument();expect(document.querySelectorAll('.agenda-entry')).toHaveLength(2);expect(fetch).toHaveBeenCalledTimes(1);
});

test.each(['en','pl'] as const)('ISM historical differences stay neutral and details preserve report and prior versions in %s',async language=>{
 setLanguage(language);
 const provenance={source_url:'https://www.prnewswire.com/news-releases/ism.html',document_published_at:'2026-10-01T14:00:00Z',retrieved_at:'2026-10-26T12:00:00Z',raw_hash:'a'.repeat(64),version:'official_release'};
 const m:CalendarMeasure={...measure('ISM Manufacturing PMI'),series_id:'ISM_MANUFACTURING_PMI',feature_name:'raw',unit:'index points',actual:54.5,previous:54.6,data_version:'official_release',previous_data_version:'official_release',actual_provenance:provenance,previous_provenance:provenance,previous_before_report:{value:54.7,provenance},previous_revision_confirmed:true};
 const item:CalendarEvent={...events()[0],release_id:null,event_id:'ism:manufacturing:2026-09-01',event_type:'ism_report',release_name:'ISM Manufacturing PMI',measures:[m]};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({events:[item],start_date:'2026-10-26',end_date:'2026-11-01'})})));
 render(<CalendarPage/>);const button=await screen.findByRole('button',{name:language==='en'?'ISM Manufacturing PMI (Sep)':'ISM PMI przemysłu (wrz)'}),row=button.closest('tr')!;
 expect(row.querySelector('.agenda-comparison')).toHaveClass('agenda-comparison--neutral');expect(row.textContent).not.toContain('%');
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent(tText('Previous is the preceding month as reported in this document.'));
 expect(detail).toHaveTextContent(tText('Previous was revised in this report.'));expect(detail).toHaveTextContent('a'.repeat(64));
 expect(detail).toHaveTextContent(tText('Document publication time'));expect(detail).toHaveTextContent(tText('Retrieved'));
 expect(detail.textContent).not.toContain(' ? ');
 expect(detail).toHaveTextContent(tText('ISM document versions are not a complete first-release history. A report timestamp does not date all months in its history table.'));
});

test.each(['en','pl'] as const)('Michigan has two numeric report stages with restricted results and independent timing in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2026-11-06T12:00:00Z'));
 const items:CalendarEvent[]=(['preliminary','final'] as const).map((stage,i)=>({...events()[0],release_id:null,event_id:`michigan:2026-11:${stage}`,event_type:i?'michigan_final':'michigan_preliminary',release_name:`Michigan Consumer Sentiment — ${i?'Final':'Preliminary'}`,release_date:i?'2026-11-20':'2026-11-06',release_datetime_utc:i?null:'2026-11-06T15:00:00Z',reference_period:'2026-11-01',publication_stage:stage,expects_numeric_result:true,series:[],measures:[],result_integration_status:'publisher_permission_required',publisher_reports_url:'https://data.sca.isr.umich.edu/reports.php?year=2026',license_source_url:'https://data.sca.isr.umich.edu/agreement.php',document_status:'unconfirmed'}));
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({events:items,start_date:'2026-11-02',end_date:'2026-11-08'})})));
 render(<CalendarPage/>);
 const preliminary=await screen.findByRole('button',{name:tText(items[0].release_name)+(language==='en'?' (Nov)':' (lis)')});
 expect(document.querySelectorAll('.agenda-entry')).toHaveLength(2);
 expect(preliminary.closest('tr')).toHaveTextContent('16:00');
 expect(within(preliminary.closest('tr')!).getByRole('img',{name:tText('Importance 3 of 3')})).toBeInTheDocument();
 expect(screen.getAllByRole('link',{name:tText('Publisher reports')})).toHaveLength(2);
 expect(screen.queryByRole('link',{name:tText('Data at publisher')})).not.toBeInTheDocument();
 expect(countdown(nextInstant([items[1]],new Date('2026-11-06T12:00:00Z')),new Date('2026-11-06T12:00:00Z'))).toBeNull();
 expect(countdown(nextInstant(items,new Date('2026-11-06T12:00:00Z')),new Date('2026-11-06T12:00:00Z'))).toBeTruthy();
 fireEvent.click(preliminary);
 const detail=document.getElementById(preliminary.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent(tText('Previous would compare the preceding month, not Preliminary versus Final of the same month. No Previous value is integrated.'));
 expect(within(detail).getByRole('link',{name:tText('Publisher usage agreement')})).toHaveAttribute('href',items[0].license_source_url);
 expect(detail).toHaveTextContent(tText('No matching report link has been verified; this does not establish that the report is unpublished.'));
 expect(detail).not.toHaveTextContent(tText('No numerical result is expected for this event.'));
 fireEvent.keyDown(detail,{key:'Escape'});expect(preliminary).toHaveFocus();
 fireEvent.click(screen.getByLabelText(/Only|Tylko/));expect(document.querySelectorAll('.agenda-entry')).toHaveLength(1);
 expect(preliminary).toBeInTheDocument();
});

test.each(['en','pl'] as const)('Empire State shows one neutral level measure, provenance and NY Fed rights in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2026-10-29T12:00:00Z'));
 const rights={source:'Federal Reserve Bank of New York',copyright:'© 2026 Federal Reserve Bank of New York. Content from the New York Fed subject to the Terms of Use at newyorkfed.org.',terms_url:'https://www.newyorkfed.org/privacy/termsofuse',original_url:'https://www.newyorkfed.org/medialibrary/media/survey/empire/data/esms_seasonallyadjusted_diffusion.csv',modifications:'MacroLens computes index-point differences. The New York Fed does not endorse MacroLens.',redistribution_conditions:'https://www.newyorkfed.org/privacy/termsofuse'};
 const actual:CalendarMeasure={...measure('General Business Conditions — SA'),series_id:'NYFED_EMPIRE_GACDISA',feature_name:'raw',unit:'index points',reference_period:'2026-10-01',previous_period:'2026-09-01',actual:25.5,previous:7.6,data_version:'current_vintage',source_url:rights.original_url,usage_rights:rights,actual_provenance:{source_url:rights.original_url,version:'current_vintage',raw_hash:'a'.repeat(64),retrieved_at:'2026-10-29T10:00:00Z'}};
 const item:CalendarEvent={...events()[0],release_id:null,event_id:'empire-state:2026-10:monthly',event_type:'empire_state',release_name:'Empire State Manufacturing Survey',reference_period:'2026-10-01',release_date:'2026-10-15',release_datetime_utc:'2026-10-15T12:30:00Z',importance:'medium',series:[{...cpi,series_id:actual.series_id,category:'growth'}],measures:[actual],usage_rights:rights,document_status:'available',document_url:'https://www.newyorkfed.org/medialibrary/media/survey/empire/example.pdf'};
 const next:CalendarEvent={...item,event_id:'empire-state:2026-11:monthly',reference_period:'2026-11-01',release_date:'2026-11-16',release_datetime_utc:'2026-11-16T13:30:00Z',measures:[{...actual,reference_period:'2026-11-01',previous_period:'2026-10-01',actual:null,previous:25.5,result_status:'scheduled',missing_reason:{actual:'not_yet_published',previous:null}}]};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({events:[item,next],start_date:'2026-10-15',end_date:'2026-11-16'})})));
 render(<CalendarPage/>);
 const button=await screen.findByRole('button',{name:tText('General Business Conditions — SA')+(language==='en'?' (Oct)':' (paź)')});
 expect(document.querySelectorAll('.agenda-entry')).toHaveLength(2);
 const row=button.closest('tr')!;expect(row).toHaveTextContent(language==='en'?'17.9':'17,9');expect(row).not.toHaveTextContent('%');
 expect(filterEvents([item,next],new Set([3]),false,new Set())).toHaveLength(0);
 expect(filterEvents([item,next],new Set([2]),false,new Set(['activity']))).toHaveLength(2);
 expect(row.querySelector('.agenda-difference .favorable')).toBeNull();
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent('Federal Reserve Bank of New York');expect(detail).toHaveTextContent('a'.repeat(64));
 expect(within(detail).getByRole('link',{name:tText('NY Fed Terms of Use')})).toHaveAttribute('href',rights.terms_url);
 expect(within(detail).getByRole('link',{name:tText('Original NY Fed CSV')})).toHaveAttribute('href',rights.original_url);
 fireEvent.keyDown(detail,{key:'Escape'});expect(button).toHaveFocus();
 const future=document.querySelectorAll('.agenda-entry')[1];expect(future.querySelector('.agenda-actual')).toHaveTextContent('—');expect(future).toHaveTextContent(language==='en'?'25.5':'25,5');
});

test.each(['en','pl'] as const)('ADP monthly NER keeps independent periods, restricted results and no Pulse in %s',async language=>{
 setLanguage(language);vi.setSystemTime(new Date('2026-11-03T12:00:00Z'));
 const label='ADP National Employment Report';
 const items:CalendarEvent[]=['2026-09-30','2026-11-04','2026-12-02'].map((day,i)=>({...events()[0],release_id:null,event_id:i===2?'adp:calendar:2026-12:monthly':`adp:2026-${i?'10':'09'}:monthly`,event_type:'adp_monthly',release_name:label,release_date:day,release_datetime_utc:i===2?null:day+(i?'T13:15:00Z':'T12:15:00Z'),reference_period:i===2?null:`2026-${i?'10':'09'}-01`,publication_stage:'monthly',expects_numeric_result:true,series:[],measures:[],result_integration_status:'publisher_permission_required',publisher_reports_url:'https://mediacenter.adp.com/press-releases?l=100',license_source_url:'https://www.adp.com/legal.aspx',document_status:i?'unconfirmed':'available',document_url:i?null:'https://mediacenter.adp.com/monthly-report'}));
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({events:items,start_date:'2026-11-02',end_date:'2026-11-08'})})));
 render(<CalendarPage/>);
 const button=await screen.findByRole('button',{name:tText(label)+(language==='en'?' (Oct)':' (paź)')});
 expect(document.querySelectorAll('.agenda-entry')).toHaveLength(3);
 expect(button.closest('tr')).toHaveTextContent('14:15');
 expect(within(button.closest('tr')!).getByRole('img',{name:tText('Importance 3 of 3')})).toBeInTheDocument();
 expect(screen.getAllByRole('link',{name:tText('Data at publisher')})).toHaveLength(1);
 expect(screen.getAllByRole('link',{name:tText('Publisher reports')})).toHaveLength(2);
 expect(filterEvents(items,new Set([3]),false,new Set(['labor']))).toHaveLength(3);
 expect(filterEvents(items,new Set([3]),false,new Set(['activity']))).toHaveLength(0);
 expect(countdown(nextInstant([items[2]],new Date()),new Date())).toBeNull();
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent(tText('Monthly NER'));
 expect(detail).toHaveTextContent(tText('Previous would be the preceding month’s employment change, with its data version. No Previous value is integrated.'));
 expect(within(detail).getByRole('link',{name:tText('Publisher usage agreement')})).toHaveAttribute('href','https://www.adp.com/legal.aspx');
 expect(detail).not.toHaveTextContent(tText('No numerical result'));
 fireEvent.keyDown(detail,{key:'Escape'});expect(button).toHaveFocus();
});

test('custom date validation and presets retain saved-data requests',async()=>{
 const fetch=mockApi();render(<CalendarPage/>);await screen.findByRole('button',{name:'CPI MoM (Sep)'});fireEvent.click(screen.getByRole('button',{name:'Date range'}));
 fireEvent.change(screen.getByLabelText('Start date'),{target:{value:'2026-11-01'}});fireEvent.change(screen.getByLabelText('End date'),{target:{value:'2026-10-01'}});fireEvent.click(screen.getByRole('button',{name:'Apply range'}));expect(screen.getByRole('alert')).toHaveTextContent('The start date must not follow');expect(fetch).toHaveBeenCalledTimes(1);
 fireEvent.change(screen.getByLabelText('Start date'),{target:{value:'2025-01-01'}});fireEvent.click(screen.getByRole('button',{name:'Apply range'}));expect(screen.getByRole('alert')).toHaveTextContent('366 days');
 fireEvent.click(screen.getByRole('button',{name:'Tomorrow'}));await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).includes('start_date=2026-10-27'))).toBe(true));
});

test('empty stored data, loading and errors remain distinct',async()=>{
 mockApi('empty');render(<CalendarPage/>);expect(await screen.findByText('No stored events in this date range.')).toBeInTheDocument();cleanup();
 mockApi('loading');render(<CalendarPage/>);expect(screen.getByText('Loading calendar...')).toBeInTheDocument();cleanup();mockApi('error');render(<CalendarPage/>);expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load calendar.');expect(screen.getByRole('button',{name:'Retry'})).toBeInTheDocument();
});

test.each(['en','pl'] as const)('compact names, periods and values render in %s without refetching',async language=>{
 setLanguage(language);const fetch=mockApi();render(<CalendarPage/>);const button=await screen.findByRole('button',{name:language==='pl'?'Inflacja CPI m/m (wrz)':'CPI MoM (Sep)'});
 expect(button.closest('tr')).toHaveTextContent(language==='pl'?'0,30%':'0.30%');expect(screen.getByRole('heading',{name:language==='pl'?'Kalendarz':'Calendar'})).toBeInTheDocument();expect(fetch).toHaveBeenCalledTimes(1);
});

test('entry and focus keep the existing shared refresh and cooldown',async()=>{
 const fetch=mockApi('ready',true);render(<CalendarPage/>);await screen.findByRole('button',{name:'CPI MoM (Sep)'});await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).includes('calendar_start_date=2026-10-26'))).toBe(true));
 const before=fetch.mock.calls.length;fireEvent(window,new Event('focus'));await new Promise(r=>setTimeout(r,30));expect(fetch).toHaveBeenCalledTimes(before);
});

test('Warsaw dates, calendar weeks and DST keep their existing behavior',()=>{
 expect(todayIso(new Date('2026-12-31T23:30:00Z'))).toBe('2027-01-01');expect(weekRange('2027-01-01')).toEqual({startDate:'2026-12-28',endDate:'2027-01-03'});
 expect(presetRange('nextWeek',new Date('2026-12-31T23:30:00Z'))).toEqual({startDate:'2027-01-04',endDate:'2027-01-10'});
 expect(formatPolandTime('2026-03-13T12:30:00Z')).toBe('13:30 PL');expect(formatPolandTime('2026-09-30T12:30:00Z')).toBe('14:30 PL');expect(formatPolandTime('2026-10-29T12:30:00Z')).toBe('13:30 PL');
 expect(rangeError('2024-01-01','2024-12-31')).toBeNull();expect(rangeError('2024-02-30','2024-03-01')).not.toBeNull();
});

test('chronological ordering, deduplication, editorial stars and elapsed-time logic are unchanged',()=>{
 const source=events();expect(groupAgenda([source[3],source[1],source[0],{...source[0]}])[0].events.map(e=>e.release_id)).toEqual([10,50,18]);
 expect(filterEvents(source,new Set([3]),false,new Set())).toHaveLength(2);expect(filterEvents(source,new Set(),true,new Set())).toHaveLength(1);
 expect(resultPending(source[0],{...measure(),actual:null},new Date('2026-10-26T13:00:00Z'))).toBe(true);expect(countdown(nextInstant([source[0]],new Date(NOW)),new Date('2026-10-26T12:30:00Z'))).toBeNull();
});

test('GDP previous estimate, confirmed revision and current vintage stay explicit in details; nonnumeric events use one row',async()=>{
 const gdp={...events()[0],release_id:53,release_name:'Gross Domestic Product',measures:[{...measure('Real GDP QoQ, annualized'),series_id:'GDPC1',feature_name:'qoq_annualized',frequency:'quarterly',reference_period:'2026-04-01',previous_period:'2026-04-01',previous_kind:'previous_estimate' as const,actual:2.22,previous:1.48,revision_confirmed:true,data_version:'current_vintage' as const,previous_data_version:'stored_date_vintage' as const}]};
 const conference={...events()[0],release_id:null,event_id:'conference',release_name:'Policy conference',series:[],measures:[],expects_numeric_result:false};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[gdp,conference]})})));render(<CalendarPage/>);
 const button=await screen.findByRole('button',{name:'Real GDP QoQ, annualized (Q2)'}),row=button.closest('tr')!;expect(row).toHaveTextContent('2.22%');expect(row).toHaveTextContent('1.48%');expect(row).not.toHaveTextContent('Current-vintage');fireEvent.click(button);
 const detail=document.getElementById(button.getAttribute('aria-controls')!)!;expect(detail).toHaveTextContent('Confirmed revision');expect(detail).toHaveTextContent('Current-vintage value');expect(detail).toHaveTextContent('Previous compares the earlier stored estimate of the same quarter');expect(detail).toHaveTextContent('Stored date-level vintage');
 const event=screen.getByRole('button',{name:'Policy conference'});expect(event.closest('tr')).not.toHaveTextContent('Awaiting');expect(document.querySelectorAll('.agenda-entry')).toHaveLength(2);
});

test('compact labels and units respect the existing transformation and never invent periods',()=>{
 expect(compactMeasureName({...measure(),series_id:'PAYEMS',feature_name:'monthly_change'})).toBe('Nonfarm payrolls change (NFP)');
 expect(compactMeasureName({...measure(),series_id:'DGORDER'})).toBe('Durable goods orders MoM');expect(compactMeasureName({...measure(),series_id:'DGORDER',feature_name:'raw'})).toBe('Durable goods orders');expect(compactMeasureName({...measure(),feature_name:'yoy'})).toBe('CPI YoY');
 expect(compactPeriod({...measure(),reference_period:null},'2026-10-26')).toBe('');expect(compactPeriod({...measure(),reference_period:'2025-09-01'},'2026-10-26')).toBe('Sep 2025');
 expect(compactMeasureValue(null,'percent')).toBe('—');expect(compactMeasureValue(1275,'thousand homes/year (SAAR)')).toBe('1,275\u00a0k');expect(compactMeasureValue(7079,'thousand openings')).toBe('7.08\u00a0m');
 setLanguage('pl');expect(compactMeasureName({...measure(),series_id:'DGORDER'})).toBe('Zamówienia na dobra trwałe m/m');expect(compactMeasureValue(-.5,'index points')).toBe('-0,5\u00a0pkt');
});

test('relevant refresh failures remain visible while unrelated partial failures do not downgrade this range',async()=>{
 const response={start_date:'2026-10-26',end_date:'2026-11-01',events:events(),automatic_refresh_supported:false,check:{status:'complete',checked_at:NOW,sources:[],required_resources:['fred:calendar']},refresh:{status:'partial',results:[{resource:'ism:manufacturing',status:'error',error_code:'discovery_failed'}]}};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>response})));render(<CalendarPage/>);expect(await screen.findByText('Sources checked:')).toBeInTheDocument();cleanup();
 response.refresh.results=[{resource:'fred:calendar',status:'error',error_code:'fetch_failed'}];render(<CalendarPage/>);expect(await screen.findByText('Unable to check some sources — stored data shown.')).toBeInTheDocument();expect(screen.queryByText('Check details')).not.toBeInTheDocument();expect(document.querySelector('.calendar-check details')).toBeNull();
});


test.each(['en','pl'] as const)('comparison columns and accessible explanations work in %s without opening event details',async language=>{
 setLanguage(language);
 const nfp={...measure(),series_id:'PAYEMS',feature_name:'monthly_change',unit:'thousand jobs',actual:157,previous:182,forecast:120,consensus_status:'available' as const};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[{...events()[1],measures:[nfp]}],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);await screen.findByRole('button',{name:language==='en'?/NFP.*Sep/:/NFP.*wrz/});
 expect([...document.querySelectorAll('thead th')].map(h=>h.textContent)).toEqual(['Time','Event','Importance','Forecast','vs forecast','Actual','vs previous','Previous'].map(tText));
 const row=document.querySelector('.agenda-entry')!;expect(row.children).toHaveLength(8);
 expect(row.children[3]).toHaveTextContent('120');expect(row.children[4]).toHaveTextContent('+37');expect(row.children[5]).toHaveTextContent('157');expect(row.children[6]).toHaveTextContent('25');expect(row.children[7]).toHaveTextContent('182');
 expect(row.querySelector('.agenda-comparison--favorable')).toBeInTheDocument();expect(row.querySelector('.agenda-comparison--unfavorable')).toBeInTheDocument();
 const trigger=within(row.children[4] as HTMLElement).getByRole('button');fireEvent.focus(trigger);expect(screen.getByRole('tooltip')).toHaveTextContent(language==='en'?'consensus':'konsensus');
 fireEvent.keyDown(trigger,{key:'Escape'});expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
 fireEvent.mouseEnter(trigger.parentElement!);expect(screen.getByRole('tooltip')).toBeInTheDocument();fireEvent.mouseLeave(trigger.parentElement!);expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
 fireEvent.click(trigger);expect(screen.getByRole('tooltip')).toBeInTheDocument();expect(document.querySelector('.agenda-detail')).toBeNull();fireEvent.pointerDown(document.body);expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
});


test('future FOMC displays the prior range and effective date while awaiting a statement',async()=>{
 const policy:CalendarMeasure={...measure(),series_id:'DFEDTARL/DFEDTARU',feature_name:'target_range',frequency:'decision',reference_period:'2026-10-28',previous_period:'2026-09-16',previous_kind:'previous_decision',actual:null,previous:3.75,actual_range:null,previous_range:[3.75,4],data_version:null,previous_data_version:'official_release',previous_effective_date:'2026-09-17',missing_reason:{actual:'official_decision_not_available',previous:null},previous_provenance:{source_url:'https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm',version:'official_release'}};
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-26',end_date:'2026-11-01',events:[{...events()[0],release_id:null,event_type:'fomc_decision',release_date:'2026-10-28',release_name:'FOMC policy decision',measures:[policy]}],automatic_refresh_supported:false})})));
 render(<CalendarPage/>);const button=await screen.findByRole('button',{name:'Fed decision — interest rates'}),row=button.closest('tr')!;
 expect(row.querySelector('.agenda-actual')).toHaveTextContent('\u2014');expect(row.children[7]).toHaveTextContent('3.75\u20134.00%');expect(row.querySelector('.agenda-comparison')).toBeNull();
 fireEvent.click(button);const detail=document.getElementById(button.getAttribute('aria-controls')!)!;
 expect(detail).toHaveTextContent('No official decision statement is stored');expect(detail).toHaveTextContent('Previous decision effective date:');expect(detail).toHaveTextContent('Sep 17, 2026');expect(detail).toHaveTextContent('Previous is the target range announced before this meeting');
});

test('a newly confirmed publication reloads actual and its difference after the shared publication revision changes',async()=>{
 let reads=0,finish:(()=>void)|undefined;
 const response=(published:boolean)=>({start_date:'2026-10-26',end_date:'2026-11-01',data_revision:published?'after':'before',automatic_refresh_supported:true,events:[{...events()[0],measures:[{...measure(),actual:published ? .3 : null,result_status:published?'available':'scheduled'}]}]});
 const fetch=vi.fn(async(input:string|URL)=>{
  if(new URL(String(input)).pathname.endsWith('/brief/refresh'))return new Promise<{ok:boolean;json:()=>Promise<unknown>}>(resolve=>{finish=()=>resolve({ok:true,json:async()=>({status:'complete',publication_id:'after',next_check_at:'2026-10-26T10:15:00Z',results:[]})});});
  return {ok:true,json:async()=>response(++reads>1)};
 });
 vi.stubGlobal('fetch',fetch);render(<CalendarPage/>);
 const row=(await screen.findByRole('button',{name:'CPI MoM (Sep)'})).closest('tr')!;
 expect(row.querySelector('.agenda-actual')).toHaveTextContent('—');expect(row.querySelector('.agenda-comparison')).toBeNull();
 await waitFor(()=>expect(finish).toBeTypeOf('function'));finish!();
 await waitFor(()=>expect(row.querySelector('.agenda-actual')).toHaveTextContent('0.30%'));
 expect(row.children[6]).toHaveTextContent('+0.1');expect(row.children[7]).toHaveTextContent('0.20%');expect(reads).toBe(2);
});
