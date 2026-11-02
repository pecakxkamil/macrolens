import {afterEach, expect, test, vi} from 'vitest';
import {cleanup, render, screen, fireEvent, within} from '@testing-library/react';
import type {CalendarEvent, EconomyBriefResponse} from '../api/macrolens';
import wireCases from './__fixtures__/marketImpact.json';
import {eventImportanceStars, eventIdentity, eventImportanceNote, eventPriority, overviewEventPriorities, overviewUpcomingEvents, upcomingEventReport} from './upcomingEvents';
import {filterEvents, groupAgenda} from '../calendar/calendarAgenda';
import {CalendarPage} from '../calendar/CalendarPage';
import {setLanguage, tText} from '../i18n/language';

type Case = {before:number;expected:number;overview_key:string|null;identity:string;event:CalendarEvent};
const cases = wireCases as unknown as Case[];
const events = cases.map(row=>row.event);
afterEach(()=>{cleanup();setLanguage('en');vi.unstubAllGlobals();});

test.each(cases)('$event.release_name keeps canonical API stars, identity and eligibility',row=>{
 expect(eventImportanceStars(row.event)).toBe(row.expected);
 expect(eventIdentity(row.event)).toBe(row.identity);
 expect(eventPriority(row.event)?.key??null).toBe(row.overview_key);
 expect(eventIdentity({...row.event,market_impact_stars:null,importance:'low'})).toBe(row.identity);
 expect(upcomingEventReport(row.event)).toContain(`Market impact: ${row.expected}; scope: event; policy: 2026-11-k2-v1`);
});

test('29 kinds have exactly six promotions and the same 17 Overview candidates',()=>{
 expect(cases.filter(c=>c.before!==c.expected)).toHaveLength(6);
 expect([3,2,1].map(n=>events.filter(e=>eventImportanceStars(e)===n).length)).toEqual([17,11,1]);
 expect(events.filter(eventPriority)).toHaveLength(17);
 expect(overviewEventPriorities.map(r=>r.key)).toEqual(['fomc','fomc_press_conference','fomc_sep','employment','cpi','pce','gdp','ism_manufacturing','ism_services','adp_monthly','michigan_preliminary','michigan_final','retail','empire_state','ft900','claims','fomc_minutes']);
 const result=overviewUpcomingEvents({calendar_start_date:'2026-10-18',calendar_end_date:'2026-10-24',calendar:{status:'ready',data:{events}},policy:{status:'ready',data:{next_decision:null}}} as EconomyBriefResponse,new Date('2026-10-18T00:00:00Z'));
 expect(result.selected).toHaveLength(4);
 expect(result.selected.map(e=>eventPriority(e)?.key).sort()).toEqual(['employment','fomc','fomc_press_conference','fomc_sep']);
 for(const id of [46,97,192])expect(result.selected.some(e=>e.release_id===id)).toBe(false);
});

test('API is authoritative over names, legacy classes and Key/Tracked labels',()=>{
 const cpi=events.find(e=>e.release_id===10)!;
 expect(eventImportanceStars({...cpi,importance:'high',market_impact_stars:1})).toBe(1);
 expect(eventImportanceStars({...cpi,market_impact_stars:null})).toBeNull();
 const legacy={...cpi};delete legacy.market_impact_stars;
 expect(eventImportanceStars({...legacy,importance:'low'})).toBe(1);
 for(const importance of ['unknown','constructor','toString'])expect(eventImportanceStars({...legacy,importance:importance as CalendarEvent['importance']})).toBeNull();
 expect(eventImportanceNote).toContain('Key/Tracked labels describe Overview selection only');
 expect(eventImportanceNote).not.toContain('Claims and weekly');
});

test('filters inherit report stars without multiplying publications or changing chronology',()=>{
 expect(filterEvents(events,new Set([3]),false,new Set())).toHaveLength(17);
 expect(filterEvents(events,new Set([2]),false,new Set())).toHaveLength(11);
 expect(filterEvents(events,new Set([2,3]),false,new Set())).toHaveLength(28);
 const report=events.find(e=>e.release_id===9)!;
 const enriched={...report,measures:[{series_id:'RSAFS'},{series_id:'RSFSXMV'},{series_id:'RETAIL_CONTROL'}]} as CalendarEvent;
 expect(filterEvents([enriched],new Set([3]),false,new Set())).toHaveLength(1);
 expect(groupAgenda([enriched,enriched])[0].events).toHaveLength(1);
 expect(enriched.measures).toHaveLength(3);
});

test.each(['en','pl'] as const)('Calendar six promotions, filters and reset remain local in %s',async language=>{
 setLanguage(language);
 const promoted=cases.filter(row=>row.before!==row.expected).map(row=>({...row.event,measures:[]}));
 const fetch=vi.fn(async()=>({ok:true,json:async()=>({start_date:'2026-10-19',end_date:'2026-10-25',events:promoted,automatic_refresh_supported:false})}));
 vi.stubGlobal('fetch',fetch);
 render(<CalendarPage/>);
 await screen.findByRole('button',{name:tText(promoted[0].release_name)});
 for(const event of promoted){const button=screen.getByRole('button',{name:tText(event.release_name)});expect(within(button.closest('tr')!).getByRole('img',{name:tText('Importance 3 of 3')})).toBeInTheDocument();}
 fireEvent.click(screen.getByLabelText(/Only|Tylko/));
 for(const event of promoted)expect(screen.getByRole('button',{name:tText(event.release_name)})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:tText('Clear filters')}));
 expect(document.querySelectorAll('.agenda-entry')).toHaveLength(6);
 expect(fetch).toHaveBeenCalledTimes(1);
});
