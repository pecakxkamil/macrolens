# MacroLens — E2E Activation V2: zakończona aktywacja

Wykonano **04.11.2026, Europe/Warsaw**, C:\Projects\macrolens, main.

**E2E V2 ACTIVATED — 23 reports / 45 metrics**

Normalny APPLY zakończył się kodem 0 i COMMIT. Previous działa w normalnym
Calendar. Nie wykonano restore/rollbacku normalnej bazy, restartu API/Vite,
zmiany UI lub importu Market Cap.

## 1. Zgoda, commit i CI

Zatwierdzony i wykonany kanoniczny hash:

`16230d2bf6c8dc91c05836b57352b7f90d8587373f7bfb45adc06ad41c875593`

Target: **localhost:5432/macrolens**, PostgreSQL **17**, rola **macrolens**,
OID **16384**, klaster **7682090371041935398**. Plan był identyczny przed
commitem, po nim, po CI i po świeżym backup/restore. Wszystkie 26 zamrożonych
artefaktów, DDL i ledger są zgodne. Nie użyto historycznej zgody V1.

Commit **5b31cdb1ea042cd10483f701c262b85a958efc08**,
**Add scoped earnings history activation V2**, obejmuje dokładnie pięć plików:

- app/database/activate_earnings_history_v2.py
- tests/postgres_earnings_history_v2_validation.py
- tests/test_earnings_history_activation_v2.py
- docs/audits/equity-earnings-previous-activation-v2-readiness-2026-11-04.md
- .github/workflows/ci.yml — jeden nowy nazwany krok PostgreSQL V2

Test V2 przyjmuje service ID Actions wyłącznie pod bramką GITHUB_ACTIONS,
właściwej kontrolnej bazy V2, roli macrolens_ci, loopback i pełnego ID.
Produkcji nie zmieniono. Zachowano wszystkie 17 wcześniejszych walidacji.
Bez zmian dependencies, lockfile, uprawnień, timeoutów lub guardów HTTP.
Actionlint, 7 lokalnych testów bramek i rzeczywisty SQL V2 z service ID passed.

Pierwszy push odrzucił automatyczny przegląd, który nie uznał załącznika
za bezpośrednią zgodę na push do domyślnej gałęzi. Nie obchodzono odrzucenia.
Po bezpośrednim potwierdzeniu przez użytkownika zwykłego pusha tego konkretnego
commita w rozmowie wykonano git push origin main z kodem 0, bez force.

[Actions dla dokładnego SHA](https://github.com/pecakxkamil/macrolens/actions/runs/41908882549):

| Job | Zakończony wynik |
|---|---|
| Backend tests | success |
| Frontend tests and build | success |
| PostgreSQL integration tests | success — 18/18 nazwanych walidacji, w tym V2 |

Normalny APPLY wykonano dopiero po trzech sukcesach. Nie deklaruje się CI
na podstawie wcześniejszych lokalnych wyników 1468/694. Dwa dodatkowe testy
CalendarPage użytkownika pozostają poza commitem.

## 2. Świeży backup, pełny restore i klon

Nowy pg_dump custom: **31 220 380 B**, SHA-256:

`18f13c48c3212bf52535f8358b92c15629bb0d0915585284d89bf89cdca0cdb5`

Archiwum/manifest są ignorowane w data/raw/earnings-previous-v2-apply-2026-11-04.
Eksport korzystał z jednego REPEATABLE READ READ ONLY i pg_export_snapshot.
pg_dump miał wymuszone default_transaction_read_only. Nie zatrzymywano aplikacji.

TOC i pełny restore do własnego PG17 na loopback **55487** passed, kod 0.
Wszystkie **23 tabele / 2 963 543 rekordy**, pełne hash/count oraz oba
katalogi schematu odpowiadają eksportowanemu snapshotowi. Zero niezwalidowanych
constraints. Dowód restore wiąże target, SHA archiwum i pełne snapshoty.

Świeży pełny klon odtworzono z tego archiwum. Jego plan różnił się wyłącznie
targetem i target_label izolacji; pozostałe pola porównano jako identyczne.
Nie podstawiano normalnej tożsamości pod klon. Wykonano również rzeczywisty
backup/restore klonu przed próbą.

SQL 1/0 po pierwszym raporcie wycofał razem DDL i seed. Prawidłowy import dał
23/45, a powtórzenie already_initialized bez zmiany danych lub timestampów.
Wszystkie 23 pierwotne tabele klonu były byte-identyczne. Realny read-only
API/SQL potwierdził wymagane Previous i 34 datowane wydarzenia.

Aktualny SQL V2 i CI sprawdziły także konkurencyjnego aktywatora, bounded lock
timeout, zapis makro przed i podczas importu, niezmienny hash po zmianie makro,
blokadę writera Earnings, negatywne bramki, append-only i zależności FK.
Negatywne testy zapisujące wykonywano wyłącznie w izolacji.

## 3. Normalny APPLY i integralność po COMMIT

Runner CLI prepare z nowym backupem zwrócił dokładnie zatwierdzony hash.
CLI apply otrzymał jawne confirm-target i confirm-plan. Receipt
normal-apply-receipt.json ma outcome=created i zatwierdzony hash.

W jednej READ COMMITTED transakcji pobrano advisory **726530020** i SHARE
na dziesięciu starych tabelach Earnings w stałej kolejności. Po blokadach
ponownie sprawdzono target, dane, katalogi i zależności. Limity lock **5s**,
statement **120s**. Nie pobierano makro lease 726530019 ani blokad tabel makro.
DDL i seed zatwierdzono razem dopiero po ponownej pełnej kontroli.

Powstała tylko earnings_historical_reports, 13 zatwierdzonych constraints,
cztery indeksy UNIQUE, earnings_history_guard() i trzy triggery insert,
immutable, no_truncate. **23 rekordy raportów zawierają 45 metryk JSONB:
23 revenue i 22 reported diluted EPS.** Nie dodano tabeli obserwacji.
CRWD Previous EPS jest nieobecny. Constraints są zwalidowane; definicje,
stany triggerów/indeksów i zależności są zgodne z reference.after planu.

Niezależne połączenia read-only po COMMIT i po Chrome potwierdziły pełną
byte-identyczność dziesięciu wcześniejszych tabel, także timestampów:

| Tabela | Przed = po |
|---|---:|
| earnings_companies | 53 |
| earnings_company_aliases | 55 |
| earnings_periods | 37 |
| earnings_events | 37 |
| earnings_source_evidence | 40 |
| earnings_date_confirmations | 66 |
| earnings_financial_documents | 6 |
| earnings_financial_observations | 12 |
| earnings_report_documents | 27 |
| earnings_report_observations | 46 |

Bez nowych events, periods i emitentów lub zmian E2A–E2D. Nowe 23 raporty
zachowały pełny hash/count między receipt, SQL/API i końcem Chrome.
GET Earnings nie importuje ani nie odpytuje wydawców: potwierdzają to kod,
testy no-HTTP i brak zmiany historii po odczytach. Nie jest to twierdzenie
o braku zapytań do źródeł działających równolegle procesów makro.

Końcowo **24 tabele / 2 963 741 rekordów**. Podczas zwykłej pracy makro
zmieniły się source_check_runs (2618→2666), release_dates (804→931),
overview_publications (8→8) i overview_refresh_state (1→1). Nie wymagano
ich byte-identyczności. Katalog makro i pozostałe dziewięć tabel makro są
identyczne. Runner nie zapisuje do makro; bez jego DDL/importu, globalnych
blokad i bez restore/rollbacku normalnej bazy.

## 4. Rzeczywiste API i Chrome

Bez restartu API 8000/Vite 5173: **35 GET HTTP 200**, 34 datowane wydarzenia,
**27 wydarzeń z Previous**. Porównano dokładne wartości i fiskalne okresy
z ledgerem; poniżej zaokrąglenia widoczne w tabeli:

| Bieżący / Previous | EPS Previous | Revenue Previous |
|---|---:|---:|
| AAPL Q4 / Q3 FY2026 | 2,02 USD | 109,42 mld USD |
| PLTR Q3 / Q2 2026 | 0,41 USD | 1,94 mld USD |
| AMD Q3 / Q2 2026 | 1,38 USD | 11,54 mld USD |
| INTC Q3 / Q2 2026 | −2,16 USD | 16,13 mld USD |
| AMZN Q3 / Q2 2026 | 5,75 USD | 200,61 mld USD |
| NVDA Q2 / Q1 FY2027 | 2,39 USD | 81,62 mld USD |

NVDA Q3 FY2027 ma Current null i Previous Q2 EPS 2,46 USD. CRWD Previous EPS
pozostaje null, revenue dostępne. ARM/QCOM nie mają niezweryfikowanego
Previous. Cztery prognozy są null. Nie wpisano wartości do frontendu.

Chrome na prawdziwym http://localhost:5173/#/calendar, API 8000 i normalnej
bazie, bez fixture: **841 kontroli / 32 odpowiedzi API 200**, dodatkowo
**37 bezpośrednich GET 200**, zero JS/console.error/HTTP 503. PL/EN,
1366/390 px. Sprawdzono siedem kolumn, Current/Previous EPS/revenue,
Actual/Prognoza, okresy, mniejszy Previous, źródła, brak Status i Szczegóły,
zakresy/domeny, wewnętrzny scroll i brak overflow strony oraz żądań przeglądarki
do wydawców. Obejrzano desktop EN i mobile PL, także prawą część tabeli.
To nie jest pełny audyt WCAG.

Pierwszy helper Chrome miał błędnie zakodowane oczekiwania nagłówków;
DOM był poprawny. Poprawiono wyłącznie ignorowany helper do jawnego UTF-8
i powtórzono cały zestaw z sukcesem. Bez zmiany aplikacji lub osłabienia asercji.

Market Cap pokazuje samą kapitalizację, źródła DeltaScreener/TGMCharts
pozostały w nagłówku, bez daty/dostawcy w komórkach. Cache byte-identyczny:
**49/53** firm i cztery braki, SHA-256
`94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799`.
Bez importu Market Cap lub zmiany polityki 7/45 dni.

## 5. Ochrona prac i zakończenie

Początkowo 9 modified / 9 untracked, indeks pusty. Nowy manifest i pełny diff
są w ignorowanym katalogu etapu. Wszystkie **13 chronionych prac użytkownika**
i wcześniejszy raport STOP V1 (razem 14) zachowano byte-identycznie.
E2D Activation, E2E, Market Cap, UI i dane źródłowe nie wymagały edycji.
Staged diff obejmował tylko pięć uzgodnionych plików.

Klony i bazy restore usunięto. Własny Chrome zakończono przez CDP **9277**.
Własny kontener PG17 i wolumen usunięto po kontroli pełnego ID
`92fa352d0336bc955a6c4477acafb7a3e84207e600c91a2b6473c3bee298cd0a`,
etykiety earnings-previous-v2-apply-2026-11-04, braku baz poza control/
postgres/template i braku innych klientów. Normalny macrolens_postgres,
API i Vite pozostawiono działające. Brak diagnostycznych blokad/lease.

Końcowo **9 modified / 6 untracked**, indeks pusty, main i origin/main
**5b31cdb1ea042cd10483f701c262b85a958efc08**. Szósty nieśledzony plik to ten
raport; bez dodatkowego commita z metadanymi po pushu. Bez reset, clean,
amend, force push i globalnego formatowania. Backupy, plany, receipt,
snapshoty, logi, screenshoty i helpery pozostają ignorowane w data/raw;
nie wystawiono archiwów lub sekretów.
