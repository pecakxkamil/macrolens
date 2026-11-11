# MacroLens — Forecast F1 Activation: zakończona aktywacja

Wykonano **05.11.2026, Europe/Warsaw**, C:\Projects\macrolens, main.

**FORECAST F1 ACTIVATED — 20 observations / runtime enabled**

Normalny APPLY zakończył się COMMIT. Niezależne read-only verify potwierdziło
20 seedów, puste początkowe freezes i dwa checks. Dopiero potem wykonano
enable-runtime. Normalny Calendar pokazuje 14 nowcastów i Revenue guidance
NVIDIA. Nie wykonano nowego HTTP do Cleveland podczas aktywacji ani kontroli
runtime: obowiązuje początkowy cooldown 24 h. API/Vite i monitor Earnings
pozostają działające, bez ręcznego restartu.

## 1. Zgoda, Git i CI

Wykonano dokładnie zatwierdzony kanoniczny plan:

`33fb364f3f518a193d7d451c9dfad6f1d5e005eec2a67c8a01ab626c6c531289`

Plan pozostaje w
`data/raw/forecast-f1-activation-2026-11-05/normal-reviewed-final.json`.
Nie zastąpiono go nowym hashem. Przed Git, po CI, po świeżym backupie i próbie
klonu wszystkie 260 artefaktów, ledger, DDL, referencje i target były zgodne.
Testowe dostosowanie CI nie zmieniło żadnego z tych artefaktów.

Commity:

| SHA | Zakres |
|---|---|
| `a26248b8667bfc422dec3ecd43644e4158b4c639` | Add verified earnings monitor and session presentation — 29 ścieżek zależności |
| `c42cf6c411c85a64927fe5c6b3cf98f9e906c871` | Add verified forecasts and guarded F1 activation — 28 ścieżek F1, adapter testowy CI i ci.yml, razem 30 |

F1 i aktywator zamknięto razem ze względu na istniejące bezpośrednie importy
runtime, bindings i kontrolowanego writera. Nie zmieniano zamrożonego kodu
w celu uzyskania sztucznego podziału. Zależności Earnings wydzielono wcześniej.
CalendarPage wystawiono selektywnie: tylko import i komórkę ForecastValue,
bez wcześniejszej zmiany Previous week użytkownika.

Automatyczny przegląd odrzucił pierwszą próbę commita/pusha, nie uznając
instrukcji załącznika za bezpośrednią zgodę na publikację na main. Polecenie
nie zostało wykonane. Po odpowiedzi użytkownika w rozmowie:
„Tak, zatwierdzam commit F1 i git push origin main” wykonano commit i zwykły
push z kodem 0. Bez amend, force, reset lub clean.

[Actions dla dokładnego SHA c42cf6c411c85a64927fe5c6b3cf98f9e906c871](https://github.com/pecakxkamil/macrolens/actions/runs/42036608364):

| Job | Zakończony wynik |
|---|---|
| Backend tests | success |
| Frontend tests and build | success |
| PostgreSQL integration tests | success — 20 nazwanych walidacji |

Zachowano wszystkie 18 wcześniejszych kroków PostgreSQL i dodano F1 oraz
F1 Activation. Adapter CI tworzy syntetyczną bazę, wykonuje prawdziwy
backup/restore i wspólną pełną próbę klonu. Wymaga GITHUB_ACTIONS, roli
macrolens_ci, loopback, kontrolnej nazwy i pełnego ID serwisu. Nie łączy się
z normalną macrolens. Nie zmieniono guardów produkcyjnych, dependencies,
lockfile, uprawnień lub timeoutów CI. Normalny APPLY nastąpił po trzech sukcesach.

## 2. Testy dokładnego indeksu

| Kontrola | Zależności Earnings | F1 z aktywatorem |
|---|---|---|
| Pełny backend | 1506 passed | 1541 passed, 88,57 s |
| Pełny frontend | 713 passed / 35 plików | 717 passed / 36 plików, 34,38 s |
| TypeScript noEmit | passed | passed |
| Production build | passed, 4,32 s | passed, 5,15 s |
| Największy chunk | 407,04 kB | 407,04 kB |
| Dotychczasowe PostgreSQL | 19/19 passed | 20/20 passed |
| Nowa pełna próba aktywacji F1 | — | passed; łącznie 21 walidacji lokalnych |

F1 sprawdzono na eksporcie **423 zgodnych blob IDs indeksu**. Dwa dodatkowe
testy CalendarPage użytkownika pozostają poza commitem; stąd 717 zamiast
719 z wcześniejszego working tree. Actionlint i diff --check passed.
Pełna lokalna walidacja monitora używała zachowanych oficjalnych PDF ARM/QCOM;
nie dodano tych dokumentów do repo ani nie utożsamiono jej z osobnym krokiem CI.

Pierwszy pomocnik selektywnego stagingu użył błędnego kodowania Windows.
Dotyczyło to wyłącznie kopii indeksu; poprawiono UTF-8 i ponowiono pełny
frontend. Pierwsza syntetyczna baza CI miała niedopuszczony prefiks: bramka
odrzuciła inicjalizację. Poprawiono nazwę bazy testowej, bez osłabienia guarda.
Nieudanych prób nie zaliczono. Kod produkcyjny i 260 artefaktów zachowały bajty.

## 3. Świeży backup poza repo i pełny restore

Po CI wykonano nowy spójny pg_dump custom normalnej bazy:

- rozmiar: **32 533 471 B**;
- SHA-256: `cad17d64d7ed7acaddf77d745af40b721f0e6e2255c593b17cccec56927a9d14`;
- plik poza repo:
  `C:\Users\a\AppData\Local\Temp\macrolens-forecast-f1-approved-ho2ye1wq\normal-e2e.dump`.

Backup pozostawiono. Manifest, TOC i dowód restore są w ignorowanym
`data/raw/forecast-f1-apply-2026-11-05/`. Eksport używał jednego
REPEATABLE READ READ ONLY i pg_export_snapshot, a pg_dump tego samego
snapshotu i default_transaction_read_only. Nie zatrzymywano pracy makro.

Pełny restore na własnym PG17, loopback **55515**, zakończył się kodem 0.
Wszystkie **26 tabel / 3 137 373 rekordy**, uporządkowane binary COPY hash/count
i oba katalogi odpowiadały eksportowi. Zero niezwalidowanych constraints.
Nie użyto starszego archiwum ani restore do normalnej bazy.

Ze świeżego archiwum odtworzono kolejny klon, z jego rzeczywistą tożsamością.
Wykonano także własny backup/restore klonu. Plan klonowy różnił się od
normalnego wyłącznie targetem i target_label. Przeszły SQL 1/0 przy dziesiątym
seedzie z rollbackiem całego DDL/policy/importu, poprawny APPLY 20/0/2,
niezależne verify i ponowne already_initialized bez zmiany danych/timestampów.
Wszystkie 26 starych tabel zachowano byte-identycznie.

Próba sprawdziła zmienione referencje i indeks, rzeczywisty lock timeout 5 s,
zmianę Overview bez zmiany hasha oraz równoległy zapis makro i idempotentny
writer E2D. Nie był to import nowego raportu emitenta. Oddzielna lokalna
regresja monitora sprawdziła pełny import ARM/QCOM, rollback i konkurencyjny
proces. Negatywne zapisy, wymuszony termin HTTP, crash i testowe transporty
dotyczyły wyłącznie izolacji.

## 4. Normalny COMMIT i niezależne verify

Rzeczywisty target, ponownie odczytany przed i po APPLY:

| Pole | Wartość |
|---|---|
| Host / port / database | localhost:5432/macrolens |
| Rola / PostgreSQL | macrolens / 17 |
| Database OID | 16384 |
| Cluster system identifier | 7682090371041935398 |

Oryginalny CLI apply dostał jawne confirm-target i pełny confirm-plan.
`normal-apply-receipt.json` ma outcome=created i zatwierdzony hash.
Jedna transakcja READ COMMITTED pobrała advisory 726530032/726530031 oraz
zatwierdzone SHARE na sześciu referencjach Earnings i trzech referencjach
makro, z lock_timeout 5 s i statement_timeout 120 s. Preflight po lockach
i kontrola katalogów, referencji i artefaktów przed COMMIT przeszły.
Bez globalnego makro lease 726530019 i bez blokowania observations/features,
Overview lub source checks.

Powstały tylko trzy zatwierdzone tabele, constraints/indeksy, forecast_f1_guard
i osiem triggerów. DDL i seed zatwierdzono razem. Niezależne połączenie
read-only sprawdziło pełne payloady, deterministyczne UUID, fingerprinty,
wersje i zgodność katalogu z reference.after; constraints są zwalidowane.
Append-only sprawdzono zapisem w izolacji oraz zgodnością definicji w normalnej
bazie, bez negatywnych prób UPDATE/DELETE w normalnym środowisku.

| Tabela | Po COMMIT, przed runtime | Po runtime i końcowej kontroli |
|---|---:|---:|
| forecast_vintages | 20 | 20 |
| forecast_freezes | 0 | 6 |
| forecast_refresh_checks | 2 | 2 |

Nadal **16 model_nowcast / 4 issuer_guidance / 0 consensus**. SQL captured_at
oznacza rzeczywisty nowy zapis. Nie przypisano dawnego capture/first print.
Ponowne CLI apply zwróciło already_initialized przez read-only verify.
Pełne 29 snapshotów po runtime i po końcowych GET/idempotencji są identyczne.
Bez automatycznego restore/rollbacku po COMMIT.

## 5. Runtime, cooldown i freeze

Po niezależnym verify wykonano osobne CLI enable-runtime. Normalny token
`data/raw/forecast-f1/activation.json` odpowiada zatwierdzonemu planowi,
rzeczywistemu targetowi, aktywnej niezmiennej policy i 260 artefaktom.
Pozostawiono go aktywny.

Normalny status: **registered=true, activated=true, cooldown**.
Pierwszy rzeczywisty worker zwrócił added=0, frozen=2. Kolejne wybudzenia
zwróciły added=0, frozen=0. Dwa zamrożone subjecty QCOM dały sześć wierszy
(trzy typy na metrykę), wszystkie bez prognozy znanej przed Actual.
Nie jest to sześć nowych obserwacji ani dopisanie historycznego guidance.

Najwcześniejszy retry_at to **06.11.2026, 16:05:40 Europe/Warsaw**
(`2026-11-06T15:05:40.784569+00:00`). Następna próba zależy także od
działającego backendu, autoryzacji, lease, robots i zgodności warunków.
Nie ominięto cooldownu i nie wykonano nowego HTTP Cleveland podczas tego etapu.
Aktywny runtime nie oznacza, że natychmiast pobrano nowe dane.

Wykorzystuje istniejący lifecycle Earnings i coordinator, bez drugiego
schedulera, timera lub procesu. Kontrole busy/lease, trwałego claim przed HTTP,
restartu, 429/403, historii, idempotencji i freeze mają wyniki z testów
izolowanych; normalne wybudzenia potwierdziły cooldown i brak duplikatów.
Nie wymuszano normalnego błędu wydawcy. GET Calendar niczego nie zamraża.

Zakres źródła pozostaje lokalny, osobisty, niekomercyjny. Nie dodano kont,
płatności, kontaktu z dostawcami, nowych miesięcy, emitentów lub parsera
automatycznych guidance. Zamknięta lista Cleveland obejmuje tylko
**październik/listopad 2026**. F1 nie jest pełnym konsensusem analityków.

## 6. Rzeczywisty Calendar i zachowanie istniejących danych

Chrome korzystał z **http://localhost:5173/#/calendar**, API 8000 i normalnej
bazy, bez fixture, mockowania JSON lub własnego preview. Końcowy przebieg,
obejmujący rzeczywisty reload: **215 kontroli / 24 odpowiedzi API 200**.
PL/EN, 1366/390 px, zero błędów JS/console.error/503 i żądań przeglądarki
do wydawców. Obejrzano desktop EN i prawą część tabeli mobile PL.
Nie deklaruje się pełnego audytu WCAG.

Potwierdzono wszystkie **14 nowcastów** z właściwymi miarami i źródłem,
w tym CPI październik MoM SA `0,24% · Nowcast`, bez consensus surprise,
zamiany CPI/Core CPI, MoM/YoY, SA/NSA lub GDP Q4 na Q3. NVIDIA Q3 FY2027
pokazuje Revenue `105,84–110,16 mld USD · Guidance`, EPS Forecast pozostaje —.
Zakres nie został zastąpiony midpointem. QCOM Forecast pozostaje null;
nie dodano wydarzenia ARM Q3. Siedem kolumn Earnings i osiem makro zachowano,
źródła działają, tabela ma wewnętrzny scroll bez overflow całej strony.

Dodatkowe **37 GET HTTP 200** sprawdziło listę 34 datowanych wydarzeń,
ich szczegóły i oba statusy runtime. Potwierdzono konkretne kwartały Previous
AAPL/PLTR/AMD/INTC/AMZN, null EPS Previous CRWD oraz bieżące Actual:
ARM EPS 0,12 USD / Revenue 1,443 mld USD i QCOM EPS 1,17 USD /
Revenue 10,322 mld USD. Pierwszy pomocniczy selektor API wybrał wcześniejszy
kwartał AAPL z szerokiego zakresu; doprecyzowano FY/Q i ponowiono kontrolę,
bez zmian aplikacji lub osłabienia asercji.

Wszystkie **26 wcześniejszych tabel**, w tym 13 Earnings, są byte-identyczne
między pełnym snapshotem przed APPLY a kontrolami po COMMIT i runtime.
Nie zatrzymywano procesów makro; ten wynik dotyczy konkretnego okna,
nie wymogu zatrzymania lub niezmienności makro w przyszłości. Katalog zmian
odpowiada dokładnie trzem tabelom F1. Nie dodano events, periods lub spółek.
E2D zachowuje 29/50, Previous 23 raporty / 45 metryk, eventów/okresów nadal 37.
Końcowo **29 tabel / 3 137 401 rekordów**.

Monitor Earnings nadal loop_running=true, activated=true, completed,
checked=0; jego token, artefakty i SQL policy przeszły niezależną autoryzację.
Market Cap nadal 49/53, bez importu i zmiany polityki 7/45 dni. Cache SHA:
`94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799`.

## 7. Ochrona prac i zakończenie

Wejście: 24 modified / 42 untracked, pusty indeks. Manifest wszystkich
66 plików i pełny diff zapisano w ignorowanym katalogu tego etapu.
**Wszystkie 13 chronionych prac użytkownika zachowano byte-identycznie.**
Z 66 początkowych plików 65 zachowało bajty; zmieniono tylko test aktywacji
F1 dla syntetycznego trybu CI. Pozostałe dodatki to adapter testowy, dwa kroki
ci.yml i ten raport. Nie zmieniono żadnego zamrożonego artefaktu planu.
Wcześniejsze raporty zachowano jako historyczne dowody.

Własny Chrome zamknięto przez CDP 9295. Klon
macrolens_forecast_f1_activation_0caf98efdcd1 usunięto. Własny PG17 i wolumen
usunięto po kontroli pełnego ID
`da5a34cd167d3612544f1deabd81243c7d4f1a5b5101f76190b3eb3a13c2558c`,
etykiety forecast-f1-apply-2026-11-05, braku innych klientów i baz poza
control/postgres/template. Normalnego PostgreSQL, API/Vite i aktywnych tokenów
nie objęto sprzątaniem. Nie pozostawiono diagnostycznych blokad lub lease.

Końcowo **9 modified / 7 untracked**, indeks pusty. Siódmy nieśledzony plik
to ten raport. main i origin/main:
`c42cf6c411c85a64927fe5c6b3cf98f9e906c871`.
Bez dodatkowego commita z metadanymi po pushu. Backup poza repo pozostaje;
plany, receipts, pełne snapshoty, logi, screenshoty i helpery są ignorowane
w data/raw/forecast-f1-apply-2026-11-05. Nie wystawiono sekretów ani pełnych
dokumentów wydawców do Git.
