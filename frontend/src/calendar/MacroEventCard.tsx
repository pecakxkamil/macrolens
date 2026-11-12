import {macroMissingReason} from './MissingValue';
import type {ReactNode} from 'react';
import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {formatObservationDate} from '../format';
import {tText} from '../i18n/language';
import {formatCalendarDate,formatPolandTime} from './calendarDates';
import {eventInstant} from '../brief/upcomingEvents';
import {calendarComparison} from './calendarComparisons';
import {compactMeasureName,calendarReadingValue} from './calendarPresentation';
import {et} from './earningsPresentation';
import {macroFamily,familyText} from './macroInsightFamilies';
import {macroInsight,insightWarnings} from './macroInsight';
import {MacroTrend} from './MacroTrend';
import {MacroMarketContext} from './MacroEconomicContext';
import './macroEventCard.css';

const safe=(value?:string|null)=>value&&/^https?:\/\//.test(value)?value:null;
export function MacroEventCard({event,measure,children}:{event:CalendarEvent;measure?:CalendarMeasure;children:ReactNode}){
 const family=macroFamily(event,measure),comparison=measure?calendarComparison(measure,'previous'):null;
 const period=measure?.reference_period??event.reference_period,actual=measure?.actual;
 const restricted=event.result_integration_status==='publisher_permission_required',nonnumeric=event.expects_numeric_result===false;
 const documentAvailable=event.document_status==='available';
 const available=!restricted&&!nonnumeric&&actual!==null&&actual!==undefined&&Number.isFinite(actual);
 const interpretation=available?macroInsight(event,measure):null;
 const report=safe(event.document_url)??safe(event.publisher_reports_url)??safe(event.source_link),source=safe(measure?.source_url)??safe(event.source_link);
 const mode=measure?({mom:et('Month-on-month','Miesiąc do miesiąca'),yoy:et('Year-on-year','Rok do roku'),qoq_annualized:et('Quarter-on-quarter, annualized','Kwartał do kwartału, annualizowane')} as Record<string,string>)[measure.feature_name]:null;
 const seasonality=measure?.seasonal_adjustment?tText(measure.seasonal_adjustment):family?.seasonality==='SA'?et('Seasonally adjusted (SA)','Odsezonowane (SA)'):null;
 return <section className="macro-event-card" aria-label={et('Event insight','Analiza wydarzenia')}>
 <header><h3>{measure?compactMeasureName(measure):tText(event.release_name)}</h3>
 <p>{et('USA','USA')}{period?` · ${formatObservationDate(period,measure?.frequency??'monthly')}`:''}{mode?` · ${mode}`:''}{seasonality?` · ${seasonality}`:''}</p>
 <p>{et('Publication: ','Publikacja: ')}{formatCalendarDate(event.release_date)} · {eventInstant(event)!==null?formatPolandTime(event.release_datetime_utc):et('Time unconfirmed','Godzina niepotwierdzona')}</p></header>
 {available&&measure?<dl className="macro-insight-values"><div><dt>{et('Actual','Aktualny')}</dt><dd>{calendarReadingValue(measure,'actual')}</dd></div><div><dt>{et('Change vs previous','Zmiana vs poprzednio')}</dt><dd className={`macro-insight-change--${comparison?.direction??'neutral'}`}>{comparison?.text??'—'}</dd></div><div><dt>{et('Previous','Poprzednio')}</dt><dd>{calendarReadingValue(measure,'previous')}</dd></div></dl>
 :<p className="macro-insight-state">{restricted?(documentAvailable?et('Data available in the source report','Dane dostępne w raporcie źródłowym'):et('Numerical results are not integrated. Check the publisher’s reports.','Odczyty liczbowe nie są zintegrowane. Sprawdź raporty wydawcy.')):nonnumeric?et('This event has no numerical reading.','To wydarzenie nie ma odczytu liczbowego.'):measure?.result_status==='publisher_unavailable'?macroMissingReason(event,measure,'actual'):et('Awaiting publication','Oczekiwanie na publikację')}{(restricted||nonnumeric)&&report?<> · <a href={report} target="_blank" rel="noreferrer">{et('Source report','Raport źródłowy')}</a></>:null}</p>}
 {insightWarnings(event,measure).map(warning=><p className="macro-insight-warning" key={warning}>{warning}</p>)}
 <div className="macro-insight-body"><div className="macro-insight-copy">
 {family?<section><h4>{et('What does this indicator measure?','Co pokazuje ten wskaźnik?')}</h4><p>{familyText(family.description)}</p></section>:null}
 {interpretation?<section><h4>{et('What does this reading show?','Co oznacza aktualny odczyt?')}</h4><p>{interpretation}</p></section>:null}
 <MacroMarketContext event={event} measure={measure} hasDefinition={!!family}/>
 </div>
 {available&&measure?<MacroTrend measure={measure}/>:null}
 </div>
 <footer>{et('Source: ','Źródło: ')}{family?<a href={family.url} target="_blank" rel="noreferrer">{family.publisher}</a>:source?<a href={source} target="_blank" rel="noreferrer">{et('Publisher / data source','Wydawca / źródło danych')}</a>:et('See technical details','Zobacz szczegóły techniczne')}{source&&family&&source!==family.url?<> · <a href={source} target="_blank" rel="noreferrer">{source.includes('fred.stlouisfed.org')?'FRED / ALFRED':et('Data record','Odczyt źródłowy')}</a></>:null}</footer>
 <details className="macro-insight-technical"><summary>{et('Sources, revisions and technical details','Źródła, rewizje i szczegóły techniczne')}</summary>{children}</details>
 </section>;
}
