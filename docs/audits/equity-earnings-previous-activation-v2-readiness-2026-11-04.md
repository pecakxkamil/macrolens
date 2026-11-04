# MacroLens — E2E Activation V2: gotowość, bez normalnego APPLY

Wykonano **04.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`, main,
HEAD `eeb92abcfa948806a41f7fcbafa678edec6072de`.

**Przygotowano nowy plan V2. Nie wykonano APPLY w normalnej bazie.**
Normalny PostgreSQL był używany wyłącznie read-only. API i Vite pozostawiono
uruchomione. Nie wykonano stagingu, commita ani pusha.

## 1. Poprzedni STOP i nowy hash

V1 w `prepare()` wykonywał `financial.table_snapshots(connection)` bez zakresu,
porównywał wszystkie 23 tabele z `backup.source_snapshots`, a potem umieszczał
pełne snapshoty i backup w kanonicznym planie. `apply()` ponownie wymagał
zgodności tych 23 tabel. Legalne zmiany `source_check_runs`,
`overview_publications` i `overview_refresh_state` z poprzedniego etapu
naruszyły ten warunek mimo zgodności wszystkich 10 tabel Earnings. To
rzeczywista rozbieżność danych, nie problem czasu wykonania komendy.

Historyczny, nieobowiązujący dla V2 hash V1:
`6d224e8299ba70a2c133e3c2cadc345a3ed16f60a41aefa7427892d112f073fb`.
V1, jego raporty, zatwierdzony plan i wcześniejsze zgody pozostawiono bez zmian.

Nowy **pełny SHA-256 kanonicznego planu V2**:

`16230d2bf6c8dc91c05836b57352b7f90d8587373f7bfb45adc06ad41c875593`

Plan: `data/raw/earnings-previous-v2-2026-11-04/normal-v2-plan.json`.
Hash liczy istniejące `base.digest()`: JSON z posortowanymi kluczami i
kanonicznymi separatorami. Hash bajtów pliku z wcięciami nie jest hashem planu.
Status to `ready_for_apply=true`, `awaiting_new_explicit_approval` — gotowość
techniczna, bez udzielenia autoryzacji. Wielokrotne prepare normalnej bazy
oraz prepare klonu przed/po zapisach makro dały identyczne odpowiednie plany.
Plan klonu ma własny hash, ponieważ identyfikuje inny target.

## 2. Chroniony zakres i zależności

Target: **localhost:5432/macrolens**, rola **macrolens**, PostgreSQL **17**,
OID **16384**, cluster system identifier **7682090371041935398**.
Dziesięć pełnych snapshotów danych, także timestampów, jest zamrożonych:

| Tabela | Wiersze |
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

Plan zawiera pełne katalogi Earnings: relacje, kolumny, definicje constraints,
indeksów, triggerów i funkcji. V2 dodaje rekurencyjne przejście rzeczywistych
`pg_depend`, jawny odczyt FK, stan włączenia wszystkich triggerów i stan
valid/ready/live indeksów. Nie używa ogólnego ignorowania rozbieżności.
Nieoczekiwany FK do makro lub obcego schematu powoduje STOP. Klucze CIK/ticker
23 emitentów sprawdzane są wobec istniejących company_id; FK nowej historii
pozostaje w SQL. Przejrzano także ciała funkcji PL/pgSQL i importer, bo tekstowe
odwołania w PL/pgSQL nie są kompletnym grafem zależności `pg_depend`.

Tożsamość obiektów katalogowych jest kanonizowana bez lokalnych OID.
Wewnętrzne nazwy triggerów RI zawierające OID nie są fingerprintem schematu;
ich stan jest identyfikowany przez tabelę, constraint i funkcję RI.
Definicje i stany ochrony nadal są sprawdzane.

Tabele makro nie są zależnością DDL/importu E2E i pozostają poza zakresem
zapisu i porównania **danych** planu. Dotyczy to także computed_features,
observation_vintages, publisher_documents i pozostałych tabel makro. Nie ma
`ignore_all_snapshot_mismatches`. Zmiana chronionych danych zmienia nowo
przygotowany plan albo odrzuca już zatwierdzony; zmiana chronionego schematu,
ledgeru, DDL, artefaktów lub targetu powoduje STOP.

## 3. Dokładne operacje planu

Jedna transakcja może wyłącznie utworzyć `public.earnings_historical_reports`,
jej 13 constraints, cztery indeksy UNIQUE, funkcję `earnings_history_guard()`
i triggery `earnings_history_insert`, `earnings_history_immutable`,
`earnings_history_no_truncate`, a następnie dopisać dokładnie **23 snapshoty /
45 metryk: 23 revenue i 22 reported diluted EPS**. Constraints obejmują PK
`document_id`, FK `company_id` do earnings_companies, self-FK `supersedes_id`,
unikalność fingerprintu, poprzednika i company/FY/Q/version oraz CHECK CIK,
FY/Q, wersji, JSONB i powodu rewizji. Pełne nazwy i definicje znajdują się
w `reference.after.catalog` i zamrożonym DDL planu.

Brak nowych emitentów, events lub periods. Brak UPDATE/DELETE/TRUNCATE
istniejących tabel, zmian Current/forecast, Market Cap lub konfiguracji makro.
Importer/guard zachowują skalowanie, waluty, GAAP/IFRS, diluted/share basis,
append-only, dokładnego poprzednika i brak reaktywacji starego fingerprintu.

Plan zamraża 26 artefaktów: runner V2 oraz dotychczasowe DDL, importery,
czytniki i zależności V1/E2D. Ledger pozostaje byte-identyczny:
SHA pliku `a9c6aae5dfa4be3f3c7005374240bf889258c0c37f0b2437f1041782cc3a12d4`,
fingerprint rekordów `135d8159459593a91528b57d0440eaa02f0f96024aa07421e8094e77ea23acc5`.
DDL SHA `e2a6a484afe41db60628ab37808b08b93231ed96d4817982391ebac8277dc695`.

## 4. Współbieżność i warunki APPLY

Prepare używa jednego REPEATABLE READ READ ONLY. Przyszły apply wymaga nowego
pełnego hasha i target label. Najpierw sprawdza zamrożone artefakty, DDL,
ledger, liczby, manifest metryk i dowód backup/restore. Potem w jednej
transakcji READ COMMITTED pobiera try-lock **726530020** i blokuje dziesięć
tabel Earnings w stałej kolejności w trybie **SHARE**. Dopiero po otrzymaniu
wszystkich blokad odczytuje tożsamość, katalogi i snapshoty. Nie pobiera
makro lease 726530019 i nie blokuje tabel makro.

READ COMMITTED daje świeży snapshot zapytania po uzyskaniu blokad, więc
zapis Earnings zakończony podczas oczekiwania nie pozostaje poza kontrolą.
SHARE utrzymuje dane stabilne do COMMIT i pozwala na zwykłe SELECT. Dobór
wynika z [izolacji PostgreSQL 17](https://www.postgresql.org/docs/17/transaction-iso.html)
i [macierzy blokad](https://www.postgresql.org/docs/17/explicit-locking.html).

`lock_timeout=5s`, `statement_timeout=120s`, brak bezterminowego oczekiwania.
Konkurencyjny importer/aktywator powoduje STOP. DML/DDL tabel Earnings jest
blokowane w chronionym przedziale; wykryta rozbieżność, zajęta blokada,
częściowy store lub błąd SQL wycofuje razem DDL i seed. Przed COMMIT ponownie
sprawdzane są wszystkie stare dane, katalogi, dependencies, dokładny manifest
nowego store i liczniki. Powtórzenie wymaga identycznego nowego store i nie
zmienia wersji ani captured_at. Nie ma automatycznego restore po COMMIT.

Warunek późniejszej kontroli po COMMIT: niezależny read-only odczyt tożsamości,
10 starych snapshotów, katalogów i 23/45 oraz realnego API Previous; zachować
receipt i sprawdzić idempotencję. Rozbieżność po COMMIT oznacza STOP i osobną
decyzję zgodnie z istniejącym raportem rollbacku, bez CASCADE i nadpisania bazy.

## 5. Świeży backup i pełny klon

Wykonano świeży `pg_dump --format=custom` normalnej bazy z eksportowanego
snapshotu transakcji REPEATABLE READ READ ONLY. Archiwum **31 220 380 B**,
SHA-256 `36793a15fa900719a893c1af21478125433350e0d751142011a5d29e2e97cc65`.
TOC sprawdzono. Pełny restore do własnej losowej bazy PostgreSQL 17 zakończył
się kodem 0; wszystkie **23 tabele / 2 963 543 rekordy** i obie reprezentacje
katalogów są zgodne, zero niezwalidowanych constraints. Dowód restore
przechowuje hash archiwum i został sprawdzony przez istniejący walidator.

Backup i dowód są osobnymi wymaganymi artefaktami operacyjnymi. Ich pełne dane
makro nie wchodzą do hasha V2. Walidator nadal sprawdza integralność pełnego
archiwum/proof, target oraz zgodność chronionych danych i katalogu Earnings
z planem. Zmiany niepowiązanych danych makro nie wymagają podmiany planu.

Na świeżo odtworzonym pełnym klonie powtórzono także własny backup/restore,
a potem pełny test V2: 23/45, rollback DDL+seed po SQL 1/0, negatywne bramki,
SHARE/timeout, konkurencyjny aktywator, zapis makro przed i podczas importu,
append-only, idempotencję i realny read-only API/SQL. Drugi odrębny pełny klon
wykazał zmianę hasha po testowym UPDATE Earnings. Oba klony były własne;
nie zmieniano żadnych normalnych danych w celu uzyskania zgodności.

Zmiany source_check_runs, overview_publications i overview_refresh_state
wykonał oddzielny testowy writer. Hash planu przed/po tych zmianach jest
identyczny. Writer makro zakończył COMMIT podczas blokad Earnings, przy
celowo zajętym makro lease. Po apply snapshoty makro odpowiadały dokładnie
writerowi; aktywator nic do nich nie dopisał. Dziesięć starych Earnings
pozostało byte-identyczne. SQL rollback zachował cały poprzedni stan.
Wersje, brak dziedziczenia pominiętego EPS i stare fingerprinty dodatkowo
przeszły w dotychczasowej rzeczywistej walidacji historii.

## 6. Previous i wyniki testów

Realny GET korzystał z SQL i read-only połączeń, bez fixture odpowiedzi lub
HTTP wydawców. Sprawdzono 34 datowane wydarzenia:

| Bieżący / poprzedni | EPS Previous | Revenue Previous |
|---|---:|---:|
| AAPL Q4 / Q3 FY2026 | 2,02 USD | 109,42 mld USD |
| PLTR Q3 / Q2 2026 | 0,41 USD | 1,94 mld USD |
| AMD Q3 / Q2 2026 | 1,38 USD | 11,54 mld USD |
| INTC Q3 / Q2 2026 | −2,16 USD | 16,13 mld USD |
| AMZN Q3 / Q2 2026 | 5,75 USD | 200,61 mld USD |
| NVDA Q2 / Q1 FY2027 | 2,39 USD | 81,62 mld USD |

Przyszła NVDA Q3 ma Current null i Previous Q2 EPS 2,46. CRWD Previous EPS
pozostaje null z powodu splitu, revenue jest dostępne. ARM/QCOM nie otrzymały
niezweryfikowanego Previous. Porównano dokładne wartości, a nie zaokrąglenia.

| Kontrola | Wynik |
|---|---|
| Pełny backend offline | **1468 passed**, pytest 76,75 s |
| Pełny frontend offline, Node 22.23.4 | **694 passed / 33 pliki**, 34,21 s |
| TypeScript noEmit | passed |
| Production build | passed, Vite 4,35 s; największy chunk 407,04 kB |
| Dotychczasowe PostgreSQL 17 | **17/17 passed** |
| Nowy PostgreSQL V2, syntetyczny | passed |
| Nowy PostgreSQL V2, świeży pełny klon | passed |
| Nowy plan normalny | prepare read-only; powtarzalny hash |
| Normalne API / Vite localhost | HTTP 200 / 200 |
| diff --check / składnia i whitespace nowych plików | passed |

Nie zmieniono CI, zależności ani lockfile; nie uruchamiano nowego Actions
lub actionlint. Wyniki lokalne nie są nowym wynikiem CI.

Pierwsza próba katalogu V2 ujawniła zmienne nazwy wewnętrznych triggerów RI;
kanonizację poprawiono bez pomijania ich stanu. Pierwszy helper pełnego klonu
próbował referencyjnego DDL na własnym połączeniu read-only; PostgreSQL
odrzucił go. Helper otrzymał osobne zapisywalne połączenie wyłącznie izolacji.
Jedno ponowienie wstrzymał limit automatycznego przeglądu uprawnień; po
poleceniu „Kontynuuj” ponowiono je przez tę samą kontrolę. Smoke Vite pod
127.0.0.1 nie połączył się; właściwy localhost zwrócił 200 bez restartu.
Nieudanych prób nie zaliczono jako sukcesów.

## 7. Normalne dane, Git i zakończenie

Odczyty normalnej bazy miały wymuszone read-only. Porównanie pełnych COPY po
PK i katalogów przed/po potwierdziło ten sam target, **10 identycznych tabel
Earnings**, obie identyczne reprezentacje schematu i brak tabeli historii.
W badanym przedziale zmienił się wyłącznie overview_refresh_state podczas
zwykłej pracy makro; nie przypisuje się tej zmiany aktywatorowi. Liczba
rekordów pozostała 2 963 543. Nie wykonano normalnego DDL/importu/UPDATE/
DELETE/restore/rollbacku ani normalnego apply. Nie zatrzymywano API/Vite
lub odświeżeń makro; normalne API nadal ma null Previous AAPL.

Manifest i pełny diff wejściowych **9 modified / 5 untracked** są ignorowane
w `data/raw/earnings-previous-v2-2026-11-04`. Wszystkie 14 wcześniejszych
plików, w tym **13 chronionych prac użytkownika**, zachowano byte-identycznie.
Nie edytowano V1, E2D Activation, E2E, UI, Market Cap ani starych raportów.
Cache nadal zawiera **49/53** firm, cztery jawne braki, SHA
`94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799`.

Cztery nowe pliki:

- `app/database/activate_earnings_history_v2.py`
- `tests/test_earnings_history_activation_v2.py`
- `tests/postgres_earnings_history_v2_validation.py`
- `docs/audits/equity-earnings-previous-activation-v2-readiness-2026-11-04.md`

Końcowo **9 modified / 9 untracked**, indeks pusty, HEAD/main bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend i globalnego formatowania.
Własne losowe bazy usunięto; własny kontener i wolumen usunięto po kontroli
pełnego ID `a03a655d4c8f657e747ab2d734549388e3df17a144ffb519ff728ad3a2e49d43`,
etykiety i braku baz poza kontrolnymi/postgres/template. Normalny
macrolens_postgres pozostaje poza sprzątaniem. Backupy, plany, logi,
manifesty i helpery pozostają ignorowane w data/raw.

**STOP zgodny ze zleceniem: normalny APPLY V2 wymaga odrębnej wyraźnej zgody
użytkownika na powyższy nowy pełny hash i target. Nie wygenerowano zgody;
stary hash V1 nie jest autoryzacją V2.**
