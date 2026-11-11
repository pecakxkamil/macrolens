import {afterEach,expect,it} from 'vitest';
import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {setLanguage} from '../i18n/language';
import {macroMarketContext} from './macroMarketProfiles';
import {trendGeometry} from './macroTrendData';
const event={} as CalendarEvent;
const measure={series_id:'JTSJOL',feature_name:'raw',frequency:'monthly',unit:'thousand openings',actual:7523,previous:7190,reference_period:'2026-09-01',previous_period:'2026-08-01',previous_kind:'previous_period',mapping_status:'confirmed'} as CalendarMeasure;
afterEach(()=>setLanguage('en'));
it.each(['en','pl'] as const)('explains economy and conditional USD channels in %s',language=>{
 setLanguage(language);
 const up=macroMarketContext(event,measure),down=macroMarketContext(event,{...measure,actual:6000});
 expect(up.economy).toContain(language==='pl'?'firmy szukają więcej pracowników':'firms are seeking more workers');
 expect(up.usd).toContain(language==='pl'?'Możliwe wsparcie USD':'Potential USD support');
 expect(down.usd).toContain(language==='pl'?'Możliwa presja na USD':'Potential USD headwind');
 const claims=macroMarketContext(event,{...measure,series_id:'ICSA',frequency:'weekly',unit:'claims',reference_period:'2026-09-05',previous_period:'2026-08-29'});
 expect(claims.usd).toContain(language==='pl'?'Możliwa presja na USD':'Potential USD headwind');
 const cpi=macroMarketContext(event,{...measure,series_id:'CPIAUCSL',feature_name:'mom',unit:'percent'});
 expect(cpi.economy).toContain(language==='pl'?'nie świadczy':'does not by itself');
});
it.each([{actual:null},{previous:null},{actual:7190},{mapping_status:'unconfirmed'},{comparison_status:'mixed_sources'},{source_comparison:'conflict'},{previous_period:'2025-01-01'}])('does not assign a current directional USD signal without a valid nonzero comparison %j',patch=>{
 const context=macroMarketContext(event,{...measure,...patch} as CalendarMeasure);
 expect(context.economy).toMatch(/^Reading guide:/);expect(context.usd).not.toContain('Potential USD');
});
it.each(['CIVPART','PSAVERT','CENSUS_FT900_TOTAL','NFCI','MORTGAGE30US','DFF'])('keeps ambiguous channels mixed for %s',series_id=>{
 const unit=series_id==='CENSUS_FT900_TOTAL'?'USD bn':series_id==='NFCI'?'index points':'percent';
 const frequency=['NFCI','MORTGAGE30US'].includes(series_id)?'weekly':series_id==='DFF'?'daily':'monthly';
 const context=macroMarketContext(event,{...measure,series_id,unit,frequency});expect(context.usd).not.toContain('Potential USD');expect(context.usd).not.toContain('Mixed channel');expect(context.usd.length).toBeGreaterThan(50);
});
it('retains thresholds and comparability caveats instead of inventing growth or FX outcomes',()=>{
 expect(macroMarketContext(event,{...measure,series_id:'ISM_SERVICES_PMI',unit:'index points',actual:49,previous:48}).note).toContain('slower contraction, not expansion');
 expect(macroMarketContext(event,{...measure,series_id:'CFNAI',unit:'index points'}).note).toContain('not necessarily recession');
 expect(macroMarketContext(event,{...measure,series_id:'NYFED_EMPIRE_GACDISA',unit:'index points'}).note).toContain('zero, not 50');
 expect(macroMarketContext(event,{...measure,series_id:'GDPC1',feature_name:'qoq_annualized',frequency:'quarterly',unit:'percent'}).note).toContain('smaller contraction');
 expect(macroMarketContext(event,{...measure,series_id:'NFCI',frequency:'weekly',unit:'index points',reference_period:'2026-09-05',previous_period:'2026-08-29'}).economy).toContain('tightening');
});
it.each(['adp_monthly','michigan_preliminary','michigan_final','fomc_minutes','fomc_sep','fomc_press_conference'] as const)('explains documents without fabricating a numerical signal: %s',event_type=>{
 const context=macroMarketContext({...event,event_type});expect(context.economy).not.toContain('No reviewed');expect(context.usd).toContain('no integrated numerical signal');
});
it.each([{series_id:'UNKNOWN'},{feature_name:'unknown'},{unit:'index'},{frequency:'quarterly'}])('does not guess meaning from a name or incompatible metadata %j',patch=>{
 expect(macroMarketContext(event,{...measure,...patch}).usd).toBe('No directional USD signal is assigned.');
});
it.each([[-2,-1,0],[0,0,0],[7190,7523,7335],[0.0001,0.0002,0.0003]])('provides ordered finite axis ticks and bounded points for %j',(a,b,c)=>{
 const points=[a,b,c].map((value,i)=>({value,period:`2026-0${i+1}-01`}));
 for(const width of [300,540]){const g=trendGeometry(points,'monthly',width);expect(g.ticks.length).toBeGreaterThanOrEqual(3);expect(g.ticks.length).toBeLessThanOrEqual(7);expect(g.ticks[0].value).toBeLessThanOrEqual(Math.min(a,b,c));expect(g.ticks[g.ticks.length-1].value).toBeGreaterThanOrEqual(Math.max(a,b,c));expect(g.dots.every(p=>Number.isFinite(p.y)&&p.y>=g.top&&p.y<=g.bottom&&p.x>=g.left&&p.x<=g.right)).toBe(true);expect(g.xTicks).toHaveLength(width<370?2:3);}
});

// Reviewed Calendar identities; this is scope coverage, not synthetic forecast data.
it.each([["AWHAETP", "raw", "monthly", "hours"], ["CCSA", "raw", "weekly", "claims"], ["CENSUS_FT900_TOTAL", "raw", "monthly", "USD bn"], ["CES0500000003", "mom", "monthly", "percent"], ["CFNAI", "raw", "monthly", "index points"], ["CIVPART", "raw", "monthly", "percent"], ["CPIAUCSL", "mom", "monthly", "percent"], ["CPIAUCSL", "yoy", "monthly", "percent"], ["CPILFESL", "mom", "monthly", "percent"], ["CPILFESL", "yoy", "monthly", "percent"], ["DFEDTARL/DFEDTARU", "target_range", "decision", "percent"], ["DFF", "raw", "daily", "percent"], ["DFII10", "raw", "daily", "percent"], ["DGORDER", "mom", "monthly", "percent"], ["DGS10", "raw", "daily", "percent"], ["DGS2", "raw", "daily", "percent"], ["DSPIC96", "mom", "monthly", "percent"], ["ECIALLCIV", "qoq", "quarterly", "percent"], ["GDPC1", "qoq_annualized", "quarterly", "percent"], ["HOUST", "raw", "monthly", "thousand homes/year (SAAR)"], ["HSN1F", "raw", "monthly", "thousand homes/year (SAAR)"], ["ICSA", "raw", "weekly", "claims"], ["INDPRO", "mom", "monthly", "percent"], ["ISM_MANUFACTURING_PMI", "raw", "monthly", "index points"], ["ISM_SERVICES_PMI", "raw", "monthly", "index points"], ["JTSJOL", "raw", "monthly", "thousand openings"], ["MORTGAGE30US", "raw", "weekly", "percent"], ["NFCI", "raw", "weekly", "index points"], ["NYFED_EMPIRE_GACDISA", "raw", "monthly", "index points"], ["PAYEMS", "monthly_change", "monthly", "thousand jobs"], ["PCEC96", "mom", "monthly", "percent"], ["PCEPI", "mom", "monthly", "percent"], ["PCEPILFE", "mom", "monthly", "percent"], ["PCEPILFE", "yoy", "monthly", "percent"], ["PERMIT", "raw", "monthly", "thousand homes/year (SAAR)"], ["PPIFES", "mom", "monthly", "percent"], ["PPIFIS", "mom", "monthly", "percent"], ["PSAVERT", "raw", "monthly", "percent"], ["RETAIL_CONTROL", "mom", "monthly", "percent"], ["RSAFS", "mom", "monthly", "percent"], ["RSFSXMV", "mom", "monthly", "percent"], ["TCU", "raw", "monthly", "percent"], ["U6RATE", "raw", "monthly", "percent"], ["UNRATE", "raw", "monthly", "percent"], ["WPSFD49116", "mom", "monthly", "percent"]])('covers the reviewed Calendar identity %s %s',(series_id,feature_name,frequency,unit)=>{
 const context=macroMarketContext(event,{...measure,series_id,feature_name,frequency,unit});expect(context.definition).toBeTruthy();expect(context.economy).not.toContain('No reviewed');expect(context.url).toMatch(/^https:/);
});
