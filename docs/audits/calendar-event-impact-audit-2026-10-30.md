# MacroLens — K1: audyt ważności wydarzeń ekonomicznych

Audyt wykonano **02.11.2026, Europe/Warsaw**. Nazwę pliku
`calendar-event-impact-audit-2026-10-30.md` zachowano zgodnie ze zleceniem;
nie oznacza ona wykonania tej kontroli 30 października.
Repozytorium `C:\Projects\macrolens`, `main`, HEAD
**`b89f744fe7c41f22203cf7ef59e3140367dfb53a`** —
`Optimize frontend bundle with lazy-loaded overview`.

**Wyłącznie diagnostyka i ten nowy raport. Nie zmieniono ocen, kodu, testów,
konfiguracji, danych ani bazy. Bez stagingu, commita i pusha. K2 nie rozpoczęto.**

## 1. Wynik i zasady liczenia

- Zidentyfikowano **28 głównych rodzin publikacji**: 17 rzeczywiście
  zmapowanych rodzin FRED po wyłączeniu technicznego FOMC Press Release
  oraz 11 publikacji z dedykowanych adapterów.
- Po wyodrębnieniu osobnego wydarzenia **G.17 annual revision** pełny
  inwentarz obejmuje **29 rodzajów**. W ten sposób liczone są wszystkie
  poniższe sumy gwiazdek. Nie są to liczby rekordów dat lub miar.
- Backend: **12 high, 16 medium, 1 low**.
- Efektywne Calendar: **11 × ★★★, 17 × ★★, 1 × ★, 0 unknown**.
- Do wyboru Overview kwalifikuje się **17 rodzajów**: 11 z ★★★ i 6 z ★★.
  Faktycznie widoczne są najwyżej cztery w bieżącym oknie. Pozostałe
  12 rodzajów nie kwalifikuje się, nawet jeżeli otrzymałyby high w API.
- Wśród 31 pozycji transkrypcji: **20 jednoznacznych dopasowań**,
  **3 ambiguous/manual review**, **8 NOT_SUPPORTED**.
  Z 20 dopasowań **14 ma obecnie ★★★**, a **6 ma ★★**.
  Sześć potwierdzonych rozbieżności dotyczy **6 rodzin**. Osobne #19
  Core Retail nie zwiększa tego licznika bez potwierdzenia jego definicji.
- **Grupa A: 2 rodziny** rekomendowane z wysoką pewnością do ★★★:
  Retail Sales i JOLTS. Obejmują 2 pewne pozycje referencji (#6, #18)
  i warunkowego kandydata #19 po rozstrzygnięciu znaczenia „Core”.
- **Grupa B: 12 tematów decyzyjnych**, z osobnym liczeniem GDP
  Second/Third/Updated. Nie każdy wymaga zmiany.
- **Grupa C: 8 nieobsługiwanych pozycji referencji**. Flash/final S&P mogą
  oznaczać więcej przyszłych tożsamości niż te dwie pozycje sektorowe.

Wyniki policzono z inwentarza i faktycznej funkcji `eventImportanceStars`,
nie z oszacowania liczby wierszy na ekranie. Rodzaj ISM rozróżnia seria;
sam `event_type=ism_report` nie wystarcza. Etapy GDP, daty miesięczne,
miary wspólnego raportu i powtórzenia tygodniowe nie zwiększają powyższej
liczby rodzin. Osobną rewizję G.17 pokazano jawnie zamiast ją pominąć.

## 2. Stan wejściowy i ochrona

HEAD zgadza się ze zleceniem, lecz working tree jest nowsze niż opis
„4 modified / 2 untracked”. Przy wejściu było **9 modified / 2 untracked**:
oprócz wcześniejszych plików znajdują się zlecone poprawki minimalistycznej
listy Overview, poprzedniego tygodnia w Calendar i odstępów nagłówków dat.
W K1 potraktowano wszystkie 11 plików jako zastany stan do zachowania.
Indeks był pusty.

**Ważna różnica SHA:** podany w zleceniu historyczny hash styles.css
`7696bd5cac8c8bb3792f86d23e588c97f1fd87a5aef407a9f141ceb07b9b20e0`
nie odpowiada już plikowi przy wejściu do K1. Po wcześniejszej, jawnie
zleconej korekcie paddingu dat bieżący hash wynosi
`40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c`.
Nie cofano tej zmiany w celu uzyskania starego hasha.
Pozostałe pięć chronionych hashy zgadza się ze zleceniem.
Wszystkie sześć zachowano byte-identycznie względem początku K1.

## 3. Metoda i granice dowodów

1. Odczytano aktualne definicje, mapowania, adaptery, tłumaczenia i testy.
2. PostgreSQL odczytano przez niezależne połączenia z `read_only=True`;
   `SHOW transaction_read_only` potwierdziło **on**. Zapytania dotyczyły
   wyłącznie economic_releases, series_release_map i aktywnych series
   ograniczonych do load_series_config. Nie odczytywano lub przepisywano
   Actual/Previous. Transakcje zakończono rollbackiem.
3. W pamięci wykonano czyste funkcje obecnego TS, transpilowane istniejącym
   TypeScript: priorytet, gwiazdki i tłumaczenie nazw. Nie montowano UI,
   nie uruchamiano hooków ani jobów. Pomocnicze deskryptory typów nie
   zawierały nowych dat i nie były zapisywane jako wydarzenia.
4. Odczytano zachowane oficjalne dowody etapów BEA i sprawdzono dwa
   odpowiednie komunikaty na stronie BEA. Sprawdzono też publiczne
   oficjalne źródła kandydatów brakującego pokrycia przez przeglądarkę.
   Nie wywoływano importerów, nie zapisywano RAW lub nowych snapshotów.
5. Referencją Investing jest wyłącznie **transkrypcja użytkownika**
   z załączonego polecenia. Samych obrazów nie oglądano.
   `SCREENSHOT_VERIFIED` oznacza w tym raporcie potwierdzenie w tej
   transkrypcji, nie niezależne OCR lub dostęp do Investing API.
   Nie otwierano kalendarza Investing ani jego endpointów i nie kopiowano
   opisów. Wyniki wyszukiwarki z innych domen nie są podstawą ocen.

Nie wykonano pomiaru reakcji S&P 500, Nasdaq, futures, zmienności lub
niespodzianek wobec konsensusu. Proponowane ratingi są **własną oceną
redakcyjną ex ante**, nie empirycznie wytrenowanym modelem wpływu cenowego.
Wartości K1 nie są prognozą zwrotu, kierunku lub amplitudy ruchu.

## 4. Dokładne miejsca definiowania ocen

| Kod | Plik i linie | Obecna odpowiedzialność |
| --- | --- | --- |
| S1 | app/analytics/release_calendar.py:42–84, 119–132, 195–246 | Zbiory nazw high/medium/low; fallback medium; pominięcie technicznego FOMC 101; overlay oficjalnych terminów; osobna roczna rewizja G.17 |
| S2 | app/ingestion/sync_fomc_calendar.py:137–152, 205–208 | Decision high; Press Conference/SEP high; Minutes medium; odrębne identyfikatory i dokumenty |
| S3 | app/analytics/ism_calendar.py:17–21; app/local_ism.py:5–8 | ISM manufacturing/services high; dwie lokalne serie, jeden wspólny event_type |
| S4 | app/analytics/michigan_calendar.py:15–19 | Preliminary high, Final medium |
| S5 | app/analytics/adp_calendar.py:13–17 | ADP monthly high |
| S6 | app/analytics/empire_state.py:24–29 | Empire medium, origin macrolens_editorial |
| S7 | app/analytics/ft900_calendar.py:21–26 | FT900 medium, origin macrolens_editorial |
| S8 | frontend/src/brief/upcomingEvents.ts:7–30, 86–93 | Tablica 17 priorytetów; Key=3, Tracked=2, pierwszeństwo przed importance |
| S9 | frontend/src/brief/upcomingEvents.ts:51–74 | Osobna kwalifikacja i kolejność top czterech; deduplikacja i okno |
| S10 | frontend/src/calendar/calendarAgenda.ts:20–32; CalendarPage.tsx:131–178 | Kategorie, filtr gwiazdek, rendering oraz domyślny filtr |
| S11 | frontend/src/api/macrolens.ts:458–489; app/analytics/calendar_readings.py:23–39, 84–113, 237–246 | Event importance i powiązanie wielu miar; miary nie mają osobnego market-impact ratingu |
| S12 | frontend/src/brief/EconomyBrief.tsx:74–81, 129–137; briefModel.ts:186,205 | Wspólne gwiazdki w Overview; bieżący minimalistyczny ekran; priorytety i provenance w eksporcie |

Linie dotyczą working tree z chwili K1, nie obietnicy stałych numerów
w przyszłym kodzie. Dodatkowo sprawdzono config/series.yaml, mapowanie
economic_releases/series_release_map, release_times, calendar_evidence
i reguły okresów, retail_measures, ppi_measures oraz testy wskazane niżej.
Konfiguracja serii nie definiuje własnej skali gwiazdek.

### 4.1 Backend nie pobiera oceny ważności z FRED

Tabela economic_releases w schema.sql:41 przechowuje ID, nazwę, link,
press_release i timestampy, **bez kolumny importance**. release_importance
wylicza ocenę po dokładnej nazwie przy odczycie. Jest to klasyfikacja
MacroLens, nie rating FRED, BLS, BEA lub Investing.

High: Employment Situation, Consumer Price Index, Personal Income and
Outlays, Gross Domestic Product, Unemployment Insurance Weekly Claims Report.

Jawny medium: JOLTS, Industrial Production and Capacity Utilization,
Retail, New Residential Construction, New Residential Sales, NFCI.
Low: H.15 Selected Interest Rates. **Wszystko inne domyślnie medium**.

Istotne szczegóły: prawdziwa nazwa G.17 w bazie ma prefiks G.17 i nie
pasuje do krótszej nazwy w zbiorze medium; dostaje ten sam wynik przez
fallback. PPI, ECI, M3, Primary Mortgage Market Survey i CFNAI także
korzystają z fallbacku medium. Nie jest to dowód oceny wydawcy.
FRED 101 „FOMC Press Release” jest świadomie pomijane, nie jest drugim
wydarzeniem decyzji i nie weszło do statystyki 29.

### 4.2 Końcowa reguła frontendu

```text
rule = eventPriority(event)
jeśli rule istnieje: Key event → 3; Tracked event → 2
w przeciwnym razie: importance high → 3; medium → 2; low → 1
nieznana/brakująca wartość poza regułą → null
```

Nazwy `overviewStars` i komentarz „calendar metadata unchanged” mogą
wprowadzać w błąd: API nie jest mutowane, ale **Calendar używa tej samej
funkcji**, również w filtrze. Nie istnieją niezależne widoczne ratingi
Calendar i Overview.

Dla zwykłych rodzin FRED frontend dopasowuje regułę po dokładnej nazwie,
nie release_id. Dedykowane typy mają część stabilnych dopasowań po
event_type; fomc_decision ma specjalny alias do reguły „fomc”.
ISM wymaga nazwy lub odpowiedniego klucza, bo event_type jest wspólne.
Zmiana nazwy źródłowej może więc zmienić dopasowanie i rating.

**Jedyna faktyczna rozbieżność backend → frontend w obecnym inwentarzu:**
Claims **high → ★★**, bo „claims” jest Tracked event.
Retail i JOLTS to **medium → ★★**; ich problemem jest różnica względem
referencji, nie sprzeczność bieżących dwóch warstw.
Testy pokazują też, że reguła ISM potrafi podnieść syntetyczne medium do 3,
ale nie udajemy, że produkcyjne ISM ma obecnie medium.

## 5. Pełny inwentarz

K = Key event; T = Tracked event; # = pozycja w tablicy wyboru Overview.
`—` w event_type oznacza brak tego pola dla generycznych eventów FRED;
`null` release ID dedykowanych adapterów nie oznacza nieznanej tożsamości.

Kolumna PL pokazuje **wynik obecnego tText(release_name)**. Przy miarach
Calendar często wyświetla inną, kompaktową nazwę miary; nie dorabiano
tłumaczenia tam, gdzie funkcja nadal zwraca EN. Kategorie podano jak
w źródłowych seriach; growth/consumer przechodzą w UI na activity,
financial_conditions na financial. Michigan i FOMC mają własne reguły kategorii.

| Event EN | Event PL / fallback EN | Event type / release ID | Series / measure inputs | Kategoria źródłowa | Backend importance | Priorytet | Calendar | Overview | Reguła |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Advance Monthly Sales for Retail and Food Services | Wstępna miesięczna sprzedaż detaliczna i gastronomiczna | — / 9 | RSAFS, RSBMGESD, RSFSDP, RSFSXMV, RSGASS | consumer | medium | T #13 | ★★ | ★★ * | S1 + S8 |
| 2. Consumer Price Index | Indeks cen konsumpcyjnych | — / 10 | CPIAUCSL, CPILFESL | inflation | high | K #5 | ★★★ | ★★★ * | S1 + S8 |
| 3. Employment Cost Index | Indeks kosztów zatrudnienia | — / 11 | ECIALLCIV | inflation | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 4. G.17 Industrial Production and Capacity Utilization | G.17 Industrial Production and Capacity Utilization | — / 13 | INDPRO, TCU | growth | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 5. H.15 Selected Interest Rates | H.15 — wybrane stopy procentowe | — / 18 | DFF, DFII10, DGS10, DGS2 | financial_conditions | low | — | ★ | niekwalifikowane | S1 + S8 |
| 6. New Residential Construction | Nowe budownictwo mieszkaniowe | — / 27 | HOUST, PERMIT | housing | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 7. Producer Price Index | Producer Price Index | — / 46 | PPICOR, PPIFES, PPIFID, PPIFIS, WPSFD49116, WPUFD49116 | inflation | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 8. Employment Situation | Sytuacja na rynku pracy | — / 50 | AWHAETP, CES0500000003, CIVPART, PAYEMS, U6RATE, UNEMPLOY, UNRATE | labor | high | K #4 | ★★★ | ★★★ * | S1 + S8 |
| 9. Gross Domestic Product | Produkt krajowy brutto | — / 53 | GDPC1 | growth | high | K #7 | ★★★ | ★★★ * | S1 + S8 |
| 10. Personal Income and Outlays | Dochody i wydatki osobiste | — / 54 | DSPIC96, PCEC96, PCEPI, PCEPILFE, PSAVERT | consumer+inflation | high | K #6 | ★★★ | ★★★ * | S1 + S8 |
| 11. Manufacturer's Shipments, Inventories, and Orders (M3) Survey | Manufacturer's Shipments, Inventories, and Orders (M3) Survey | — / 95 | DGORDER | growth | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 12. New Residential Sales | Sprzedaż nowych domów | — / 97 | HSN1F | housing | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 13. Unemployment Insurance Weekly Claims Report | Tygodniowy raport o wnioskach o zasiłek | — / 180 | CCSA, ICSA | labor | high | T #16 | ★★ | ★★ * | S1 + S8 |
| 14. Primary Mortgage Market Survey | Badanie rynku kredytów hipotecznych | — / 190 | MORTGAGE30US | housing | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 15. Job Openings and Labor Turnover Survey | Wolne miejsca pracy i rotacja zatrudnienia | — / 192 | JTSJOL | labor | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 16. Chicago Fed National Activity Index | Indeks aktywności gospodarczej Chicago Fed | — / 219 | CFNAI | growth | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 17. Chicago Fed National Financial Conditions Index | Indeks warunków finansowych Chicago Fed | — / 221 | NFCI | financial_conditions | medium | — | ★★ | niekwalifikowane | S1 + S8 |
| 18. FOMC policy decision | Decyzja FOMC w sprawie polityki pieniężnej | fomc_decision / null | DFEDTARL/DFEDTARU (measure) | financial_conditions | high | K #1 | ★★★ | ★★★ * | S2 + S8 |
| 19. FOMC Press Conference | Konferencja prasowa FOMC | fomc_press_conference / null | — | financial_conditions | high | K #2 | ★★★ | ★★★ * | S2 + S8 |
| 20. Fed Economic Projections (SEP) | Projekcje gospodarcze Fed (SEP) | fomc_sep / null | — | financial_conditions | high | K #3 | ★★★ | ★★★ * | S2 + S8 |
| 21. FOMC Meeting Minutes | Protokół FOMC | fomc_minutes / null | — | financial_conditions | medium | T #17 | ★★ | ★★ * | S2 + S8 |
| 22. ISM Manufacturing PMI | ISM PMI przemysłu | ism_report / null | ISM_MANUFACTURING_PMI | growth | high | K #8 | ★★★ | ★★★ * | S3 + S8 |
| 23. ISM Services PMI | ISM PMI usług | ism_report / null | ISM_SERVICES_PMI | growth | high | K #9 | ★★★ | ★★★ * | S3 + S8 |
| 24. Michigan Consumer Sentiment — Preliminary | Nastroje konsumentów Michigan — wstępne | michigan_preliminary / null | — | consumer | high | K #11 | ★★★ | ★★★ * | S4 + S8 |
| 25. Michigan Consumer Sentiment — Final | Nastroje konsumentów Michigan — końcowe | michigan_final / null | — | consumer | medium | T #12 | ★★ | ★★ * | S4 + S8 |
| 26. ADP National Employment Report | ADP — zatrudnienie w sektorze prywatnym | adp_monthly / null | — | labor | high | K #10 | ★★★ | ★★★ * | S5 + S8 |
| 27. Empire State Manufacturing Survey | Empire State — aktywność przemysłu | empire_state / null | NYFED_EMPIRE_GACDISA | growth | medium | T #14 | ★★ | ★★ * | S6 + S8 |
| 28. U.S. Trade Balance — Goods and Services | Bilans handlowy USA — towary i usługi | ft900 / null | CENSUS_FT900_TOTAL | growth | medium | T #15 | ★★ | ★★ * | S7 + S8 |
| 29. G.17 annual revision | G.17 — roczna rewizja | — / 13 | — | brak (series=[]) | medium | — | ★★ | niekwalifikowane | S1 + S8 |

Gwiazdki Overview oznaczone * są tymi samymi gwiazdkami **jeżeli wydarzenie
zostanie wybrane**. Nie oznaczają, że wszystkie 17 pojawiają się jednocześnie.

Roczna rewizja G.17 ma potwierdzony osobny wpis reguły na 24.11.2026,
event_id `release:13:annual_revision:2026`, estimate_stage annual_revision
i brak miesięcznej pary Actual/Previous. Ma puste series, więc w obecnym
frontendzie nie pasuje do żadnej włączonej kategorii; bez filtra kategorii
pozostaje ★★. To dodatkowy przypadek do testów, bez naprawy w K1.

## 6. 31 pozycji referencji i dopasowanie miar

Każda pozycja poniżej pochodzi z listy ★★★ użytkownika. „Zgodne” oznacza
wyłącznie zgodność liczby gwiazdek, nie zgodność wartości, vintage lub
godziny między aplikacjami.

| # | Pozycja z transkrypcji | Dopasowanie MacroLens / obecnie | Status i wynik |
| --- | --- | --- | --- |
| 1 | Initial Jobless Claims | 180 / ICSA raw / ★★ | SCREENSHOT_VERIFIED; rozbieżność |
| 2 | Nonfarm Payrolls | 50 / PAYEMS monthly_change / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 3 | Unemployment Rate | 50 / UNRATE raw / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 4 | Average Hourly Earnings m/m | 50 / CES0500000003 mom / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 5 | ADP Nonfarm Employment Change | adp_monthly, własny monthly ID / ★★★ | SCREENSHOT_VERIFIED; zgodne, liczby zablokowane prawami, nie zastępować PAYEMS |
| 6 | JOLTS Job Openings | 192 / JTSJOL raw / ★★ | SCREENSHOT_VERIFIED; rozbieżność; daty 1 i 29 IX nie są dwoma rodzajami |
| 7 | CPI m/m | 10 / CPIAUCSL mom / ★★★ | SCREENSHOT_VERIFIED; zgodne na poziomie miary |
| 8 | CPI y/y | 10 / CPIAUCSL yoy / ★★★ | AMBIGUOUS_VARIANT: rodzina pasuje, ale transkrypcja nie potwierdza SA/NSA wariantu Investing |
| 9 | Core CPI m/m | 10 / CPILFESL mom / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 10 | PPI m/m | 46 / PPIFIS mom / ★★ | SCREENSHOT_VERIFIED; rozbieżność; nie rozciągać referencji na pozostałe core/NSA |
| 11 | Core PCE m/m | 54 / PCEPILFE mom / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 12 | Core PCE y/y | 54 / PCEPILFE yoy / ★★★ | SCREENSHOT_VERIFIED; zgodne; nie Headline PCE |
| 13 | ISM Manufacturing PMI | ism_report / ISM_MANUFACTURING_PMI raw / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 14 | ISM Services PMI | ism_report / ISM_SERVICES_PMI raw / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 15 | S&P Global Manufacturing PMI | brak integracji | NOT_SUPPORTED; flash/final nieustalone per rekord |
| 16 | S&P Global Services PMI | brak integracji | NOT_SUPPORTED; flash/final nieustalone per rekord |
| 17 | Philadelphia Fed Manufacturing Index | brak integracji | NOT_SUPPORTED; nie NYFED_EMPIRE_GACDISA |
| 18 | Retail Sales m/m | 9 / RSAFS mom / ★★ | SCREENSHOT_VERIFIED; rozbieżność |
| 19 | Core Retail Sales m/m | 9 / kandydat RSFSXMV mom / ★★ | AMBIGUOUS_VARIANT: sam tytuł Core nie potwierdza wyłączeń; sprawdzić ex Autos vs Control Group |
| 20 | Conference Board Consumer Confidence | brak integracji | NOT_SUPPORTED; nie Michigan |
| 21 | GDP q/q | 53 / GDPC1 qoq_annualized / ★★★ | SCREENSHOT_VERIFIED na poziomie rodziny i dat; Third Q2 30 IX, Advance Q3 29 X |
| 22 | Federal Funds Rate Decision | fomc_decision / DFEDTARL/DFEDTARU target_range / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 23 | FOMC Statement | dokument powiązany z fomc_decision, brak osobnego event_type | AMBIGUOUS_VARIANT / częściowe pokrycie; brak osobnego ratingu Statement |
| 24 | FOMC Press Conference | fomc_press_conference / ★★★ | SCREENSHOT_VERIFIED; zgodne |
| 25 | FOMC Meeting Minutes | fomc_minutes / ★★ | SCREENSHOT_VERIFIED; rozbieżność |
| 26 | FOMC Economic Projections / SEP | fomc_sep / ★★★ | SCREENSHOT_VERIFIED; zgodne; tylko potwierdzone spotkania |
| 27 | Existing Home Sales | brak integracji NAR | NOT_SUPPORTED; nie New Residential Sales |
| 28 | New Home Sales | 97 / HSN1F raw / ★★ | SCREENSHOT_VERIFIED; rozbieżność |
| 29 | Crude Oil Inventories | brak integracji | NOT_SUPPORTED; wydawcę i definicję EIA/API trzeba potwierdzić |
| 30 | Wybrane wystąpienia Fed, w transkrypcji np. „Warsh” | brak kalendarza przemówień | NOT_SUPPORTED; nazwisko nie ustala funkcji, tożsamości ani wpływu |
| 31 | Wybrane przemówienia prezydenta USA | brak integracji | NOT_SUPPORTED; brak automatycznego ratingu politycznych przemówień |

CPI r/r nie jest „brakiem obsługi CPI”. Własna implementacja istnieje,
ale nie potwierdzono pełnej równoważności metodologicznej z obrazem.
[BLS rozróżnia SA i NSA](https://www.bls.gov/cpi/seasonal-adjustment/);
etykieta y/y sama tego nie rozstrzyga. Nie orzekamy tutaj, jakiego szeregu
używa Investing w konkretnym wierszu. Liczenie mniej konserwatywne,
po samej rodzinie, dałoby 22 pokryte pozycje, lecz nie oznaczałoby
22 jednoznacznych dopasowań metodologicznych. Analogicznie #19 wymaga
potwierdzenia, czy „Core” oznacza wyłącznie ex Autos. Trzecia pozycja
manual review to Statement; nie pominięto osobnego ratingu już istniejącego
eventu — taki event po prostu nie istnieje.

Święto Pracy nie weszło do 31 pozycji ani do rekomendowanych trzech gwiazdek.

## 7. Warianty, wspólne raporty i rewizje

### Event nie jest tym samym co measure

API przypisuje jeden importance całej publikacji. AgendaRow powtarza go
dla wszystkich jej miar. NFP, bezrobocie i płace nie są trzema odrębnymi
eventami 50, choć mają trzy pozycje referencyjne. Pozostałe miary Employment
(np. uczestnictwo, U-6 i godziny) dziedziczą obecnie ★★★, bez własnego
potwierdzenia screenshot.

CPI ma headline/core i m/m/y/y. Core CPI y/y nie ma własnej pozycji
w dostarczonej referencji. PIO 54 ma sześć miar: PCEPI mom,
PCEPILFE mom/yoy, DSPIC96 mom, PCEC96 mom i PSAVERT raw; screenshot
potwierdza wyłącznie dwa Core PCE. Nie przypisuje się pozostałym oceny
Investing tylko dlatego, że wspólny event MacroLens ma ★★★.

Retail 9 ma headline RSAFS, ex Autos RSFSXMV i własny RETAIL_CONTROL.
W MacroLens ex Autos obejmuje wyłączenie pojazdów/części; Control Group dodatkowo
wyłącza paliwa, materiały budowlane i gastronomię, z jawnie kontrolowanych
wejść. Bez opisu wyłączeń transkrypcja #19 nie jest jednoznacznym dowodem
dopasowania ani do ex Autos, ani do Control Group. Typowym kandydatem jest
RSFSXMV; nie zatwierdzamy tego wyłącznie po słowie „Core”. Rodzina Retail
pozostaje pewnie dopasowana dzięki headline #18.
PPI ma trzy miesięczne miary oraz niezależny kontekst NSA y/y;
ich połączenie wierszy nie tworzy osobnych ratingów.

Claims obejmuje ICSA i CCSA z innymi tygodniami. Referencja #1 nie dowodzi,
że Investing przypisał trzy gwiazdki Continuing Claims.

### GDP i oddzielne etapy

Zachowany oficjalny harmonogram w read_evidence oraz
[komunikat 30.09 — Third Q2](https://www.bea.gov/news/2026/gdp-third-estimate-industries-corporate-profits-state-gdp-and-state-personal-income-2nd)
i [29.10 — Advance Q3](https://www.bea.gov/news/2026/gdp-advance-estimate-3rd-quarter-2026)
potwierdzają te etapy niezależnie od litery „P” w transkrypcji.
Miara MacroLens to realny GDP q/q **SAAR**, nie nominalny poziom lub
nieannualizowane tempo q/q. Do audytu gwiazdek nie importowano wartości.

Obecne gwiazdki **nie rozróżniają** advance/second/third/updated: wszystkie
dziedziczą high + regułę gdp = ★★★. Identyfikatory dowodów i etapów są
natomiast odrębne. Komunikat z 30 IX obejmuje także annual update; nie wolno
uznać go za mało istotny tylko dlatego, że jest Third.
Rutynowa rewizja i duża przebudowa roczna wymagają jawnych metadanych,
nie ratingu zmienianego po poznaniu liczby.

Analogicznie rozróżnia się M3 advance/full, pozwolenia initial/revised_permits,
Michigan preliminary/final, a w przyszłości PMI flash/final.
G.17 annual_revision już jest osobnym eventem bez miesięcznej liczby.

### FOMC

Istnieją oddzielne Decision, Press Conference, Minutes i SEP.
Statement jest własnym dokumentem polityki powiązanym z decyzją, lecz nie
piątym event_type; nie należy raportować pięciu zaimplementowanych eventów.
[Oficjalny kalendarz Fed](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
wiąże dokumenty i oznacza posiedzenia z projekcjami.
Ewentualne oddzielenie Statement w przyszłości wymaga decyzji produktowej
o unikaniu dwóch wierszy tego samego komunikatu, a nie powielenia ID.

## 8. Centralna tabela rekomendacji

Propozycje są redakcyjnymi decyzjami ex ante dla obserwacji S&P 500/Nasdaq.
Nie są zweryfikowaną empirycznie siłą reakcji. ★★★ może oznaczać kanał
inflacji, rynku pracy, stóp, wzrostu lub komunikacji; nie gwarantuje ruchu.
Rozmiar Actual i późniejsza reakcja ceny nie ustalają ratingu.

| Event MacroLens | Event type / release ID | Obecne gwiazdki | Investing ze screena | Proponowane | Pewność | Powód |
| --- | --- | --- | --- | --- | --- | --- |
| Advance Monthly Sales for Retail and Food Services | — / 9 | ★★ | SCREENSHOT_VERIFIED #18; AMBIGUOUS_VARIANT #19 | ★★★ | A / wysoka dla raportu | Headline opisuje popyt konsumpcyjny; kanał przychodów i oczekiwań wzrostu. Dopasowanie Core do ex Autos wymaga potwierdzenia wyłączeń. |
| Consumer Price Index | — / 10 | ★★★ | SCREENSHOT_VERIFIED #7,9; AMBIGUOUS_VARIANT #8 | ★★★ | utrzymać / wysoka dla raportu | Kanał inflacji i dyskonta; rating raportu nie rozstrzyga SA/NSA ani ważności każdej miary. |
| Employment Cost Index | — / 11 | ★★ | NOT_IN_SCREENSHOTS | ★★★? | B / średnia | Koszt pracy i presja płacowa jako wejście oczekiwań stóp; propozycja własna, bez referencji screenshot. |
| G.17 Industrial Production and Capacity Utilization | — / 13 | ★★ | NOT_IN_SCREENSHOTS | ★★ | utrzymać / średnia | Miesięczna aktywność przemysłowa, szerszy GDP ma inny zakres. |
| H.15 Selected Interest Rates | — / 18 | ★ | NOT_IN_SCREENSHOTS | ★ | utrzymać / wysoka | Rutynowe serie stóp/yieldów, nie nowa decyzja Fed. |
| New Residential Construction | — / 27 | ★★ | NOT_IN_SCREENSHOTS | ★★ | utrzymać / średnia | Mieszkaniówka i finansowanie, starty i pozwolenia to miary jednego raportu. |
| Producer Price Index | — / 46 | ★★ | SCREENSHOT_VERIFIED #10 tylko headline m/m | ★★★? | B / średnia | Koszty/ceny producentów i kanał oczekiwań inflacyjnych; nie kopiować trójki na każdy core i roczny wariant. |
| Employment Situation | — / 50 | ★★★ | SCREENSHOT_VERIFIED #2–4 | ★★★ | utrzymać / wysoka | Zatrudnienie, płace i bezrobocie w jednym raporcie; identyfikatory miar odrębne. |
| Gross Domestic Product | — / 53 | ★★★ | SCREENSHOT_VERIFIED #21 | Advance ★★★; pozostałe wg tabeli B | utrzymać/report stage B | Wzrost i stopy; pierwsza estymacja i kolejne rewizje nie są tym samym newsem. Roczny update może uzasadniać ★★★. |
| Personal Income and Outlays | — / 54 | ★★★ | SCREENSHOT_VERIFIED #11–12 tylko Core | ★★★ dla raportu | utrzymać / wysoka dla Core | Core inflacja i kanał Fed; headline PCE, real PCE, DPI oraz saving rate nie mają automatycznej referencji Investing. |
| Manufacturer's Shipments, Inventories, and Orders (M3) Survey | — / 95 | ★★ | NOT_IN_SCREENSHOTS | ★★ | utrzymać / średnia | Inwestycje i sektor przemysłu; advance i full M3 wymagają oddzielnego traktowania czasu i rewizji. |
| New Residential Sales | — / 97 | ★★ | SCREENSHOT_VERIFIED #28 | ★★ | B / średnia | Sygnał sektorowy; własna skala szerokich indeksów może świadomie pozostać poniżej referencji. |
| Unemployment Insurance Weekly Claims Report | — / 180 | ★★ | SCREENSHOT_VERIFIED #1 tylko Initial | ★★★? dla raportu | B / średnia | Szybki tygodniowy sygnał rynku pracy; szum i rewizje uzasadniają osobną decyzję. Continuing ma inną referencję tygodnia. |
| Primary Mortgage Market Survey | — / 190 | ★★ | NOT_IN_SCREENSHOTS | ★★ | utrzymać / średnia | Finansowanie mieszkalnictwa; nie to samo co komunikat FOMC. |
| Job Openings and Labor Turnover Survey | — / 192 | ★★ | SCREENSHOT_VERIFIED #6 | ★★★ | A / wysoka | Popyt na pracę i ocena napięć rynku pracy; wiarygodne dopasowanie JTSJOL. |
| Chicago Fed National Activity Index | — / 219 | ★★ | NOT_IN_SCREENSHOTS | ★★ | utrzymać / średnia | Złożony wskaźnik aktywności, dodatkowy kontekst. |
| Chicago Fed National Financial Conditions Index | — / 221 | ★★ | NOT_IN_SCREENSHOTS | ★★ | utrzymać / średnia | Warunki finansowe; rating publikacji nie jest ratingiem każdej składowej. |
| FOMC policy decision | fomc_decision / null | ★★★ | SCREENSHOT_VERIFIED #22; #23 ambiguous | ★★★ | utrzymać / wysoka | Bezpośredni kanał stóp i komunikacji Fed; statement jest dokumentem decyzji, nie odrębnym eventem. |
| FOMC Press Conference | fomc_press_conference / null | ★★★ | SCREENSHOT_VERIFIED #24 | ★★★ | utrzymać / wysoka | Nowe wyjaśnienia polityki, bez prognozy kierunku kursów. |
| Fed Economic Projections (SEP) | fomc_sep / null | ★★★ | SCREENSHOT_VERIFIED #26 | ★★★ | utrzymać / wysoka | Ścieżka oczekiwań i projekcje; oddzielny event tylko na potwierdzonych posiedzeniach. |
| FOMC Meeting Minutes | fomc_minutes / null | ★★ | SCREENSHOT_VERIFIED #25 | ★★ (opcjonalnie ★★★ po decyzji) | B / średnia | Informacja o wcześniejszym posiedzeniu; nie każdy protokół dostarcza nowego impulsu porównywalnego z decyzją. |
| ISM Manufacturing PMI | ism_report / null / ISM_MANUFACTURING_PMI | ★★★ | SCREENSHOT_VERIFIED #13 | ★★★ | utrzymać / wysoka | Krajowa ankieta aktywności, cen i zatrudnienia; odrębna od S&P Global. |
| ISM Services PMI | ism_report / null / ISM_SERVICES_PMI | ★★★ | SCREENSHOT_VERIFIED #14 | ★★★ | utrzymać / wysoka | Krajowy sektor usług i presja cenowa; odrębna od S&P Global. |
| Michigan Consumer Sentiment — Preliminary | michigan_preliminary / null | ★★★ | NOT_IN_SCREENSHOTS | ★★★ do decyzji B | B / średnia | Wczesne nastroje oraz kontekst oczekiwań inflacyjnych raportu; nie wnioskować o reakcji z samego headline sentiment. |
| Michigan Consumer Sentiment — Final | michigan_final / null | ★★ | NOT_IN_SCREENSHOTS | ★★ | B / średnia | Późniejsza estymacja; brak referencji nie dowodzi oceny Investing. |
| ADP National Employment Report | adp_monthly / null | ★★★ | SCREENSHOT_VERIFIED #5 | ★★★ do decyzji B | B / średnia | Prywatne zatrudnienie; osobne badanie, nie NFP ani gwarantowany predyktor NFP. |
| Empire State Manufacturing Survey | empire_state / null | ★★ | NOT_IN_SCREENSHOTS | ★★ | B / średnia | Regionalna ankieta NY, nie Philadelphia Fed ani krajowy PMI. |
| U.S. Trade Balance — Goods and Services | ft900 / null | ★★ | NOT_IN_SCREENSHOTS | ★★ | utrzymać / średnia | Handel i wkład do kontekstu GDP; saldo nie jest wkładem eksportu netto do realnego GDP. |
| G.17 annual revision | — / 13 | ★★ | NOT_IN_SCREENSHOTS | ★★ | utrzymać / średnia | Osobna rewizja historii, bez pojedynczego miesięcznego Actual; nie podnosić po zobaczeniu wielkości rewizji. |
| S&P Global Manufacturing PMI | brak | NOT_SUPPORTED | ★★★ #15; wariant P/flash wymaga przeglądu | po osobnym wdrożeniu flash ★★★, final ★★ do decyzji | C / brak obecnego dopasowania | Wczesna informacja o aktywności, nie podwójne ISM |
| S&P Global Services PMI | brak | NOT_SUPPORTED | ★★★ #16; wariant P/flash wymaga przeglądu | jak wyżej | C / brak obecnego dopasowania | Usługi, odrębna próba i badanie |
| Philadelphia Fed | brak | NOT_SUPPORTED | ★★★ #17 | przyszłe ★★ | C / propozycja własna | Regionalny zakres; nie kopiować narodowej skali PMI |
| Conference Board Consumer Confidence | brak | NOT_SUPPORTED | ★★★ #20 | przyszłe ★★/★★★ do osobnej decyzji | C / średnia koncepcja | Nastroje i rynek pracy, odrębne od Michigan |
| Existing Home Sales | brak | NOT_SUPPORTED | ★★★ #27 | przyszłe ★★ | C / propozycja własna | Rynek wtórny i znaczenie sektorowe |
| Crude Oil Inventories | brak | NOT_SUPPORTED | ★★★ #29 | przyszłe ★★; szczególny kontekst ręcznie | C / wydawca do ustalenia | Duży wpływ na energię nie jest automatycznie szerokim wpływem na Nasdaq |
| Wybrane wystąpienia Fed | brak | NOT_SUPPORTED | ★★★ #30 | indywidualna ocena, bez stałej trójki | C / manual review | Osoba, temat i kontekst, nie samo stanowisko |
| Przemówienia prezydenta | brak | NOT_SUPPORTED | ★★★ #31 | indywidualna ocena | C / manual review | Szeroki temat polityczny nie definiuje jednorodnej publikacji |
| FOMC Statement osobno | dokument decyzji, brak osobnego event ID | osobnego ratingu brak | ★★★ #23 | bez automatycznego dodania duplikatu | AMBIGUOUS_VARIANT | Powiązanie z decyzją istnieje, oddzielny wiersz wymaga uzgodnienia modelu |

Pierwsze 29 wierszy odpowiada inwentarzowi. Końcowe 9 są wierszami
porównawczymi braków/niejednoznaczności, nie dziewięcioma nowymi eventami.

### A — dwie zmiany z wysokim przekonaniem

1. **Retail Sales: ★★ → ★★★**, raport 9 z pewnym dopasowaniem headline
   #18; wariant #19 wymaga manual review. Popyt konsumenta jest istotnym kanałem przychodów
   i wzrostu; jest to własne uzasadnienie redakcyjne, nie dowód siły reakcji.
   Nie nadaje automatycznie osobnej oceny referencyjnej Control Group.
2. **JOLTS: ★★ → ★★★**, 192/JTSJOL (#6). Raport o popycie na pracę
   wspiera ocenę napięcia rynku pracy i oczekiwań polityki pieniężnej.
   K2 musi osobno zdecydować, czy dodać go do kwalifikacji Overview.

### B — 12 decyzji, bez automatycznej implementacji

| Przypadek | Obecnie | Bazowa propozycja do zatwierdzenia | Dlaczego wymaga decyzji |
| --- | --- | --- | --- |
| B1 Initial Claims / raport 180 | ★★, backend high | ★★★ | Szybkość sygnału kontra szum tygodniowy; ustalić dziedziczenie CCSA |
| B2 PPI / raport 46 | ★★ | ★★★ dla raportu | Inflacja wejściowa i kanał stóp; brak referencji wszystkich core i y/y |
| B3 FOMC Minutes | ★★ | pozostawić ★★ | Starsze posiedzenie, kontekst może podnieść potencjalne znaczenie; screenshot ma ★★★ |
| B4 GDP Second | ★★★ | rutynowy Second ★★ | Mniej nowej informacji niż Advance, bez empirycznej kalibracji |
| B5 GDP Third | ★★★ | zachować ★★★ do rozróżnienia routine/annual | 30 IX zawiera annual update; samo „Third” nie wystarcza do obniżenia |
| B6 GDP Updated | ★★★ | ★★ po ręcznym ustaleniu zakresu | Updated nie jest nowym kwartałem; zachować wyjątki przy szerszej rewizji |
| B7 ADP | ★★★ | zachować ★★★ | Jasna referencja, lecz osobna metodologia i ograniczenia liczb; nie traktować jako NFP |
| B8 Michigan Preliminary | ★★★ | zachować ★★★ do decyzji | Wczesny raport i kontekst oczekiwań inflacyjnych, bez screenshot referencji |
| B9 Michigan Final | ★★ | zachować ★★ | Final jest późniejszym wariantem, bez dowodu oceny Investing |
| B10 New Home Sales | ★★ | zachować ★★ | Sektorowe znaczenie, mimo ★★★ w referencji |
| B11 Empire State | ★★ | zachować ★★ | Regionalna ankieta NY; nie Philadelphia i nie krajowy PMI |
| B12 ECI | ★★ | rozważyć ★★★ | Koszt pracy i inflacja; propozycja wyłącznie własna, NOT_IN_SCREENSHOTS |

Pozostawienie ★★ przy Minutes/New Home Sales jest świadomą propozycją
własnej skali, nie twierdzeniem, że użytkownik błędnie odczytał Investing.
Dla ECI nie przedstawiamy referencji, której nie dostarczono.
Philadelphia, Conference Board i Existing Home Sales wymagają analogicznej
decyzji dopiero w osobnej pracy pokrycia C; nie są obecnymi zmianami K2.

## 9. Braki pokrycia i sprawdzone źródła

Brak w tym inwentarzu oznacza brak aktywnej, zweryfikowanej integracji
kalendarzowej MacroLens, a nie nieistnienie oficjalnych danych.
Nie korzystano z kont subskrypcyjnych, kluczy lub prób obejścia ograniczeń.

| Pozycja | Wydawca / rodzaj | Oficjalne źródło | Integracja teraz / kalendarz | Actual/Previous i uprawnienia | Tylko harmonogram? | Potencjalna wartość dla indeksów |
| --- | --- | --- | --- | --- | --- | --- |
| S&P Manufacturing | S&P Global, PMI przemysłu | [FAQ](https://www.spglobal.com/market-intelligence/en/solutions/products/resources/pmi-faq), [kalendarz](https://pmi.spglobal.com/Public/Release/ReleaseDates) | brak; kalendarz wskazany publicznie, bezpośredni odczyt kalendarza w K1 się nie udał | FAQ potwierdza komunikaty i dostęp subskrypcyjny; nie potwierdzono licencji magazynu/redystrybucji | kandydat po zweryfikowaniu konkretnych wierszy i warunków | wczesna aktywność/ceny/zatrudnienie |
| S&P Services | S&P Global, PMI usług | te same własne źródła | brak; flash/final muszą dostać osobne tożsamości | jak wyżej; nie pożyczać danych ISM | jak wyżej | duży zakres sektora usług |
| Philadelphia Fed | Philadelphia Fed, MBOS Current General Activity | [badanie](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/manufacturing-business-outlook-survey), [daty](https://www.philadelphiafed.org/calendar-of-events?release=manufacturing-business-outlook-survey) | brak; publiczny kalendarz i archiwum potwierdzone | dostępne raporty; praw automatycznego zapisu/dystrybucji nie rozstrzygnięto; nie jest to prawna pochodna warunków NY Fed | techniczny kandydat; warunki do kontroli | regionalny sygnał wyprzedzający, baza ★★ |
| Conference Board | The Conference Board / Consumer Confidence | [strona badania](https://www.conference-board.org/topics/consumer-confidence/), [dane](https://www.conference-board.org/data/consumerconfidence.cfm) | brak; wyszukiwarka oficjalnej strony potwierdza komunikaty i termin kolejnego wydania, bezpośrednie odczyty timeout | publikowane headline i odsyłacze subskrypcji; brak potwierdzenia licencji i kompletnego feedu | możliwe po weryfikacji dat i warunków, nie wdrożono | nastroje i ocena rynku pracy |
| Existing Home Sales | NAR, rynek wtórny | [dane](https://www.nar.realtor/research-and-statistics/housing-statistics/existing-home-sales), [kalendarz](https://www.nar.realtor/press-releases/nar-statistical-news-release-schedule) | brak; oficjalne daty dostępne | NAR jawnie ogranicza m.in. przechowywanie/redistribucję przez nieczłonków bez uprzedniej zgody; dostęp strony nie daje licencji importerowi | osobna ocena praw; harmonogram nie oznacza zgody na liczby | głównie mieszkaniówka i kanał stóp |
| Crude Oil Inventories | kandydat EIA, WPSR; API to inny wydawca | [WPSR](https://www.eia.gov/petroleum/supply/weekly/), [harmonogram](https://www.eia.gov/petroleum/supply/weekly/schedule.php), [reuse](https://www.eia.gov/about/copyrights_reuse.php) | brak; kalendarz wyjątków i formaty tabel dostępne | EIA dopuszcza użycie własnych danych z atrybucją i wyjątkami dla cudzych materiałów/logo; właściwa definicja stocks/change i zakres bez SPR do sprawdzenia | dobry kandydat EIA, po potwierdzeniu tożsamości #29 | duży sygnał energii, nie automatyczne ★★★ szerokich indeksów |
| Wybrane wystąpienia Fed | Board i regionalne banki, wydarzenia tekstowe | [kalendarz Fed](https://www.federalreserve.gov/newsevents/calendar.htm) | brak; publiczne miesiące kalendarza dostępne, nie scentralizowana gwarancja kompletności wszystkich mówców | Actual/Previous zwykle nie dotyczy; treści i uprawnienia badać osobno | technicznie możliwe dla potwierdzonych dat; ręczna selekcja | zależy od mandatu, tematu i niespodziewanej komunikacji |
| Przemówienia prezydenta | White House, komunikacja polityczna | [Briefings & Statements](https://www.whitehouse.gov/briefings-statements/) | brak; strona komunikatów istnieje, kompletnego strukturalnego kalendarza przyszłych wystąpień nie potwierdzono | brak jednorodnych liczbowych Actual/Previous; nie przenosić praw całej strony na każdy materiał | nie obiecywać kompletności; tylko niezależnie potwierdzone wydarzenia | warunkowo wysoka, bez reguły każdego wystąpienia |

S&P FAQ odróżnia [flash od final](https://www.spglobal.com/market-intelligence/en/solutions/products/resources/pmi-faq).
To nie kolejna nazwa ISM. W przyszłości trzeba osobno ocenić Manufacturing
Flash, Manufacturing Final, Services Flash, Services Final i ewentualny
Composite. Composite nie jest dodatkową pozycją transkrypcji K1.
Nie potwierdzono tu operacyjnego feedu ani dostępu produkcyjnego do liczb.

## 10. Skutki przyszłej zmiany dla interfejsu

- **Calendar:** filtr i render używają wspólnego eventImportanceStars.
  Podniesienie eventu z 2 do 3 przeniesie wszystkie jego miary do ★★★.
  Domyślny filtr obejmuje 2+3, więc taki event już teraz jest widoczny;
  istotna różnica dotyczy „Tylko ★★★”. Włączenie go ustawia dokładnie
  {3}; wyłączenie wraca do {2,3}, nie przywraca uprzedniej kombinacji.
  „Wyczyść filtry” daje {1,2,3} oraz unknown.
- **Kategorie i liczniki:** kategorie wynikają z serii i wyjątków typów,
  nie z gwiazdek. PIO może należeć jednocześnie do activity i inflation.
  Rating nie powinien zmieniać kategorii. W bieżącym panelu nie ma osobnych
  badge liczników kategorii/gwiazdek. Każdy przyszły licznik musi rozróżnić
  eventy i wiersze miar; jeden Employment/CPI nie może być policzony kilka
  razy jako oddzielna publikacja tylko przez liczbę wierszy.
- **Overview:** najpierw odrzucane są wydarzenia spoza tablicy 17,
  potem sortuje się po **indeksie reguły w tablicy**, wybiera cztery,
  a dopiero na końcu sortuje chronologicznie. Ani high API, ani podniesienie
  wyniku eventImportanceStars nie dodają automatycznie eventu do top czterech.
  Nawet zmiana Tracked na Key bez przesunięcia reguły nie zmienia indeksu.
  JOLTS i PPI nie są dziś kwalifikowane do tego wyboru.
- **Chronologia i równoczesność:** Calendar groupAgenda porządkuje po dniu,
  chwili i nazwie, bez skutecznych gwiazdek. Backend ma osobne sortowanie
  po dniu, importance i nazwie, lecz UI i tak grupuje ponownie.
  Przyszła zmiana backendowego importance może zmienić kolejność surowego API
  i klientów korzystających z niego bez groupAgenda; równoczesnych publikacji
  nie należy scalać tylko dlatego, że mają ten sam czas.
- **PL/EN:** rating ma być niezależny od tłumaczenia. Obecne dokładne nazwy
  EN są kruchym kluczem; etykiety measure nie zastępują ID. Nie trzeba
  modyfikować tekstów ekonomicznych, jednostek lub liczb, aby zmienić rating.
- **Markdown:** upcomingEventReport i eventImportanceNote zawierają
  Key/Tracked i opis skali, nie tylko ikonki. briefModel:205 przekazuje
  tę notę do eksportu. K2 musi zaktualizować opis prawdziwej polityki,
  a nie zostawić historyczne zdanie „Claims/Retail = 2”.
- **Tożsamość:** dla generycznych wydarzeń eventIdentity używa obecnie
  eventPriority.key, jeśli rozpozna alias. Dodanie reguły JOLTS/PPI może
  więc zmienić UI key z release_id na klucz redakcyjny, mimo niezmienionego
  event_id API. Trzeba oddzielić trwałą tożsamość od ratingu/rankingu.
  Dedykowane identyfikatory miesięczne i FOMC nie powinny się zmieniać.
- **Historia:** zmiana czystej funkcji natychmiast przeliczy gwiazdki także
  dla dawnych dat. Bez wersji polityki nie jest to historyczny rating „jak
  oceniano wtedy”. Nowe daty i stare obserwacje nie wymagają przepisywania
  wartości; trzeba jawnie wybrać prezentację aktualnej polityki dla historii
  albo wersjonowany rating as-of. Nie zmieniać Actual/vintage.
- **Bieżące lokalne UI:** osobna odległa decyzja FOMC została wcześniej
  usunięta z ekranu Overview na zlecenie użytkownika; nextFomc nadal istnieje
  w modelu/eksporcie. Ta wcześniejsza poprawka nie jest zmianą gwiazdek K1.

## 11. Propozycja jednego źródła prawdy

Docelowo jedna **wersjonowana polityka MacroLens**, rozpoznawana po
kanonicznych release_id / event_type / source-series-kind / estimate_stage,
z opcjonalnym zakresem miary series_id + feature_name.
Wydawca dokumentu i metodologia są częścią tożsamości: nie wolno mapować
Philly → Empire, S&P → ISM, ADP → PAYEMS, Existing → New Home Sales.

Rekomendowana przyszła architektura:

1. Backend rozstrzyga rating w jednym miejscu i zwraca addytywne
   market-impact metadata: stars/unknown, policy_version, rule_id,
   rationale i zakres event/measure. Nie usuwać bez migracyjnego kontraktu
   dotychczasowego importance ani nie nazywać go „ratingiem wydawcy”.
2. Frontend renderuje i filtruje wynik; nie przelicza go drugim zbiorem
   aliasów. Jeżeli trzeba zachować tryb offline, wspólny wygenerowany
   artefakt polityki może zastąpić dwa ręcznie utrzymywane źródła.
3. **Zostawić oddzielny ranking top czterech**, lecz nazwać go wprost
   overview_rank/eligibility i oprzeć na tych samych kanonicznych ID.
   Ocena wpływu i ograniczenie miejsca to różne cele. Zatwierdzić osobno,
   czy rank wprowadza JOLTS/PPI i które wydarzenia wtedy wypiera.
4. Najpierw wdrożyć zgodne z decyzją ratingi **event-level**. Jeżeli
   gwiazdki mają opisywać pojedynczy wiersz, potrzebne są jawne override
   measure-level i oznaczenie inherited. Nie symulować tej precyzji
   przez kopiowanie jednej oceny na miary, których screen nie obejmował.
5. Zachować event_id i rozdzielić jego budowę od ratingu. Zdecydować
   o wersjonowaniu historycznych ratingów; dodać testy retrospektywne.
   Rewizja liczby nie zmienia ratingu według wielkości niespodzianki.
6. Unknown powinien oznaczać brak dopasowania, nie automatyczne medium
   o pozornej pewności. Ewentualny legacy fallback musi być jawnie opisany.

To plan, nie nowa konfiguracja. Nie dodano tych pól API, generatora,
migracji lub wspólnego modułu w K1.

## 12. Testy do późniejszej aktualizacji K2

Odczytano istniejące testy, nie uruchamiano pełnych zestawów dla dokumentu:

- frontend/src/brief/upcomingEvents.test.ts:23–65, 68–95, 121–130:
  FOMC [3,3,2], oba ISM, Michigan [3,2], Empire 2, ADP 3, cztery sloty,
  odrzucenie nieznanych high, parametr każdej reguły i fallback unknown.
  Zmiana labelu reguły bez osobnej asercji celu rynkowego może dać
  pozornie poprawny test — trzeba dodać jawne oczekiwania dla ID.
- frontend/src/calendar/CalendarPage.test.tsx:134,166–204:
  nonnumeric Fed, domyślne filtry, „Tylko ★★★”, lokalność filtrów,
  te same gwiazdki dla miar i równoczesność. Retail ma trzy miary w jednym
  raporcie; testy PPI sprawdzają trzy wiersze z kontekstem NSA.
- frontend/src/brief/EconomyBrief.test.tsx: zdarzenia kompaktowe, aria-label
  Importance, cztery wiersze, eksport noty i prawa. Nie przywracać długich
  opisów usuniętych wcześniej z ekranu tylko dla testu ratingu.
- tests/test_release_calendar.py:84,147,223,277:
  mapowanie nazw importance, sortowanie API, serialization i pomijanie 101.
- tests/test_fomc_calendar.py, test_ism_calendar.py,
  test_michigan_calendar.py, test_adp_calendar.py oraz test_empire_state.py
  i test_ft900.py: backendowe klasy i oddzielne tożsamości adapterów.
- tests/test_calendar_agenda.py, test_calendar_key_publications.py,
  test_calendar_periods.py, test_calendar_core_ppi.py,
  test_calendar_retail_measures.py i test_calendar_employment_measures.py:
  brak mnożenia eventów przez miary, poprawne okresy i etapy.

K2 powinno dodać porównanie API/Calendar/Overview/Markdown dla 29 rodzajów,
wariantów GDP i dziedziczenia miar, testy ID po zmianie reguły, nazw EN/PL,
braku konsensusu, niezmienności R1/R2/R3 oraz ratingu niezależnego od Actual.
Nie aktualizować snapshotów bez uzasadnienia zmiany oczekiwanego zachowania.
Bieżące wnioski opierają się na kodzie i czystych funkcjach, nie na nowym
przebiegu Chrome albo testach e2e.

## 13. Plan decyzji i późniejszego K2

1. Zatwierdzić skalę ex ante, grupę A i konkretne odpowiedzi B1–B12.
2. Uzgodnić event vs measure oraz los osobnego FOMC Statement.
3. Osobno uzgodnić ranking Overview i politykę historyczną.
4. Dopiero w osobnym zleceniu K2 centralizować klasyfikację i testy;
   utrzymać cztery sloty, wszystkie identyfikatory i metody ekonomiczne.
5. Braki C pozostawić jako backlog osobnych integracji ze źródłami,
   prawami, harmonogramami i provenance. Nie dodawać ich samym ratingiem.

Trzy gwiazdki nie gwarantują ruchu: liczą się oczekiwania, kontekst i
niespodzianka. Nie integrowano Forecast/consensus ani serwisu Investing.
Nie przewiduje się kierunku ceny z samych gwiazdek.

## 14. Końcowa ochrona i Git

Porównano SHA-256 przed i po K1. „Identyczny” odnosi się do faktycznego
stanu wejściowego K1; rozbieżność historycznego styles.css opisana w sekcji 2.

| Plik chroniony | SHA-256 przy wejściu K1 | Po K1 |
| --- | --- | --- |
| README.md | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` | identyczny |
| frontend/src/brief/SourceCheckStatus.tsx | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` | identyczny |
| frontend/src/brief/SourceCheckStatus.test.tsx | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` | identyczny |
| frontend/src/styles.css | `40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c` | identyczny |
| docs/audits/calendar-next-releases-priority-2026-10-29.md | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` | identyczny |
| docs/audits/calendar-release-day-latency-2026-10-29.md | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` | identyczny |

Zachowano również pozostałe pięć wcześniej zmienionych plików kodu/testów
(EconomyBrief, CalendarPage i calendarAgenda) byte-identycznie.
Jedynym nowym plikiem K1 jest ten dokument. Końcowo **9 modified / 3 untracked**,
staging pusty, HEAD/main bez zmian:

```text
 M README.md
 M frontend/src/brief/EconomyBrief.test.tsx
 M frontend/src/brief/EconomyBrief.tsx
 M frontend/src/brief/SourceCheckStatus.test.tsx
 M frontend/src/brief/SourceCheckStatus.tsx
 M frontend/src/calendar/CalendarPage.test.tsx
 M frontend/src/calendar/CalendarPage.tsx
 M frontend/src/calendar/calendarAgenda.ts
 M frontend/src/styles.css
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
?? docs/audits/calendar-release-day-latency-2026-10-29.md
?? docs/audits/calendar-event-impact-audit-2026-10-30.md
```

Nie zmieniono logiki, testów, konfiguracji, gwiazdek, PostgreSQL, obserwacji,
RAW/cache, odświeżania lub polityk R1/R2/R3. Nie uruchamiano migracji, DDL,
ingestion, backfillu, POST refresh, inicjalizatora lub nowego CI.
Nie dodano pomocniczych skryptów do repozytorium. Nie uruchamiano pełnego
backend/frontend/build dla samego raportu i nie przypisano mu dawnych wyników.
Bez stagingu, commita, pusha, resetu, clean, amend albo zmiany historii.

