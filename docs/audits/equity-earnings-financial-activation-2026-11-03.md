# MacroLens — E2B Activation: przygotowanie i zatwierdzone wykonanie

Weryfikacja **03.11.2026, Europe/Warsaw**, repozytorium
`C:\Projects\macrolens`, `main`, HEAD
**`4f4e12ce138be210bedbb13924cf0c4e52d65411`** —
`Add official earnings financial actuals and table`.

**Aktywowano E2B 03.11.2026 w normalnej localhost:5432/macrolens po wyraźnym
zatwierdzeniu planu d39f1c33…402ac65. API i Vite działają; normalny Calendar
pokazuje Revenue Actual i GAAP diluted EPS. Wyniki wykonania: sekcja 16.**
Sekcje przygotowania opisują stan historyczny przed zgodą i wykonaniem.
Sekcje 1–12 opisują pierwsze przygotowanie. Wykonano identyfikację, odczytowy preflight,
świeży pg_dump oraz pełne odtworzenie do osobnej efemerycznej bazy.
Nową procedurę apply uruchamiano tylko na własnym PostgreSQL testowym.
Nie wykonywano stagingu, commita ani pusha. Nie rozpoczęto E2C.

## 1. Stan wejściowy i zachowanie prac

Potwierdzono HEAD, main, pusty indeks oraz **9 modified / 4 untracked**.
Przeczytano E1, E2A, Activation i raport implementacji/zamknięcia E2B;
sprawdzono bieżące modele, importer, schema SQL, ochronę inicjalizatorów,
procedurę E2A i testy. Zapisano nowy pełny diff i SHA-256 wszystkich
13 zastanych plików. Zachowano je byte-identycznie. Nie edytowano
wcześniejszych raportów, kodu E2A/E2B, UI, zależności lub CI.

`config/earnings_financial_manual.json`, schema E2B, importer, czytnik
i inicjalizatory odpowiadają zatwierdzonym blobom HEAD po normalizacji Git.
SHA-256 bajtów pliku danych:
**`7feb36d2a226e29bada634386c41729dcb8aa92792807ee5c7e21f837c5bb7ad`**.
Nie dodano innych raportów lub liczb. Nie pobierano SEC/IR lub pełnych
komunikatów. Sprawdzenie danych używa zatwierdzonych lokalnych metadanych.

## 2. Rzeczywisty backend i cel

| Pole | Ponownie potwierdzona wartość |
|---|---|
| Backend | Worker PID 16352, Uvicorn app.api.main:app, 127.0.0.1:8000 |
| Katalog procesu | C:\Projects\macrolens |
| Host / port z procesu | localhost / 5432 |
| Baza / rola z procesu | macrolens / macrolens |
| Kontener | macrolens_postgres, PostgreSQL 17 |
| Pełny ID kontenera | 1b318d8850fde04efdc47d51fc0be83154cac656a12485840b252b327ce35738 |
| Aktualny OID bazy | **16384** |
| Aktualny identyfikator klastra | **7682090371041935398** |
| transaction_read_only diagnostyki | **on** |

Wybrane niesekretne DB_HOST/DB_PORT/DB_NAME/DB_USER i cwd odczytano
z rzeczywistego procesu obsługującego port 8000, następnie porównano
z niezależnym połączeniem SQL i parametrami klastra. Nie oparto się
wyłącznie na dawnych identyfikatorach lub konfiguracji na dysku.
Nie wypisywano ani nie zapisywano hasła, pełnego środowiska lub .env.

Normalny schemat ma **19 tabel public**, w tym dokładnie sześć E2A.
Brak obu tabel finansowych E2B i jakichkolwiek kolizji ich obiektów.
E2A: **3 companies, 3 aliases, 6 periods, 6 events, 5 source evidence,
12 date confirmations**. Schemat E2A jest zgodny z wzorcem wykonanym
na izolowanym PostgreSQL, nie częściowy lub obcy.

## 3. Początkowe liczby i hashe wszystkich tabel

Poniższe wartości pochodzą z aktualnego spójnego snapshotu PostgreSQL,
użytego także przez pg_dump. SHA-256 liczono z pełnego binary COPY,
z wierszami uporządkowanymi po PK; nie są to przybliżone statystyki.
Łącznie **2 924 443 rekordy**. To świeży stan, a nie przepisane liczby
z poprzedniego raportu E2B.

| Tabela | Rekordy przed / po | SHA-256 przed = po |
|---|---:|---|
| alfred_backfills | 15 | `e3b943e5151b7ddda3a7e2a7fe355528bb266f3630344728f9429ce59497b65e` |
| computed_features | 1048232 | `ed81789d6b3bf5df0f6a977101c0368a021dacd63952006188c56dcdd7fe6539` |
| earnings_companies | 3 | `674c5e2ed93a346ca4804cd79dcdc6e3038c2f0c7db6c10260f79ef416b9d853` |
| earnings_company_aliases | 3 | `ad54505df5ff5a50fafb9214c73f61646b4c2efb34f59bc23d386b90ed3f5eac` |
| earnings_date_confirmations | 12 | `9ac2ca6ea377eb91325c52ba2bec1f9990f762919c122b2de51f22555c2df5c2` |
| earnings_events | 6 | `9b6e45181937c2244847ba739de0ef8060a3934ba870bd01044d0b848a32cc6d` |
| earnings_periods | 6 | `940693c31b6f8e2e682073e1600c794a3023ca1ec98a2f9b0093885ec05371b0` |
| earnings_source_evidence | 5 | `b06315419b8203a7ca6a3f985bb74557fb25cf161853c080a1d86278cc892832` |
| economic_releases | 18 | `9fad16df8f5a9011ff2a46915e956e7c964e57a4b9ce9e7e3f190d3b38c14cc9` |
| ism_documents | 22 | `70de199f658a1528704162235a2d365e92fbc7e84aa5116d998f386e4fa70efd` |
| ism_observations | 264 | `a76ed493a80e36cca32c566636565544e180f3a4a590d411ed21f44734892ab3` |
| observation_vintages | 1873243 | `93daa952560a3a0b0e231c8cda7b81abf770cc17c46a25f8ff9a17afa341da9a` |
| overview_publications | 8 | `97f9a051e40f9bdeb06a8332bcc85388f33809c58558f30f5dac4c1420f2efa7` |
| overview_refresh_state | 1 | `37f48e69d1c442c6da597806f52311348963017b858e543e6a356d4b0ef7dfd4` |
| publisher_documents | 24 | `547ee8108ef7a6cad05a5d9793cfb9fbcb422a5c73f4af963201dbf08b0aff5a` |
| release_dates | 804 | `3385a38806129a73cf1fbac215e38c5fb3242f8d672e8eb039b1329adcd43746` |
| series | 58 | `f4cd1add01658ea0d16892004ddf7ef7cce89103de274142672a58f38c1b9ac0` |
| series_release_map | 45 | `e5eb3c6545828d89d6165b879d43305da0588c01ded45618a3731a05235ece84` |
| source_check_runs | 1674 | `436b17f90dbc5241b9071c5137f285ddd96e060c1addb1260ce9e8a7433ad83f` |

Wszystkie 19 hashy i liczników ponownie porównano po testach z normalną
bazą: **identyczne**. Nie ograniczano kontroli do count albo MAX(timestamp).
Chroniono osobno pełne pierwotne wiersze E2A, w tym wszystkie daty,
dowody i istniejące ID. Nie wykonano zapisów w tych tabelach.

## 4. Świeży backup i pełne odtworzenie

Kopia lokalna, ignorowana przez Git:

`data/raw/earnings-financial-activation-2026-11-03/macrolens-before-financials-2026-11-03.dump`

| Pole | Wynik |
|---|---|
| Format | pg_dump custom, PGDMP |
| Rozmiar | **30 822 948 B** |
| SHA-256 | **1481e2c07a13d8ab8e373eb88cbb39760968715a052c701492e54500a7e12716** |
| Zakres | Cała normalna baza, --no-owner --no-acl |
| pg_dump | Kod **0**, wymuszone read-only |
| TOC | pg_restore --list kod **0**, spis zachowany lokalnie |
| Pełny pg_restore | Kod **0**, --exit-on-error --single-transaction --no-owner --no-acl |
| Odtworzone tabele / wiersze | **19 / 2 924 443**, wszystkie hash/count zgodne |
| Schemat | Zgodne kolumny, constraints, indeksy, triggery i funkcje |
| Niezwalidowane constraints | **0** |

Snapshot do porównania i pg_dump był wspólny, przez pg_export_snapshot.
Źródłowe połączenie było REPEATABLE READ READ ONLY; klient pg_dump miał
PGOPTIONS wymuszające default_transaction_read_only. Tymczasowy session
lease 726530019 chronił spójne przygotowanie przed zwykłym importerem
koordynatora. Zwolniono go w finally; nie pozostawiono blokady aplikacji.

Odtwarzano do losowej bazy `macrolens_financial_restore_<uuid>` na
**osobnym PostgreSQL 17**, kontenerze
`macrolens_financial_activation_20261103`, loopback **55451**.
Nigdy do macrolens. Odtworzenie objęło także FRED/ALFRED,
computed_features, dokumenty, publikacje/stan koordynatora i wszystkie
sześć tabel E2A. Owner/ACL nie były przenoszone do izolowanego serwisu;
kontrola zgodności dotyczy struktury i pełnych danych bazy.

Manifest `backup-manifest.json` wiąże kopię z aktualnym hostem, bazą,
rolą, OID i klastrem. Spis jest w `backup-toc.txt`, dowód pełnego restore
w `restore-validation.json`. SHA-256 dowodu:
`1729a2aa2fd715fb341a6d4631fd1325dab7bfc9f973f205aed984af4ef5a88e`.
Manifest zapisuje również hash i pełne liczniki źródłowych tabel.
Samo sprawdzenie TOC nie zastępuje wykonanego restore.

Losową bazę odtworzeniową usunięto po kontroli. Własny wolumen testowy
również usunięto przy końcowym cleanup. Dump i dowód pozostają lokalnie.
Nie wykorzystano dawnego backupu E2A jako zabezpieczenia E2B.

## 5. Dokładny zakres przyszłego zapisu

DDL to zamrożony plik `app/database/earnings_financial_schema.sql`:
**dwie nowe tabele** `earnings_financial_documents` i
`earnings_financial_observations`, ich PK/UNIQUE/FK/CHECK i indeksy,
jedna funkcja `earnings_financial_guard()` i cztery triggery ochronne.
Bez ALTER sześciu tabel E2A, bez DDL makro, CASCADE lub schedulera.

Importer doda cztery brakujące historyczne periods/events:
NVDA Q1/Q2 FY2027, AMZN Q2 2026 i INTC Q2 2026. Istniejące eventy
AMZN/INTC Q3 zostają użyte pod tymi samymi ID, bez UPDATE. Nie powstaną
fikcyjne date confirmations dla nowych czterech wydarzeń.

| Spółka | Okres | Revenue, mln USD | GAAP diluted EPS, USD |
|---|---|---:|---:|
| NVDA | Q1 FY2027 | 81615 | 2.39 |
| NVDA | Q2 FY2027 | 96221 | 2.46 |
| AMZN | Q2 2026 | 200606 | 5.75 |
| AMZN | Q3 2026 | 201944 | 1.89 |
| INTC | Q2 2026 | 16128 | -2.16 |
| INTC | Q3 2026 | 16513 | 0.60 |

Dokumenty, źródłowe jednostki, period_end i metodologia pochodzą wyłącznie
z zatwierdzonego lokalnego JSON. Revenue jest skonsolidowane; EPS GAAP
diluted, dla Intela attributable to Intel. Decimal zachowuje jednostki
i ujemne/zerowe EPS. Nie ma nowego konsensusu, surprise lub automatycznego
HTTP, archiwum komunikatów, fikcyjnego RAW hash/HTTP 200/SEC accession.

| Obiekt | Teraz | Oczekiwane po osobno zatwierdzonym apply |
|---|---:|---:|
| Companies | 3 | 3 |
| Aliases | 3 | 3 |
| Periods | 6 | 10 |
| Events | 6 | 10 |
| Source evidence dat | 5 | 5 |
| Date confirmations | 12 | 12 |
| Financial documents | Brak tabeli | 6 |
| Financial observations | Brak tabeli | 12 |

Przyszła NVDA Q3 FY2027 nadal ma Actual null; nie przenosi się Q2 do Q3.
Nowy czytnik z zatwierdzonego kodu sprawdzono read-only na normalnej bazie:
`not_activated`, revenue/EPS null, 17.11 ok. 22:20 PL i call 23:00 PL.

## 6. Osobna procedura E2B Activation

Nowy moduł **app/database/activate_earnings_financials.py** ma osobne
prepare/apply. Nie jest importowany przez API, startup lub scheduler.
Istniejące testowe initializery i wcześniejsze procedury pozostały
byte-identyczne. Dawny hash propozycji f666… i zatwierdzenie E2A nie
uprawniają do wykonania nowej aktywacji.

Prepare wymaga świeżego połączenia, dokładnego target, zgodnej bazy/roli/
OID/klastra, wzorca E2A z izolowanego wykonania, oczekiwanych liczników,
sprawdzonej kopii i dowodu **pełnego** restore. Porównuje schemat oraz
wszystkie dane z backupem. Zmiana po backupie zatrzymuje przygotowanie,
zamiast cicho aktualizować zatwierdzany stan. Normalne prepare ma
read_only=True i SQL REPEATABLE READ READ ONLY.

Apply jest przygotowane, ale **nieuruchomione na normalnym celu**. Wymaga
pełnego hasha konkretnego planu i dokładnej etykiety target. Przed wejściem
do transakcji sprawdza zamrożone artefakty, nagłówek/rozmiar/SHA backupu,
SHA pliku dowodu restore, target kopii, kod restore, zgodność hashy i
usunięcie własnej bazy restore. Ponownie odczytuje żywy cel i schemat.

Jedna transakcja **SERIALIZABLE READ WRITE**, search_path public,pg_catalog,
**lock_timeout=5s**, **statement_timeout=120s**, locki 726530019 i 726530020
obejmuje DDL i cały import. Przed i po porównuje pełne hash/count makro,
cały istniejący zestaw wierszy E2A i wzorzec schematu. Po imporcie sprawdza
oczekiwane 6 dokumentów/12 miar, ich deterministyczne ID, wszystkie pola
źródłowe, kanoniczne kwoty, wersje i metodologię. Błąd w transakcji wycofuje
również utworzone tabele, cztery okresy/eventy i dokumenty/obserwacje.

Idempotencja dopuszcza jedynie kompletny, identyczny schemat E2B i dokładny
zatwierdzony seed. Pomija DDL, znane rekordy nie tworzą wersji ani nowych
timestampów. Obcy/połowiczny schemat, dodatkowe dane, zmiana makro lub E2A
powodują odmowę; nie ma automatycznego naprawiania częściowego DDL.
Po przyszłym COMMIT procedura zwraca receipt z hashem planu, target,
licznikami, manifestem nowych ID i pełnymi hashami stanu po operacji.

## 7. Zamrożone artefakty i sygnatury

| Artefakt | SHA-256 |
|---|---|
| app/database/activate_earnings_financials.py | `213b0af4a3293d53cbf300302286b4bfce5357ea7590cac2fc7e17c546435904` |
| app/database/earnings_financial_schema.sql | `9fbbb8bbbabf76ab23546e2e0fd24a0e1727b69812eb4892b3a83a4fef55e7e1` |
| app/database/activate_earnings.py | `183f77edef67b40640f8773868e5a661014e1427f44923bd9448321d0d4f79f0` |
| app/earnings.py | `9a6372bb6effc7528e2aa35fd64389d969459ec97dced76944b704f75355925b` |
| app/earnings_financials.py | `5f0f3bcc123118f05b2bc6139b9748b04ff7ee22f10a5543d10b9ba145b5fe90` |
| config/earnings_financial_manual.json | `7feb36d2a226e29bada634386c41729dcb8aa92792807ee5c7e21f837c5bb7ad` |
| docs/audits/equity-earnings-financial-activation-rollback-2026-11-03.md | `cdc410c18d3ee43451bcc763242e734c5557c96870dd8ccc27ebf5f94dd11624` |

Sygnatura E2A z normalnego celu i izolowanego wzorca:
`212008551ba85a43e38a4f0e1605e788c4f25a6a44a7a4846e19378666db25cc`.

Oczekiwana sygnatura Earnings po E2B, rzeczywiście wykonana w PostgreSQL:
`8e392331cf452f5dd837a541d53aadcdbc33152af5403abb7d5ce30f270712bd`.

Sygnatura schematu makro:
`ba1b47aaf7d21b170b579369ca5c20b2e6fee871ee382e15fe519a43d37a2cf5`.

`schema-reference.json` zachowuje oba wykonane wzorce. Zmiana artefaktu,
kopii, dowodu, target lub danych po zatwierdzanym preflight unieważnia
ten plan. Nie podmienia się automatycznie pełnego hasha do późniejszego apply.

## 8. Testy rzeczywiście wykonane

| Kontrola | Wynik tego etapu |
|---|---|
| Pełny backend offline | **1251 passed, 42,62 s** |
| Nowe testy bramek bez DB | **12 passed** |
| PostgreSQL 17 Activation fresh | passed |
| PostgreSQL 17 E2A → E2B | passed |
| Świeży backup normalnej bazy i rzeczywisty pełny restore | passed, 19 identycznych tabel |
| Końcowe odczyty normalnej bazy | 19 identycznych hash/count, tylko E2A |
| Zastane SHA, zgodność z HEAD, whitespace | passed |

Nowy `tests/postgres_earnings_financial_activation_validation.py` tworzy
wyłącznie losowe własne bazy, używa rzeczywistych pg_dump/pg_restore
syntetycznego stanu i istniejącego guarda publisher HTTP. Testuje:
fresh/upgrade, 6 dokumentów/12 obserwacji, ponowienie bez duplikatów i
zmian timestampów, rzeczywistą odmowę na innym połączeniu/bazie, błędny
target/token/artefakty/backup, drift schematu i makro, zły CIK/period_end/
jednostkę/metodologię, przerwany import po DDL i pierwszym raporcie,
pełny rollback DDL+seed, zachowanie E2A/makro i read-only GET.
Przyszła NVDA i trzy Q4 pozostają bez wyników/dat. Wyjściowe i końcowe
projekcje danych przy GET są identyczne. Brak zewnętrznego HTTP.

Test jednostkowy ze sztucznym nagłówkiem PGDMP sprawdza wyłącznie walidację
bramek i nie jest przedstawiany jako backup. Nowa walidacja PostgreSQL
używa prawdziwych archiwów i rzeczywiście je odtwarza. Osobno wykonany
restore danych użytkownika opisuje sekcja 4.

Pierwsza próba testu miała błędną asercję długości własnej nazwy bazy
w cleanup (53 zamiast 55 znaków). Poprawiono tylko test; pełna kolejna
walidacja fresh/upgrade przeszła, a jedną pozostałą własną referencyjną
bazę usunięto jawnie po sprawdzeniu nazwy, portu i własnego serwisu.
Nie zmieniano normalnej bazy ani nie zaliczono tej próby jako sukcesu.

Nie uruchamiano nowego CI, Chrome lub pełnego frontendu: nie zmieniono UI,
API, kontraktu danych finansowych lub zależności. Dawne zielone CI i 121
kontroli Chrome z zamknięcia E2B nie są wynikami tego etapu. Nie zwiększano
timeoutów lub nie pomijano testów. Nie zmieniano K2, Overview, R1–R3,
źródeł BEA/FRED/ALFRED lub zapisanych obserwacji makro.

## 9. Osobny plan cofnięcia

[Plan rollback po COMMIT](equity-earnings-financial-activation-rollback-2026-11-03.md)
jest oddzielnym, zamrożonym dokumentem. **Nie wykonano go.** Wymaga receipt
z apply, osobnej zgody, zgodnego target i porównania stanu po aktywacji.
Późniejsze rewizje, nowe dokumenty, date confirmations, zależności lub
zmiany E2A zatrzymują cofnięcie. Nie używa DROP CASCADE.

Zakres: tylko dwie tabele finansowe, ich funkcja oraz cztery nowo utworzone
eventy/okresy z manifestu, po sprawdzeniu zależności. Nie usuwa istniejących
AMZN/INTC Q3, spółek, aliasów lub dat. Każdy błąd ma wycofać całą operację.
Nie dostarczono automatycznie wywoływanego rollbacku lub narzędzia
nadpisującego normalną bazę starszą kopią. Przy pełnym odzyskiwaniu najpierw
restore do nowej bazy i osobna decyzja, z ochroną późniejszych poprawnych danych.

## 10. Stan aplikacji i pozostałe uwagi

Normalny działający API zwrócił **HTTP 200, 1 datowany NVDA / 3 unknown**
dla 17.11. Ten wcześniej uruchomiony proces **nie zwraca jeszcze pól
finansowych E2B**. Nie utożsamiano plików obecnego HEAD z kodem już
załadowanym w pamięci procesu. W tej sesji nie restartowano aplikacji.

To nie blokuje przygotowania planu DB. Po osobnej zgodzie i udanym apply
trzeba przeładować normalny backend z zatwierdzonym kodem i sprawdzić
nowe pola/API/UI. Czytnik E2B z plików HEAD został niezależnie sprawdzony
na normalnej bazie read-only: poprawnie zwraca not_activated i null Actual.
Nie deklaruje się działania finansów w codziennej aplikacji przed aktywacją.

Brak blokujących niezgodności schematu, celu, kopii lub danych. Przy
jakiejkolwiek zmianie stanu przed przyszłym apply należy zatrzymać się
i przygotować nowy plan do przeglądu, a nie omijać walidację. Ograniczenia
licencyjne/operacyjne SEC/IR i brak konsensusu z E1/E2B pozostają bez zmian;
nie wdrożono feedu, nowych źródeł, prognoz lub E2C.

## 11. Pliki, cleanup i końcowy Git

Dodano wyłącznie pięć plików:

- app/database/activate_earnings_financials.py
- tests/test_earnings_financial_activation.py
- tests/postgres_earnings_financial_activation_validation.py
- docs/audits/equity-earnings-financial-activation-rollback-2026-11-03.md
- docs/audits/equity-earnings-financial-activation-2026-11-03.md

Wszystkie 13 zastanych modified/untracked plików zachowano byte-identycznie,
łącznie z CalendarPage/Previous week i testami, CSS, README, Overview,
SourceCheckStatus oraz czterema nieśledzonymi audytami. Ochronione hashe
są w baseline.json; raporty i artefakty zatwierdzonego E2B nie były edytowane.
Końcowo **9 modified / 9 untracked**, indeks pusty, main i HEAD bez zmian.

Własne losowe bazy i kontener usunięto po sprawdzeniu pełnego ID
`ad890e8377d2d009c22ab779bda0f3c2a0e3718e0c7bfd369dedcdc336d44e6d`
i etykiety financial-activation-2026-11-03. Przed usunięciem pozostały
jedynie control/postgres/template. Usunięto tylko własny kontener i jego
anonimowy wolumen; macrolens_postgres i procesy normalnej aplikacji pozostały.
Nie pozostawiono diagnostycznego lease.

Backup, manifesty, dowody restore, plan, snapshoty, logi i helpery są
ignorowane przez Git pod `data/raw/earnings-financial-activation-2026-11-03/`.
Nie wysłano ich do GitHub i nie dodano sekretów do nowych plików.
Bez stagingu, commita, pusha, resetu, clean, amend lub formatowania globalnego.

## 12. Konkretny plan do osobnego zatwierdzenia

Cel: **localhost:5432/macrolens**, rola **macrolens**, OID **16384**,
klaster **7682090371041935398**. Zakres: dwie nowe tabele finansowe z ich
ochroną, cztery nowe historyczne okresy/eventy, sześć dokumentów i 12 miar
z zatwierdzonego seeda, w jednej transakcji. Makro i zastane E2A bez zmian.

Plan:
`data/raw/earnings-financial-activation-2026-11-03/activation-plan.json`

**Pełny hash kanonicznego planu:**

`ef4d0f2b1084c0feeff532c270016cb96995541c5f7dcedcb7e83bb3ab7d2b82`

Ten hash identyfikuje przygotowany zakres; sam nie stanowi zgody.
Zatrzymano się przed pierwszym DDL/importem w normalnej bazie.
Do wykonania apply potrzebne jest osobne, wyraźne zatwierdzenie tego celu
i pełnego hasha. Normalna baza nadal ma tylko E2A.

**Gotowe do zatwierdzenia.**

## 13. Zgoda użytkownika, zatrzymanie zapisu i nowy plan — 03.11.2026

Użytkownik wyraźnie zatwierdził cel localhost:5432/macrolens, rolę
macrolens, OID 16384 i klaster 7682090371041935398, lecz **wyłącznie**
plan ef4d0f2b1084c0feeff532c270016cb96995541c5f7dcedcb7e83bb3ab7d2b82.
Zgoda nakazywała zatrzymać się i przygotować nowy plan przy zmianie danych,
schematu, artefaktów lub celu. Nie obejmowała automatycznej zgody na nowy hash.

Przed jakimkolwiek zapisem ponownie sprawdzono pełny hash planu,
wszystkie zamrożone artefakty, format/rozmiar/SHA kopii, dowód pełnego
restore i jego SHA, tożsamość bazy, podpisy obu schematów, pełne binary
COPY hash/count wszystkich 19 tabel i wszystkie pierwotne rekordy E2A.
Połączenie miało read_only=True i REPEATABLE READ READ ONLY.

**Cel, schematy, artefakty, poprzednia kopia i dowód restore były zgodne.
Pierwotne E2A było identyczne. Jednak trzy tabele miały zmienione dane:**

| Tabela | Liczba w zatwierdzonym planie | Liczba aktualna | Wynik |
|---|---:|---:|---|
| overview_publications | 8 | 8 | SHA-256 zmienione |
| overview_refresh_state | 1 | 1 | SHA-256 zmienione |
| source_check_runs | 1674 | 1720 | 46 dodatkowych rekordów, SHA-256 zmienione |

Pozostałe **16 tabel**, w tym observation_vintages, computed_features
i komplet sześciu tabel E2A, miało identyczne hash/count. Nie ustalano
przyczyny zmian koordynatora przez uruchamianie importerów lub refresh.
Nie potraktowano tych zmian jako dopuszczalnego wyjątku od zgody.
Zatrzymano się w **odczytowym preflight**, bez uruchomienia apply.
Nie obchodzono walidacji i nie modyfikowano zatwierdzonych artefaktów.

Dowody porównania i snapshot plików przed wznowieniem zapisano lokalnie
w poprzednim katalogu diagnostyki jako `approved-run-preflight.json`
i `approved-run-before-files.json`. Stary plan i backup zachowano;
nie nadpisano ich nowymi plikami ani nie użyto starej zgody do zapisu.

### Nowa kopia i pełne odtworzenie

Ponownie sprawdzono parametry DB z działającego backendu PID 16352
oraz SQL. Cel pozostaje bez zmian. Wykonano nowy pełny pg_dump z tej
samej read-only snapshot transakcji co hash/count tabel. Tymczasowy lease
726530019 dotyczył tylko spójnego backupu i został zwolniony w finally.

Nowy katalog, lokalny i ignorowany przez Git:
`data/raw/earnings-financial-activation-replan-2026-11-03/`.

| Pole | Nowy wynik |
|---|---|
| Kopia | macrolens-before-financials-2026-11-03.dump w nowym katalogu |
| Format | pg_dump custom, --no-owner --no-acl |
| Rozmiar | **30 827 508 B** |
| SHA-256 | **540e786d2ae2d7d2534bd3002ac36e147f89635a308f7ab64b50f423de68f530** |
| pg_dump / pg_restore --list | Kod **0** / **0** |
| Pełny restore | Kod **0**, --exit-on-error --single-transaction --no-owner --no-acl |
| Odtworzone tabele / rekordy | **19 / 2 924 489** |
| Zgodność danych | Wszystkie 19 binary COPY hash/count identyczne |
| Zgodność schematu | Tak, w tym funkcje, triggery, indeksy i constraints |
| Niezwalidowane constraints | **0** |

Pełne odtworzenie wykonano wyłącznie do losowej własnej bazy na osobnym
PostgreSQL 17: `macrolens_financial_activation_replan_20261103`, loopback
**55453**. Nigdy do normalnej macrolens. Powtórnie wykonany izolowany
wzorzec E2A/E2B ma te same zatwierdzone sygnatury. Nie odtwarzano lub
nie nadpisywano żadnych danych normalnej bazy. Nowy manifest i dowód
pełnego restore znajdują się obok nowej kopii.

### Nowy konkretny plan

Read-only prepare nowej procedury ponownie sprawdził żywą bazę względem
nowej kopii: zgodny cel, wszystkie 19 tabel i ich aktualne dane,
wszystkie pierwotne rekordy E2A, brak obiektów E2B i zgodne artefakty.
Nie uruchamiano nowych testów jednostkowych lub frontendowych i nie
przypisano tej próbie dawnych wyników. Nowymi kontrolami są pełny preflight,
świeży backup, pełny restore oraz izolowane wykonanie wzorcowego schematu
i zatwierdzonego seeda. Procedura i jej testowane zabezpieczenia są bez zmian.

**Nowy plan, wymagający osobnej zgody:**

`data/raw/earnings-financial-activation-replan-2026-11-03/activation-plan.json`

**Pełny SHA-256 kanonicznego nowego planu:**

`2c88a90a609eee3a009669a72578cab5b4a21e2bfa03a7e9fa100be1e29db5c3`

Cel nadal **localhost:5432/macrolens**, rola **macrolens**, OID **16384**,
klaster **7682090371041935398**. Zakres DDL i importu jest identyczny:
dwie tabele finansowe z ochroną, cztery historyczne periods/events,
sześć dokumentów i 12 obserwacji. Zmieniła się zatwierdzana podstawa
danych i nowa kopia, dlatego obowiązuje inny hash.

### Wynik tego wykonania

**E2B nie zostało aktywowane w normalnej bazie.** Nadal: 3 firmy,
6 okresów, 6 wydarzeń, 5 dowodów dat i 12 potwierdzeń; brak obu tabel
finansowych. Nie wykonano apply ani idempotentnego powtórzenia na tym
celu. Nie restartowano backendu, nie wykonywano poaktywacyjnego Chrome
lub testu revenue/EPS w normalnym Calendar, ponieważ zależą od aktywacji.
Nie deklaruje się, że finansowe Actual już działają w codziennej aplikacji.
Nie wykonano rollbacku, SEC/IR HTTP, integracji konsensusu lub E2C.

Własne bazy restore i referencyjną usunięto. Po sprawdzeniu ID i etykiety
usunięto tylko własny kontener replan wraz z jego anonimowym wolumenem.
Normalna aplikacja i macrolens_postgres nie były zatrzymywane lub zmieniane.
Z 18 zastanych plików zmieniono wyłącznie ten raport wykonania; pozostałe
17 zachowano byte-identycznie, w tym wszystkie zamrożone artefakty planu.
Git nadal **9 modified / 9 untracked**, pusty indeks, HEAD/main bez zmian.
Bez stagingu, commita i pusha.

Ścisłe zabezpieczenie obejmuje także późniejsze zmiany stanu odświeżania
i source checks. Jeżeli wystąpią przed kolejnym apply, plan ponownie wymaga
przeglądu. Nie wyłączano R1–R3 i nie osłabiano porównania danych.

**Gotowe do zatwierdzenia nowego planu. Stara zgoda nie została wykonana.**

## 14. Ponowna zgoda na 2c88 i zatrzymanie przed zapisem

03.11.2026 użytkownik zatwierdził pełny hash
`2c88a90a609eee3a009669a72578cab5b4a21e2bfa03a7e9fa100be1e29db5c3`,
z obowiązkiem zatrzymania przy kolejnej zmianie danych. Ponowny preflight
read-only potwierdził dokładny target localhost:5432/macrolens, rolę
macrolens, OID 16384 i klaster 7682090371041935398. Potwierdzono pełny hash
planu, wszystkie zamrożone artefakty, kopię i dowód pełnego restore,
sygnatury schematów i brak tabel E2B. Sprawdzono też tożsamość rzeczywistego
backendu PID 16352, jego katalog i cztery niesekretne parametry bazy.

Pełne binary COPY hash/count wykazało kolejną zmianę względem tego planu:

| Tabela | Zatwierdzony stan | Obecny stan |
|---|---:|---:|
| overview_publications | 8 | 8, inny hash |
| overview_refresh_state | 1 | 1, inny hash |
| source_check_runs | 1720 | 1766, inny hash |

Pozostałe 16 tabel oraz pełna projekcja wszystkich pierwotnych rekordów
E2A są identyczne. Wynik zapisano w ignorowanym
`data/raw/earnings-financial-activation-replan-2026-11-03/second-approved-preflight.json`.
Zmiany są zgodne z możliwością zwykłej aktywności makro, lecz nie stanowią
wyjątku od obowiązku zgodności zatwierdzonego snapshotu.

**Zatrzymano aktywację przed apply, DDL i importem. E2B nadal nie działa
w normalnej bazie.** Nie zatrzymywano ani nie restartowano backendu:
zatrzymanie po wykryciu różnicy nie przywróciłoby zatwierdzonego stanu.
Nie tworzono blokad diagnostycznych. PostgreSQL i aplikacja pozostały
uruchomione; nie zmieniono R1–R3. Nie wykonano rollbacku, SEC/IR lub E2C.
Nie przeprowadzono zależnych od aktywacji testów UI i idempotencji.

Plan 2c88 nie jest już wykonalny na obecnym stanie. Kolejne przygotowanie
powinno objąć kontrolowane wstrzymanie backendu przed snapshotem i backupem,
a następnie nowy plan do osobnego zatwierdzenia. Nie wygenerowano ani nie
wykonano zastępczego planu w tej próbie. Zmieniono tylko ten raport;
Git: 9 modified / 9 untracked, indeks pusty, bez stagingu, commita i pusha.

## 15. Kontrolowane okno serwisowe i stabilny plan

03.11.2026, zgodnie z nowym zleceniem, zatrzymano procesy zapisujące przed
przygotowaniem kolejnego planu. Dawne plany ef4d i 2c88 pozostają
nieaktualne; żadnego nie użyto do apply.

### Źródło zapisów i kontrolowane zatrzymanie

Ponownie odczytano rzeczywiste procesy Windows. Jedyną parą procesów
Python aplikacji był launcher **10512** i worker **16352**, uruchomione
przez `.venv\Scripts\python.exe -m uvicorn app.api.main:app --host
127.0.0.1 --port 8000`, cwd `C:\Projects\macrolens`. Worker faktycznie
obsługiwał port 8000 i miał DB_HOST=localhost, DB_PORT=5432,
DB_NAME=macrolens, DB_USER=macrolens. Nie ujawniano haseł lub całego env.
Nie było procesu reload ani osobnego procesu Python schedulera/CLI.

Log `normal-api.log` zawiera POST `/api/v1/economy/us/brief/refresh`
oraz późniejsze odpytywanie statusu. Calendar używa
`useBackgroundRefresh` z `frontend/src/brief/useOverviewRefresh.ts`;
klient API wykonuje POST, gdy nadejdzie termin kontroli. Endpoint w
`app/api/main.py` wywołuje koordynator, a ten uruchamia wątek
`overview-refresh` w backendzie. Nie jest to osobny worker procesu.

SQL pokazał ostatnią sekwencję source checks **22:09:22–22:09:57 PL**
(BEA, serie FRED i calendar:periods), a publikację Overview i zakończenie
koordynatora **22:10:00 PL**. Przed zatrzymaniem status koordynatora był
`partial`, bez działającego zadania i bez aktywnej sesji backendu w SQL.
Ten mechanizm i zapisane przebiegi wyjaśniają zmiany trzech tabel; nie
były zapisami Earnings. Tabela historii nie zapisuje PID procesu, a log
access nie ma timestampów, więc nie przedstawia się tego jako osobnej
forensycznej identyfikacji każdego historycznego INSERT.

Zatrzymano tylko potwierdzone PID **10512 i 16352**, po zapisaniu ich
poleceń uruchomienia. Vite **18480** na localhost:5173 pozostał uruchomiony.
PostgreSQL `macrolens_postgres` nie był zatrzymywany. Powtórne sprawdzenie
nie wykazało procesu Python/Uvicorn ani listenera portu 8000. Nie zmieniono
kodu, konfiguracji, R1–R3, lease lub interwałów.

Nie znaleziono zadania Harmonogramu Windows wskazującego MacroLens.
Pierwszy odczyt Get-ScheduledTask zwrócił błąd XML systemowego zadania;
powtórny odczyt przez Schedule.Service COM zakończył się poprawnie i nie
znalazł pasujących zadań. Działające kontenery obejmowały normalny
PostgreSQL i wyłącznie własny serwis restore. W normalnym kontenerze
pozostał użytkowy `psql`, bezczynny (`idle`, xact_start=null); nie zamykano
go. Nie stwierdzono niezależnego aktywnego procesu zapisującego.

### Stabilność wszystkich danych

Dwa odczyty wykonano z niezależnych połączeń, w REPEATABLE READ READ ONLY,
z 30-sekundową przerwą po pierwszym pełnym odczycie. Zakończenia snapshotów:
**22:20:35 i 22:21:11 PL**. Wszystkie **19 tabel / 2 924 582 rekordy** mają
identyczne binary COPY SHA-256 i liczniki. Obejmuje to 13 tabel makro i
sześć E2A, nie tylko zmieniające się wcześniej trzy tabele.

`source_check_runs` ma **1813** rekordów, overview_publications **8**,
overview_refresh_state **1**. Nie porównywano ich do dawnej zgody jako
rzekomo zgodnych: nowy plan opisuje ten nowy, ustabilizowany stan.
E2A nadal ma 3 firmy, 3 aliasy, 6 okresów, 6 eventów, 5 dowodów i
12 potwierdzeń dat. Brak obu tabel finansowych. Nie wykonywano UPDATE,
DDL, importu ani inicjalizacji w normalnej bazie.

Pierwsza próba helpera stabilności umieściła inspect w już otwartej
transakcji; bramka poprawnie odmówiła. Poprawiono tylko ignorowany helper,
aby inspect używał świeżego połączenia. Dopiero dwa poprawne pełne odczyty
zaliczono jako stabilne. Produkcyjnego kodu nie zmieniono.

### Świeża kopia i rzeczywisty restore

Nowy ignorowany katalog: `data/raw/earnings-financial-maintenance-2026-11-03/`.

| Kontrola | Wynik |
|---|---|
| Cel | localhost:5432/macrolens, rola macrolens |
| OID / klaster | 16384 / 7682090371041935398 |
| Dump | macrolens-before-financials-2026-11-03.dump |
| Rozmiar | **30 834 892 B** |
| SHA-256 | `bf91860031fe15dce4b100bf27c89961b4a2b56e3841313954ddbd4c24d098a9` |
| pg_dump / TOC / pełny pg_restore | **0 / 0 / 0** |
| Odtworzone dane | **19 tabel / 2 924 582 rekordy**, wszystkie hash/count zgodne |
| Schemat / niezwalidowane constraints | Zgodny / **0** |

Kopię wykonano read-only ze wspólnego pg_export_snapshot dla dump i
pełnych hashy. Restore wykonano do własnej losowej bazy na osobnym
PostgreSQL 17, port loopback **55455**, z --exit-on-error,
--single-transaction, --no-owner i --no-acl. Nigdy do macrolens.
Własne bazy restore/referencyjną usunięto; wykonano też rzeczywisty
izolowany wzorzec E2A/E2B i kontrolę zatwierdzonego seeda.
Manifest, dowód restore, pełne snapshoty i logi pozostają lokalnie.

Przed cleanup potwierdzono pełny ID kontenera
`ea3b56c8c465d16b5120bf5281287026f74a1f09edaca3218746756b4c927f5f`,
etykietę financial-maintenance-2026-11-03 i wyłącznie domyślne bazy
macrolens/postgres/template0/template1. Usunięto tylko własny
`macrolens_financial_maintenance_20261103` i jego anonimowy wolumen.
Normalny macrolens_postgres pozostał uruchomiony.

### Nowy plan do zatwierdzenia

Plik: `data/raw/earnings-financial-maintenance-2026-11-03/activation-plan.json`.

**Pełny SHA-256 kanonicznego planu:**

`d39f1c331ed3582b4e3dde633702227bc37b2a2470961631d2fb6c5c2402ac65`

Cel: **localhost:5432/macrolens**, rola **macrolens**, OID **16384**,
klaster **7682090371041935398**. Zakres nie rozszerza poprzedniego:
dwie nowe tabele finansowe z ochroną, cztery historyczne periods/events,
sześć dokumentów, 12 obserwacji Revenue Actual / GAAP diluted EPS.
Oczekiwane po osobno zatwierdzonym apply: **3 firmy / 10 okresów /
10 eventów / 12 istniejących confirmations / 6 dokumentów / 12 obserwacji**.
Wszystkie zastane wiersze E2A i makro mają pozostać identyczne.

Zamrożone artefakty z sekcji 7 są bez zmian. Zachowano wszystkie bramki:
pełny target/hash, backup i dowód restore, porównania danych/schematów,
jedną transakcję SERIALIZABLE, istniejące locki, timeouty, idempotencję,
rollback błędu całej transakcji i odmowę przy partial/obcym schemacie.
Nie uruchomiono apply. Stare zgody nie uprawniają do tego nowego planu.

Końcowy trzeci pełny odczyt potwierdził zgodność z oboma stabilnymi
snapshotami, backupem i planem; pierwotne E2A identyczne. Sprawdzono
ponownie hash planu, artefakty, dowód restore i zero diagnostycznych
advisory locks 726530019/726530020. Wszystkie własne połączenia zamknięto.
Nie pozostawiono transakcji ani lease.

### Pozostawiony stan i wznowienie w razie odłożenia aktywacji

**Backend pozostaje zatrzymany do następnej decyzji użytkownika.**
Vite działa, ale bez API normalny Calendar nie będzie teraz wczytywał
danych. To oczekiwany stan okna serwisowego, nie błąd migracji.
**E2B nadal nie jest aktywne w normalnej bazie.** Nie wykonywano testów
poaktywacyjnych UI, nowych testów frontend/backend lub CI; kod jest bez
zmian. Nowe wyniki to diagnostyka, stabilne pełne snapshoty, backup,
pełny restore i odczytowe prepare. Nie uruchamiano SEC/IR lub E2C.

Jeżeli użytkownik odłoży aktywację i chce przywrócić aplikację, najpierw
sprawdzić, że port 8000 jest wolny, następnie uruchomić w PowerShell:

```powershell
Start-Process -FilePath 'C:\Projects\macrolens\.venv\Scripts\python.exe' `
  -ArgumentList '-m','uvicorn','app.api.main:app','--host','127.0.0.1','--port','8000' `
  -WorkingDirectory 'C:\Projects\macrolens' -WindowStyle Hidden
```

To instrukcja, **nie wykonano jej**. Używa zachowanej konfiguracji projektu,
bez nadpisania .env. Po uruchomieniu sprawdzić /health i Calendar.
Wznowione zwykłe kontrole makro mogą unieważnić nowy plan; wtedy wymagane
są nowy snapshot, backup/restore, plan i osobna zgoda. Również ręczny zapis
przez pozostawiony psql lub inne źródło przed apply wymaga odmowy aktywacji.

Zmieniono wyłącznie ten raport spośród 18 zastanych plików; pozostałe
17, w tym wszystkie zamrożone artefakty i prace użytkownika, pozostają
byte-identyczne. Git: **9 modified / 9 untracked**, indeks pusty,
HEAD/main **4f4e12ce138be210bedbb13924cf0c4e52d65411** bez zmian.
Bez stagingu, commita, pusha lub zmian historii.

## 16. Zatwierdzone wykonanie i normalna aplikacja — 03.11.2026

### Ostateczna zgoda, preflight i COMMIT

Użytkownik wyraźnie zatwierdził wyłącznie pełny hash
`d39f1c331ed3582b4e3dde633702227bc37b2a2470961631d2fb6c5c2402ac65`
oraz localhost:5432/macrolens, rolę macrolens, OID **16384**, klaster
**7682090371041935398**. Nie użyto poprzednich unieważnionych planów.

Przed wykonaniem ponownie potwierdzono brak backendu i listenera 8000,
pełny kanoniczny hash planu, wszystkie siedem zamrożonych artefaktów,
tożsamość celu i podpisy schematów. Zweryfikowano nagłówek, rozmiar i SHA
świeżej kopii z sekcji 15, jej manifest i hash dowodu pełnego restore.
Nie wykonywano ponownie restore ani nie przedstawia się wcześniejszego
restore jako nowej próby; potwierdzono niezmienność jego dowodu i kopii.

Bezpośredni odczyt REPEATABLE READ READ ONLY dał pełną zgodność binary COPY
hash/count wszystkich **19 tabel** z zatwierdzonym snapshotem. Pełne
pierwotne wiersze E2A były identyczne. Brak blokad 726530019/726530020.
Nie zmieniono planu, kodu procedury, schematu SQL ani seeda.

Wykonano osobną ścieżkę apply. Wynik **created**, poprawny COMMIT.
Jedna transakcja SERIALIZABLE obejmowała dwa nowe obiekty tabelaryczne,
ich zabezpieczenia, cztery historyczne okresy/eventy, sześć dokumentów
i 12 obserwacji. Backend przez cały zapis i kontrolę integralności był
zatrzymany. Nie wykonano automatycznego rollbacku po COMMIT.

| Tabela | Po aktywacji |
|---|---:|
| earnings_companies | **3** |
| earnings_company_aliases | **3** |
| earnings_periods | **10** |
| earnings_events | **10** |
| earnings_source_evidence | **5** |
| earnings_date_confirmations | **12** |
| earnings_financial_documents | **6** |
| earnings_financial_observations | **12** |

Powtórzenie dokładnie tego samego planu zwróciło **already_initialized**,
bez DDL, nowych wersji, duplikatów lub zmian timestampów. Pełne snapshoty
wszystkich **21 tabel** po obu wywołaniach są identyczne.

### Integralność przed wznowieniem backendu

Wszystkie **13 pierwotnych tabel makro** porównano z pełnym snapshotem
bezpośrednio sprzed apply: liczniki i SHA-256 uporządkowanego binary COPY
są identyczne. Dotyczy to także source_check_runs **1813**,
overview_publications **8** i overview_refresh_state **1**.

Pełna projekcja wszystkich pierwotnych wierszy sześciu tabel E2A jest
identyczna. Dla rozszerzonych periods/events porównanie wyklucza dokładnie
cztery nowe deterministyczne ID z zatwierdzonego manifestu; nie pomija
innych zastanych danych. Date confirmations i evidence pozostały bez zmian.
Wynik kontroli integralności i idempotencji uzyskano **przed restartem**,
więc późniejsze zwykłe zapisy makro nie są traktowane jako zmiana migracji.

Receipt, receipt idempotencji i bezpośredni snapshot sprzed aktywacji są
w ignorowanym katalogu z sekcji 15 jako `apply-receipt.json`,
`idempotency-receipt.json` i `immediate-before-apply.json`.

### Normalny backend i rzeczywiste API

Uruchomiono normalny backend z `.venv\Scripts\python.exe -m uvicorn
app.api.main:app --host 127.0.0.1 --port 8000`, cwd
`C:\Projects\macrolens`. Launcher **19376**, rzeczywisty worker **15516**;
Vite nadal **18480**, localhost:5173. Nie zastępowano API izolowanym
serwisem ani fixture odpowiedzi. Nie zmieniano konfiguracji projektu,
.env, R1–R3, kodu odświeżania lub parametrów źródeł.

Odczyt startowego bloku środowiska nowego procesu nie miał jawnie
ustawionych czterech DB_* (aplikacja ładuje konfigurację projektu przez
dotenv); nie przedstawia się pustych wartości jako odczytu celu SQL
z pamięci. Cwd/polecenie procesu potwierdzono, a niezależne SQL potwierdziło
zatwierdzony target. **Wszystkie 12 observation_id, wartości, wersje i
captured_at zwracane przez HTTP porównano z zapisanymi rekordami normalnej
bazy** — zgodność obejmuje czas rzeczywistej aktywacji, nie tylko liczby
z tego samego seeda. Nowy worker zwraca pola E2B i financial_store_status
available, w przeciwieństwie do starego procesu sprzed okna serwisowego.

Rzeczywiste GET health, companies, lista Earnings i szczegóły wszystkich
siedmiu datowanych wydarzeń przeszły HTTP 200. Lista za 01.05–30.11 ma
**7 datowanych + 3 unknown**. Stare API makro za 02–08.11 zwróciło
**HTTP 200 / 16 wydarzeń**.

| Raport | Revenue, mln USD | GAAP diluted EPS, USD |
|---|---:|---:|
| NVDA Q1 FY2027 | 81 615 | 2,39 |
| NVDA Q2 FY2027 | 96 221 | 2,46 |
| AMZN Q2 2026 | 200 606 | 5,75 |
| AMZN Q3 2026 | 201 944 | 1,89 |
| INTC Q2 2026 | 16 128 | −2,16 |
| INTC Q3 2026 | 16 513 | 0,60 |

Sprawdzono wszystkie sześć raportów jako Decimal, kanoniczny revenue USD
i source_value w mln USD. Forecast pozostaje null. NVDA Q3 FY2027
17.11 nadal ma null obu Actual, approximate release 22:20 PL, call 23:00;
trzy przyszłe Q4 pozostają unknown bez dat. Nie dodano faktów spoza seeda,
konsensusu, surprise lub statusu published dla przyszłej NVIDIA.

### Chrome na localhost:5173

**121 kontroli**, EN/PL, desktop **1366 px**, mobile **390 px**,
**21 zakończonych odpowiedzi API HTTP 200**, **zero wyjątków JS,
console.error i HTTP 503**. Test używał zwykłego Vite i API 8000,
rzeczywistych odpowiedzi i normalnej bazy. Potwierdzono:

- Wszystkie spółki domyślnie, bez checkboxów tickerów, jeden nagłówek tabeli.
- Historyczne Actual, ujemny EPS, null Forecast jako `—`, brak beat/miss.
- NVDA około 22:20 / call 23:00, Intel AMC 21:00+ / call 22:00,
  Amazon call 22:00 bez fikcyjnej godziny release.
- Sześć historycznych raportów, przyszła NVDA bez Actual i trzy unknown.
- Makro / Earnings / Wszystkie, historyczne i przyszłe zakresy,
  brak zbędnego GET Earnings przy przejściu do Wszystkie.
- Źródła HTTPS, szczegóły, Escape/focus, EN/PL, scroll wewnątrz tabeli
  na telefonie bez overflow całej strony. Obejrzano desktop EN i mobile PL.
- Kontrolowany błąd transportu wyłącznie endpointu Earnings i odzyskanie
  przez prawdziwy Retry po odblokowaniu. Nie podstawiano JSON.

Pierwsze próby dodatkowego helpera API porównywały różne tekstowe formaty
tej samej chwili UTC; następnie Python 3.9 nie przyjął krótkiego `+00`.
Poprawiono wyłącznie ignorowany helper na natywny datetime PostgreSQL.
Końcowe porównanie wszystkich 12 timestampów i wartości przeszło.
Nie zmieniano produkcyjnego kodu ani nie zaliczano błędnych prób.

Test odbywał się pod tymczasowym session lease 726530019, na połączeniu
read-only, **dopiero po zakończeniu apply i kontroli idempotencji**.
Nie kolidował z lockami aktywatora. Chronił smoke przed uruchomieniem
importerów przez zwykły hook; nie zmieniał R1–R3. Po API/Chrome wykonano
pełne porównanie wszystkich 21 tabel ze stanem po COMMIT: identyczne.
Nie uruchomiono SEC/IR, E2C ani scraperów. Nie powtarzano pełnych suite
backend/frontend lub CI, bo kod i artefakty pozostały bez zmian.

### Końcowy stan

Zamknięto tylko własny diagnostyczny Chrome i zwolniono session lease.
Potwierdzono **zero** pozostawionych advisory locks 726530019/726530020.
Własne połączenia zamknięte, bez diagnostycznych transakcji. Nie wykonywano
rollbacku ani nie usuwano danych. Zwykłe odświeżanie może działać dalej
według istniejącego kodu i ustawień po kolejnym należnym żądaniu.

**Normalne API i Vite pozostawiono uruchomione. E2B działa w codziennej
aplikacji: http://localhost:5173/#/calendar.** Aby zobaczyć AMZN/INTC Q3,
wybrać Wyniki spółek i zakres obejmujący **29.10.2026**; dla NVDA Q3 —
**17.11.2026**, a dla wszystkich sześciu raportów — **01.05–30.11.2026**.
Bieżący tydzień nie musi zawierać historycznych raportów.

Aktualizowano tylko ten raport spośród 18 zastanych modified/untracked
plików. Pozostałe 17 zachowano byte-identycznie, w tym wszystkie siedem
zamrożonych artefaktów. Snapshoty, logi, zrzuty, helpery i receipts pozostają
ignorowane w data/raw. Git: **9 modified / 9 untracked**, indeks pusty,
HEAD/main **4f4e12ce138be210bedbb13924cf0c4e52d65411** bez zmian.
Bez stagingu, commita, pusha, resetu, clean lub zmiany historii.

## 17. Osobne zamknięcie Git E2B Activation

Na późniejsze wyraźne zlecenie użytkownika przygotowano commit
**Add safe earnings financial activation**, bez ponownego apply, importu,
DDL lub rollbacku w normalnej bazie. Stan wejściowy zamknięcia:
HEAD 4f4e12ce138be210bedbb13924cf0c4e52d65411, 14 modified / 17 untracked,
pusty indeks. Zapisano manifest 31 zastanych plików i cały diff.

Pierwszy zakres ma dokładnie **6 plików**: pięć plików procedury/testów/
raportów Activation oraz .github/workflows/ci.yml. E2C pozostaje poza
tym commitem. Workflow dodaje ósmy nazwany krok PostgreSQL financial
activation and recovery. Skrypt testowy dopuszcza kontrolną bazę CI;
identyfikator kontenera usługi jest przyjmowany wyłącznie w GitHub Actions,
dla jawnej roli macrolens_ci, hosta loopback i pełnego ID kontenera.
Lokalna bramka prefiksu własnego serwisu i zakaz normalnej macrolens
pozostają. Dane testów są syntetyczne; pg_dump/restore są rzeczywiste.

Dokładny indeks wyeksportowano do osobnej kopii, sprawdzono wszystkie
**327 blob IDs**, pełny staged diff i whitespace. Kopia używa wersji
chronionych plików z HEAD, bez zmian użytkownika i bez plików E2C.
Walidacja indeksu: **1251 backend passed**, **658 frontend passed**,
Node 22.23.4 typecheck/build passed, największy chunk 407,04 kB,
PostgreSQL **8/8 passed**, actionlint passed. Nie zmieniano timeoutów,
guardów, zależności lub testów użytkownika. Kod procedury jest identyczny
z wcześniej wykonaną aktywacją; zmiana zamknięcia dotyczy CI/testowej bramki.

Nowy working tree całego zakresu także przeszedł **1294 backend / 664
frontend**, typecheck/build i **9/9 PostgreSQL**. To wyniki nowego
zamknięcia, nie przepisane liczby implementacji. E2C zostanie zatwierdzone
oddzielnie po własnej walidacji dokładnego indeksu.

Po walidacji edytowano tylko ten raport i jego staging. Pełne SHA obu
commitów, zwykły push i rzeczywiście zakończone wyniki trzech jobów Actions
będą w końcowej odpowiedzi po ich uzyskaniu. Nie tworzy się dodatkowego
commita wyłącznie dla metadanych po pushu. Nie przypisuje się przyszłemu
CI wyników lokalnych. Historyczne „bez commita” opisuje wcześniejsze etapy.

## 18. Wynik GitHub Actions i przygotowana poprawka CI

Oba commity wypchnięto zwykłym pushem: Activation
`565a0fa126a0e2a09f5b858ed61074feebe9dc96` oraz E2C
`a3627bdddbf88eb179771a48d7dce3d523e9048e`.
[Uruchomienie Actions](https://github.com/pecakxkamil/macrolens/actions/runs/41733244851)
zakończyło backend i frontend sukcesem: **1294 / 662 passed**.
PostgreSQL przeszedł kroki 1–7, lecz krok 8 Activation zakończył się
`KeyError: 'port'`; krok 9 E2C został pominięty. Nie deklaruje się zielonego CI.

Przyczyna jest w skrypcie walidacyjnym: na runnerze Linux
`ConnectionInfo.get_parameters()` pomija domyślny port 5432.
Przygotowana lokalna poprawka w dwóch miejscach pobiera host, port i rolę
z jawnych właściwości `ConnectionInfo`. Nie zmienia aktywatora, danych,
workflow lub zabezpieczeń. Po poprawce na osobnym PostgreSQL 17 przeszły
Activation fresh/upgrade z prawdziwym backup/restore oraz walidacja E2C.
Użyto pełnego ID kontenera i bramki GITHUB_ACTIONS; testowy kontener
i jego wolumen usunięto po sprawdzeniu tożsamości oraz cleanup baz.
Normalnej bazy i aplikacji nie zmieniano.

Użytkownik następnie wyraźnie zatwierdził osobny trzeci commit naprawczy
`Fix earnings financial activation CI validation` i zwykły push, bez amend
i force push. Zakres obejmuje tylko dwie linie skryptu oraz ten raport;
workflow nie wymaga zmiany. Potwierdzono w kodzie zainstalowanego psycopg,
że `get_parameters()` celowo zwraca wyłącznie parametry różne od wartości
domyślnych; właściwość `info.port` zachowuje rzeczywisty port połączenia.
Nie dodano zastępczej wartości portu i nie pominięto kontroli restore.

Końcowa walidacja dokładnego indeksu naprawy: **335 blob IDs zgodnych**,
Activation fresh/upgrade i rzeczywisty backup/restore **passed, 6,42 s**,
E2C **passed, 4,16 s**. Actionlint oraz oba `git diff --check` przeszły.
Staging zawiera dokładnie dwa zatwierdzone pliki; żaden z 13 chronionych
plików ani data/raw nie wchodzi do commita. Chronione bajty są identyczne.
Własny PostgreSQL 17 na 55463 usunięto po sprawdzeniu pełnego ID, etykiety
i braku pozostawionych baz prób. Nie użyto normalnej bazy do zapisów.
Po tych kontrolach zmieniono wyłącznie ten dopisek dokumentacji.
Wynik nowego uruchomienia Actions i pełny SHA trzeciego commita zostaną
podane w odpowiedzi końcowej po pushu; nie zakłada się sukcesu CI.
