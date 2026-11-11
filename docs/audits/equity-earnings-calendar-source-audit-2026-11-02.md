# MacroLens — E1: audyt źródeł kalendarza wyników spółek

Audyt **02.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`.
`main`, HEAD **`14e4829d79f3f4f0916629a560cfc0cf2a122836`** —
`Unify economic calendar impact ratings`.

**Wyłącznie badanie źródeł, odczyt repozytorium i ten raport.**
Bez implementacji, zmian kalendarza, SQL/DDL, ingestion, backfillu,
stagingu, commita i pusha. Nie rozpoczęto E2. Nie uruchamiano aplikacji,
koordynatora, przeglądarkowego UI lub testów integracyjnych. Nie łączono
się z bazą użytkownika: odczyt schematu i kodu wystarczył do projektu.

## 1. Rekomendacja i granice dowodu

**E2 jest technicznie wykonalne, lecz nie ma jeszcze gotowego feedu
produkcyjnego ani potwierdzonej licencji całego rozwiązania.** Zalecam
osobny model earnings i wspólną warstwę prezentacji Calendar. Najpierw
E2A: potwierdzenia terminów i odnośniki; następnie E2B: oficjalne revenue
i GAAP diluted EPS; dopiero E2C: adjusted EPS, segmenty, guidance i kolejne
spółki. Każdy etap wymaga osobnego zlecenia i bramek opisanych dalej.

Oficjalne IR i SEC zawierają daty oraz minimalne wyniki trzech pilotów.
Nie dostarczają jednak automatycznie przyszłej daty każdego kwartału,
godziny pierwszej dostępności, jednolitego adjusted EPS ani licencjonowanego
konsensusu. Brak daty pozostaje poprawnym wynikiem audytu, a nie luką do
wypełnienia przewidywaniem. SEC nie może być jedynym źródłem planowanych
terminów i nie trzeba czekać na 10-Q, jeżeli poprawny release jest już dostępny.

Badanie obejmowało oficjalne strony IR, sześć historycznych komunikatów,
zapowiedzi, wybrane powiązane dokumenty SEC, dokumentację API i warunki
użycia. Wszystkie źródła w raporcie sprawdzano **02.11.2026**.
Odczyt przeglądarkowym narzędziem badawczym może korzystać z indeksowanej
reprezentacji strony; nie jest dowodem ciągłej dostępności endpointu HTTP.
Wyniki wyszukiwarki służyły odnajdywaniu oryginałów. Nie użyto agregatora
jako jedynego dowodu liczb, nie korzystano z Investing ani płatnego konta.

Osobna, sekwencyjna próba zwykłego HTTP w pamięci dała:

| Publiczny zasób | Faktyczny wynik tej próby |
| --- | --- |
| `investor.nvidia.com/rss/Event.aspx?LanguageId=1` | HTTP 403; wcześniejsze narzędzie WWW nie obsłużyło XML RSS |
| `data.sec.gov/submissions/CIK0001045810.json` | HTTP 403 |
| `data.sec.gov/submissions/CIK0001018724.json` | HTTP 403 |
| `data.sec.gov/submissions/CIK0000050863.json` | HTTP 403 |

Użyto identyfikatora `MacroLens-E1-Audit/0.1` z adresem publicznego
repozytorium jako kontaktem, odstępu co najmniej sekundy i jednego klienta.
Nie używano fikcyjnego adresu e-mail, logowania lub sekretów. Nie ustalono
przyczyny 403; nie uznano jej za dowód braku publicznego API. Nie zmieniano
User-Agent w celu obchodzenia blokady, nie rotowano IP i nie ponawiano
tych prób. Company Facts nie pobierano po odmowach. **Działający dostęp
Submissions/Company Facts z docelowego backendu: NOT VERIFIED.**
E2 musi ustalić prawdziwy kontakt operacyjny, zgodny identyfikator klienta
i dozwolony dostęp; sam opis API nie usuwa tego warunku.

## 2. Stan repozytorium i istniejąca architektura

Początkowo **9 modified / 3 untracked**, indeks pusty; stan zgadza się
z celowo zachowanymi pracami po K2. Dwanaście SHA-256 zapisano przed
audytowaniem w kontekście sesji; końcowe porównanie jest w sekcji 17.
Nie przyjmowano wcześniejszych wyników CI za nowo uruchomione testy E1.

| Obszar i rzeczywiste pliki | Stan obecny | Wniosek dla E2 |
| --- | --- | --- |
| `app/database/schema.sql` | economic_releases ma numeryczny release_id; series_release_map wiąże serie; release_dates klucz (release_id, release_date) | Nie pasuje do tożsamości emitent/kwartał. Nie tworzyć fikcyjnych FRED release_id lub series |
| observation_vintages / computed_features / alfred_backfills | Klucze series/date/vintage i metodologia cech makro; istnieje source fred_snapshot/alfred | Nie używać dla EPS, earnings lub first print; nie zmieniać PIT/MCI |
| publisher_documents | UUID, source, kind, source_url, retrieved_at, HTTP, hash, raw_path, metadata; UNIQUE(source,kind,raw_hash); hash/path są NOT NULL | Przydatny wspólny magazyn legalnie zachowanych bajtów, ale nie wystarcza dla metadata-only i historii każdego pobrania |
| Dwa FK observation_vintages do dokumentów | source_document_id i publication_document_id; BEA wymaga zgodności obu | Powtórzyć zasadę dowodu finansowej wartości, a nie używać ekonomicznej tabeli obserwacji |
| `sync_bea_reports.py`, `calendar_evidence.py` | Receipts, RAW/hash, walidacja okresu, zmiany dokumentów; część dowodów harmonogramu pochodzi z plików derived | Wykorzystać wzorzec adaptera, idempotencji i walidacji, nie parser lub binding GDP/PCE |
| source_check_runs / `app/source_checks.py` | Trwały status kontroli, scope JSONB, attempted/finished i błąd | Można rozszerzyć przestrzeń resource o earnings; sprawdzenie źródła nie potwierdza wyniku |
| overview_refresh_state / overview_publications | source_versions JSONB, stan joba, wspólna generacja/cache Overview | Nie wkładać wartości earnings do JSON jako drugiego magazynu. Nie dopisywać earnings do 17 reguł Overview w E2A |
| `release_calendar.py` | Tracked FRED + dedykowane adaptery; kanoniczna polityka K2 przed sortowaniem | Zachować czytnik makro i jego identyfikatory |
| `calendar_agenda.py` | GET Calendar z readings: REPEATABLE READ, wiązanie wyników, zakres kontroli i data_revision; limit 366 dni | Nowy agregator musi jawnie rozdzielać pokrycie domen; nie przypisywać kontroli FRED spółkom |
| `calendar_readings.py` | SPECS per release/seria, okres poprzedni wg częstotliwości, current-vintage, specjalne BEA/ISM/FT900/Fed | Nie przepuszczać earnings przez fallback serii lub period_before |
| `app/api/main.py` | `/api/v1/calendar`, opcjonalne include_readings; `/api/v1/releases/{release_id}` | Zachować istniejący kontrakt makro; opt-in wspólny endpoint omówiono niżej |
| `frontend/src/api/macrolens.ts` | CalendarEvent wymaga release_date, series, importance, ma zamknięty event_type i makro CalendarMeasure | Potrzebna discriminated union; nie rzutować earnings na CalendarEvent z pustą sztuczną serią |
| `calendarAgenda.ts`, `calendarDates.ts` | Kategorie z serii i wyjątków; filtr gwiazdek, grupowanie po dniu/chwili/nazwie; dedupe event_id lub release_id:date; IANA Warsaw | Zachować wspólne formatowanie znanej chwili, osobno obsłużyć nieznany polski dzień earnings |
| `CalendarPage.tsx` | Zwykle osobny wiersz miary, szczegóły i source evidence, Actual/Previous/Forecast; brak czasu pokazuje kreskę | Earnings ma jeden zwarty wiersz na kwartał, finanse w szczegółach, nie dziewięć makro-podobnych wierszy |
| `calendar_market_impact.py`, `upcomingEvents.ts` | K2 `2026-11-k2-v1`: 29 rodzajów, 17/11/1; frontend czyta ocenę, ranking Overview osobny: 17 reguł / max 4 | Nie nadawać earnings tych gwiazdek; samo dopisanie event_type nie wystarcza |
| R1–R3: hook, refresh/store, bea_release_refresh, request_budget | Jeden anulowalny timer UI, hidden/focus/abort, backend deadline; wspólny lock 726530019; standard 900 s, wolne zasoby 21600 s; BEA T/+2/+5/+10/+20 i okno 30 min | Użyć kontroli współbieżności/backoff, lecz nie kopiować punktów BEA, jego tożsamości lub budżetu FRED jako gotowej polityki SEC |

Obecny `request_budget` ma deadline joba i odstęp dla **FRED**; nie jest
globalnym limiterem SEC na wiele maszyn. Zwykłe odczyty Calendar nie
pobierają dokumentów wydawców. W E2 musi pozostać taka granica.

## 3. Dowody trzech pilotów

CIK potwierdzono w oficjalnym [pliku mapowania SEC](https://www.sec.gov/files/company_tickers.json)
oraz kartach filingów poniżej: **NVDA 0001045810**, **AMZN 0001018724**,
**INTC 0000050863**. Nie wyznaczano CIK z tekstu tickera. Plik SEC jest
bieżącym mapowaniem, nie pełną historią tickerów lub klas akcji.

### 3.1 NVIDIA

[Oficjalny event Q3 FY27](https://investor.nvidia.com/events-and-presentations/events-and-presentations/event-details/2026/NVIDIA-3rd-Quarter-FY27-Financial-Results/default.aspx)
podaje **17.11.2026, 17:00 EST** i link do webcastu. To potwierdzony
termin tego wydarzenia IR; jako najwcześniejszy earnings release i jego
dokładny czas — **NOT VERIFIED**. Konwersja webcastu: 22:00 UTC,
**23:00 PL**. Nie przenosić tej godziny do pola release_published_at.
Dokładnego period_end przyszłego Q3 nie zatwierdzono samym tytułem.

[Zapowiedź Q2 z 29.07](https://nvidianews.nvidia.com/news/nvidia-sets-conference-call-for-second-quarter-financial-results-6927195/)
oddziela call 26.08 o 14:00 PT / 17:00 ET od planowanej publikacji około
13:20 PT i późniejszego komentarza CFO. To dowód dwóch zegarów, a nie
pomiar pierwszej dostępności HTTP. Ta sama godzina nie jest regułą Q3.

| Okres i źródło release | Period end / data komunikatu | Revenue, mln USD | GAAP diluted EPS, USD/share | Non-GAAP diluted EPS | Segment i guidance |
| --- | --- | ---: | ---: | ---: | --- |
| [Q1 FY2027](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-First-Quarter-Fiscal-2027/default.aspx) | 26.04.2026 / 20.05.2026 | 81615 | 2.39 | 1.87 | Data Center 75,2 mld; guidance Q2 revenue 91,0 mld ±2%, także gross margin i operating expenses |
| [Q2 FY2027](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2027) | 26.07.2026 / 26.08.2026 | 96221 | 2.46 | 2.22 | Data Center 89,0 mld; guidance Q3 revenue 108,0 mld ±2%, także gross margin i operating expenses |

Kwoty tabeli są z wiersza Revenue, nie zaokrąglonego nagłówka. Komunikaty
mają własne tabele GAAP/non-GAAP i reconciliation. FY2027 nie oznacza
„kwartał kalendarzowy 2027”; Q1 i Q2 zakończyły się w 2026. Nowy podział
platform/segmentów w Q1 wymaga zachowania nazw i wersji definicji.

SEC: [Q1 8-K, 0001045810-26-000051](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000051/0001045810-26-000051-index.htm)
z 20.05 oraz [Q2 8-K, 0001045810-26-000073](https://www.sec.gov/Archives/edgar/data/1045810/0001045810-26-000073-index.htm)
z 26.08 mają Item 2.02, EX-99.1 release i EX-99.2 CFO commentary.
[Treść Q2 8-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/nvda-20260826.htm)
wiąże dokumenty z 26.07.2026. [Q2 10-Q, 0001045810-26-000075](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/0001045810-26-000075-index.htm)
zawiera iXBRL i ten sam period_end. Indeksy podają przyjęcie 8-K o
16:21:19 i 10-Q o 16:36:00 dnia 26.08; nie są to timestampy pierwszego IR.

### 3.2 Amazon

[Zapowiedź z 15.10](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-to-Webcast-Third-Quarter-2026-Financial-Results-Conference-Call/)
potwierdza call **29.10.2026 o 14:00 PT / 17:00 ET**, czyli 21:00 UTC /
**22:00 PL**. Dokładny czas pierwszego release nie wynika z tej zapowiedzi.
Nowy przyszły oficjalny termin po Q3: **NOT VERIFIED**; nie wyliczać go z rytmu.

| Okres i źródło release | Period end / data komunikatu | Total net sales, mln USD | Diluted EPS GAAP, USD/share | AWS net sales, mln USD | Operating income i guidance |
| --- | --- | ---: | ---: | ---: | --- |
| [Q2 2026](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Second-Quarter-Results/default.aspx) | 30.06.2026 / 30.07.2026 | 200606 | 5.75 | 42232 | Operating income 27,5 mld; guidance Q3 sales 197–202 mld, operating income 22,5–26,5 mld |
| [Q3 2026](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Third-Quarter-Results/default.aspx) | 30.09.2026 / 29.10.2026 | 201944 | 1.89 | 45984 | Operating income 28,1 mld; guidance Q4 sales 240–247 mld i operating income 28,5–33,5 mld; capex FY2026 około 220 mld |

Nie znaleziono jawnej pary adjusted/non-GAAP EPS w tych komunikatach:
**NOT VERIFIED**, a nie 0 lub własne odjęcie zysków inwestycyjnych.
EPS guidance również nie potwierdzono. Non-GAAP miary cash flow lub
growth excluding FX nie są adjusted EPS. AWS to segment, nie total sales.

SEC: [Q2 8-K, 0001018724-26-000024](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000024/0001018724-26-000024-index.html)
z 30.07 i [Q3 8-K, 0001018724-26-000038](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000038/0001018724-26-000038-index.htm)
z 29.10 mają Item 2.02 i wskazują właściwe EX-99.1. [Treść Q3 8-K](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000038/amzn-20261029.htm)
i [EX-99.1](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000038/amzn-20260930xex991.htm)
są odrębnymi dokumentami jednego raportu. [Q3 10-Q, 0001018724-26-000040](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000040/amzn-20260930.htm)
potwierdza okres 30.09. Nie trzeba czekać na jego Company Facts, aby użyć
zweryfikowanego release.

### 3.3 Intel

[Zapowiedź z 06.10](https://www.intel.com/content/www/us/en/newsroom/news/corporate/intel-reports-third-quarter-2026-financial-results.html)
podaje **29.10.2026 po zamknięciu rynku** oraz osobno call **14:00 PDT**.
[Widget IR](https://www.intc.com/news-events/ir-calendar) opisuje ten call
„2:00 PM PST”, sprzecznie z IANA dla października. W tym przypadku jawne
PDT w datowanej zapowiedzi rozstrzyga na 21:00 UTC / **22:00 PL**;
surowe PST należy zachować jako konflikt źródła, nie interpretować jako −08.
Release AMC nie dostaje fikcyjnego 16:00 ET. Strona główna IR pokazuje
przy release 16:01 EDT; to deklarowany timestamp strony, nie dowód pierwszej
dostępności. Kalendarz przy odczycie nie pokazał przyszłych wydarzeń.

| Okres i źródło release | Period end / data komunikatu | Net revenue, mln USD | GAAP diluted EPS attributable to Intel | Non-GAAP diluted EPS | Guidance kolejnego kwartału |
| --- | --- | ---: | ---: | ---: | --- |
| [Q2 2026](https://www.intc.com/news-events/press-releases/detail/1776/intel-reports-second-quarter-2026-financial-results) | 27.06.2026 / 23.07.2026 | 16128 | −2.16 | 0.42 | Q3 revenue 15,8–16,8 mld; EPS GAAP 0,31 / non-GAAP 0,38 |
| [Q3 2026](https://www.intc.com/news-events/press-releases/detail/1786/intel-reports-third-quarter-2026-financial-results) | 26.09.2026 / 29.10.2026 | 16513 | 0.60 | 0.52 | Q4 revenue 15–16 mld; EPS GAAP 0,10 / non-GAAP 0,25; gross margin 37,1% / 38,0% |

Q3 raportuje m.in. DCAI 7,3 mld i Intel Foundry 6,7 mld, lecz istnieją
transakcje wewnętrzne i eliminacje; suma segmentów nie zastępuje revenue
skonsolidowanego. GAAP loss w Q2 oraz dodatni adjusted wynik to różne
miary. Tabele reconciliation są dostępne, nie należy odtwarzać EPS z
wybranych korekt lub total net income bez właściwej atrybucji.

SEC: [Q2 8-K, 0000050863-26-000155, oficjalna kopia IR](https://www.intc.com/filings-reports/all-sec-filings/content/0000050863-26-000155/0000050863-26-000155.pdf)
i [Q3 8-K, 0000050863-26-000188](https://www.sec.gov/Archives/edgar/data/50863/000005086326000188/0000050863-26-000188-index.htm).
[Treść Q3 Item 2.02](https://www.sec.gov/Archives/edgar/data/50863/000005086326000188/intc-20261029.htm)
wiąże okres i [EX-99.1](https://www.sec.gov/Archives/edgar/data/50863/000005086326000188/q326earningsrelease.htm).
Odczytano też oficjalne kopie IR [Q2 10-Q, 0000050863-26-000157](https://www.intc.com/filings-reports/all-sec-filings/content/0000050863-26-000157/intc-20260627.htm)
oraz [Q3 10-Q, 0000050863-26-000191](https://www.intc.com/filings-reports/all-sec-filings/content/0000050863-26-000191/intc-20260926.htm).
Kopie IR filings oznaczono jako kopie, nie udany bezpośredni odczyt API SEC.

### 3.4 Porównanie pilotów

| Kryterium | NVDA | AMZN | INTC |
| --- | --- | --- | --- |
| Oficjalny kalendarz IR | Tak, [Events](https://investor.nvidia.com/events-and-presentations/events-and-presentations/default.aspx); część treści dynamiczna | [Events](https://ir.aboutamazon.com/events/default.aspx); przyszły termin NOT VERIFIED | [IR Calendar](https://www.intc.com/news-events/ir-calendar); brak przyszłych wpisów przy odczycie |
| Oficjalna zapowiedź daty | Q2 29.07; Q3 event 17.11 | Q3 zapowiedź 15.10 dla 29.10 | Q3 zapowiedź 06.10 dla 29.10 |
| Godzina earnings release | Q2 około 13:20 PT planowane; Q3 NOT VERIFIED | Dokładna pierwsza publikacja NOT VERIFIED | AMC potwierdzone; 16:01 EDT na stronie nie jest first availability |
| Earnings call | Q2 14 PT; Q3 17:00 EST | Q3 14 PT / 17 ET | Q3 14 PDT z zapowiedzi; widget PST konflikt |
| SEC 8-K | Q1 i Q2, 2.02/99.1/99.2 | Q2 i Q3, 2.02/99.1 | Q2 i Q3, 2.02/99.1 |
| SEC 10-Q/10-K | Q2 10-Q/iXBRL odczytany; 10-K linki w IR, pełny annual parser NOT VERIFIED | Q3 10-Q odczytany; 10-K nie był potrzebny do próby kwartalnej | Q2/Q3 10-Q z IR; IR ma też odnośnik 10-K, parser annual NOT VERIFIED |
| GAAP EPS | Diluted, jawna tabela | Diluted, jawny wynik | Diluted attributable to Intel, jawna tabela |
| Non-GAAP EPS | Tak, osobna tabela/reconciliation | NOT VERIFIED w badanych release | Tak, osobna tabela/reconciliation |
| Revenue | Consolidated i Data Center | Total net sales, produkty/usługi, AWS | Consolidated i segmenty z eliminacjami |
| Guidance | Revenue ±%, marże, wydatki; nie potwierdzono EPS guidance | Sales/operating income/capex; EPS guidance NOT VERIFIED | Revenue, GAAP/non-GAAP EPS i marże |
| Automatyzacja | HTML release czytelny; dynamiczny kalendarz i RSS 403 | HTML komunikatów czytelny; daty z zapowiedzi; brak zweryfikowanego publicznego API IR | Czytelny HTML i bogate linki, konflikt oznaczenia czasu |
| Ryzyka licencyjne | Restrykcyjne ogólne warunki, zakres IR do ustalenia | Właściwe warunki IR i redystrybucja NOT VERIFIED | Ogólne warunki ograniczają kopiowanie Documents, nie przenosić praw QuoteMedia |
| Rekomendacja E2 | Włączyć do E2A jako jawny event/call; E2B po bramkach dostępu/praw | Dobry pierwszy adapter parsowania podstawowych pól | Równie dobry technicznie, trudniejsza metodologia i prawa |

Żadna z kolumn nie oznacza przetestowanego importera. Technicznie najprostsze
HTML podstawowych Actual mają AMZN i INTC; NVDA również ma dobre tabele,
ale kalendarz i odmowa RSS zwiększają ryzyko discovery. Gotowość prawna
nie wynika z tej kolejności.

## 4. SEC: model źródeł i walidacja dokumentu

[Dokumentacja API SEC](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
potwierdza publiczne JSON bez klucza: Submissions identyfikowany 10-cyfrowym
CIK oraz Company Facts. Submissions dostarcza formularz, accession,
primaryDocument i czasy/metadane; listy recent są kolumnowe, starsze
zakresy mogą być w dodatkowych plikach. Company Facts agreguje standardowe
tagi dla całego emitenta, nie gwarantuje segmentów lub custom non-GAAP.
`data.sec.gov` nie wspiera browser CORS; komunikacja ma należeć do backendu.
Opisywane krótkie opóźnienia przetwarzania API nie są SLA pierwszej publikacji.

Proponowany wybór dokumentu w E2B:

1. Ograniczyć discovery do trzech zatwierdzonych CIK i właściwego okna.
2. Dla 8-K sprawdzić Items 2.02 i indeks załączników, nie sam form=8-K.
3. Wybrać faktyczny earnings release po treści; EX-99.1 nie zawsze musi
   być wynikiem i nie zawsze numer 99.1 będzie właściwym załącznikiem.
4. Zweryfikować emitenta, fiscal year/quarter, period start/end, metodologię,
   nagłówki kolumn i jednostki. Odrzucić prezentację konferencyjną,
   niezwiązany komunikat, dawny kwartał i podmianę porównawczej kolumny.
5. Revenue i EPS mogą być przyjęte niezależnie; brak EPS oznacza partial,
   nie zapożyczenie non-GAAP lub wartości z poprzedniego okresu.
6. Przy późniejszym 10-Q/10-K powiązać filing i porównać właściwy kontekst.
   Rozbieżność nie usuwa wcześniejszego release. Amendment 8-K/A, 10-Q/A
   i 10-K/A to nowe źródła, nie zwykłe ponowne pobranie.

W [badanych 8-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/nvda-20260826.htm)
release/CFO commentary bywają **furnished**, z wyłączeniem traktowania
jako filed w określonych przepisach. Nie należy opisywać ich jako
audytowanego 10-K ani mylić tej klauzuli z prawem do redystrybucji.

Przyszłe mapowanie XBRL: kandydaci `us-gaap:EarningsPerShareDiluted`,
`EarningsPerShareBasic`, `RevenueFromContractWithCustomerExcludingAssessedTax`,
ewentualnie inny udokumentowany revenue tag. **Dokładne Company Facts
mapowanie per spółka i runtime odpowiedź: NOT VERIFIED** wobec 403.
Wybór musi uwzględniać accession, unit, start/end, duration i dimensions;
nie wystarcza „ostatni fact”. Trzymiesięczny i dziewięciomiesięczny wynik
z tego samego 10-Q są różnymi kontekstami. `fy/fp` metadanych filing nie
zastępuje ustalenia okresu historycznej porównawczej liczby. Nie wyprowadzać
Q4 EPS przez annual minus 9M: ważone liczby akcji nie są addytywne.

## 5. Fair access i prawa

[Developer Resources SEC](https://www.sec.gov/about/developer-resources)
ogranicza sumę do **nie więcej niż 10 requests/s na użytkownika**, niezależnie
od maszyn. [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
wymaga deklarowania klienta i pokazuje identyfikujący User-Agent z kontaktem.
To limit maksymalny, nie docelowe tempo trzech pilotów. Nie utożsamiać
publicznego JSON data API z osobnym, uwierzytelnianym API do składania
filingów EDGAR Next — E2 nie składa raportów.

Projektować jeden wspólny limiter SEC na wszystkie workery i hosty,
początkowo **1 request/s, jedna równoległa próba** i mały budżet okna.
Cache mapowania CIK, stan discovery i dokumenty po accession/hash.
Wykorzystywać ETag/Last-Modified tylko gdy konkretny serwer je zwraca;
nie ogłaszać ich dostępności dla wszystkich endpointów. 304 nie potwierdza
nowych wyników. W tej próbie 403 brak tych nagłówków nie opisuje odpowiedzi
200. 403 zatrzymuje automatyczne próby danego źródła do diagnozy; 429/503
respektują Retry-After, brak poprawnego nagłówka uruchamia ograniczony
backoff, nigdy natychmiastową pętlę. Inna ścieżka, IP lub mirror nie są
narzędziem obchodzenia zakazu. Nie pobierać całych ZIP ani archiwów w E2A.

Publiczna widoczność i bezpłatny dostęp SEC nie oznaczają, że każdy tekst
emitenta jest utworem rządu USA lub wolną kopią całego IR. [Copyright Office](https://www.copyright.gov/help/faq/faq-protect.html)
odróżnia fakty od chronionej formy ich wyrażenia. To argument za minimalnymi
faktami i linkami, nie opinia prawna o kontraktach, bazach danych,
jurysdykcji, logo, prezentacjach lub pełnych archiwach.

| Źródło | Widoczność / logowanie / API | Pobranie automatyczne | SQL i publiczne pojedyncze fakty | Pełne dokumenty / prawa |
| --- | --- | --- | --- | --- |
| SEC, wszystkie trzy CIK | Publiczne filing/JSON według dokumentacji; bez klucza | Dozwolona ścieżka fair access; operacyjnie Submissions 403 w E1 | Technicznie wykonalne; minimalne fakty z atrybucją wymagają oceny zakresu użycia; nie ma w E1 zakupionej licencji komercyjnego feedu | Nie deklarować, że złożenie w SEC przenosi prawa autora. Polityka retencji/pełnego RAW do zatwierdzenia |
| NVDA IR/newsroom | Publiczne HTML; webcast może wymagać formularza; publiczne API IR NOT VERIFIED | HTML widoczne w badaniu, RSS 403; zgoda na produkcyjne pobieranie/archiwum NOT VERIFIED | Dla metadanych i faktów osobna decyzja; nie wywodzić jej z technicznego odczytu | [Warunki NVIDIA](https://www.nvidia.com/en-eu/about-nvidia/terms-of-service/) ograniczają Materials do osobistego, niekomercyjnego użycia; zakres IR i regionalnej wersji wymaga ustalenia |
| AMZN IR | Publiczne komunikaty i zapowiedzi; API IR NOT VERIFIED | Warunki właściwe dla IR i automatyzacji NOT VERIFIED | Przechowywanie/redystrybucja projektu NOT VERIFIED; proponowany zakres minimalnych faktów i linków | Próba odczytu About Amazon terms-of-use nie dała treści. Nie stosować w ciemno Seller Central, API sklepowego, AWS lub warunków programu afiliacyjnego do IR |
| INTC IR/newsroom | Publiczne HTML, prezentacje, filing mirrors; API IR NOT VERIFIED | Produkcyjne prawa do automatycznego pobierania NOT VERIFIED | Oddzielić liczby od kopii Documents; publiczny produkt wymaga wyjaśnienia zakresu | [Intel Terms §8.1](https://www.intel.com/content/www/us/en/legal/terms-of-use.html) ogranicza kopiowanie Documents do osobistego niekomercyjnego celu i zabrania publikacji na network computer; nie ogłaszać zgody na archiwum/redistribucję |

Warunki NVIDIA otwarto po przekierowaniu z adresu US do `en-eu` — nie
przypisano ich bez zastrzeżeń każdemu IR subsite. Warunki Intel wymagają
uwzględnienia dodatkowych regulaminów. Widoczny na intc.com copyright
QuoteMedia dotyczy market data i nie jest licencją na earnings release.
Nie archiwizowano pełnych dokumentów w E1 i nie kopiowano ich na frontend.
Nie potwierdzono osobnego opublikowanego limitu IR dla trzech emitentów.

Bezpieczny fallback produktu: ręcznie zweryfikowane metadane, status
niepotwierdzonego terminu, link do wydawcy i brak treści/liczb, których
użycia nie zatwierdzono. Metadata-only też wymaga określenia dozwolonego
sposobu pozyskania; sam fallback nie legalizuje zabronionego scrapingu.
Pełne dokumenty finansowe, slajdy, nagrania i transkrypcje nie są zakresem
publicznego serwowania w E2A/B. Wątpliwości prawne pozostają otwarte.

## 6. Daty, czas i tożsamość wydarzenia

Poniżej jest **projekt E2, nie obecny kontrakt aplikacji**. Oddzielić
`date_status` (unknown / estimated / confirmed / changed / cancelled)
od `publication_status` (pending / partial / published / corrected).
Zmiana daty zachowuje wcześniejsze potwierdzenie; bieżący rekord wskazuje
nowe. Published wymaga dokumentu i rozpoznanego okresu, nie upływu zegara.
Confirmed conference call nie oznacza confirmed release time ani Actual.
Szacunki agregatorów w E2A pomijać; jeżeli później zostaną dopuszczone,
przechowywać oddzielne pochodzenie i nigdy nie awansować do confirmed.

Jeden główny event na emitenta i raportowany kwartał. Wewnątrz osobne
komponenty `earnings_release` i `conference_call`; 8-K oraz 10-Q/10-K
są dokumentami powiązanymi, nie automatycznie dodatkowymi wierszami Calendar.
Gdy potwierdzono wyłącznie call, wiersz mówi wprost „konferencja wynikowa”,
a szczegóły „czas publikacji wyników nieustalony”. Przeniesienie kotwicy
na potwierdzony release nie zmienia event_id. Osobna opcja pokazywania calls
może powstać później; domyślnie unikać trzech kopii tego samego raportu.

| Tożsamość | Proponowany klucz i granica |
| --- | --- |
| Emitent | Wewnętrzne company_id UUID, unikalny zweryfikowany CIK CHAR(10); ticker i nazwa mają historię |
| Papier / ticker | Osobny zapis klasy, giełdy i okresu ważności; GOOGL/GOOG nie tworzą dwóch raportów Alphabet |
| Reporting period | period_id UUID i UNIQUE(company_id, fiscal_year, fiscal_quarter, period_kind); etykieta roku od emitenta, nie rok daty publikacji |
| Earnings event | event_id UUID, UNIQUE(period_id, event_kind); publiczny namespace `earnings:<UUID>`; release/call to komponenty |
| SEC filing | Accession number z indeksu + potwierdzony CIK; forma i accepted_at są metadanymi, nie kluczem kwartału |
| Dokument / wersja | Wydawca, rola, rzeczywisty URL i wersja receipt/hash; IR i EX-99.1 mogą być dwiema reprezentacjami tego samego komunikatu |
| Miara | Stabilny kod, np. revenue_consolidated lub eps_gaap_diluted, z zakresem, jednostką, atrybucją i metodą; wersja wartości ma osobny UUID |

Period end nie powinien być jedynym kluczem ani obowiązkowym polem nowego
przyszłego eventu: może jeszcze nie być potwierdzony. Po potwierdzeniu ma
historię dowodu; korekta nie tworzy drugiego kwartału. Przykłady Q2 FY2027
NVDA kończącego się 26.07 oraz Q3 INTC kończącego się 26.09 wykluczają
założenie „każdy kwartał kończy się ostatniego dnia miesiąca”. Rok fiskalny
NVDA wyświetlać jako **Q3 FY2027**, z period_end dopiero gdy jest znany.
Ewentualny okres przejściowy po zmianie roku fiskalnego wymaga osobnego
period_kind i długości okresu, bez wciskania w zwykły kwartał.

### 6.1 Precyzja zegara i grupowanie

Zapisywać source_local_date, opcjonalne source_local_time, IANA timezone,
surową etykietę strefy, precision i session. UTC powstaje tylko z poprawnie
rozstrzygniętej chwili. Precision: exact / approximate / session / date_only /
unknown. Session: before_open / after_close / during_market / unknown.
„Po sesji” pozostaje sesją, a nie 16:00 ET. Przy godzinie przybliżonej UI
zachowuje „około”; brak godziny nigdy nie staje się 00:00.

Poniższe konwersje policzono offline biblioteką IANA, nie stałym +6:

| Dowód lub przypadek kontrolny | UTC | Europe/Warsaw | Wniosek |
| --- | --- | --- | --- |
| AMZN call, 29.10.2026 17:00 America/New_York, EDT | 29.10 21:00 | 29.10 22:00 CET | Jesienny okres różnicy 5 h |
| NVDA event, 17.11.2026 17:00 America/New_York, EST | 17.11 22:00 | 17.11 23:00 CET | Tu różnica 6 h; nadal zegar webcastu |
| Kontrola, 22.10.2026 17:00 NY, EDT | 22.10 21:00 | 22.10 23:00 CEST | Przed europejską zmianą czasu |
| Kontrola, 16.03.2026 17:00 NY, EDT | 16.03 21:00 | 16.03 22:00 CET | Wiosenny okres różnicy 5 h |
| NVDA Q2 plan około 26.08 13:20 America/Los_Angeles, PDT | 26.08 20:20 | 26.08 22:20 CEST | Przybliżony release, nie call |
| INTC call 29.10 14:00 America/Los_Angeles, PDT | 29.10 21:00 | 29.10 22:00 CET | Nie interpretować błędnego widgetowego PST jako −08 |
| **Syntetyczny**, 17.11 19:30 NY, EST | 18.11 00:30 | **18.11 01:30 CET** | Data w PL jest następna; to nie ogłoszony termin spółki |

Data bez godziny nie ustala jednoznacznie polskiego dnia. Dla takiego
eventu pokazać np. „17 lis, data emitenta · godzina PL nieustalona”,
z osobną sekcją terminów nieprecyzyjnych. Zapytanie zakresowe może
uwzględniać przedział możliwych lokalnych dni z jawnym precision, lecz
nie duplikować eventu w dwóch grupach. Przedział techniczny nie jest
godziną publikacji. Brak daty trafia do „Termin nieogłoszony” poza osią czasu.
Regułę należy zatwierdzić produktowo przed E2A.

## 7. Finanse: Actual, porównania, guidance i konsensus

**Minimum E2B jest potwierdzone w badanych dokumentach wszystkich trzech
emitentów:** company/CIK, etykieta fiscal year/quarter, historyczny period end,
consolidated revenue/net sales, GAAP diluted EPS i URL dowodu. Ticker jest
potwierdzany mapowaniem SEC. Oficjalny przyszły scheduled release oraz
dokładny source publication timestamp nie są obowiązkowo dostępne i muszą
być nullable. Capture timestamp powstanie dopiero przy rzeczywistym E2
pobraniu; nie wpisywać do bazy czasu badania WWW jako fikcyjnego receipt.

Actual to konkretna miara za konkretny okres i z konkretnego dokumentu.
Revenue przechowywać jako NUMERIC w walucie bazowej, z zachowaniem
oryginalnego tekstu, skali i precision. Np. mln USD i mld USD normalizować
dziesiętnie, bez float. Total net sales AMZN nie jest AWS, Data Center NVDA
nie jest consolidated revenue; segment INTC z intersegment eliminations
nie może być dodany do consolidated bez reconciliation. Net product/service
sales i wzrost FX-neutral mają własne miary, jednostki oraz zakres.
Nie przeliczać walut bez osobnego jawnego źródła kursu i daty.

Podstawowy EPS: **GAAP diluted, zgodny z opublikowaną atrybucją**.
Basic, diluted, continuing operations, attributable to common shareholders
lub parent oraz adjusted/non-GAAP to różne definicje. Zapisać etykietę
oryginalną i odpowiadające jej wymiary, zamiast ujednolicać wszystkie do EPS.
Nie odtwarzać adjusted EPS z samodzielnie wybranych korekt; NVDA/INTC
wymagają własnego opublikowanego wyniku i reconciliation. Zmiana definicji
adjusted wymaga nowej wersji metodologii. Strata jest poprawną wartością
ujemną; zero jest liczbą, nie zamiennikiem brakującej wartości.

Comparative po splicie musi mieć wspólną podstawę liczby akcji i informację,
czy jest wartością przeliczoną/restated. Nie porównywać dawnego 1 USD/share
z późniejszym EPS po splicie bez jawnego dostosowania emitenta. Nie liczyć
Q4 EPS przez annual minus 9M: średnie ważone i rozwodnienie nie są addytywne.
Analogicznie nie mylić kolumny trzech miesięcy z year-to-date w 10-Q.

Rekomendowany domyślny comparator: **ten sam kwartał poprzedniego roku**,
opisany „Rok wcześniej”, najlepiej w postaci porównawczej z tego samego
bieżącego release. Osobno „Poprzedni kwartał”, wyłącznie po świadomym
wyborze. Nie używać nieopisanej kolumny Previous do obu. Zapisywać ID okresu,
wersji i split/restatement basis obu stron. Dawna przechwycona wartość
oraz porównawcza wartość restated są różnymi dowodami. Niepewna zgodność
oznacza brak wyliczonej zmiany i wyjaśnienie; nie wyszukiwać najbliższej daty.

Guidance należy do **przyszłego target period**, nie Actual bieżącego.
Struktura rozdziela metric, basis GAAP/non-GAAP, walutę/jednostkę i kind:
point, range, qualitative, not_provided. Range ma lower/upper; point ma value;
tekst jakościowy ma własny tekst/odnośnik; not_provided ma puste liczby.
NVDA revenue ±2% zachować jako center + relative tolerance z oryginalnym
tekstem, bez twierdzenia, że wyliczone krańce były literalnie opublikowane.
Guidance EPS INTC nie oznacza, że AMZN też je podał. Marża jest procentem,
operating income kwotą, a capex może dotyczyć całego roku. Operating expenses
NVDA to kolejna osobna miara. E2B ograniczyć do revenue i GAAP EPS Actual;
rozbudowany guidance zostawić E2C, aby ograniczyć liczbę definicji parsera.

### 7.1 Konsensus jest odrębnym produktem danych

Oficjalne [FactSet Consensus Estimates](https://insight.factset.com/resources/factset-consensus-estimates-datafeed)
i [LSEG I/B/E/S Estimates](https://www.lseg.com/en/data-catalogue/company-data/ibes-estimates/broker-estimates)
to potencjalne kierunki umowy/feedu, nie darmowa licencja wynikająca z
istnienia strony produktu. [LSEG Estimates API](https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/estimates-API)
wymaga osobnego ustalenia dostępu i uprawnień. W E1 nie uzyskano konta,
oferty, umowy, działającego API lub zgody na redistribucję tych produktów.

Przed przyszłym surprise trzeba potwierdzić: GAAP vs adjusted, diluted,
walutę, split basis, okres fiskalny, cutoff as-of przed release, mean/median,
liczbę analityków oraz licencję SQL/cache/public display. Guidance spółki
nie zastępuje tego konsensusu. E2A/B: **consensus=null, surprise=null,
brak beat/miss**. Nie scrapować płatnych serwisów. Publikowany przez niektóre
IR zbiór szacunków też nie jest automatycznie uniwersalnym konsensusem
z prawem redystrybucji.

## 8. Proponowany magazyn E2 — słownik pól

To koncepcja przyszłego DDL, **żadnej tabeli nie utworzono**. Oddzielne
tabele earnings są prostsze niż rozszerzanie economic_releases i FRED
vintages. Poniższe grupy pól mają wspólne reguły; każdy wymieniony element
dziedziczy typ/nullability/indeks opisany w swoim wierszu. PK/FK/UNIQUE
oznaczają przyszłe constrainty, I oznacza dodatkowy indeks, „—” jego brak.
Wszystkie FK powinny blokować usunięcie użytego dowodu, bez kaskadowego
kasowania historii. Wartości i assertions są append-only; aktualny wskaźnik
może być zmieniany transakcyjnie po walidacji.

### 8.1 Spółki i okresy

| Tabela / pola | Typ; NULL | Klucz / indeks | Źródło i walidacja | Wersjonowanie |
| --- | --- | --- | --- | --- |
| earnings_companies.company_id | UUID; nie | PK | Wygenerowane raz po rozpoznaniu emitenta | Stałe |
| cik | CHAR(10); nie | UNIQUE | Oficjalne SEC mapping + filing; cyfry i padding | Nie podmieniać CIK przy zmianie tickera; reorganizacja do przeglądu |
| legal_name | TEXT; nie | — | SEC/IR; niepusta | Historia nazw w atrybutach niżej |
| created_at | TIMESTAMPTZ; nie | — | Zegar zapisu UTC | Niezmienne |
| earnings_company_aliases.alias_id | UUID; nie | PK | Lokalny identyfikator | Append-only |
| company_id | UUID; nie | FK; I(company_id,valid_from) | Emitent istnieje | Stałe |
| alias_kind / value | TEXT / TEXT; nie | I(alias_kind,value) | name lub ticker; SEC/IR | Nowy przedział przy zmianie |
| exchange / security_class | TEXT; tak | W indeksie wyszukiwania tickera, jeśli potrzebny | Oficjalny rynek/klasa, nie wnioskować z nazwy | Wersja aliasu |
| valid_from / valid_to | DATE; tak | — | Potwierdzone granice; null = nieustalone; bez sprzecznych przedziałów tej samej klasy | Nie wymyślać wcześniejszej historii |
| evidence_receipt_id | UUID; nie | FK | Dowód nazwy/tickera | Wskazuje wersję |
| earnings_periods.period_id | UUID; nie | PK | Wewnętrzny identyfikator | Stały |
| company_id / fiscal_year / fiscal_quarter / period_kind | UUID / INT / SMALLINT / TEXT; nie | FK + UNIQUE całości | Fiscal quarter 1–4 dla quarter; issuer FY; transition wymaga osobnej reguły, nie dopisywać Q5 | Tożsamość; błędny klucz wymaga kontrolowanego scalania, nie nowego dubla |
| period_start / period_end | DATE; tak | I(company_id,period_end) | Dokument emitenta; end≥start; null przyszłego okresu dozwolony | Zmiany przez assertion/dowód i revision link |
| period_label / evidence_receipt_id | TEXT / UUID; label nie, dowód tak przed potwierdzeniem granic | FK dowodu | Q3 FY2027 z emitenta; brak potwierdzenia widoczny | Historia potwierdzeń, nie nadpisanie bez śladu |

### 8.2 Event i potwierdzenia dat

| Tabela / pola | Typ; NULL | Klucz / indeks | Źródło i walidacja | Wersjonowanie |
| --- | --- | --- | --- | --- |
| earnings_events.event_id / period_id / event_kind | UUID / UUID / TEXT; nie | PK, FK, UNIQUE(period_id,event_kind) | Event aggregate earnings; nie filing | Stała tożsamość |
| date_status / publication_status | TEXT; nie | I(statusy) | Zamknięte stany sekcji 6; HTTP 200 nie daje published | Projekcja z dowodów, zmiana w transakcji |
| active_release_confirmation_id / active_call_confirmation_id | UUID; tak | FK | Komponent zgodny z własnym eventem | Poprzednie potwierdzenia zachowane |
| revision / updated_at | BIGINT / TIMESTAMPTZ; nie | I(updated_at,event_id) | Monotoniczna rewizja, serwerowy czas zapisu | Zmiana tylko po rzeczywistej zmianie projekcji |
| earnings_date_confirmations.confirmation_id / event_id | UUID / UUID; nie | PK, FK; I(event_id,captured_at) | Nowy dowód dotyczący właściwego emitenta/okresu | Append-only |
| component / date_status | TEXT / TEXT; nie | — | release albo call; status z dowodu | Nowy rekord dla zmiany/odwołania |
| source_local_date / source_local_time | DATE / TIME; tak | I(source_local_date) | Oficjalna data/godzina; nie generować z rytmu kwartalnego | Surowy dowód pozostaje |
| source_timezone / timezone_label_raw | TEXT / TEXT; tak | — | IANA po walidacji; EST/PST raw osobno; konflikt blokuje exact | Wersja potwierdzenia |
| scheduled_at_utc | TIMESTAMPTZ; tak | I(scheduled_at_utc,event_id) przez projekcję | Tylko exact/approximate i rozstrzygnięta strefa; approximate jawne | Nie tworzyć dla date_only/session |
| precision / session | TEXT / TEXT; nie | — | Enum sekcji 6; unknown dozwolone | Wersja potwierdzenia |
| receipt_id / captured_at | UUID / TIMESTAMPTZ; nie | FK / — | Własny receipt; capture ≠ publisher time | Niezmienne |
| supersedes_id / change_reason | UUID / TEXT; tak | FK / — | Własny event, brak cyklu; zmiana wymaga powodu | Łańcuch historii |

### 8.3 Źródła i filing

Istniejący publisher_documents może obsłużyć legalnie zachowaną kopię
z `source` namespacowanym dla earnings i CIK oraz `kind` wskazującym rolę
i okres. Nie dodawać fikcyjnego raw_path/hash dla metadata-only, bo są dziś
NOT NULL. Osobny receipt umożliwia link bez kopii i kolejne pobrania tych
samych bajtów. Wspólna warstwa dokumentów to opcja reuse, nie nowy
uniwersalny framework. E2 musi sprawdzić deduplikację obecnego UNIQUE
(source,kind,raw_hash) dla komunikatów zawierających kilka okresów.

| Tabela / pola | Typ; NULL | Klucz / indeks | Źródło i walidacja | Wersjonowanie |
| --- | --- | --- | --- | --- |
| earnings_source_receipts.receipt_id / company_id | UUID / UUID; nie | PK / FK; I(company_id,retrieved_at) | Własny capture i potwierdzony emitent | Append-only |
| source_kind / document_role / source_url / publisher | TEXT; nie | I(source_kind,source_url) | IR/SEC; announcement/release/call/filing; allowlista HTTPS, final redirect host i tożsamość | Każdy capture osobny |
| retrieved_at / http_status | TIMESTAMPTZ / SMALLINT; nie | I(retrieved_at) / — | Rzeczywisty request; 100–599; ręczny dowód wymaga osobnego trybu zamiast zmyślonego HTTP 200 | Niezmienne |
| source_published_at / published_label_raw | TIMESTAMPTZ / TEXT; tak | — | Wiarygodny zegar wydawcy, bez zastępowania fetched_at | Wersja dowodu; precyzja jawna |
| declared_title / locator | TEXT; tak | — | Własny tytuł i selektor tabeli/wiersza lub sekcji; nie pełna treść strony | Wersja receipt |
| raw_sha256 / publisher_document_id | CHAR(64) / UUID; tak | I(raw_sha256) / FK | Tylko jeśli faktycznie uzyskano bajty i zatwierdzono retencję; kontrola zgodności hash/FK | Nie zmieniać istniejącego hasha |
| access_policy / access_policy_version | TEXT; nie | — | metadata_only / facts_allowed / archive_allowed / blocked; zatwierdzona polityka, nie wniosek parsera | Nowa decyzja ma wersję, nie legalizuje starych pobrań |
| parser_version / validation_status / error_code | TEXT / TEXT / TEXT; parser i error tak | — | Parser rzeczywiście użyty; valid/partial/rejected/unparsed; error bez sekretów | Wynik walidacji przy capture |
| supersedes_id | UUID; tak | FK | Tylko uzasadniona korekta/wersja; inny hash sam nie dowodzi kolejności | Append-only, bez cyklu |
| earnings_filings.accession / company_id | TEXT / UUID; nie | PK accession / FK; I(company_id,accepted_at) | SEC index, wzór accession; issuer nie wyliczony z pierwszych cyfr accession | Stałe |
| form / filing_date / accepted_at / report_date | TEXT / DATE / TIMESTAMPTZ / DATE; report_date tak | I(form,filing_date) | SEC; form 8-K/8-K/A/10-Q/10-K itd.; accession nie jest chwilą IR | Amendments mają nowe accession |
| receipt_id / period_id / amends_accession | UUID / UUID / TEXT; receipt nie, pozostałe tak | FK | Nie przypinać nieustalonego okresu na podstawie samej daty filing; amendment wskazuje poprzednika gdy dowód istnieje | Powiązania wersjonowane przy rozstrzygnięciu |

Metadata-only capture nie może tworzyć fikcyjnego pełnego RAW. W takim
trybie parser może wymagać ręcznej weryfikacji albo dopuszczonego odczytu
w pamięci; jeżeli nie zatwierdzono nawet tego, pozostać przy linku bez
automatycznego pobierania. Dla audytowalnych Actual E2B trzeba z góry
zatwierdzić minimalny zachowywany dowód, a nie dopiero po zebraniu archiwum.

### 8.4 Miary, rewizje i guidance

| Tabela / pola | Typ; NULL | Klucz / indeks | Źródło i walidacja | Wersjonowanie |
| --- | --- | --- | --- | --- |
| earnings_actual_versions.value_id / period_id | UUID / UUID; nie | PK / FK; I(period_id,metric_code,recorded_at) | Właściwy okres i emitent dowodu | Append-only |
| metric_code / basis / dilution / attribution / scope | TEXT; nie | Część klucza logicznej miary | Jawne kody; dla revenue dilution=not_applicable, dla EPS diluted/basic; scope consolidated/segment | Zmiana definicji tworzy inną miarę, nie cichą rewizję |
| segment_name / operations_scope | TEXT; segment tak | — | Segment tylko z dokumentu; all/continuing/not_applicable jawne | Definicja/wersja segmentu zachowana |
| value / currency / unit | NUMERIC / CHAR(3) / TEXT; nie | — | Np. USD i currency albo currency_per_share; bez NaN/Inf; EPS ujemny poprawny | Wartość w wersji |
| source_scale_exponent / source_precision / raw_numeric_text | INT / INT / TEXT; nie | — | Skala 6 dla mln, 9 dla mld; precision z dokumentu, nie z float | Niezmienne |
| receipt_id / source_locator / parser_version | UUID / TEXT / TEXT; nie | FK / — / — | Dowód miary/kolumny; podwójne sprawdzenie tożsamości i okresu; brak blank fallback | Niezmienne |
| recorded_at / supersedes_value_id / revision_reason | TIMESTAMPTZ / UUID / TEXT; ostatnie dwa tak | I(recorded_at) / FK / — | Zegar capture; własna logiczna miara; poprawka z dowodem | Łańcuch korekt, first captured zachowany |
| comparative_period_id / comparative_value_id / comparative_basis | UUID / UUID / TEXT; tak | FK / FK / — | Dokładny okres, wersja i as_reported/restated/split_adjusted; zgodne units/basis | Nie nadpisuje dawnej opublikowanej liczby |
| earnings_guidance.guidance_id / event_id / target_period_id | UUID / UUID / UUID; target tak | PK / FK / FK; I(event_id,metric_code) | Docelowy okres, opcjonalnie tekst okresu gdy nieustalony | Nowa wersja guidance |
| metric_code / basis / kind / unit | TEXT; nie | — | Revenue/EPS/op income/margin/capex itd.; point/range/qualitative/not_provided | Osobna miara i metodologia |
| currency / target_period_label | CHAR(3) / TEXT; waluta tak, label nie | — | Waluta tylko miar kwotowych; kwartał/rok zgodny z emitentem | Wersja |
| point / lower / upper / relative_tolerance | NUMERIC; tak | — | CHECK zgodności z kind, lower≤upper; center±tolerance zachowane jako takie | Brak = null, nigdy zero |
| text / receipt_id / source_locator | TEXT / UUID / TEXT; text tak, pozostałe nie | FK dowodu | Krótka faktograficzna reprezentacja/oryginalna liczba, zakres dozwolonego cytowania; brak pełnego release | Wersja dokumentu |
| recorded_at / supersedes_id | TIMESTAMPTZ / UUID; drugie tak | I(recorded_at) / FK | Czas zapisu, własna miara/target, bez cyklu | Append-only |

Projekcja aktualnych wartości może być widokiem wybierającym zatwierdzoną
wersję, bez drugiej kopii liczb w cache JSON. Spójność FK receipt→company,
period→company i event→period wymaga constraintów złożonych lub jawnej
walidacji transakcyjnej oraz testu błędnego cross-company FK. Nie wystarczy,
że sam UUID istnieje. Kontrolowane przejście statusu i publikacja projekcji
następują w jednej transakcji z wartościami; błąd SQL zostawia poprzedni stan.

## 9. Provenance, wykrywanie i historia

Przed przyjęciem release parser musi potwierdzić oficjalny host/wydawcę,
emitenta/CIK, typ komunikatu, fiscal year/quarter, period end oraz własne
kolumny liczb. Artykuł „to report”, zaproszenie na webcast, slajd z samym
guidance, 8-K o innym zdarzeniu lub wynik wyszukiwarki nie tworzą Actual.
Nie szukać pierwszej liczby przypominającej EPS. Nie konstruować przyszłych
URL na podstawie tytułu poprzedniego kwartału.

IR release może dać pierwszy zatwierdzony Actual. Właściwy 8-K Item 2.02
z EX-99.1 służy jako niezależny dowód/późniejsze uzupełnienie. Po 10-Q/10-K
porównać te same miary, okres i podstawę; nie zastępować automatycznie
release tylko dlatego, że filing ma późniejszą datę. Amendment i restatement
tworzą wersje z powodem oraz linkiem do wcześniejszego dowodu. Konflikt
oficjalnych dokumentów bez wyjaśnienia oznacza review i zachowanie
ostatniej zatwierdzonej wersji, nie średnią z dwóch wartości.

Source publication time, SEC accepted_at, retrieved_at oraz database
recorded_at opisują różne zdarzenia. Known_since oznacza najwcześniejszy
**przechwycony przez MacroLens** dowód, nie pierwszą dostępność w internecie.
Przy braku timestampu wydawcy zachować datę/precision i null czasu.
Nie nazywać późno pobranego historycznego release „first print as-of”.

Identyczne bajty: nowa kontrola dostępu, bez nowej wersji liczby i bez zmiany
jej original capture. Nowy hash, te same liczby: wersja reprezentacji/dowodu,
bez ogłoszenia rewizji finansowej. Nowe liczby: rewizja dopiero po walidacji.
Powrót znanego starszego hasha nie cofa aktywnej wersji. Kolejność pobrań
nie rozstrzyga kolejności dwóch nieznanych, nieoznaczonych wersji emitenta;
potrzebny timestamp/korekta lub review. Zachować ten sam poziom ostrożności
co R2, bez deklaracji kompletnego intraday archive.

## 10. API i wspólny Calendar

Propozycja najmniej inwazyjna: zachować stare `/api/v1/calendar` i
`/api/v1/releases/{release_id}` jako makro. Dodać opt-in agregator:

| Przyszły odczyt | Kontrakt |
| --- | --- |
| `GET /api/v1/calendar/events?start_date=...&end_date=...&domains=macro,earnings&tickers=NVDA,AMZN` | Wspólna agenda z event union, walidowanym zakresem i limitem, bez HTTP do wydawców |
| `GET /api/v1/earnings/events/{event_id}` | Komponenty terminu/call, okres, wersje Actual, provenance, linki i status kontroli |
| `GET /api/v1/earnings/companies` | Mała allowlista obserwowanych emitentów, CIK, tickery i klasy; nie publiczny skaner całego EDGAR |

Nowa struktura TS: `CalendarItem = MacroItem | EarningsItem`, z
discriminatorem `domain: 'macro' | 'earnings'`. MacroItem owija obecny
CalendarEvent, EarningsItem ma company/period/event/temporal/status i
opcjonalne podsumowanie finansowe. Nie dodawać `series=[]`, losowego
release_id lub importance=medium, aby zaspokoić istniejący typ. Pola
nullable mają jawne statusy/precision; API nigdy nie obiecuje liczby
z samego receipt bez powiązanej zatwierdzonej wartości SQL.

Filtry **Makro / Wyniki spółek / Wszystkie**, osobna kategoria Earnings
i multiselect tickerów. Domyślnie zachować Makro i aktualny stan filtrów.
Filtr makro ★★★ działa w domenie makro, bez ukrywania earnings jako
„unknown importance”. Dla earnings wystarcza watchlista. Ewentualna
przyszła klasyfikacja spółek musi mieć oddzielną politykę: m.in. udział
w indeksie z licencjonowanego źródła i datą as-of, powiązania sektorowe,
płynność i koncentracja. E1 nie ustala gwiazdek spółek.

Minimalny wiersz: **data/sesja/status po lewej; ticker, nazwa i fiscal
quarter po prawej**, dostęp do szczegółów. Bez pełnego komunikatu i trzech
prawie identycznych wierszy. Published/partial/corrected są odróżnialne.
W szczegółach revenue i jawny EPS GAAP, później adjusted/guidance oraz
komparatory z nazwą okresu. Makro Actual/Previous/Forecast i minimalistyczne
Overview pozostają zgodne z obecną semantyką. Nie dodawać earnings do
Overview bez osobnej decyzji o rankingu i czterech slotach.

Agregator powinien zwracać `macro_data_revision`, `earnings_data_revision`
i assembled_at. Nie deklarować wspólnej atomowej generacji, jeżeli domeny
odczytano z różnych transakcji. Docelowy pojedynczy snapshot SQL wymaga
przekazania wspólnego połączenia czytnikom, testu isolation i jawnego
zakresu E2; obecny calendar_agenda sam zarządza połączeniem. Osobna
projekcja earnings nie może podszyć się pod publication_id Overview.

## 11. Dwa procesy i ograniczone odświeżanie

**Discovery terminów:** odczyt oficjalnych zapowiedzi/eventów; porównanie
stanu confirmed/changed/cancelled oraz komponentów. **Discovery wyników:**
wyszukanie własnego release, walidacja okresu i liczb, późniejsze powiązanie
8-K/10-Q. Sukces pierwszego procesu nie jest sukcesem drugiego.

Proponowana polityka startowa do zatwierdzenia w E2:

- E2A: discovery dat maksymalnie raz na 21600 s na emitenta przy aktywnej
  aplikacji; jeden odczyt właściwej strony zapowiedzi/eventów, bez crawlera.
  Jawny backoff wydawcy ma pierwszeństwo. Brak oficjalnej daty jest stanem,
  a nie powodem ciągłego odpytywania.
- E2B: wyniki kontrolować w dotychczasowych dozwolonych jobach, nie częściej
  niż standardowe 900 s, z osobnym małym budżetem trzech pilotów. Nie czekać
  na 10-Q przed przyjęciem poprawnego IR. Uzupełnianie filings robić wolniej,
  np. przy kolejnej kontroli 21600 s, i zatrzymać zbędne żądania znanego
  accession. To propozycja kadencji, nie zmiana globalnych interwałów.
- Szybsze okno zostawić osobnej decyzji po pomiarach. Jeśli potrzebne,
  wymaga własnej polityki exact/AMC/BMO, trwałych rezerwacji, końca okna
  i wspólnego budżetu SEC. Sam call nie ustala startu okna release; AMC
  nie daje jednej dokładnej chwili. Nie kopiować T/+2/+5/+10/+20 BEA.

Można współdzielić istniejącą blokadę launch 726530019, kolejkę pracy i
pojedynczy mechanizm deadline UI. Trzeba jednak mieć osobne resource/scope,
stan earnings i terminy, tak aby rezerwacja spółki nie zmieniała liczników
GDP/PIO, pełnego cooldown lub cache makro. Worker rezerwuje kontrolę
trwale pod blokadą przed HTTP; restart i druga karta nie zerują limitu.
Początkowo nie tworzyć demona ani drugiego timera React. Backendowy
deadline może uwzględniać earnings dopiero po udowodnieniu zgodności R1–R3.

Cały budżet joba to nie limiter dostawcy: osobno SEC 1 rps/jedno in-flight,
osobno oszczędny per-host IR i Retry-After. Po błędzie parsera nie zmieniać
automatycznie kanału na scraping innej strony. HTTP 403 wymaga diagnozy;
429/503 backoff musi przetrwać rollback danych. Cache known accession/hash
ogranicza koszty, ale ETag/200/nowy hash nie potwierdzają wyniku.

Bez procesu działającego w tle aktualizacja jest demand-driven: backend
i aktywne żądania aplikacji muszą działać. Uśpienie, ukryta karta, throttling,
lock i sieć mogą opóźniać kontrolę. Nie jest to gwarancja natychmiastowego
Actual ani pełnej historii wszystkich publikacji intraday. E1 nie mierzył
latencji źródeł lub czasu nowej publikacji.

## 12. Dwadzieścia przypadków granicznych i przyszłe testy

To oczekiwane zachowania E2 i propozycje testów; nie istniejący importer.

| # | Przypadek | Deterministyczne zachowanie / asercja przyszłego testu |
| --- | --- | --- |
| 1 | Brak ogłoszonego terminu | unknown, null daty i czasu; brak wymyślonego wpisu na osi; widoczny status watchlisty |
| 2 | Prognoza agregatora | E2A odrzuca jako oficjalne potwierdzenie; ewentualny przyszły estimated zawsze osobny i opisany |
| 3 | Zmiana daty | Ten sam event_id; nowy confirmation supersedes stary; jedna aktualna pozycja i historia zmiany |
| 4 | Release przed call | Actual dostępny z release; call pozostaje późniejszym komponentem, nie blokuje wyniku |
| 5 | Call jest, wyników brak | Potwierdzona konferencja i pending results, brak Actual; zegar call nie ogłasza published |
| 6 | 8-K późniejszy niż IR | Przyjąć zatwierdzony IR; dopiąć filing bez drugiego eventu i bez cofania capture |
| 7 | 10-Q po kilku dniach | Uzupełnić dowód; różnicę porównać po okresie/metodzie, ewentualna rewizja zachowuje release |
| 8 | GAAP i adjusted różne | Dwie miary z etykietami/reconciliation; podstawowy EPS GAAP, bez zamiany na korzystniejszy |
| 9 | Guidance bez EPS | Revenue/op income guidance mogą istnieć; EPS guidance null/not_provided, nie zero |
| 10 | Inny rok fiskalny | Użyć FY i granic emitenta; NVDA Q3 FY2027 nie nazywać kalendarzowym Q3 2026 |
| 11 | Strata | Ujemny NUMERIC, poprawny znak i precision; nie null i nie wartość bezwzględna |
| 12 | Miliony i miliardy | Normalizacja Decimal/skali z zachowaniem raw; identyczna wartość nie tworzy rewizji liczby |
| 13 | Segmenty revenue | Osobne scope/segment; AWS/Data Center nie zastępują consolidated, eliminacje nie znikają |
| 14 | Comparative po splicie | Wymaga zgodnej split basis i własnego dowodu; brak zgodności wyłącza wyliczenie zmiany |
| 15 | Korekta danych | Append-only wersja z supersedes/reason; dawny capture i dokument nadal osiągalne |
| 16 | Zmiana tickera | Ten sam company_id/CIK i okresy; historia aliasów, wyszukiwanie bez duplikowania raportów |
| 17 | Różne timestampy dokumentów | IR published, SEC accepted i capture pokazane osobno; nie wybierać wcześniejszego jako „first internet” |
| 18 | Brak dokładnej godziny | date_only/session, UTC null, brak 00:00 i fikcyjnego 16:00; jawna niepewność dnia PL |
| 19 | USA po sesji, PL następny dzień | Dla znanej chwili grupować po Europe/Warsaw; test 19:30 NY→01:30 PL dnia następnego |
| 20 | Brak licencji konsensusu | consensus/surprise null, brak beat/miss; guidance nie wypełnia estimate |

Dodatkowe testy konieczne przed E2B: 8-K bez 2.02, EX-99.1 o innym okresie,
niezgodny CIK, 3M vs 9M, brak jednej miary, obcy redirect, HTML zmieniony,
liczba z footnote zamiast tabeli, sporny PST/EDT, 403 bez retry loop,
429 Retry-After i 503, duplicate capture oraz nieznana kolejność rewizji.

Na rzeczywistym PostgreSQL, w osobnej losowej bazie testowej: fresh/upgrade
przyszłego schematu, unikalność emitenta/okresu/eventu, nullable date/time,
precision CHECK, NUMERIC i EPS ujemny, oba powiązania emitent–okres–dowód,
amendments, idempotencja, rewizje, błąd SQL/rollback i dwie instancje workera
z jednym lease. Testy HTTP syntetyczne i z obecnym guardem H1; nie wysyłać
żądań do SEC/IR w CI. Testy React: EN/PL, Macro/Earnings/All, tickery,
nieznany czas, jeden wiersz, source details, Escape/fokus i brak regresji
minimalistycznego Overview, filtrów dat oraz K2. Pełne istniejące testy
i build dopiero dla zmian E2; audyt E1 ich nie zastępuje.

## 13. Backlog ośmiu emitentów — bez integracji

Sprawdzono oficjalne landing pages i wskazane strony wydarzeń. Priorytet
jest redakcyjną kolejnością dalszego badania: kanał cloud/consumer/semis,
pokrycie szerokiego rynku, jakość źródła i trudność parsera. Nie zmierzono
wag indeksowych, korelacji ani wpływu cenowego; nie jest to nowy rating
gwiazdkowy. Żadna przyszła data nie została wyznaczona z częstotliwości.
Warunki użycia każdego z tych źródeł wymagają osobnego audytu.

| Spółka | Oficjalne IR / kalendarz | Widoczność kalendarza / prawdopodobny format | Szczególna trudność | Priorytet |
| --- | --- | --- | --- | --- |
| MSFT | [Microsoft Investor](https://www.microsoft.com/en-us/investor/default) | Earnings hub/raporty dostępne; osobny przyszły kalendarz NOT VERIFIED; HTML i raporty | FY inne niż kalendarzowe, cloud i segmenty, GAAP/adjusted definicje | P1: znaczenie cloud i dobry oficjalny hub |
| AAPL | [Apple IR](https://investor.apple.com/investor-relations/default.aspx) | Quarterly reports/news/SEC; przyszłe wpisy kalendarza NOT VERIFIED; HTML/PDF do walidacji | Fiscal year i tygodniowe granice okresów, produkty/usługi i regiony | P1: kanał konsument/technologia, silne źródła pierwotne |
| GOOGL/GOOG | [Alphabet IR](https://abc.xyz/investor/), [Events](https://abc.xyz/investor/events/default.aspx) | Strona Events istnieje, część treści dynamiczna; wyniki i SEC dostępne | Dwie klasy tickerów jednego emitenta; segmenty i zmiany definicji | P1: cloud/reklama i jedna integracja dla emitenta |
| META | [Meta IR](https://investor.atmeta.com/home/default.aspx), [Events](https://investor.atmeta.com/investor-events/) | Komunikaty/kwartały; Events „Stay tuned”, brak potwierdzonego przyszłego terminu w odczycie | Segmenty, expense/capex guidance, dynamiczne strony | P1: reklama/technologia, oficjalne release |
| TSLA | [Tesla IR](https://ir.tesla.com/) | Czytelna tabela kwartalna: earnings date, shareholder deck, webcast, SEC i consensus | Deliveries to inne wydarzenie; deck/PDF i adjusted; prawa do issuer-compiled consensus osobno | P2: dobre daty, większy koszt dokumentów i definicji |
| AMD | [AMD IR](https://ir.amd.com/), [IR Calendar](https://ir.amd.com/news-events/ir-calendar) | Oficjalne wpisy wyników i inne konferencje; HTML release, presentations | Odfiltrować konferencje branżowe; GAAP/non-GAAP i segmenty | P2: synergia z pilotem semis i czytelne IR |
| AVGO | [Broadcom IR](https://investors.broadcom.com/) | Quarterly results i Events & Presentations w nawigacji; konkretny przyszły termin NOT VERIFIED | Fiscal year, przejęcia/segmenty, adjusted i split basis | P2: semis/infrastruktura, osobna walidacja metod |
| ORCL | [Oracle IR](https://investor.oracle.com/home/default.aspx), [Events](https://investor.oracle.com/events-and-presentations/default.aspx) | Strona wydarzeń istnieje; przyszłe daty NOT VERIFIED; komunikaty HTML | Fiscal year, constant currency i różne EPS, guidance | P2 po czterech P1: cloud i dostępne źródła, dodatkowe definicje |

## 14. Decyzje produktowe przed E2

| Decyzja | Opcje | Rekomendacja | Powód | Ryzyko |
| --- | --- | --- | --- | --- |
| Jeden earnings czy osobny call | 1 agregat / 2 wpisy / filing jako wpis | Jeden agregat, call i filings w szczegółach; gdy tylko call znany, jasno tak go nazwać | Mniej duplikatów, stabilny ID | Błędna etykieta może sugerować potwierdzony release |
| Niepotwierdzone daty | Ukryć / osobna sekcja / estimated w osi | E2A unknown poza osią, bez szacunków agregatorów | Nie udawać oficjalnego terminu | Mniej przyszłych pozycji jest poprawnym skutkiem braku dowodów |
| Nieznany polski dzień | Udawać midnight / data emitenta / osobna sekcja | Data emitenta z jawną niepewnością PL | Brak fikcyjnej godziny | Wymaga świadomej semantyki filtrów zakresu |
| Podstawowy EPS | GAAP basic / GAAP diluted / adjusted | GAAP diluted z atrybucją; adjusted osobno w E2C | Jednoznaczna miara pilota | Straty i rozwodnienie wymagają czytania tabel |
| Previous | QoQ / YoY / ostatni okres | Domyślnie nazwane „Rok wcześniej”, QoQ osobno | Q4 nie myli się z Q3 | Restatements/split mogą blokować porównanie |
| Guidance | Jedno pole / typed miary / brak | Typed revenue/EPS/op income/margin/capex w E2C | Zakresy i jednostki nie są wymienne | Więcej definicji i testów |
| Źródło szybkich Actual | Tylko SEC Facts / release IR+SEC / czekać 10-Q | Zweryfikowany release IR lub właściwy EX-99.1; filings uzupełniają | SEC Facts i 10-Q mogą być późniejsze | Dostęp IR i prawa wymagają bramek |
| First print i korekty | Nadpisywanie / append-only | First captured + wersje dowodów i liczb | Nie gubić wcześniejszego stanu | Nie gwarantuje pełnej historii first print/intraday |
| Konsensus | Scraping / licencjonowany / brak | Na start null i brak surprise/beat-miss | Brak właściwej umowy i metodologii | Mniejszy zakres funkcji, ale bez fałszywych porównań |
| Prawa i RAW | Pełne archiwum / facts+links / metadata-only | Jawna polityka per źródło i rola dokumentu; minimum dopuszczonych faktów | Publiczny dostęp nie przesądza retencji | Nierozstrzygnięte warunki mogą blokować automatyczne E2B |
| SQL | Rozbudować FRED / osobne earnings | Osobne tabele, wspólny dokument tylko gdy pasuje kontrakt | Fiscal period i GAAP nie są FRED vintage | Konieczna migracja/testy dopiero w E2 |
| Calendar | Nowy ekran / wspólna agenda | Wspólna agenda z typed union i filtrami domen | Mało zmian dla użytkownika | Filtr gwiazdek nie może przypadkiem chować earnings |
| Gwiazdki/Overview | Skopiować K2 / nowa polityka / brak | Brak earnings stars i automatycznego Overview w E2A/B | Skala makro nie opisuje emitenta | Przyszły ranking wymaga danych i decyzji |
| Krótkie okno refresh | Skopiować R3 / standard / nowa polityka | Najpierw standard i pomiar, potem osobna polityka | Calls i AMC nie mają tego samego zegara co BEA | Bez gwarancji latencji; wymagany limiter SEC |

Otwarte bramki: realny kontakt User-Agent i dostęp backendu po 403;
właściwe regulaminy IR/zakres minimalnych faktów i retencji; zachowanie
date-only w filtrach PL; kotwica call-only; polityka comparative/restatement;
kontrakt nowego endpointu i wspólnego snapshotu; dopuszczenie ewentualnego
krótkiego okna. To decyzje do osobnego E2, nie prośba o rozpoczęcie go teraz.

## 15. Małe etapy i kryteria akceptacji E2

**E2A — daty, trzy spółki.** Najpierw rozwiązać dostęp/prawa dla metadanych,
wybrać dokładne oficjalne źródła i jawny kontakt klienta. Nowy osobny model
company/period/event/date receipt, wspólny Calendar za filtrem domeny.
Akceptacja: rzeczywiste potwierdzenie co najmniej jednej zapowiedzi każdego
pilota, poprawne unknown przy braku nowej daty, brak generowanych terminów,
release/call odróżnione, test zmiany/odwołania i stabilnego ID, IANA/DST i
brak 00:00, brak podwójnych wpisów i regresji makro/K2/R1–R3. Jeśli oficjalna
data dopiero ma zostać ogłoszona, poprawnym stanem jest unknown, nie
fikcyjny przyszły wiersz. Read-only API bez HTTP do dostawców; walidacja
PostgreSQL na własnej usuwanej bazie oraz frontend EN/PL.

**E2B — revenue i GAAP diluted EPS.** Dopiero po zatwierdzeniu sposobu
pozyskania i minimalnego przechowywanego dowodu. Parsery dla trzech
emitentów, rozpoznanie okresu i miary, finansowe NUMERIC/FK/receipts,
idempotencja i rewizje. Akceptacja: dwa rzeczywiste okresy na firmę z
własnym źródłem, zła firma/kwartał/kolumna/GAAP odrzucone, strata i skala
poprawne, brak przypadkowego segmentu/YTD, IR przed 10-Q działa, późniejsza
korekta nie niszczy capture, błąd SQL zachowuje ostatni dobry stan.
Wszystkie 20 przypadków ma test lub jawny testowalny brak funkcji; consensus
i surprise null. Zakres kontrolowanego pierwszego importu i zgoda na bazę
użytkownika muszą wynikać z osobnego zlecenia, nie z samego E1.

**E2C — rozszerzenia.** Oddzielnie adjusted EPS z reconciliation, typed
guidance i segmenty, następnie małe partie kolejnych spółek według backlogu.
Akceptacja dla każdej miary: definicja, unit, fiscal target, źródło, prawa,
provenance i testy graniczne. Konsensus tylko jako odrębny, licencjonowany
projekt z cutoff as-of; nie warunek uruchomienia E2A/B. Ewentualny ranking
earnings i szybszy refresh także wymagają osobnej polityki.

Rozdzielenie dat od liczb **realnie zmniejsza ryzyko**: E2A nie potrzebuje
parsera EPS/reconciliation, comparative i guidance; ujawnia wcześniej
problemy źródeł, DST i dedupe. Nie usuwa jednak ryzyka licencji metadanych
ani błędu call-as-release. E2B nie może powstać przez dopisanie liczb do
opisu eventu lub JSON bez spójnego dowodu SQL. Nie rozpoczęto żadnego etapu.

## 16. Rejestr źródeł i granice walidacji E1

**Data kontroli wszystkich linków: 02.11.2026, Europe/Warsaw.** Dokładne
adresy sześciu release, trzech zapowiedzi/eventów oraz accession SEC są
przy dowodach w sekcji 3. Parametry i daty zapowiedziane przez emitentów
nie są nowymi danymi zapisanymi w aplikacji. Źródła dokumentacji i praw
podano w sekcjach 4–5, konsensusu w 7.1, backlogu w 13.

| Zbiór źródeł | Zakres potwierdzony | Ograniczenie |
| --- | --- | --- |
| NVDA Q1/Q2 FY2027 IR + SEC 8-K/10-Q | Revenue, obie odmiany EPS, Data Center, guidance, fiscal period i relacje dokumentów | Q3 17.11 to event/webcast; dokładny release NOT VERIFIED; RSS HTTP 403 |
| AMZN Q2/Q3 2026 IR + SEC | Net sales, diluted GAAP EPS, AWS, guidance sales/op income, Q3 call | Adjusted EPS i EPS guidance NOT VERIFIED; następny przyszły termin NOT VERIFIED |
| INTC Q2/Q3 2026 IR + filings | Revenue, GAAP/non-GAAP EPS, reconciliation, guidance i okresy | Sprzeczny PST widgetu, przyszły termin nieobecny; część filings czytana przez oficjalną kopię IR |
| [NVIDIA quarterly hub](https://investor.nvidia.com/financial-info/quarterly-results/default.aspx), [Intel Q3 event](https://www.intc.com/news-events/ir-calendar/detail/20261029-q3-2026-intel-corporation-earnings-conference-call), [Q2 event](https://www.intc.com/news-events/ir-calendar/detail/20260723-q2-2026-intel-corporation-earnings-conference-call) | Linki do webcastów, prezentacji/komentarzy/filings | Nie wdrożono parsera slajdów, PDF, audio lub transkrypcji; nie zachowano archiwum |
| [SEC API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [Developer](https://www.sec.gov/about/developer-resources), [Access EDGAR](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), [CIK mapping](https://www.sec.gov/files/company_tickers.json) | Publiczny model API, fair access, mapowanie CIK i filing metadata | Trzy runtime Submissions 403; Company Facts i operacyjny feed NOT VERIFIED |
| NVIDIA/Intel terms, Amazon próba terms, Copyright Office | Różnica publicznego dostępu, faktów i kopiowania dokumentów | Brak formalnej opinii prawnej i potwierdzonej licencji całego rozwiązania |
| FactSet i LSEG | Potencjalne legalne produkty konsensusu | Brak umowy, tokena, testu feedu lub redistribucji |
| Osiem oficjalnych IR backlogu | Jakość landing pages, linki do wyników/eventów | Bez implementacji, licencji i domniemanych przyszłych dat |

Nie ustalono pełnego mapowania XBRL tag/context dla wszystkich firm,
historycznej kompletności Submissions, SLA dostawców, stabilności HTML,
licencji consensus, dostępności przyszłych dat AMZN/INTC ani pełnego
annual parsera 10-K. Dokumentacja potwierdza możliwości techniczne,
a nie zakończoną integrację. Same błędy 403 nie ustalają ich przyczyny.

Wykonano odczyt kodu/schematu, umiarkowane sprawdzenie publicznych źródeł
i powyższe konwersje czasu w pamięci. Nie uruchamiano 1163/644 testów dla
dokumentu, aplikacji, Chrome UI, jobów CI, importerów lub koordynatora.
Nie wykonano SQL, DDL, migracji, inicjalizacji, backfillu, POST refresh,
zapisu do bazy, RAW/cache albo nowych helperów w repozytorium. Wcześniejsze
zielone CI K2 nie są nowymi wynikami E1. Jedynym nowym plikiem jest raport.

## 17. Końcowa ochrona plików i Git

Porównanie wykonano ponownie po napisaniu raportu: wszystkie **12 plików**
ma identyczne bajty i SHA-256 względem początku E1. Nie przywracano
historycznej wersji CSS lub innych wcześniejszych poprawek użytkownika.

| Plik zastany | SHA-256 przy wejściu | Po E1 |
| --- | --- | --- |
| `README.md` | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` | identyczny |
| `frontend/src/brief/EconomyBrief.tsx` | `017f87c9f580a10c7125e14cb0415f1556c2fcaa2724295f943eef26b82dfcc1` | identyczny |
| `frontend/src/brief/EconomyBrief.test.tsx` | `bb5c2f6adac6d3c182e893e0d58fa32ff711aee9d7722feaad0d67ad7c598ed5` | identyczny |
| `frontend/src/brief/SourceCheckStatus.tsx` | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` | identyczny |
| `frontend/src/brief/SourceCheckStatus.test.tsx` | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` | identyczny |
| `frontend/src/calendar/CalendarPage.tsx` | `92fe810add14ec6ba952be5fc12a8e1c2ddea7417891a98454af0a49d3d3d5c9` | identyczny |
| `frontend/src/calendar/CalendarPage.test.tsx` | `4e62ca7c6345190a79048dfaa09dd6178e76e141f3e6695607c4eba5edf637d9` | identyczny |
| `frontend/src/calendar/calendarAgenda.ts` | `57c84376346095d0beb65b3535105cf21dea2221c8705c85d0e004a0d1ece5f0` | identyczny |
| `frontend/src/styles.css` | `40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c` | identyczny |
| `docs/audits/calendar-event-impact-audit-2026-10-30.md` | `35e876926cea3c82e3b2df837876d6fb3cabd82ba55db67a4de7ad06159f6f1d` | identyczny |
| `docs/audits/calendar-next-releases-priority-2026-10-29.md` | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` | identyczny |
| `docs/audits/calendar-release-day-latency-2026-10-29.md` | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` | identyczny |

Cały istniejący tracked diff również jest identyczny: SHA-256 wyniku
`git diff --binary` przed i po:
`d6b0fa5d3916fe8db9c6f4e13a447eb6c402f59d797f5cf39d5d670f716d24c0`.
Indeks pozostaje pusty. HEAD i gałąź pozostają
`14e4829d79f3f4f0916629a560cfc0cf2a122836`, `main`.
`git diff --check` oraz osobna kontrola whitespace nowego raportu przeszły.

Końcowo **9 modified / 4 untracked**. Trzy wcześniejsze untracked zachowano;
czwartym jest wyłącznie raport E1:

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
?? docs/audits/calendar-event-impact-audit-2026-10-30.md
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
?? docs/audits/calendar-release-day-latency-2026-10-29.md
?? docs/audits/equity-earnings-calendar-source-audit-2026-11-02.md
```

**Brak zmian kodu, konfiguracji, zależności, danych i bazy.** Nie wykonano
stagingu, commita, pusha, resetu, clean, amend ani zmiany historii.
Nie dodano helperów, RAW, logów, cache, sekretów lub artefaktów przeglądarki.
Nie rozpoczęto E2; warunki uruchomienia pozostają opisanymi rekomendacjami.
