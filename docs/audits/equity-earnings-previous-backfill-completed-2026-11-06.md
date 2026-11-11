# MacroLens — uzupełnienie Previous: wykonana aktywacja

06.11.2026, Europe/Warsaw, `C:\Projects\macrolens`.

**ACTIVATED: siedem nowych raportów / 13 metryk w normalnej bazie.**
Użytkownik bezpośrednio zatwierdził w rozmowie zakres i pełny hash planu:

`b576ccc0df847e1fc6367c10cdc3be23ef3e7668c32019e9fcbac28d5b0c8df6`

Target: localhost:5432/macrolens, PG17, rola macrolens, OID 16384,
system_identifier 7682090371041935398. Nie używano zgód wcześniejszych etapów.
Źródła i metodologia pozostają w [raporcie gotowości](equity-earnings-previous-backfill-readiness-2026-11-05.md).

## Ponowna kontrola i świeży backup

Read-only CLI plan przed backupem i z nowym backupem zwróciły identyczny
zatwierdzony dokument/hash. Backend, ledger i dane chronione nie zmieniły się.
Nowe zwykłe rekordy makro nie zmieniły planu.

Świeży pełny pg_dump custom: **32827288 B**, SHA-256:

`e15399a4150e7f7c3ff853939db18666e85874f3cfebb642857e4923cd592893`

Dump pochodzi z jednego REPEATABLE READ READ ONLY i pg_export_snapshot;
pg_dump korzystał z tego snapshotu oraz default_transaction_read_only.
TOC i pełny restore na własnym PG17 55531: kod 0, **29 tabel / 3152412
rekordów**, wszystkie uporządkowane binary COPY hash/count i oba katalogi
zgodne, zero niezwalidowanych constraints. Dowód wiąże target i SHA archiwum.

Następnie utworzono osobny pełny klon oraz wykonano jego własny backup/restore.
Ponownie przeszło **318 kontroli rzeczywistego SQL/API**: siedem raportów,
dokładne okresy i wartości, idempotencja, brak zmiany wcześniejszych danych,
konkurencyjny writer, pięciosekundowy lock timeout, obcy schemat, append-only
oraz rzeczywisty błąd SQL wycofujący całą partię. Normalny i klonowy plan
różniły się wyłącznie targetem/target_label. Powtórzono także **10 testów
offline bramek** z sukcesem. Kod operacji nie wymagał edycji.

## Normalny COMMIT i niezależna weryfikacja

Zatwierdzony runner CLI APPLY otrzymał jawny target i pełny hash oraz świeży
backup/restore. Exit code 0, receipt `outcome=created`, reports=7, metrics=13.
W jednej transakcji READ COMMITTED pobrał advisory 726530020 i SHARE na
istniejących tabelach Earnings, przy lock_timeout 5 s / statement_timeout
120 s. Dodano tylko siedem wierszy do earnings_historical_reports.
Nie wykonano DDL, UPDATE/DELETE, zmian policy/tokenów F1 ani importu Current.

Niezależne połączenie read-only potwierdziło `outcome=verified`, kompletne
payloady, deterministyczne UUID/fingerprinty i **30 raportów / 58 metryk**.
Pełne dane wszystkich **28 pozostałych tabel** odpowiadały nowemu backupowi.
Wcześniejsze 23 wiersze historii, włącznie z timestampami, są byte-identyczne.
Schemat, constraints, triggery i krytyczne referencje zachowano.

| Bieżący raport → Previous | EPS Previous USD | Revenue Previous USD |
|---|---:|---:|
| ARM Q2 FY2027 → Q1 FY2027 | 0.25 | 1289000000 |
| QCOM Q4 FY2026 → Q3 FY2026 | 1.87 | 9947000000 |
| PANW Q1 FY2027 → Q4 FY2026 | -0.35 | 3410000000 |
| SNOW Q3 FY2027 → Q2 FY2027 | -0.55 | 1546793000 |
| NVDA Q1 FY2027 → Q4 FY2026 | 1.76 | 68127000000 |
| AMZN Q2 2026 → Q1 2026 | 2.78 | 181519000000 |
| INTC Q2 2026 → Q1 2026 | — | 13577000000 |

Rzeczywiste API zwraca nadal **34 datowane wydarzenia** i **66/68 pól
Previous**: wszystkie Revenue, 32 EPS. Pozostałe null to CRWD EPS ze względu
na split/pro forma i INTC EPS ze względu na istniejącą niezgodność metodologii
attributable-to-Intel z modelem historii. Szczegóły w raporcie gotowości.
Nie zmieniono tych podstaw w celu wymuszenia porównania.

## Normalne API i Chrome

Na początku API 8000 i Vite 5173 były wyłączone. Odczyt API przed importem
wykonano przez TestClient na rzeczywistym normalnym SQL, bez kontekstu
lifespan uruchamiającego workery. Po COMMIT i niezależnym verify uruchomiono
zwykłe API i Vite. Pozostają dostępne pod http://127.0.0.1:5173/#/calendar.

Chrome na normalnym Vite/API/SQL, bez fixture: **208 kontroli / 16 API GET
HTTP 200**, PL/EN, 1366/390 px, zero JS/console.error, 503 lub żądań
przeglądarki do wydawców. Potwierdzono komórki Previous ARM/QCOM/PANW/SNOW,
zachowanie Current i istniejących Previous, sześć kolumn Wszystko, osiem
Dane, siedem Wyniki, wspólną chronologię, 22:00+, ważność, nazwy, przejście
do Wyniki oraz wewnętrzny scroll mobile bez overflow strony. Obejrzano
desktop EN oraz telefon PL przewinięty osobno do EPS i Revenue Previous.
Nie deklaruje się pełnego audytu WCAG ani poprawności całego historycznego
makro; zastany problem szerokiego zakresu opisany w gotowości pozostaje.

Dodatkowo **37 bezpośrednich GET HTTP 200**: lista 34 wydarzeń, ich szczegóły
i dwa statusy runtime. **692 porównania** potwierdziły zachowanie Current,
poprzednich prawidłowych Previous, okresów, Forecast, czasu, źródeł i Market
Cap. Dokładne FY/Q i nowe wartości wszystkich siedmiu raportów są zgodne.
Po workerach, GET i Chrome wszystkie pełne snapshoty nadal odpowiadały
stanowi bezpośrednio po COMMIT, również makro w tym konkretnym oknie.

F1 V2: activated=true, cooldown, added=0/frozen=0, wszystkie 155 artefaktów
zgodne; 20 vintages, sześć freezes, trzy checks bez zmian. Earnings monitor:
activated=true, loop_running=true, completed, checked=0. F2 nie aktywowano.
Market Cap pozostaje 49/53, cache SHA
`94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799`.
Nie importowano kapitalizacji ani nowych prognoz.

Pełne wcześniejsze testy przygotowanego kodu (1598 backend, 794 frontend,
TypeScript/build i 22 wcześniejsze PostgreSQL) pozostają wynikami gotowości,
nie nowym przebiegiem tego wykonania. W tym etapie powtórzono bramki,
pełny restore/próbę klonu, weryfikację normalnego SQL/API i Chrome.

## Ochrona i sprzątanie

Zapisano nowy manifest i pełny diff. Wszystkie **467 zastanych plików**
zachowano byte-identycznie, w tym chronione prace, F2 i osiem plików backfill.
Dodano wyłącznie ten raport. Nie zmieniono kodu, UI, konfiguracji,
zależności, workflow, autoryzacji lub wcześniejszych audytów.

Własny Chrome/CDP 9313 zakończono po kontroli PID/argumentów. Własny klon
usunięto, następnie własny kontener PG17 z anonimowym wolumenem po kontroli
pełnego ID `2752bb8a33a889a309818e3b77033820f90b6d2b45cec1e0e66944b9f6b42e87`,
etykiety earnings-previous-backfill-apply-2026-11-06, braku klientów i baz
poza control/postgres/template. Normalny PostgreSQL, API i Vite pozostawiono
działające. Nie wykonano restore/rollbacku normalnej bazy.

Plany, nowy dump, dowody restore, receipt, snapshoty, logi i screenshoty
pozostają ignorowane w data/raw/earnings-previous-backfill-apply-2026-11-06.
Bez sekretów lub pełnych komunikatów w Git. Końcowo **17 modified / 45
untracked**, indeks pusty, main/HEAD c42cf6c411c85a64927fe5c6b3cf98f9e906c871
bez zmian. Bez stagingu, commita, pusha, reset, clean, amend lub force.
