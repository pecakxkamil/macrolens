# MacroLens — Forecast F1: prognozy makro i wyników spółek

Wykonano **05.11.2026, Europe/Warsaw**, C:\Projects\macrolens, main,
HEAD **5b31cdb1ea042cd10483f701c262b85a958efc08**.

**Pilot z prawdziwych źródeł działał wyłącznie w izolacji PG17. Normalna baza
nie otrzymała DDL/importu F1. Nie uruchomiono normalnego odświeżania prognoz.**
Zachowano działający auto-monitor Earnings, Actual, Previous i Market Cap.
Bez stagingu, commita, pusha, kont, płatności lub kontaktowania dostawców.

## 1. Wynik i pokrycie

W izolacji zapisano **20 obserwacji prognoz: 16 model_nowcast i cztery
issuer_guidance; consensus = 0**. Earnings: **jedna prognoza EPS i trzy
Revenue**, dotyczące trzech emitentów. Nie są to cztery konsensusy.

Cleveland obejmuje październik/listopad 2026, CPI/Core CPI/PCE/Core PCE,
MoM i YoY, czyli 2×4×2 = 16. Do istniejących wierszy Calendar dopasowano
**14**: interfejs nie ma odrębnego wiersza headline PCE YoY. Nie dodano go.
W odczycie 01.11.2026–01.02.2027 jest 135 wydarzeń / 310 miar makro, w tym
20 potwierdzonych miar pięciu rodzin pilota. Spośród tych 20 **14 ma nowcast,
sześć pozostaje null**: cztery grudniowe CPI/Core CPI oraz dwa późniejsze
szacunki GDP Q3. GDPNow dotyczy Q4; nie wolno go przypisać do Q3 second/third.
Poza dopasowanymi 14 wszystkie pozostałe 296 miar w tym odczycie nie dostały
prognozy F1. Nie deklaruje się pokrycia całego kalendarza konsensusem.

Earnings, zakres 01.05–31.12.2026: 34 wydarzenia / 68 pól Current EPS/Revenue.
**Jedno Current Revenue ma guidance, 67 pozostaje null**: wszystkie 34 EPS
i 33 Revenue. Wszystkie 68 pól Previous Forecast pozostają null.
Guidance NVDA Q3 FY2027 można pokazać przed publikacją. Guidance QCOM Q4
FY2026 przejrzano po Actual: nie staje się historycznym snapshotem znanym
przed raportem. ARM Q3 FY2027 nie ma odpowiadającego eventu w rejestrze;
nie tworzono sztucznego wydarzenia tylko dla prognozy.

## 2. Audyt źródeł i uprawnień

Poniższe rozróżnienia dotyczą lokalnego, osobistego, niekomercyjnego MVP.
Publiczna dostępność nie jest sama w sobie licencją na feed lub komercyjną
redystrybucję. Oceny nie zastępują zgody dostawcy na inne zastosowanie.

| Źródło | Darmowy podgląd / dostęp | Automatyczny odczyt | Lokalne przechowywanie i wyświetlanie | Decyzja F1 |
|---|---|---|---|---|
| Cleveland Fed Inflation Nowcasting | HTML 200, bez klucza/konta, publiczne dane | Ograniczony adapter raz na dobę, robots sprawdzany przed pobraniem; niskie obciążenie. To interpretacja zamierzonego publicznego dostępu, nie kontrakt/SLA API | Warunki banku pozwalają na niekomercyjne, osobiste/edukacyjne wykorzystanie z atrybucją; brak zgody komercyjnej | W izolacji 16 nowcastów, link/atrybucja przy wartości |
| Atlanta Fed GDPNow | Strona 200, publiczny plik XLSX, aktualny odczyt 3,4% dla Q4 2026, aktualizacja 04.11 | Techniczny dostęp i robots nie stanowią osobnej licencji | Warunki dopuszczają reprodukcję niekomercyjną z atrybucją i zawierają prośbę o przesłanie kopii do Public Affairs | Konserwatywnie bez importu/wyświetlania i automatu, ponieważ kontakt wykluczono; osobno brak pasującego eventu Q4 |
| Philadelphia SPF | Publiczne raporty/Excel, ankieta profesjonalnych prognostów | Nie dodano adaptera; dane kwartalne wymagają kontroli horyzontu i wersji | Warunki dopuszczają cele informacyjne, edukacyjne/badawcze, z osobnymi ograniczeniami treści chronionych | Nie utożsamiono ankiety z miesięcznym konsensusem CPI/PCE; brak importu |
| FOMC SEP | Publiczne materiały projekcyjne | Dostępne dokumenty, bez wdrażania odświeżania w F1 | Źródło oficjalne, zakres i zastrzeżenia materiałów trzeba zachować | Roczne/Q4–Q4 projekcje uczestników nie zastępują miesięcznych prognoz lub kwartalnego QoQ SAAR |
| New York Fed Staff Nowcast | Publiczna strona i materiały badawcze | Bez nowego adaptera w tym MVP | Warunki wymagają zachowania źródła, notices i braku sugerowania poparcia banku | Rozpoznana alternatywa modelowa, nie konsensus; brak importu |
| TradingView Economic Calendar widget | Oficjalny kod osadzenia i bezpłatny widok | Osadzony widget, nie ekstrakcja własnego feedu; FAQ nie oferuje eksportu danych widgetów | Prawo do osadzenia nie oznacza prawa do przechowywania/przenoszenia liczb do własnych komórek | Nie osadzono ani nie scrapowano; zachowano istniejący wygląd |
| Investing.com Economic Calendar widget | Oficjalny generator iframe po akceptacji warunków | Osadzenie zgodnie z warunkami; bez nieoficjalnych endpointów | Warunki strony zastrzegają używanie, przechowywanie i ponowne wyświetlanie danych poza udzieloną zgodą | Bez ekstrakcji i bez importu |
| Alpha Vantage EARNINGS_ESTIMATES | Dokumentacja wymaga apikey. Oficjalny demo IBM rzeczywiście zwrócił JSON | Bez klucza błąd; demo dla AAPL zwróciło informację o ograniczeniu demo. Nie założono konta | Licencja osobista/niekomercyjna nie jest ogólnym prawem publicznej redystrybucji. Zachowanie archiwum i dostępność konkretnego endpointu trzeba zweryfikować odrębnie | Demo nie dowodzi darmowego dostępu do 53 firm; nie importowano IBM ani nie zadeklarowano niezweryfikowanego free tier |
| Finnhub EPS/Revenue estimates | Dokumentacja dostępna, dane wymagają tokenu | Oficjalny dokument HTML oznacza oba endpointy premium: Premium Access Required | Warunki zabraniają udostępniania danych/pochodnych osobom trzecim bez zgody; plany osobiste, usuwanie danych po końcu subskrypcji | Bez konta, płatności i importu |
| Oficjalny guidance emitentów / EDGAR | Zweryfikowane oficjalne dokumenty, bez klucza i konta | EDGAR udostępnia zasady fair access; nie dodano okresowego pobierania SEC bez zgodnego kontaktowego User-Agent i przejrzanego adaptera | MVP przechowuje małe ustrukturyzowane fakty z atrybucją, nie redystrybuuje pełnych komunikatów. Nie oznacza to licencji na całe załączniki lub komercyjny feed | Cztery ręcznie przejrzane obserwacje guidance, bez podszywania się pod konsensus |

GDPNow: prośba o przesłanie kopii została potraktowana zachowawczo jako
warunek wymagający wyjaśnienia. Nie twierdzi się, że sama ta prośba ustanawia
bezwzględny zakaz cytowania pojedynczego faktu. Nie kontaktowano banku.
Nie używano FinancialJuice scraperów, prywatnych Investing endpoints,
prywatnych API widgetów, rotacji tożsamości lub obejść 403.

Pierwotne dokumenty i warunki sprawdzone 05.11.2026:
[Cleveland dane](https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting),
[Cleveland warunki](https://www.clevelandfed.org/privacy),
[przewodnik metodologiczny Cleveland](https://www.clevelandfed.org/-/media/project/clevelandfedtenant/clevelandfedsite/indicators-and-data/inflation-nowcasting/nowcasting_users_guide.pdf),
[GDPNow](https://www.atlantafed.org/research-and-data/data/gdpnow),
[Atlanta warunki](https://www.atlantafed.org/en/terms-of-use),
[SPF](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters),
[Philadelphia warunki](https://www.philadelphiafed.org/about-us/privacy-notice),
[SEP](https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm),
[NY Fed Nowcast](https://www.newyorkfed.org/research/policy/nowcast),
[NY Fed warunki](https://www.newyorkfed.org/privacy/termsofuse),
[TradingView widget](https://www.tradingview.com/widget-docs/widgets/calendars/economic-calendar/),
[TradingView FAQ danych](https://www.tradingview.com/widget-docs/faq/data/),
[Investing widget i warunki](https://www.investing.com/webmaster-tools/economic-calendar),
[Alpha Vantage dokumentacja](https://www.alphavantage.co/documentation/),
[Alpha Vantage warunki](https://www.alphavantage.co/terms_of_service/),
[Finnhub EPS](https://finnhub.io/docs/api/company-eps-estimates),
[Finnhub Revenue](https://finnhub.io/docs/api/company-revenue-estimates),
[Finnhub warunki](https://www.finnhub.io/terms-of-service),
[SEC fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).

## 3. Prawdziwe dane pilota i metodologia

Cleveland HTML pobrano rzeczywistym HTTP 200. Adapter sprawdził nazwy tabel,
kolejność kolumn, miesiące, dzień aktualizacji, transformację i świeżość
maksymalnie siedmiu dni. Dane dotyczą aktualizacji **04.11.2026**, a SQL
captured_at jest rzeczywistym czasem lokalnego zapisu 05.11. Nie przypisano
im fikcyjnego czasu first print. Nie użyto starszego cache wyszukiwarki.

| Okres | CPI MoM / YoY | Core CPI MoM / YoY | PCE MoM / YoY | Core PCE MoM / YoY |
|---|---|---|---|---|
| Październik 2026 | 0,24% / 3,74% | 0,21% / 2,48% | 0,27% / 3,77% | 0,26% / 3,20% |
| Listopad 2026 | 0,19% / 3,88% | 0,20% / 2,77% | 0,25% / 3,82% | 0,26% / 3,31% |

To model_nowcast. MoM: SA, nieannualizowane; YoY według ścieżki miesięcznej
SA opisanej przez model. Dopasowanie wyłącznie do wskazanych serii SA
CPIAUCSL/CPILFESL/PCEPI/PCEPILFE i identycznej transformacji. Nie podmieniano
zagnieżdżonych miar NSA ani Actual. GDP ma osobny klucz QoQ annualized i
publication_stage, żeby advance/second/third nie mieszały się ze sobą.

| Emitent / okres docelowy | Revenue guidance | EPS guidance | Wykorzystanie |
|---|---|---|---|
| NVDA Q3 FY2027 | 108,0 mld USD ±2%, zakres 105,84–110,16 mld | brak raportowanego guidance EPS | Revenue widoczne przed istniejącym eventem; EPS null |
| QCOM Q4 FY2026 | 9,7–10,5 mld USD | GAAP diluted 1,22–1,42 USD | Capture po Actual: zachowane źródłowo, bez historycznego porównania |
| ARM Q3 FY2027 | 1,54 mld USD ±50 mln, zakres 1,49–1,59 mld | non-GAAP pominięto wobec reported GAAP Actual | Brak odpowiadającego eventu; nie dopisano kalendarza |

Źródła: [NVDA SEC EX99.1](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/q2fy27pr.htm),
[QCOM SEC EX99.1](https://www.sec.gov/Archives/edgar/data/804328/000080432826000085/qcom062826erex991.htm),
[ARM shareholder letter](https://investors.arm.com/static-files/0b5baa2e-fc47-4d05-b724-e49de7bd4356).
NVIDIA IR zwróciło HTTP 403; użyto oficjalnego SEC EX99.1 z HTTP 200, bez
obchodzenia blokady IR. QCOM SEC HTTP 200. ARM to rzeczywisty oficjalny PDF
z wcześniejszego pobrania i ponownego odczytu, SHA zachowano. Nie utworzono
fikcyjnego nowego HTTP receipt. Pełne dokumenty pozostają ignorowane w RAW.

QCOM zachowuje zakresy, bez obliczania środka 1,32 jako rzekomego konsensusu.
Nie podstawiono non-GAAP EPS 2,05–2,25. Revenue jest kwartalne,
skonsolidowane, USD; EPS diluted/common. ARM ordinary share. NVIDIA USD,
US GAAP/common. Bez FX, ADR, YTD lub wartości segmentów.

Przykłady tego samego okresu w UI: CPI październik Actual **—** / Forecast
**0,24% · Nowcast**; NVDA Q3 Actual **—** / Forecast **105,84–110,16 mld USD ·
Guidance**. QCOM ma Actual 1,17 USD i 10,322 mld USD, ale Forecast **—**,
ponieważ F1 nie znał przejrzanego guidance przed tą publikacją. Nie jest to
ocena trafności guidance ani historyczny beat/miss.

## 4. Model i historia

Trzy nowe tabele: forecast_vintages, forecast_freezes, forecast_refresh_checks.
Wspólny rekord zawiera kind, pełny subject, wartość lub zakres, źródło/URL,
published_at z precyzją, SQL captured_at, wersję, fingerprint, metodologię,
SHA rzeczywistego dokumentu, zakres praw i notatkę. Wszystkie są append-only;
UPDATE/DELETE/TRUNCATE blokowane. Wersje wymagają dokładnej sekwencji.
Idempotencja nie reaktywuje znanego starszego fingerprintu.

Makro: kraj/seria/okres/transformacja/SA lub NSA/jednostka/metodologia/etap
publikacji. Earnings: company_id, CIK, FY/Q, metryka, waluta, GAAP/IFRS lub
non-GAAP, diluted, common/ordinary/ADR i metodologia. SQL dodatkowo sprawdza
emitenta z istniejącego rejestru, finiteness, zakresy i provenance.
Brak zgodnej podstawy nigdy nie powoduje fallback do innego okresu/standardu.

Wiedza porównawcza zaczyna się od max(published_at, captured_at). Stara data
w dokumencie odczytanym dzisiaj nie jest dowodem dostępności w aplikacji
przed historycznym Actual. Worker zapisuje niezmienny freeze ostatniej
wiarygodnej prognozy sprzed cutoff albo jawny freeze null. Późniejszy capture
nie zmienia freeze. Jeśli Actual już jest, a freeze jeszcze nie ma, czytnik
zwraca freeze_pending/null; GET niczego nie zamraża ani nie zapisuje.

Dla Earnings bez dokładnego release używany jest konserwatywny początek
potwierdzonego dnia w źródłowej strefie. Może to wykluczyć prognozę z tego
samego dnia; nie udaje się dokładnego czasu publikacji. Przy braku czasu
makro lub przekroczonym cutoff bez dowodu release prognoza nie jest pokazywana
jako nadal aktualna. Nie deklaruje się complete first-print archive.

Reader makro działa w istniejącym snapshotcie transakcji. Earnings ma
osobny read-only snapshot prognoz, opisany forecast_snapshot_scope;
nie deklaruje się jednej globalnej transakcji obu domen. Odczyt jest zbiorczy,
bez SQL/requestu do wydawcy na każdy wiersz. Brak store daje nieaktywność,
częściowy store kontrolowany błąd. Wybór typu ma jawną kolejność
consensus → model_nowcast → issuer_guidance i zawsze zachowuje etykietę.
Nie dodano procentowego surprise lub porównania modelu jako konsensusu.

## 5. Odświeżanie i frontend

Przygotowano refresh.run/dispatch wykorzystujące istniejący
coordinator.launch, bez nowego schedulera, procesu lub pętli. W izolacji
rzeczywisty dispatch pobrał Cleveland i zapisał 16 rekordów. Cooldown jest
trwały, raz na dobę; lease 726530031 zapobiega konkurencyjnym pobraniom.
Timeout 25 s, limit HTML 5 MiB, robots.txt, bez nieprzejrzanych redirectów,
trwały backoff/Retry-After i blokowanie przy odmowie. Historia pozostaje.
Freeze jest operacją workera z potwierdzonymi Actual, nie GET Calendar.

**Nie podłączono okresowego Forecast dispatch do normalnego lifecycle.**
To przygotowana ścieżka do późniejszej aktywacji, nie uruchomiony normalny
feed. Source SEC guidance pozostaje ręcznie przejrzany; nie ma uniwersalnego
parsera przyszłych guidance lub pełnego konsensusu. Nowy writer/initializer/
dispatch odrzuca normalną bazę i dopuszcza tylko własny prefiks
macrolens_forecast_f1_ na PG17. Nie zmieniono działającego monitora Earnings.

Wykorzystano istniejące komórki Prognoza. Mała wartość i link oznaczają
Nowcast/Guidance/Consensus; tytuł podaje metodologię. Bez nowych kolumn,
paneli, stopek lub widgetów. Zachowano Actual/Previous, siedem kolumn
Earnings i osiem istniejących kolumn makro. Nie usuwano wcześniejszych
niezacommitowanych zmian wyglądu użytkownika.

## 6. Walidacja

| Kontrola | Wynik końcowy |
|---|---|
| Pełny backend offline | **1532 passed**, 26 nowych testów F1 |
| Pełny frontend offline | **719 passed / 36 plików**, 29,52 s; cztery nowe testy |
| TypeScript noEmit | passed |
| Production build | passed, Vite 3,95 s, największy chunk 407,04 kB |
| Wszystkie wcześniejsze PostgreSQL | **19/19 passed**, nowe przebiegi |
| Nowa walidacja F1 PG17 | passed; razem **20** walidacji |
| Chrome production preview / prawdziwe SQL/API | **203 kontrole**, **8 API HTTP 200**, zero JS/console errors i publisher requests z przeglądarki |
| Pełne snapshoty izolacji przed/po UI | wszystkie **29 tabel byte-identyczne** |
| Normalne dane/schemat Earnings i aktywny monitor | passed |
| Pusty indeks, zachowanie prac, diff --check | passed |

Nowe testy sprawdzają dokładne okresy, jednostki/SA, etapy GDP, GAAP/ADR,
przed/po cutoff, brak wstecznego dopisania prognozy, zamrożone null,
zakres bez midpointu, idempotencję i stare fingerprints. PG17 potwierdził
prawdziwy rollback całego DDL, constraints i append-only, dwa procesy,
dwóch równoległych writerów oraz trwały backoff HTTP 429 po wznowieniu.
Przypadki czasowe syntetycznych testów są tak oznaczone; nie zaliczano ich
do 20 prawdziwych rekordów pilota.

Chrome: własne API 8051, production preview 4221, PG17 55505, CDP 9291.
PL/EN, 1366/390 px, 14 makro wartości porównanych z API, typy/źródła,
nieobecność consensus surprise dla nowcastu, guidance NVDA i brak
retrospektywnego QCOM/ARM, liczba kolumn i brak overflow strony. Obejrzano
zrzuty nowcastów i guidance po przewinięciu telefonu do właściwych komórek.
Nie jest to pełny audyt WCAG. Nie podstawiano odpowiedzi API.
Makro lease 726530019 utrzymywano tylko w izolacji, aby istniejący hook nie
uruchamiał importu makro. Normalna praca makro pozostała aktywna.

Pierwsze próby ujawniły: offline TestClient widział lokalny aktywowany token
monitora, nowy czytnik użył domyślnego połączenia zamiast fabryki izolacji,
a pomocniczy Chrome miał źle zakodowaną kropkę w oczekiwaniu. Izolowano token
wyłącznie w conftest, przekazano fabrykę połączeń i naprawiono ignorowany
helper. Guard sieci/SQL pozostał bez osłabienia. Pełne zestawy powtórzono;
nieudanych prób nie zaliczono. Nie instalowano brakującego bs4: użyto stdlib.

## 7. Ochrona normalnego środowiska

Normalne localhost:5432/macrolens, rola macrolens, OID 16384, klaster
7682090371041935398, PG17 sprawdzano read-only. Pełne ordered binary COPY:
**26 tabel, 3 086 248 → 3 086 249 rekordów**. Wszystkie 13 tabel Earnings,
w tym policy i cztery checks monitora, są byte-identyczne. Katalogi Earnings
i makro również identyczne. Brak trzech nowych tabel F1.

Zmieniły się tylko source_check_runs i overview_refresh_state podczas
zwykłej pracy makro. Nie deklaruje się ich byte-identyczności. Normalny token
odpowiada zatwierdzonej policy i wszystkim artefaktom; monitor/status nadal
activated=true, completed. ARM/QCOM Actual zachowane, E2D 29/50,
Previous 23/45, Market Cap nie importowano. Nie wykonano nowego normalnego
DDL/importu, UPDATE/DELETE, apply, restore lub rollbacku.

Na potrzeby izolacji wykonano dodatkowy pg_dump normalnej bazy z wymuszonym
read-only, 32 108 812 B, i restore do własnego PG17. Przed importem prognoz
klon miał 26 zastanych tabel. Po imporcie wszystkie ich pełne snapshoty
były identyczne; doszły tylko trzy tabele F1. Ten klon nie był aktywacją
normalnej bazy ani syntetycznym źródłem wartości prognoz.

## 8. Pliki i zakończenie

Osiem modyfikacji tego etapu:

- app/analytics/calendar_agenda.py
- app/api/earnings.py
- frontend/src/api/macrolens.ts
- frontend/src/calendar/CalendarPage.tsx
- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/earningsTypes.ts
- tests/conftest.py
- tests/test_earnings_dates.py

Dziesięć nowych plików:

- app/forecast_f1.py
- app/forecast_f1_sources.py
- app/forecast_f1_refresh.py
- app/database/forecast_f1_schema.sql
- config/forecast_f1_reviewed.json
- frontend/src/calendar/ForecastValue.tsx
- frontend/src/calendar/ForecastValue.test.tsx
- tests/test_forecast_f1.py
- tests/postgres_forecast_f1_validation.py
- docs/audits/macrolens-forecast-f1-2026-11-05.md

Manifest i pełny wejściowy diff 43 zastanych dirty/untracked plików zapisano
w ignorowanym data/raw/forecast-f1-2026-11-05. Spośród tych 43 zmieniono
wyłącznie cztery konieczne pliki API/UI/types: **pozostałe 39 byte-identyczne**.
CalendarPage zachowuje wcześniejsze zmiany użytkownika; dodano import i
renderowanie komórki prognozy. Bez zmian dependencies, lockfile, CI,
globalnego CSS, ledgerów Actual, historii, aktywatorów i monitora.

Własne API/preview/Chrome zakończono, klony i losowe bazy usunięto.
Własny kontener usunięto z anonimowym wolumenem po kontroli pełnego ID
15837b32c16c44131a8f375470a92fcd1287828d6b6df4195b36a2ba2ef5773d,
etykiety forecast-f1-2026-11-05, braku klientów oraz baz poza własnymi control/
postgres/template. W trakcie regresji nazwę własnego kontenera dopasowano do
istniejącej bramki report activation; guardów nie zmieniano. Normalny
PostgreSQL, API 8000 i Vite 5173 pozostawiono działające.

Końcowo **23 modified / 34 untracked**, indeks pusty, main/HEAD bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend i globalnego formatowania.
PDF/HTML, receipts, dump, pełne snapshoty, logi, helpery i screenshoty pozostają
ignorowane w data/raw. Nie wystawiono pełnych komunikatów ani sekretów.

## 9. Późniejsza aktywacja — niewykonana

Oddzielny etap wymaga przeglądu źródeł dla docelowego sposobu użycia,
kontrolowanego runnera normalnej aktywacji trzech tabel F1, dokładnego planu,
świeżego backup/restore i odrębnej zgody na zapis. Nie przygotowano pozornego
tokenu apply ani nie wykorzystano wcześniejszej zgody monitora Earnings.
Należy także jawnie wpiąć forecast dispatch/freeze do istniejącego
wybudzania zadań, zachowując jego lease, oraz zamrozić artefakty i nową
konfigurację praw. Nie wolno po prostu usunąć izolacyjnego prefiksu guarda.

Pełny konsensus, GDP z wyjaśnionymi warunkami i zgodnym etapem publikacji,
automatyczne nowe guidance, pokrycie pozostałych emitentów oraz dowody
historycznych pre-release prognoz pozostają zakresem przyszłym. F1 nie
uzupełnia braków fikcyjnym konsensusem, fixture lub dzisiejszym szacunkiem.
