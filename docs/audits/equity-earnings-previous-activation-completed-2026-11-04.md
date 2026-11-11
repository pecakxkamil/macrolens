# MacroLens — E2E Activation: Git zakończony, STOP przed APPLY

Wykonano **04.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`, main.

**Normalnej E2E Activation NIE wykonano.** Zgodnie ze zleceniem zatrzymano
operację na ponownym sprawdzeniu zatwierdzonego planu: trzy tabele makro
zmieniły się od jego przygotowania. Wszystkie dziesięć dotychczasowych
tabel Earnings, schemat, ledger i artefakty są zgodne. Nie zmieniono planu,
nie zastąpiono hasha, nie wykonano DDL/importu do normalnej bazy.

## 1. Zakres zgody i zrealizowane etapy

Zgoda użytkownika dotyczyła wyłącznie planu:

`6d224e8299ba70a2c133e3c2cadc345a3ed16f60a41aefa7427892d112f073fb`

Zakres nadal jest jednoznaczny: jedna tabela `earnings_historical_reports`,
constraints/indeksy/funkcja i trzy triggery oraz 23 raporty / 45 metryk:
23 Revenue i 22 EPS, bez EPS CRWD. Bez nowych events/periods/emitentów,
Current, prognoz lub zmian Market Cap SQL. Wykonano etap A — Git i zielone
CI. Etap B ujawnił rozbieżność pełnych snapshotów. Zgodnie z nakazem STOP
nie rozpoczęto etapów C–G: nowego normalnego backupu, jego restore,
próby na nowym klonie ani normalnego apply i kontroli po COMMIT.

## 2. Cztery commity i push

Początek: HEAD `94526c9cf0422dde041c69fd4fdec21549a8b39e`,
**21 modified / 39 untracked**, pusty indeks. SHA wszystkich 60 zastanych
plików, pełny diff i osobny manifest 13 chronionych plików zapisano lokalnie
w ignorowanym `data/raw/earnings-previous-apply-2026-11-04/`.

| Zakres | Pełny SHA | Message |
|---|---|---|
| E2D Activation | `a9178ed8b8b2538b2fb4ffda88a8113435119f00` | Add safe earnings report activation |
| E2E Previous | `767ab378597b3f6e87d5dc043bf89b89b74fa2c7` | Add previous earnings comparisons |
| Market Cap | `93056754be133454118797c9b78fb55fc189c23d` | Add cached market capitalization data |
| E2E Activation | `eeb92abcfa948806a41f7fcbafa678edec6072de` | Add guarded earnings history activation |

Etap E2E w drugim indeksie odtworzono z zapisanego diffu sprzed Market Cap,
bez cofania working tree. Dlatego nie powstał etap wymagający brakującego
modułu cap lub niespójny frontend. Każdy staged diff przejrzano, sprawdzono
ścieżki i whitespace. Nie dodano chronionych plików, `.env`, data/raw,
cache, backupów, logów, helperów, screenshotów lub sekretów.

Minimalne zmiany CI zachowują poprzednie 11 walidacji i dodają kolejne
sześć, razem 17. Testy aktywacji E2D/E2E przyjmują service ID Actions
wyłącznie pod bramką GITHUB_ACTIONS, właściwej bazy kontrolnej, roli
macrolens_ci i loopback. Nie zmieniono produkcyjnych aktywatorów,
zatwierdzonego planu, timeoutów, zależności, lockfile ani guardów HTTP.

Pierwsza łączona próba commit/push została odrzucona przez automatyczny
przegląd przed uruchomieniem polecenia: przegląd nie uznał zgody z załącznika
za bezpośrednią, zaufaną autoryzację pusha do domyślnej gałęzi. Nie obchodzono
odrzucenia. Lokalny czwarty commit zapisano osobno, po czym użytkownik
potwierdził wprost: **„Tak, zatwierdzam git push origin main”**.
Zwykły push czterech commitów zakończył się kodem 0, bez force. Remote i
lokalny main wskazują `eeb92abcfa948806a41f7fcbafa678edec6072de`.

## 3. Testy dokładnych indeksów

Każdy indeks wyeksportowano z Git blobów, z kontrolą wszystkich blob IDs:
352 / 359 / 377 / 382 pliki. Chronione pliki w tych kopiach pochodzą z HEAD,
a nie z working tree. Późniejsze kopie umieszczono w własnych katalogach
tymczasowych poza obserwacją autoreload. Node 22.23.4, pełny offline guard.

| Indeks | Backend | Frontend | TypeScript / build | PostgreSQL |
|---|---:|---:|---|---:|
| E2D Activation | 1343 passed, 64,76 s | 670 passed | passed | 12/12 |
| E2E Previous | 1362 passed, 62,32 s | 678 passed | passed | 13/13 |
| Market Cap | 1454 passed, 67,78 s | 692 passed | passed | 16/16 |
| E2E Activation | **1461 passed, 68,06 s** | **692 passed** | passed | **17/17** |

Różnica względem 694 testów frontendowych wcześniejszego working tree
wynika z dwóch testów w chronionym CalendarPage.test użytkownika. Nie
usunięto ich i nie dołączono jego pracy w celu wyrównania licznika.
Actionlint oraz staged/working diff --check przeszły.

PostgreSQL 17 działał wyłącznie na własnym loopback 55483, z losowymi
bazami, kontrolnymi nazwami i blokadą publisher HTTP. Przeszły rzeczywiste
backup/restore na danych testowych, fresh/upgrade, błędy SQL i pełny
rollback, idempotencja, constraints/append-only, prawdziwe API oraz
niezmienność wcześniejszych tabel. To nie świeży backup normalnej bazy.
Nie uruchamiano FMP lub publicznego refreshu Market Cap.

Pierwsza próba frontendowej kopii z katalogu tymczasowego zatrzymała się
na odmowie odczytu katalogu nadrzędnego przez esbuild. Ponowiono test tej
samej kopii z uprawnieniem do potrzebnego odczytu, bez zmiany źródeł lub
asercji; cały frontend/typecheck/build przeszedł. Nieudanej próby nie
zaliczono jako sukcesu.

## 4. GitHub Actions

[MacroLens CI — run 41881667376](https://github.com/pecakxkamil/macrolens/actions/runs/41881667376)
ma **completed / success** dla dokładnego finalnego SHA
`eeb92abcfa948806a41f7fcbafa678edec6072de`.

| Job | Wynik |
|---|---|
| Backend tests | completed / success |
| Frontend tests and build | completed / success |
| PostgreSQL integration tests | completed / success, wszystkie 17 kroków walidacji |

API początkowo nie pokazywało runu po pushu. Uruchomiono istniejący
workflow_dispatch na potwierdzonym main. Opóźniony push-run 41881659411
został anulowany przez istniejącą concurrency; nie zaliczono go jako
sukcesu. Podstawą zielonej bramki jest zakończony run 41881667376 i jego
trzy joby, nie lokalne testy lub wcześniejszy SHA.

## 5. Zgodność planu, targetu i artefaktów

Kanoniczny hash zapisanego planu jest nadal dokładnie zatwierdzony.
Pełny manifest 23 raportów / 45 miar, ledger i 25 artefaktów są zgodne.
Sprawdzono pochodzenie każdego artefaktu z finalnego commita. Git
normalizuje końce linii: 17 artefaktów ma zatwierdzone bajty LF, osiem CRLF.
Wszystkie zatwierdzone SHA odtworzono dokładnie z treści Git i pierwotnej
materializacji LF/CRLF; pliki runtime mają te same zatwierdzone bajty.
Nie podmieniono treści lub hasha planu z powodu normalizacji.

Odczyt normalnej bazy wymuszał REPEATABLE READ READ ONLY. Potwierdzono:

- host localhost, port 5432, database macrolens;
- rola macrolens, OID **16384**;
- cluster system identifier **7682090371041935398**, PostgreSQL **17**;
- schema phase **before**, brak tabeli historii E2E;
- 23 tabele / **2 963 542 rekordy**;
- niezmienione reprezentacje schematu Earnings i makro.

Wszystkie 10 wcześniejszych tabel Earnings ma dokładnie zatwierdzone
liczniki i hashe: 53 companies, 55 aliases, 37 periods, 37 events,
40 evidence, 66 confirmations, 6 dokumentów/12 miar E2B i 27/46 E2D.
Nie nastąpiła aktywacja E2E przez inny proces.

## 6. Dokładna przyczyna STOP

Zatwierdzony plan wiąże **pełne dane wszystkich 23 tabel**, w tym 13 tabel
makro. Od jego przygotowania, przy działającej normalnej aplikacji,
zmieniły się trzy tabele makro. Nie jest to zmiana danych Earnings.

| Tabela | Licznik w planie | Licznik obecnie | SHA-256 w planie | SHA-256 obecnie |
|---|---:|---:|---|---|
| overview_publications | 8 | 8 | `cecbdf76f7d5b0347348a7885c01601863a672275be82d6263944441a899a004` | `6a441252a1388706f99072ba8fce7b726a3ce8c331982f9a6e8a4c517286bf4f` |
| overview_refresh_state | 1 | 1 | `d0d1a44c57e673d97eba4445a8771d70fd56e4c1ee795c1822d029ab34ac44b8` | `5f3f9f1a04fe61ed213219c0f0660c5dd53c0e74e03441e1d6f5c34bb2f09ea0` |
| source_check_runs | 2571 | 2617 | `2b4cff551b4eccbaab521ac8cc6524c2fb7a515d86e2dffaa193ddf8df8fda39` | `75194d7f0695cac581058aac98db783623d3cfc5de396e7ed9f781677a388ab1` |

Plan obejmował 2 963 496 rekordów; obecnie jest o 46 więcej. Pozostałe
20 tabel, w tym wszystkie Earnings, ma identyczne pełne snapshoty.
Nie deklaruje się identyczności trzech powyższych tabel. Nie wykonywano
żadnego własnego zapisu do normalnego PostgreSQL.

Obecny aktywator odrzuciłby te dane jako odmienne od zatwierdzonej podstawy.
Zgodnie z nakazem STOP zatrzymano się **przed otwarciem transakcji zapisującej**.
Nie wywołano normalnego apply, nie próbowano osłabić porównania makro,
nie odświeżono automatycznie planu i nie uznano innego hasha za zatwierdzony.

## 7. Backup, aplikacja i niewykonane kontrole po aktywacji

Dotychczasowy zamrożony backup **31 218 033 B**, SHA
`947e4ff0a8d092a0f72a8b204f5e892e871822dc9cd893dbb667c97e8ef104b5`,
i jego wcześniejszy dowód pełnego restore nadal mają zgodne lokalne hashe.
Nie zastępuje to wymaganego przez zlecenie świeżego backupu. Nowego dumpu,
restore normalnych danych i próby na nowym klonie **nie wykonano w tym
etapie**, ponieważ bramka B już nie przeszła. Skrypt do kolejnego etapu
pozostał nieuruchomiony; nie stanowi nowego planu.

Wynik normalnej aktywacji: **STOP, COMMIT niewykonany, 0 nowych raportów /
0 nowych miar**, tabela historii nieutworzona. Brak potrzeby i brak próby
rollbacku. Backend i Vite nie były zatrzymywane w tym zleceniu. Nie
uruchamiano drugiego backendu, Vite, Chrome lub schedulera. Zwykłe procesy
makro pozostają aktywne; R1–R3/K2/Overview bez zmian kodu i konfiguracji.

Cache Market Cap ma ten sam pełny SHA jak przed operacją: **49 wartości /
4 braki**, bez nowego refreshu, importu lub FMP. Normalne Previous nadal
obejmuje cztery wydarzenia E2B. Nowe AAPL/PLTR/AMD Previous nie zostały
udostępnione w normalnym PostgreSQL. Nie deklaruje się nowych wyników
normalnego Chrome lub wartości po aktywacji, której nie wykonano.
Wcześniejsze izolowane kontrole znajdują się w raporcie readiness, a w tym
etapie ponownie przeszła izolowana walidacja SQL/API dokładnych indeksów.

## 8. Ochrona i końcowy Git

Wszystkie 13 chronionych plików zachowano byte-identycznie i wyłączono
ze wszystkich czterech commitów. Po zakończeniu: **9 modified / 5 untracked**,
indeks pusty, main zgodny z origin/main, HEAD
`eeb92abcfa948806a41f7fcbafa678edec6072de`. Dziewięć modyfikacji i cztery
nieśledzone wcześniejsze raporty to zachowane prace użytkownika; piąty
nieśledzony plik to ten raport STOP. Nie tworzono commita dokumentacyjnego
po aktywacji, ponieważ aktywacji nie wykonano.

Nie użyto git add ., reset, clean, amend lub force push. Pełne logi,
manifesty, dowody indeksów, wyniki CI i read-only preflight zachowano
w ignorowanym data/raw. Brak sekretów/cache/backupów w Git.

Po kontroli pełnego ID
`13b51df67bd6ced7052a54c0b6528ba28f919d0237309eb3fd58c55ee66d5276`,
etykiety i braku baz poza control/postgres/template usunięto wyłącznie
własny testowy kontener PG17 i jego wolumen. Nie pozostawiono własnych
baz testowych lub lease w normalnym PostgreSQL.

Dalsza aktywacja wymaga nowego, jawnie zleconego przygotowania aktualnej
podstawy danych, świeżego backup/restore oraz nowego pełnego hasha do
osobnego zatwierdzenia. Nie utworzono go automatycznie w zastępstwie
zatwierdzonego planu. Sam zielony CI nie usuwa tego blokera.


Końcowa kontrola dostępności po STOP: Vite 5173 i normalny GET Calendar
Earnings na API 8000 zwracają HTTP 200. API ma nadal dokładnie cztery
datowane wydarzenia z Previous. Potwierdzono ponownie zgodność obu sygnatur
schematu z planem, 13 chronionych hashy oraz pusty indeks. To kontrola
istniejącej aplikacji, nie potwierdzenie nieprzeprowadzonej aktywacji.
