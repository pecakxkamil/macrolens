# MacroLens — E2B: oficjalne wyniki finansowe i tabela Earnings

Wykonano **03.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`, `main`,
HEAD **`c2898345a320496af2d11ce3b12ba1bc0b3d5f31`** —
`Add earnings calendar pilot and safe activation`.

**E2B działa i został sprawdzony w izolacji. Nie aktywowano danych finansowych
w normalnej bazie `localhost:5432/macrolens`.** Sekcje 1–12 opisują implementację
zakończoną bez stagingu, commita i pusha; osobne zamknięcie repozytorium
na późniejsze zlecenie użytkownika opisuje sekcja 13.
To manualny zestaw oficjalnych faktów, bez produkcyjnego feedu SEC/IR.

## 1. Stan wejściowy i ochrona

Potwierdzono HEAD, main, pusty indeks oraz **9 modified / 4 untracked**.
Zapisano pełny zastany diff i SHA-256 wszystkich 13 zastanych plików.
Przejrzano E1, E2A, Activation, politykę K2, istniejący model i czytniki,
komponenty, testy oraz procedury PostgreSQL. Chronionych plików nie zmieniono.
CalendarPage nie wymagał edycji: poprzedni tydzień i cały zastany diff pozostały.

Odczyt normalnej bazy potwierdził rolę macrolens, OID **16384**, klaster
**7682090371041935398** i sześć tabel E2A: 3 companies, 3 aliases, 6 periods,
6 events, 5 source evidence, 12 date confirmations. Nowych tabel finansowych
tam nie ma. Wszystkie połączenia diagnostyczne miały wymuszony read-only.
Nie uruchamiano normalnego UI, apply, refresh, inicjalizatora lub importera.

## 2. Zachowanie tabeli

**Domyślnie wszystkie rzeczywiście zapisane spółki**, bez panelu tickerów,
checkboxów NVDA/AMZN/INTC i komunikatu „Brak wyboru”. Żądanie widoku nie
przesyła ograniczenia tickerów. `/earnings/companies` czyta SQL, zamiast
zwracać stałą listę importerów. Opcjonalny filtr API waliduje składnię
symboli, nie ogranicza czytnika do trzech pilotów. Syntetyczna czwarta spółka
przeszła test PostgreSQL/API i test komponentu bez zmiany listy w UI.
Kontrolowana allowlista importera E2A i finansowego pozostaje ograniczona.

Jeden nagłówek tabeli: Spółka, Czas wyników · Polska, EPS GAAP
Actual / Prognoza, Przychody Actual / Prognoza, Status, Szczegóły / Źródło.
Wiersz ma ticker, nazwę i kwartał emitenta. Liczby są wyrównane do prawej.
Nie ma kolorów ani etykiet beat/miss. Nie ma Previous, YoY lub QoQ.

| Element | Stan E2A | Stan E2B |
|---|---|---|
| Domyślny wybór spółek | Wszystkie przy pustym wyborze, panel tickerów | Wszystkie, bez checkboxów |
| Widok Earnings | Wiersze wydarzeń | Zbiorcza tabela |
| Revenue | Brak | Oficjalne Actual |
| GAAP EPS | Brak | Oficjalne Actual |
| Forecast | Brak | Null, w UI `—` |
| Surprise | Brak | Brak obliczeń i pól, semantycznie niedostępne |
| Godziny | E2A | Bez zmian |
| Źródła | Potwierdzenia dat | Daty i dokumenty finansowe |

Wszystkie zachowuje osobne bloki makro i Earnings; nie miesza EPS z CPI/NFP.
Nie zmieniano istniejącego renderera makro lub hooka. Zmiana Earnings → Wszystkie
nie wywołuje ponownego GET Earnings. Szczegóły korzystają z już pobranych danych.
Odczyt GET kalendarza przy zmianie zakresu nie jest pobieraniem wyników od IR.
Nie dodano wyszukiwarki, paginacji ani wirtualizacji bez potrzeby.

## 3. Fakty i ponownie sprawdzone oficjalne źródła

Ręcznie otwarto **każdy z sześciu aktualnych komunikatów**. Sprawdzono
bieżącą kwartalną kolumnę, koniec okresu, jednostki, przychody skonsolidowane
i GAAP diluted EPS. E1 posłużył do znalezienia dokumentów; nie zastąpił
ponownego odczytu. Nie kopiowano pełnych komunikatów do repozytorium lub RAW.

| Spółka | Okres / period_end | Revenue Actual, mln USD | GAAP diluted EPS Actual, USD/akcję | Źródło | Status weryfikacji |
|---|---|---:|---:|---|---|
| NVDA | Q1 FY2027 / 26.04.2026 | 81 615 | 2,39 | [Release 20.05](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-First-Quarter-Fiscal-2027/default.aspx) | Ręcznie 03.11.2026 |
| NVDA | Q2 FY2027 / 26.07.2026 | 96 221 | 2,46 | [Release 26.08](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2027) | Ręcznie 03.11.2026 |
| AMZN | Q2 2026 / 30.06.2026 | 200 606 | 5,75 | [Release 30.07](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Second-Quarter-Results/default.aspx) | Ręcznie 03.11.2026 |
| AMZN | Q3 2026 / 30.09.2026 | 201 944 | 1,89 | [Release 29.10](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Third-Quarter-Results/default.aspx) | Ręcznie 03.11.2026 |
| INTC | Q2 2026 / 27.06.2026 | 16 128 | −2,16 | [Release 23.07](https://www.intc.com/news-events/press-releases/detail/1776/intel-reports-second-quarter-2026-financial-results) | Ręcznie 03.11.2026 |
| INTC | Q3 2026 / 26.09.2026 | 16 513 | 0,60 | [Release 29.10](https://www.intc.com/news-events/press-releases/detail/1786/intel-reports-third-quarter-2026-financial-results) | Ręcznie 03.11.2026 |

NVIDIA to rok fiskalny 2027 z końcami okresów w 2026. Nie przepisano tych
wyników do przyszłego Q3 FY2027. Ten event z 17.11 zachowuje puste Actual.

Amazon: **Total net sales**, nie AWS; wartości z trzech miesięcy, nie 6M/9M
lub TTM. Intel: skonsolidowane Net revenue, nie suma segmentów przed
eliminacjami. EPS Intela to **diluted attributable to Intel**. Q3 basic
0,63 nie zastępuje diluted 0,60; Q2 −2,16 nie zastępuje non-GAAP 0,42.
Metodologia zachowuje odrębność przypisania do Intel; nie przeliczano EPS
z zysku/liczby akcji. NVIDIA używa GAAP, nie kolumn non-GAAP.

W konfiguracji zapisano wyłącznie minimalne fakty i identyfikujące metadane:
oficjalny URL, CIK, FY/kwartał, period_end, datę release, rodzaj dokumentu,
verified_on i manualną wersję przeglądu. SEC accession pozostaje null:
w E2B podstawą wartości jest bezpośredni komunikat IR; nie przeprowadzono
ponownej kontroli filingów SEC. Nie dopisano fikcyjnego HTTP 200, fetched_at,
first_seen, RAW hash ani dokumentu do publisher_documents.

## 4. Jednostki, brak konsensusu i status

PostgreSQL używa NUMERIC; importer konwertuje **Decimal**. Źródłowe revenue
jest w USD_millions, z precision=0; wartość kanoniczna to USD, np.
201944 × 1 000 000 = 201944000000. EPS ma USD/share i precision=2;
zero i wartość ujemna są dozwolone. UI skaluje revenue do mld/bn albo mln/m,
zwykle do dwóch miejsc; szczegóły zachowują dokładną źródłową kwotę i jednostkę.
Przykład UI AMZN Q3: **201,94 mld USD**, EPS **1,89 USD**.

`revenue_consensus=null`, `eps_consensus=null`; brak obliczeń surprise,
procentowych odchyleń i beat/miss. Guidance nie wypełnia prognozy.
Brak danych jest `—`, nie 0. Widok szczegółów opisuje niedostępny konsensus.

Zweryfikowany earnings release z co najmniej jedną miarą daje
`financial_publication_status=published`. `financial_data_status` rozróżnia
complete, partial i unavailable. Wynik częściowy nie uzupełnia brakującej miary.
Stare pole E2A `publication_status=unconfirmed` pozostaje zgodne ze starym
kontraktem i CHECK; finansowa publikacja ma odrębne, jawne pole i status w UI.
Zapowiedź ani upływ godziny nie oznaczają opublikowania wyników.

## 5. Nowy model i historia

DDL tworzy **wyłącznie dwa nowe obiekty tabelaryczne**:

| Tabela | Odpowiedzialność |
|---|---|
| earnings_financial_documents | Firma/CIK, okres/event, period_end, release_date, URL, typ, optional accession, verified_on, metoda, source_version, dostępność i captured_at |
| earnings_financial_observations | Miara, źródłowa i kanoniczna kwota/jednostka, USD, precision, metodologia, dokument, version, supersedes, correction_reason, captured_at |

Dochodzą ich constraints/indeksy, jedna funkcja `earnings_financial_guard()`
i cztery triggery: kontrola INSERT/UPDATE/DELETE oraz TRUNCATE dla obu tabel.
Nie ma ALTER tabel E2A, DDL makro, schedulera, nowych zależności lub CI.

Złożone FK łączą company/CIK, period/company, event/company oraz
document/event/period/company. Trigger dodatkowo kontroluje zgodność
period_id z eventem i period_end dokumentu z okresem. Nie da się zamienić
kwartału w obrębie tego samego emitenta. SQL sprawdza metryki, USD,
jednostki, skalowanie, precision, skończoność wartości i przypisanie EPS.

UPDATE, DELETE i TRUNCATE historii są blokowane. Bieżąca miara to najwyższa
version dla event/metric, chroniona UNIQUE i wymaganiem wskazania dokładnie
poprzedniej wersji w supersedes. Nie ma drugiego mutowanego wskaźnika current.
Trigger blokuje event podczas wersjonowania; importer używa dotychczasowego
locka ręcznych importów 726530020. Stary znany fingerprint nie reaktywuje się
po korekcie. Nowa wersja wymaga jawnego correction_reason. Fingerprint jest
hashem **lokalnego rekordu metadanych**, nie bajtów IR. Captured_at jest czasem
lokalnego zapisu, nie pierwszej dostępności w internecie.

Importer waliduje całą partię przed zapisem i zapisuje ją w transakcji.
Odrzuca obcy CIK/ticker/host, mylne FY/kwartał/label, sprzeczny period_end,
nieobsługiwaną metodologię, non-GAAP, segment, walutę, jednostkę i prognozy.
Nie ma klienta HTTP, discovery lub parsera HTML. Nie przedstawia się
syntetycznych testów jako potwierdzenia produkcyjnego feedu.

Sześć raportów wymaga **czterech nowych historycznych periods/events**:
NVDA Q1/Q2 FY2027, AMZN Q2, INTC Q2. Istniejące AMZN/INTC Q3 są używane
przez te same ID. Nie modyfikuje się żadnego zastanego wiersza E2A; nie
dodaje się fikcyjnych date confirmations do historii. Po seedzie w izolacji:
3 companies, 3 aliases, **10 periods, 10 events**, 5 date evidence,
12 confirmations, **6 financial documents / 12 observations**.

## 6. Daty i API

Zachowano osobne release i call oraz hierarchię exact/approximate/AMC/BMO/
date_only/unknown. Nie zmieniono pliku config/earnings_manual.json.
NVDA: **ok. 22:20 — wyniki**, call **23:00**; INTC: **21:00+**, call **22:00**;
AMZN: godzina release nieznana, call **22:00**. Orientacyjne godziny i okna
sesji nadal nie gwarantują publikacji. Konwersje E2A nadal używają IANA.

Dla czterech nowych historycznych raportów znamy jedynie datę komunikatu
emitenta. Odrębne `financial_release_date` pozwala je pokazać w źródłowej
grupie dat, z jawnym nieustaleniem polskiego dnia/godziny. Nie powstaje
scheduled_at_utc ani sztuczna północ. Trzy przyszłe Q4 pozostają osobno
undated. Sortowanie: data, znany czas/granica okna, ticker, event_id;
nieustalone godziny po znanych. Grupy PL i dat emitenta pozostają rozdzielone.

Stare endpointy E2A pozostają. Lista i szczegóły dostają addytywne
revenue_actual / gaap_diluted_eps_actual (obiekt wartości z dowodem lub null),
historię, datę finansowego release, statusy i dwa jawne null konsensusu.
Decimal jest serializowany jako tekst, bez utraty dokładności w JSON.
Revision Earnings obejmuje także wartości i historię finansową; nie jest
publication_id Overview. Nie zmieniono starego endpointu makro.

Odczyty używają istniejącej REPEATABLE READ READ ONLY. Nie wykonują DDL,
importu, HTTP lub source checks. Przy **braku obu tabel E2B** czytnik zwraca
działające daty E2A i `financial_store_status=not_activated`, zamiast błędu
kalendarza. Niekompletny schemat finansowy powoduje kontrolowany błąd, bez
automatycznej naprawy lub milczącego pomijania uszkodzonych danych.

## 7. Desktop, telefon i dostępność

1366 px: wspólne kolumny i nagłówek, grupy dat, liczby po prawej.
390 px: ograniczony do tabeli poziomy scroll, opis przewijania i region
osiągalny klawiaturą. Status i źródła są dostępne po przewinięciu; brak
overflow całej strony. Nie próbowano ścisnąć wszystkich kolumn w 390 px.
Obejrzano zrzuty desktop EN i mobile PL.

Semantyczne table/thead/tbody, nagłówki scope, przycisk z nazwą firmy,
aria-expanded/controls, rozwijany wiersz szczegółów, Escape z przywróceniem
fokusu. Szczegóły zawierają czas i dokładność E2A, call, obie wartości,
źródła finansowe, źródłowe jednostki, verified_on, lokalny captured_at,
wersję i historię korekt. Nie deklarujemy pełnego audytu WCAG lub testu
konkretnym czytnikiem ekranu na podstawie samych kontroli DOM/Chrome.

## 8. Walidacja rzeczywiście wykonana

| Kontrola | Nowy wynik E2B |
|---|---|
| Pełny backend offline, końcowy przebieg | **1239 passed, 46,20 s** |
| Pełny frontend offline z no-network.cjs, Node 22.23.4 | **660 passed / 30 plików, 27,52 s** |
| TypeScript noEmit, Node 22 | passed |
| Production build, Node 22 | passed; największy chunk **407,04 kB**, próg niezmieniony |
| PostgreSQL E2B fresh i E2A → E2B | passed |
| Sześć wcześniejszych walidacji PostgreSQL | **6/6 passed**, nowe lokalne przebiegi |
| Chrome, izolowane rzeczywiste API/SQL | **121 kontroli**, **17 zakończonych odpowiedzi API 200**, zero JS/console errors |
| Whitespace, zależności, ochrona plików | passed |

Nowy backend ma 32 przypadki ponad 1207; frontend cztery ponad 656.
Nie usunięto przypadków E2A: w istniejących testach zmieniono oczekiwanie
checkboxa na brak checkboxów i jedno GET bez tickera; API testuje teraz
niepoprawną składnię zamiast odrzucania legalnego symbolu spoza pilota.
Static companies fixture zastąpiono mockiem czytnika SQL. Chronionych
testów użytkownika nie edytowano. Nie zwiększano timeoutów.

PostgreSQL sprawdził: fresh/upgrade, preflight read-only i cel, idempotencję
schematu ze zgodną sygnaturą, obcy podpis, partial, zero/ujemne EPS,
wersje, stare rekordy po korekcie, FK/CHECK/UNIQUE, cross-company i
cross-period, niezmienność historii, blokadę TRUNCATE, błąd SQL po
utworzeniu DDL i imporcie z rollbackiem **obu**, rollback całej późniejszej
partii oraz stary importer E2A. Odczyt przez rzeczywiste API i czwarta
syntetyczna firma także przeszły. Dane testowe nie trafiły do normalnej bazy.

Sześć regresji: Empire fresh/historyczny upgrade, FT900, BEA Direct,
BEA release/R3, E2A i Activation. Wszystkie użyły własnych losowych baz
na osobnym PostgreSQL 17 i istniejącego guarda publisher HTTP.
Workflow nie został zmieniony. **Nie uruchamiano GitHub Actions w E2B**;
wyniki CI poprzedniego commita nie są nowymi wynikami tego etapu.

Chrome używał produkcyjnego buildu 4187 i API 8017, własnej bazy na 55447,
bez fixture odpowiedzi. EN/PL, desktop/mobile, wszystkie trzy firmy,
sześć historycznych raportów, przyszła NVDA, unknown, źródła, godziny,
Escape/focus, Wszystkie i wiersze makro, zakresy i brak zbędnego GET.
Błąd sieci wywołano przez czasowe zablokowanie wyłącznie transportu do
endpointu Earnings; po odblokowaniu Retry pobrał prawdziwą odpowiedź.
Nie podstawiano JSON. Brak zewnętrznych żądań z aplikacji.

API miało wymuszone read-only, a osobne połączenie trzymało lease 726530019
na **izolowanej** bazie, blokując importer starego hooka. Source checks,
stan refresh, confirmations i cała projekcja obserwacji finansowych
pozostały identyczne przed/po UI. Makro w smoke działało na izolowanym
schemacie i własnych lokalnych harmonogramach, nie na produkcyjnych Actual.
Nie deklaruje to nowego pomiaru reakcji na żywą publikację.

Pierwszy Vite w sandboxie nie mógł zapisać tymczasowej konfiguracji;
ponowienie z właściwym dostępem przeszło. SQL wskazał brak nawiasów CASE
w funkcji; poprawiono przed poprawnym fresh/upgrade. Rozbudowany test SQL
ujawnił nadpisaną nazwę zmiennej w samym teście, poprawioną przed końcowym
przebiegiem. Jeden test TS wykrył kolejność nieznanej godziny w localeCompare;
zastąpiono ją jawnym kluczem porządku. Pierwszy helper Chrome szukał etykiety
Custom zamiast istniejącego Date range; poprawiono wyłącznie helper.
Nieudanych prób nie zaliczono jako sukcesów.

## 9. Normalna baza i zachowanie regresji

Odczyt wszystkich **19 tabel public**, uporządkowany po PK, porównał
SHA-256 binary COPY i liczby rekordów przed/po izolowanym smoke.
**2 772 694 rekordy, wszystkie identyczne**, w tym 35 rekordów E2A.
Wspólny hash zestawu:
`1ce86051bedd2dd29933da9034b095211e9620991d342977fbb4db7b20f0c4e4`.

Brak zapisów, DDL, seedów lub importu w normalnej macrolens.
Nie zatrzymywano jej kontenera ani procesów aplikacji. Nie zmieniano
observation_vintages, computed_features, publisher_documents, FRED/ALFRED,
BEA, K2 `2026-11-k2-v1` / 17/11/1, 29 rodzajów makro, 17 reguł Overview,
max4, R1–R3, T/+2/+5/+10/+20, 900/21600, atomic publication lub MCI/PIT.
Pełne testy istniejących mechanizmów przeszły. Zależności, lockfile, CI,
globalny CSS, lazy Overview i H1/H2 pozostają bez edycji.

Normalna baza nadal udostępnia tylko **E2A**, bez finansowych Actual E2B.
Nowy kod czytnika toleruje ten stan, ale nie aktywuje go przez GET.
Nie należy opisywać izolowanego sukcesu jako aktywacji w codziennej bazie.

## 10. Plan późniejszej aktywacji E2B — niewykonany

Dodano **wyłącznie odczytowy** `app/database/prepare_earnings_financials.py`.
Nie ma polecenia apply. Oddzielny initializer i CLI finansowy odrzucają
bazy poza `macrolens_earnings_e2b_`; stary initializer E2A jest identyczny.
Preflight wymaga jawnego target, porównuje tożsamość klastra/OID/roli,
schemat E2A/makro, brak kolizji finansowych i zgodność istniejących okresów.

Wykonany lokalny plan-propozycja:
`data/raw/earnings-e2b-2026-11-03/activation-proposal.json`, hash kanoniczny
**`f666291a4441c107b278f35f583bfe91b8cfea027291d337289759121799ec98`**.
Status **ready_for_apply=false**. To propozycja do dalszego przeglądu,
nie gotowy token pozwalający na zapis i nie zgoda użytkownika.

Plan przyszłego osobnego etapu:

1. Ponownie read-only potwierdzić localhost:5432/macrolens, macrolens,
   klaster 7682090371041935398, OID 16384, sygnatury i wartości E2A/makro.
   Zmiana celu/schematu/faktów wymaga nowego planu, przed zapisem.
2. Wykonać **świeży pełny pg_dump custom**, zapisać SHA/rozmiar/manifest
   celu, sprawdzić TOC i odtworzyć do własnej tymczasowej bazy. Starsza kopia
   sprzed aktywacji E2A nie jest aktualnym zabezpieczeniem E2B. W tej sesji
   nie wykonywano nowego backupu lub odtworzenia danych użytkownika.
3. Przygotować do przeglądu osobną ścieżkę apply: dokładny target i hash,
   zamrożone artefakty, oczekiwany schemat po izolowanej walidacji, limity
   lock/statement i jedna SERIALIZABLE transaction z dotychczasowymi
   lockami 726530019/726530020. Nie używać dawnego planu aktywacji E2A:
   obejmował inne artefakty i nie uprawnia do danych E2B.
4. Zakres DDL: tylko dwie nowe tabele finansowe, ich constraints/indeksy,
   funkcja i cztery triggery. Seed: sześć dokumentów i 12 miar, cztery
   brakujące historyczne periods/events. Zastane wiersze E2A bez UPDATE,
   nowe date confirmations nie są wymagane. Bez tabel EPS makro i scrapingu.
5. Przed pierwszym zapisem uzyskać **osobną wyraźną zgodę** na konkretny
   cel i kompletny plan po backup/restore. Nie wykonywać tego w E2B.
6. Apply ma porównać podpis istniejącego schematu; przy identycznym E2B
   pominąć DDL i idempotentnie sprawdzić seed. Częściowy/obcy schemat
   zatrzymuje operację. Błąd wycofuje nowe DDL, okresy, eventy i finanse
   razem — taki przypadek przeszedł w izolowanej walidacji.
7. Po COMMIT potwierdzić 6/12 finansów, 10 okresów/eventów, identyczne
   stare confirmations i makro, API/UI oraz brak duplikatów przy powtórce.
8. Cofnięcie po COMMIT wymaga oddzielnego przeglądu i zgody: usunąć tylko
   nowe finansowe obiekty bez CASCADE. Cztery dodane historyczne eventy/
   okresy usuwać wyłącznie według manifestu utworzenia i po wykluczeniu
   późniejszych zależności; nie usuwać istniejących AMZN/INTC Q3 lub dat.
   Niespodziewana zależność ma zatrzymać rollback. W razie pełnego odzyskania
   najpierw pg_restore --exit-on-error --single-transaction --no-owner
   --no-acl do nowej bazy, porównanie, potem osobna decyzja. Nigdy automatyczne
   nadpisanie macrolens lub utrata późniejszych zapisów.

## 11. Ograniczenia i następny krok

Nie rozwiązano operacyjnej/licencyjnej podstawy automatycznego pobierania
IR, retencji pełnych dokumentów, dostępu SEC po wcześniejszych 403 ani
Company Facts z backendu. Nie obchodzono ograniczeń i nie dodano proxy,
mirrora, automatycznego feedu lub szybkiego monitoringu. Ręczne odczytanie
publicznych faktów nie jest licencją do pełnego archiwum lub redystrybucji
komunikatów; nie przedstawiamy formalnej opinii prawnej. Konsensus wymaga
osobnego legalnego źródła. Nie badano zmian historycznych komunikatów
między wcześniejszą publikacją a dzisiejszym odczytem — to capture manualny,
nie gwarantowany first print lub kompletny restatement history.

Model dopuszcza późniejsze rewizje i poprawne porównania okresów, lecz nie
wylicza QoQ/YoY ani Q4 przez annual minus 9M EPS. Paginacja/wyszukiwanie,
kolejne firmy i źródła pozostają osobnymi decyzjami. Proponowany następny
krok to przegląd E2B i osobne przygotowanie zatwierdzanej aktywacji według
sekcji 10. Automatyzacja źródeł wymaga osobnego etapu po rozstrzygnięciu praw.

## 12. Pliki i końcowy Git

**16 plików E2B**, siedem modyfikacji i dziewięć nowych:

- app/api/earnings.py
- app/earnings.py
- app/earnings_financials.py — nowy
- app/database/earnings_financial_schema.sql — nowy
- app/database/prepare_earnings_financials.py — nowy
- config/earnings_financial_manual.json — nowy
- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/EarningsCalendar.test.tsx
- frontend/src/calendar/earningsTypes.ts
- frontend/src/calendar/earnings.css
- frontend/src/calendar/earningsFinancialPresentation.ts — nowy
- frontend/src/calendar/EarningsFinancials.test.tsx — nowy
- tests/test_earnings_dates.py
- tests/test_earnings_financials.py — nowy
- tests/postgres_earnings_financial_validation.py — nowy
- docs/audits/equity-earnings-financial-actuals-e2b-2026-11-03.md — ten raport

Chronione SHA-256 **przed = po**:

| Plik | SHA-256 |
|---|---|
| README.md | 7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b |
| EconomyBrief.tsx | 017f87c9f580a10c7125e14cb0415f1556c2fcaa2724295f943eef26b82dfcc1 |
| EconomyBrief.test.tsx | bb5c2f6adac6d3c182e893e0d58fa32ff711aee9d7722feaad0d67ad7c598ed5 |
| SourceCheckStatus.tsx | 65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900 |
| SourceCheckStatus.test.tsx | bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf |
| CalendarPage.tsx | 04d02ac84aac9d12ee78c604ab929ac47a5e189f43b2ec6f89cfae7659ef883c |
| CalendarPage.test.tsx | 4e62ca7c6345190a79048dfaa09dd6178e76e141f3e6695607c4eba5edf637d9 |
| calendarAgenda.ts | 57c84376346095d0beb65b3535105cf21dea2221c8705c85d0e004a0d1ece5f0 |
| styles.css | 40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c |
| calendar-event-impact-audit-2026-10-30.md | 35e876926cea3c82e3b2df837876d6fb3cabd82ba55db67a4de7ad06159f6f1d |
| calendar-next-releases-priority-2026-10-29.md | e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839 |
| calendar-release-day-latency-2026-10-29.md | e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b |
| equity-earnings-calendar-source-audit-2026-11-02.md | a6db1f1a877aacb9bc1980608d20a1d1f1609023d64e1a11ef8699ec659b1434 |

Końcowo **16 modified / 13 untracked**, main i HEAD bez zmian, indeks pusty.
Dziewięć wcześniejszych modyfikacji i cztery nieśledzone raporty zachowano
byte-identycznie; pozostałe wpisy to dokładnie E2B. Cały diff E2B i manifesty
są zachowane w ignorowanym `data/raw/earnings-e2b-2026-11-03/`; CalendarPage
nie ma patcha E2B, ponieważ nie był edytowany.

Po kontroli niezmienności stanu API zwolniono izolowany lease i zakończono
własne API, preview i diagnostyczny Chrome. Usunięto własne losowe bazy;
przed usunięciem kontenera sprawdzono jego pełny ID
`5072a5968ac8456db360cfbee122b5d31afe0c54b45b41d16ed4006024487462`,
etykietę earnings-e2b i brak pozostałych baz testowych. Usunięto wyłącznie
`macrolens_earnings_e2b_20261103` z jego anonimowym wolumenem.
macrolens_postgres i normalna aplikacja pozostały poza sprzątaniem.

Logi, build preview, zrzuty, propozycja aktywacji i helpery są ignorowane,
bez sekretów lub pełnych komunikatów w zakresie Git. Nie wykonano git add,
stagingu, commita, pusha, resetu, clean, amend, rebase lub formatowania globalnego.

## 13. Zamknięcie repozytorium E2B — 03.11.2026

Zgodnie z osobnym zleceniem przygotowano jeden commit
**Add official earnings financial actuals and table**, obejmujący dokładnie
16 plików E2B z sekcji 12 i minimalną zmianę `.github/workflows/ci.yml`.
Zastany HEAD/main był nadal c2898345a320496af2d11ce3b12ba1bc0b3d5f31;
na wejściu **16 modified / 13 untracked**, indeks pusty. Zapisano nowy
manifest wszystkich 29 zastanych plików oraz ponownie potwierdzono
wszystkie 13 chronionych hashy z tabeli wyżej.

Przejrzano schema SQL, append-only i złożone FK/okresy, aktualne projekcje,
walidację lokalnych faktów, idempotencję i korekty, brak HTTP, kontrakty
API, UI i źródła sześciu zatwierdzonych raportów. Kwoty, FY/kwartały,
period_end, skonsolidowany revenue i GAAP diluted EPS odpowiadają tabeli
sekcji 3 i zatwierdzonym rekordom. Nie dodano nowych raportów lub danych.
Przyszła NVDA ma nadal null Actual, 22:20 orientacyjne i call 23:00;
consensus pozostaje null, bez surprise, guidance jako forecast lub beat/miss.

Jedyna zmiana testowa zamknięcia rozszerza
`tests/postgres_earnings_financial_validation.py`: **rzeczywisty GET listy
i szczegółów na bazie z samym E2A**, przed DDL E2B, ma HTTP 200,
`financial_store_status=not_activated`, puste Actual i niezmienione
rekordy dat. Nie zastępuje to odpowiedzi API fixture'ami. Nie znaleziono
usterki produkcyjnej wymagającej zmiany kodu lub UI.

Workflow dostał dokładnie jeden krok:
**PostgreSQL Earnings financial actuals and revisions**,
`python tests/postgres_earnings_financial_validation.py`.
Pozostałe sześć kroków zachowano, razem **7/7**; ten sam PostgreSQL 17,
job-local service, kontrolna baza macrolens_ci_control i guard HTTP.
Backend/frontend jobs, dependencies, uprawnienia Actions i timeouty
pozostają bez zmian. **actionlint przeszedł**.

### Nowe lokalne testy zamknięcia

| Kontrola | Working tree | Dokładna kopia indeksu |
|---|---|---|
| Pełny backend offline | **1239 passed, 57,70 s** | **1239 passed, 46,37 s** |
| Pełny frontend offline, Node 22.23.4 | **660 passed / 30 plików, 29,59 s** | **658 passed / 30 plików, 28,38 s** |
| TypeScript noEmit | passed | passed |
| Production build, Node 22 | passed, 10,45 s | passed, 3,65 s |
| Największy chunk | **407,04 kB** | **407,04 kB** |
| PostgreSQL, wszystkie siedem skryptów | **7/7 passed** | **7/7 passed** |

Różnica dwóch frontendowych testów wynika z chronionego
CalendarPage.test.tsx: HEAD ma wcześniejszą wersję, working tree zachowuje
dwa dodatkowe przypadki użytkownika. Nie usuwano testów i nie dołączono
wcześniejszej pracy tylko dla wyrównania liczników. Pełne zestawy obejmują
E2A, K2, Overview i istniejące regresje R1–R3. Nie zmieniono timeoutów
lub globalnych guardów. Wyniki są nowymi przebiegami zamknięcia.

Siedem PostgreSQL skryptów uruchomiono osobno dla obu kopii na własnym
kontenerze PostgreSQL 17, loopback **55449**, z syntetycznymi danymi,
losowymi bazami i cleanup. W E2B ponownie przeszły fresh/upgrade, fallback
HTTP E2A-only, preflight read-only, schemat, FK, wersje, partial, rollback
DDL+seed, idempotencja, czwarta firma i zachowanie starego importera.
Makro, daty i historia E2A pozostały identyczne w testach.

### Ponowny Chrome i ochrona bazy

Kod **dokładnego indeksu**, osobny production preview 4189 i API 8019:
ponowiono **121 kontroli**, EN/PL, 1366/390 px,
**25 zakończonych odpowiedzi API 200**, zero JS/console errors i overflow
całej strony. Tabela pokazuje wszystkie firmy bez checkboxów, sześć
raportów i 12 Actual w USD, null Forecast, przyszłą NVDA i trzy unknown,
czas release/call, źródła, rozwijane szczegóły, Escape/focus, Wszystkie
z załadowanym makro i zakresy historyczne/przyszłe. Sprawdzono również
odtworzenie po kontrolowanym błędzie transportu przez prawdziwy Retry.
Nie było fixture odpowiedzi ani HTTP do wydawców.

Helper preview dodaje wyłącznie CORS dla własnego portu; API/SQL pochodzą
z indeksu. Wymuszono read-only i lease 726530019 wyłącznie na własnej
bazie. Normalna aplikacja nie była zatrzymywana lub zastępowana.
Odczyt normalnej bazy ponownie potwierdził ten sam klaster/OID/rolę,
**3 companies / 6 events / 12 confirmations** oraz **brak obu tabel E2B**.
Nie wykonywano na niej DDL, seedów, importów, apply E2A/E2B, rollbacku,
backup restore lub nowych Actual.

Pierwszy lokalny helper Chrome odczytał źródło jako domyślne kodowanie
Windows i uszkodził selektor z separatorem `·`; poprawiono tylko ignorowany
helper na jawne UTF-8 i ponowiono cały przebieg. Dodatkowy build preview
ostrzegał o outDir poza korzeniem; nie zmieniano konfiguracji i nie usuwano
katalogów projektu. Rzeczywisty kod procesu Vite potwierdzono jako 0.
Nieudanej próby helpera nie zaliczono jako sukcesu.

Po smoke porównano source checks, koordynator, potwierdzenia dat i wszystkie
obserwacje finansowe izolowanej bazy: identyczne. Zwolniono własny lease,
zakończono własne API/preview/Chrome i usunięto losowe bazy. Przed usunięciem
kontenera `macrolens_earnings_e2b_close_20261103` sprawdzono pełny ID
`a4d7a5646c82f6b735f8a5eab0c173bb0eb501750eb2373b65b60ed6b2ce214f`,
etykietę zadania oraz brak pozostawionych baz poza control/postgres/template.
Usunięto tylko ten kontener i jego anonimowy wolumen.

### Indeks, commit i granice aktywacji

Staging obejmuje **dokładnie 17 zatwierdzonych plików**. Wyeksportowano
cały indeks do osobnej kopii i potwierdzono wszystkie **322 blob IDs**
po normalizacji Git. Chronione pliki w tej kopii pochodzą z HEAD,
nie z zastanego working tree. CalendarPage i wszystkie 13 chronionych
plików pozostają poza stagingiem i byte-identyczne względem wejścia.
Przejrzano cały staged diff, nazwy, whitespace, wzorce sekretów i zależności.
Brak .env, RAW, kopii SQL, logów, zrzutów i helperów w commicie.
Obie kontrole diff --check przeszły. Nie używano git add ., reset, clean,
amend, force push ani zmian wcześniejszej historii.

Po testach aktualizowana jest jedynie ta dokumentacja i jej staging;
kod pozostaje zgodny z walidowanym indeksem. Pełny SHA, wynik zwykłego
pusha i URL oraz **zakończone** wyniki trzech jobów Actions zostaną podane
w odpowiedzi końcowej po ich uzyskaniu. Nie deklaruje się przyszłego
sukcesu CI i nie tworzy dodatkowego commita dla metadanych po pushu.

Propozycja aktywacji nadal ma **ready_for_apply=false**; hash z sekcji 10
nie jest zgodą na zapis. Nie dodano ścieżki apply. E2B finansowe pozostaje
nieaktywne w normalnej bazie do osobnego etapu z backup/restore i wyraźną
zgodą. Nie rozpoczęto SEC/IR feedu, konsensusu lub E2C. K2, ranking
Overview, R1–R3 i dane makro są poza zakresem zamknięcia.
