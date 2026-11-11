import type {CalendarEvent,CalendarMeasure} from '../api/macrolens';
import {et} from './earningsPresentation';
import {macroMarketContext} from './macroMarketProfiles';

export function MacroMarketContext({event,measure,hasDefinition}:{event:CalendarEvent;measure?:CalendarMeasure;hasDefinition:boolean}){
 const context=macroMarketContext(event,measure);
 return <section className="macro-market-context" aria-label={et('Economy and USD context','Kontekst gospodarki i USD')}>
 {!hasDefinition&&context.definition?<><h4>{et('What does this indicator measure?','Co pokazuje ten wskaźnik?')}</h4><p>{context.definition}</p></>:null}
 <h4>{et('How to interpret it?','Jak to interpretować?')}</h4>
 <p><strong>{et('Economy: ','Gospodarka: ')}</strong>{context.economy}</p>
 {context.note?<p>{context.note}</p>:null}
 <p><strong>USD / Fed: </strong>{context.usd}</p>
 </section>;
}
