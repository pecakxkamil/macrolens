import type {PreparedReading} from './readingComparisons';
import type {PreparedFedTarget} from './fedTarget';
import {fedDecisionMarkers,type Interpretation} from './economicInterpretation';
import {et} from '../calendar/earningsPresentation';

export const usdComparisonNote=()=>et(
 'Potential USD impulse versus the previous reading; excludes market consensus and actual exchange-rate reactions.',
 'Potencjalny impuls dla USD względem poprzedniego odczytu; nie uwzględnia konsensusu ani rzeczywistej reakcji kursu.');

function assessment(tone:Interpretation['tone'],reason:string):Interpretation{
 return {tone,symbol:tone==='favorable'?'+':tone==='unfavorable'?'−':'±',
  label:tone==='favorable'?et('Potential support for USD','Potencjalne wsparcie dla USD'):tone==='unfavorable'?et('Potential pressure on USD','Potencjalna presja na USD'):et('Ambiguous USD impact','Niejednoznaczny wpływ na USD'),
  reason};
}
export function usdInflationInterpretation(current:number,previous:number):Interpretation|null{
 if(!Number.isFinite(current)||!Number.isFinite(previous)||current===previous)return null;
 return assessment(current>previous?'favorable':'unfavorable',current>previous
  ?et('Higher inflation may keep Fed rates higher for longer, making dollar investments more attractive and supporting USD.','Wyższa inflacja może skłaniać Fed do dłuższego utrzymywania wysokich stóp. To zwiększa atrakcyjność inwestycji w dolarach i może wspierać USD.')
  :et('Lower inflation gives the Fed more room to cut rates. Expectations of lower returns on dollar investments may weaken USD.','Niższa inflacja daje Fed więcej miejsca na obniżki stóp. Oczekiwanie niższego oprocentowania inwestycji w dolarach może osłabiać USD.'));
}
const features:Record<string,string>={payrolls:'monthly_change',unemployment:'level',initial_claims:'raw',job_openings:'level',average_hourly_earnings:'mom',headline_cpi:'mom',core_cpi:'mom',core_pce:'mom',producer_ppi:'mom',real_gdp:'qoq_annualized',industrial_production:'mom',manufacturing_pmi:'raw',services_pmi:'raw',real_consumption:'mom',real_disposable_income:'mom',retail_sales:'mom',housing_starts:'level',building_permits:'level',mortgage_rate:'level',yield_curve_2s10s:'spread',nfci:'level'};
export function usdInterpretation(reading:PreparedReading):Interpretation|null{
 const raw=reading.raw;
 if(!raw||features[reading.key]!==raw.feature_name||!['higher','lower'].includes(reading.comparison)||!Number.isFinite(raw.current?.value)||!Number.isFinite(raw.previous?.value))return null;
 const current=raw.current!.value,previous=raw.previous!.value,higher=reading.comparison==='higher';
 if(['headline_cpi','core_cpi','core_pce','producer_ppi'].includes(reading.key))return usdInflationInterpretation(current,previous);
 if(reading.key==='mortgage_rate')return assessment('mixed',et('Mortgage rates reflect both bond yields and lending costs. Their change alone does not show whether USD should strengthen or weaken.','Oprocentowanie hipotek zależy zarówno od rentowności obligacji, jak i kosztów kredytu. Sama jego zmiana nie wskazuje, czy dolar powinien się umacniać, czy osłabiać.'));
 if(reading.key==='yield_curve_2s10s')return assessment('mixed',et('The spread can widen because 10-year yields rise or 2-year yields fall. These moves can have different effects on USD, so the spread alone gives no clear direction.','Spread może rosnąć przez wzrost rentowności 10-letnich obligacji albo spadek 2-letnich. Te ruchy mogą mieć różny wpływ na USD, więc sam spread nie daje jednoznacznego kierunku.'));
 if(reading.key==='nfci')return assessment('mixed',et('Tighter financing can support USD through higher yields, but market stress can also drive demand for dollars. NFCI alone does not distinguish these situations.','Trudniejsze warunki finansowania mogą wspierać USD przez wyższe rentowności, ale popyt na dolara może też rosnąć w czasie niepokoju na rynkach. Sam NFCI nie rozstrzyga, z którą sytuacją mamy do czynienia.'));
 if(['manufacturing_pmi','services_pmi'].includes(reading.key)&&[current,previous].some(value=>value<0||value>100))return null;
 if(['unemployment','initial_claims','job_openings','housing_starts','building_permits'].includes(reading.key)&&[current,previous].some(value=>value<0))return null;
 const support=['unemployment','initial_claims'].includes(reading.key)?!higher:higher;
 const observations:Record<string,[string,string,string,string]>={
  payrolls:['A stronger NFP reading signals firmer labor demand.','A weaker NFP reading signals softer labor demand.','Lepszy wynik NFP wskazuje na mocniejszy popyt na pracowników.','Słabszy wynik NFP wskazuje na słabszy popyt na pracowników.'],
  unemployment:['Lower unemployment points to a stronger labor market.','Higher unemployment points to a weaker labor market.','Niższe bezrobocie wskazuje na mocniejszy rynek pracy.','Wyższe bezrobocie wskazuje na słabszy rynek pracy.'],
  initial_claims:['Fewer new claims suggest fewer layoffs.','More new claims suggest more layoffs.','Mniej nowych wniosków o zasiłek sugeruje mniej zwolnień.','Więcej nowych wniosków o zasiłek sugeruje więcej zwolnień.'],
  job_openings:['More vacancies indicate stronger demand for workers, not completed hires.','Fewer vacancies indicate weaker demand for workers.','Więcej wakatów oznacza większy popyt na pracowników, ale jeszcze nie wzrost zatrudnienia.','Mniej wakatów oznacza mniejszy popyt na pracowników.'],
  average_hourly_earnings:['Higher wage growth can sustain inflation pressure.','Lower wage growth can ease inflation pressure.','Wyższa dynamika płac może podtrzymywać presję inflacyjną.','Niższa dynamika płac może ograniczać presję inflacyjną.'],
  real_gdp:['Higher real GDP growth points to stronger activity.','Lower real GDP growth points to weaker activity.','Wyższa dynamika realnego PKB wskazuje na mocniejszą aktywność gospodarczą.','Niższa dynamika realnego PKB wskazuje na słabszą aktywność gospodarczą.'],
  industrial_production:['A higher production reading points to stronger industrial activity.','A lower production reading points to weaker industrial activity.','Wyższy odczyt produkcji wskazuje na mocniejszą aktywność przemysłu.','Niższy odczyt produkcji wskazuje na słabszą aktywność przemysłu.'],
  manufacturing_pmi:['A higher manufacturing PMI suggests improving conditions in industry.','A lower manufacturing PMI suggests worsening conditions in industry.','Wyższy PMI przemysłu wskazuje na poprawę koniunktury w sektorze.','Niższy PMI przemysłu wskazuje na osłabienie koniunktury w sektorze.'],
  services_pmi:['A higher services PMI suggests improving conditions in services.','A lower services PMI suggests worsening conditions in services.','Wyższy PMI usług wskazuje na poprawę koniunktury w usługach.','Niższy PMI usług wskazuje na osłabienie koniunktury w usługach.'],
  real_consumption:['Higher real spending growth points to firmer consumer demand.','Lower real spending growth points to softer consumer demand.','Wyższa dynamika realnej konsumpcji wskazuje na mocniejszy popyt konsumentów.','Niższa dynamika realnej konsumpcji wskazuje na słabszy popyt konsumentów.'],
  real_disposable_income:['Higher real income growth gives households more spending capacity.','Lower real income growth limits households’ spending capacity.','Wyższa dynamika realnych dochodów zwiększa możliwości zakupowe gospodarstw domowych.','Niższa dynamika realnych dochodów ogranicza możliwości zakupowe gospodarstw domowych.'],
  retail_sales:['Higher retail sales growth points to stronger nominal demand.','Lower retail sales growth points to weaker nominal demand.','Wyższa dynamika sprzedaży detalicznej wskazuje na mocniejszy popyt nominalny.','Niższa dynamika sprzedaży detalicznej wskazuje na słabszy popyt nominalny.'],
  housing_starts:['More housing starts point to stronger construction activity.','Fewer housing starts point to weaker construction activity.','Więcej rozpoczętych budów wskazuje na większą aktywność budowlaną.','Mniej rozpoczętych budów wskazuje na słabszą aktywność budowlaną.'],
  building_permits:['More permits suggest more planned construction.','Fewer permits suggest less planned construction.','Więcej pozwoleń wskazuje na większą skalę planowanych inwestycji budowlanych.','Mniej pozwoleń wskazuje na mniejszą skalę planowanych inwestycji budowlanych.'],
 };
 const observation=observations[reading.key];if(!observation)return null;
 const reason=et(observation[support?0:1],observation[support?2:3]);
 return assessment(support?'favorable':'unfavorable',reason+' '+(support
  ?et('This may reduce expectations of Fed rate cuts and support USD.','To może zmniejszać oczekiwania obniżek stóp Fed i wspierać USD.')
  :et('This may increase expectations of Fed rate cuts and weaken USD.','To może zwiększać oczekiwania obniżek stóp Fed i osłabiać USD.')));
}
export function fedUsdDecisionMarkers(target:PreparedFedTarget){
 const decision=fedDecisionMarkers(target);if(!decision)return null;
 const higher=decision.tone==='positive';
 return {...decision,interpretation:assessment(higher?'favorable':'unfavorable',higher
  ?et('The Fed raised rates. Higher returns on dollar deposits and bonds may attract capital and support USD.','Fed podniósł stopy. Wyższe oprocentowanie lokat i obligacji w dolarach może przyciągać kapitał i wspierać USD.')
  :et('The Fed cut rates. Lower returns on dollar deposits and bonds may make USD less attractive and weaken it.','Fed obniżył stopy. Niższe oprocentowanie lokat i obligacji w dolarach może zmniejszać atrakcyjność USD i go osłabiać.'))};
}
