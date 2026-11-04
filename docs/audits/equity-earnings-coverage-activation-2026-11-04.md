# MacroLens — E2C Activation: plan do osobnego zatwierdzenia

Przygotowano **04.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`,
`main`, HEAD **3537b829a6eb84900f9db8e8218d72d9535c8f52**.

**Aktywowano E2C 04.11.2026 w normalnej bazie localhost:5432/macrolens:
apply=created, ponowienie=already_initialized.** Sekcje 1–10 opisują
przygotowanie i stan przed zgodą; wykonanie po wyraźnym zatwierdzeniu
tego samego pełnego hasha opisuje sekcja 11. Backend i Vite wznowiono.
Bez stagingu, commita i pusha. Nie rozpoczęto E2D.

## 1. Cel i kontrolowane okno serwisowe

| Pole | Zweryfikowana wartość |
|---|---|
| Host / port | localhost / 5432 |
| Baza / rola | macrolens / macrolens |
| OID | 16384 |
| Identyfikator klastra | 7682090371041935398 |
| Kontener normalnej bazy | macrolens_postgres |
| PostgreSQL | 17 |
| Read-only diagnostyki | on |

Backend i Vite były już wyłączone na wejściu. **Nie było PID-ów do
zatrzymania**; nie przypisuje się sobie zatrzymania dawnego procesu.
Sprawdzono aktualne procesy Python/Node i klientów pg_stat_activity.
Nie wykryto zapisujących procesów MacroLens ani innych klientów normalnej
bazy. Docker Desktop był wyłączony; uruchomiono istniejącą usługę PostgreSQL,
bez uruchamiania backendu. Nie zmieniano konfiguracji R1–R3, źródeł lub lease.
Stan i brak zatrzymanych PID zapisuje lokalny `maintenance.json`.

Backend pozostaje wyłączony do decyzji użytkownika i późniejszej kontroli
integralności. PostgreSQL działa. Nie pozostawiono diagnostycznych blokad,
sesji lub transakcji. Końcowo: zero innych klientów i zero advisory locks.

## 2. Stabilność i pełny manifest istniejących danych

Dwa niezależne połączenia REPEATABLE READ READ ONLY dały identyczne
liczniki i SHA-256 wszystkich **21 tabel / 2,924,851 rekordów**.
Ponowny snapshot przy pg_dump oraz końcowy odczyt po testach również są
identyczne. Hash liczony z pełnego binary COPY, z kolejnością po PK,
obejmuje wartości i timestampy. To nie statystyki przybliżone.

| Tabela | Rekordy przed = po | SHA-256 przed = po |
|---|---:|---|
| alfred_backfills | 15 | `e3b943e5151b7ddda3a7e2a7fe355528bb266f3630344728f9429ce59497b65e` |
| computed_features | 1048238 | `5640ff0f6589eeb0e3169274556535d437579de7afb70dd6419d9fed9e4f77df` |
| earnings_companies | 3 | `674c5e2ed93a346ca4804cd79dcdc6e3038c2f0c7db6c10260f79ef416b9d853` |
| earnings_company_aliases | 3 | `ad54505df5ff5a50fafb9214c73f61646b4c2efb34f59bc23d386b90ed3f5eac` |
| earnings_date_confirmations | 12 | `9ac2ca6ea377eb91325c52ba2bec1f9990f762919c122b2de51f22555c2df5c2` |
| earnings_events | 10 | `5542c9ce8b3c8dd8508d2a1d0972aa4dcca83233deffc1c0e00106c57de7307d` |
| earnings_financial_documents | 6 | `306598e20cedde0ddc8b0e5d74d8e55c34ed096c079f6eb6b3c9203553d839e5` |
| earnings_financial_observations | 12 | `c7b17b5730bbb87cbc98185d7910bce6b63c92ca51624d0cfd757b76f0197308` |
| earnings_periods | 10 | `30b8df0cd86112ac3319f17b0392a116b6dd674e504f8e6a39bed768ded89c97` |
| earnings_source_evidence | 5 | `b06315419b8203a7ca6a3f985bb74557fb25cf161853c080a1d86278cc892832` |
| economic_releases | 18 | `9fad16df8f5a9011ff2a46915e956e7c964e57a4b9ce9e7e3f190d3b38c14cc9` |
| ism_documents | 22 | `70de199f658a1528704162235a2d365e92fbc7e84aa5116d998f386e4fa70efd` |
| ism_observations | 264 | `a76ed493a80e36cca32c566636565544e180f3a4a590d411ed21f44734892ab3` |
| observation_vintages | 1873249 | `784778cb76ce1ab8bec7a89da26164c405efda1be973b4ee47c61f5b4eee7e6f` |
| overview_publications | 8 | `082d8bcdaf6c274f2e49556055c702d5c3f234e7d0e310ac43f4a10f20467b9b` |
| overview_refresh_state | 1 | `23509a53a5d2097b37ca95c90de830e2f2f6228ea6b1f4e2435735df2560985e` |
| publisher_documents | 24 | `547ee8108ef7a6cad05a5d9793cfb9fbcb422a5c73f4af963201dbf08b0aff5a` |
| release_dates | 804 | `3385a38806129a73cf1fbac215e38c5fb3242f8d672e8eb039b1329adcd43746` |
| series | 58 | `f4cd1add01658ea0d16892004ddf7ef7cce89103de274142672a58f38c1b9ac0` |
| series_release_map | 45 | `e5eb3c6545828d89d6165b879d43305da0588c01ded45618a3731a05235ece84` |
| source_check_runs | 2044 | `df1a9ccf10e1b1d99d2f8186a0bf81ffa3a688284c636c6b39561f16ee6108f7` |

Pełny manifest wszystkich pierwotnych wierszy ośmiu tabel Earnings,
z wszystkimi ID, wartościami, dowodami i historią, jest w ignorowanym
`data/raw/earnings-coverage-activation-2026-11-04/existing-data-manifest.json`.
SHA-256 pliku: **921d431ad1a563e2bc2dc930b5e0c33597b27707c83c93bd986aa3d2f516cce9**.
Te same kompletne wiersze są osadzone w planie jako `original_rows`.
Plan nie opiera zachowania pierwotnych danych wyłącznie na count.

## 3. Świeży backup i rzeczywisty pełny restore

Lokalna kopia (ignorowana przez Git):
`data/raw/earnings-coverage-activation-2026-11-04/macrolens-before-coverage-2026-11-04.dump`.

| Kontrola | Wynik |
|---|---|
| pg_dump custom / PGDMP | kod 0, cała baza, --no-owner --no-acl |
| Rozmiar | **30869940 B** |
| SHA-256 | **d9ec86daa7e9925e35dd6137a470a5101e8ff1afbdfe2b40ffadbc825fd7f642** |
| TOC pg_restore --list | kod 0 |
| Pełny restore | kod 0, --exit-on-error --single-transaction --no-owner --no-acl |
| Odtworzone tabele / wiersze | 21 / 2924851 |
| Wszystkie hash/count i schematy | identyczne ze źródłem |
| Niezwalidowane constraints | 0 |

pg_dump używał tego samego eksportowanego snapshotu co porównanie źródła,
z PGOPTIONS wymuszającym read-only. Nie zakładano blokady diagnostycznej.
Restore wykonano wyłącznie w losowej bazie na osobnym PostgreSQL 17,
kontenerze `macrolens_coverage_activation_20261104`, loopback **55465**.
Nie odtwarzano niczego do macrolens. Pełny ID własnego kontenera:
`cd6810be6dd8e955e8d933fe7239912d2932c4ee2b2089b5c09d11ce1fd71646`.

`backup-manifest.json` wiąże kopię z celem, klastrem/OID/rolą i snapshotem.
Dowód pełnego restore: `restore-validation.json`, SHA-256
**d150575614f93ad002ee375930ab5479ccbe41cf20fe694c41349fa42a8f0c14**. Baza restore została usunięta
po kontroli oraz testach; kopia i dowód pozostają lokalne i ignorowane.

## 4. Dokładny zakres i kontrole danych E2C

| Tabela | Teraz | Dodane po zgodzie | Oczekiwane po apply |
|---|---:|---:|---:|
| earnings_companies | 3 | 50 | 53 |
| earnings_company_aliases | 3 | 52 | 55 |
| earnings_periods | 10 | 27 | 37 |
| earnings_events | 10 | 27 | 37 |
| earnings_source_evidence | 5 | 35 | 40 |
| earnings_date_confirmations | 12 | 54 | 66 |
| earnings_financial_documents | 6 | 0 | 6 |
| earnings_financial_observations | 12 | 0 | 12 |

Zatwierdzony lokalny rejestr ma 53 unikalnych emitentów i 55 aliasów.
GOOG/GOOGL i BRK.B/BRK-B to po jednym emitencie. Sprawdzono kolizje CIK,
UUID i aliasów. Rejestr nie generuje eventów. Import obejmuje dokładnie
27 datowanych okresów dla 27 nowych firm, bez unknown placeholderów.
Brak dodatkowych firm, nowych Actual, Forecast, surprise lub beat/miss.

Walidacja istniejącego importera obejmuje ręczny ledger FY/kwartału,
period_end, oficjalne hosty i dowód, source timezone, DST oraz osobne
release/call. Date-only nie dostaje timestampu ani fikcyjnej północy.
Sześć dokumentów i 12 miar E2B pozostaje identycznych. NVDA Q3 FY2027
nie dostaje Actual. Nie wykonano nowych odczytów SEC/IR; użyto wyłącznie
wcześniej przejrzanych lokalnych metadanych. Ten etap nie jest nowym
potwierdzeniem aktualności wszystkich zapowiedzi w internecie.

## 5. Jedyna zmiana DDL

Tabela `earnings_date_confirmations`, constraint
`earnings_date_confirmations_source_timezone_check`.
Pełna stara definicja:

```sql
CHECK ((source_timezone = ANY (ARRAY['America/New_York'::text, 'America/Los_Angeles'::text])))
```

Pełna nowa definicja:

```sql
CHECK ((source_timezone = ANY (ARRAY['America/New_York'::text, 'America/Los_Angeles'::text, 'America/Chicago'::text, 'America/Denver'::text, 'America/Toronto'::text, 'Europe/Amsterdam'::text, 'Europe/London'::text, 'Asia/Taipei'::text, 'Etc/UTC'::text])))
```

Brak nowych tabel, funkcji lub triggerów. Brak ALTER innych constraints,
DDL makro, UPDATE/DELETE pierwotnych rekordów lub CASCADE.
Oba katalogi PostgreSQL porównano: jedyna różnica to powyższy CHECK.
Schemat i wszystkie dodane wiersze odpowiadają także niezależnemu
czystemu wykonaniu SQL E2A/E2B/E2C na syntetycznej bazie.

Sygnatura Earnings przed: `8e392331cf452f5dd837a541d53aadcdbc33152af5403abb7d5ce30f270712bd`.
Sygnatura Earnings po: `89b0c564a720d96fe6ff679f4d17ac7601b45a20091c04aa73f410fd0fb0f6ab`.
Sygnatura makro: `ba1b47aaf7d21b170b579369ca5c20b2e6fee871ee382e15fe519a43d37a2cf5`.

## 6. Osobny runner i bramki

`app/database/activate_earnings_coverage.py` ma odczytowe prepare i osobne
apply wymagające pełnego zatwierdzonego hasha oraz dokładnego target.
Nie jest importowany przez API/startup/scheduler. Dotychczasowy CLI E2C
i inicjalizatory zachowują swoje ograniczenia do izolowanych nazw baz.
Nie zmieniono nazw normalnej bazy ani nie obchodzono guardów.

Apply porównuje host/port/bazę/rolę/OID/klaster, kompletne katalogi, wszystkie
oryginalne wiersze oraz snapshoty 13 tabel makro. Wymaga niezmienionych
artefaktów, backupu i dowodu pełnego restore. Częściowy/obcy schemat,
kolizje aliasów, inny CIK i zmienione dane zatrzymują operację.

Jedna SERIALIZABLE READ WRITE transaction, search_path public,pg_catalog,
lock_timeout=5s, statement_timeout=120s, istniejące locki 726530019/726530020
obejmuje zmianę CHECK i cały seed. Błąd wycofuje wszystko. Ponowienie
dopuszcza tylko kompletny zgodny stan oraz dokładne oczekiwane wiersze;
nie zmienia wersji, historii ani timestampów. Brak automatycznego rollbacku
po udanym COMMIT. Osobny plan cofnięcia jest w dokumencie
[rollback](equity-earnings-coverage-activation-rollback-2026-11-04.md), niewykonany.

## 7. Nowe testy tego etapu

| Kontrola | Rzeczywisty wynik |
|---|---|
| Pełny backend offline | **1300 passed, 58,48 s** |
| Nowe jednostkowe bramki E2C Activation | **6 passed**, wliczone powyżej |
| Nowy PostgreSQL — syntetyczna baza E2A/E2B | passed, rzeczywisty backup/restore |
| Rzeczywisty drift schematu i danych w syntetycznej bazie | poprawna odmowa, stan testowy odtworzony |
| Pełny restore danych użytkownika | passed, wszystkie 21 tabel identyczne |
| Activation na odtworzonej pełnej kopii | passed, oczekiwane liczniki |
| Kontrolowany błąd SQL po DDL i imporcie | pełny rollback CHECK i całego seeda |
| Powtórzenie po COMMIT w kopii | already_initialized, identyczne pełne snapshoty |
| Ochrona E2A/E2B i 13 tabel makro w kopii | wszystkie pierwotne wartości i timestampy identyczne |
| Końcowy normalny snapshot | identyczny z pierwszym i backupem |
| Chronione 13 SHA i whitespace | passed |

Walidacje objęły błędny target/token/artefakt/backup, zmienione dane i schemat,
zgodne ID i aliasy, seed, izolowane DDL+import, odmowę oraz idempotencję.
Guard HTTP blokował transporty wydawców. Pełne dane użytkownika były
kopiowane wyłącznie do własnego lokalnego serwisu PostgreSQL na czas
testu restore, bez publikacji lub dodania do repozytorium.
Nie uruchamiano nowego frontendu, Chrome ani Actions: UI/API i workflow
nie zmieniono. Dawne 9/9 CI i Chrome nie są nowymi wynikami tego etapu.

## 8. Zamrożone artefakty

| Artefakt | SHA-256 bajtów |
|---|---|
| app/database/activate_earnings_coverage.py | `0f1510699e4d3ed3318459339c3e7a32315b4f9cb11c5be7affac10a2817ffc0` |
| app/database/activate_earnings.py | `183f77edef67b40640f8773868e5a661014e1427f44923bd9448321d0d4f79f0` |
| app/database/activate_earnings_financials.py | `213b0af4a3293d53cbf300302286b4bfce5357ea7590cac2fc7e17c546435904` |
| app/database/earnings_schema.sql | `7ddad92de5d2dca8f761e6449021a8a2ee46bab031a17c133e2480859e26fd48` |
| app/database/earnings_financial_schema.sql | `9fbbb8bbbabf76ab23546e2e0fd24a0e1727b69812eb4892b3a83a4fef55e7e1` |
| app/database/earnings_coverage_schema.sql | `36d55498a9a465465d102365e056e04e7fabb1ff9b561d2b0fe81f2157ab30eb` |
| app/earnings_coverage.py | `7d8f71da0a71e1f14939f4ac2a4f493b44eb35a40ad1eed2a3ab4cefb96afb02` |
| app/earnings.py | `50aed91204cc5dca6d7f6299c3c5ba43b9a4836fb24220a996402eea6db30a95` |
| app/earnings_financials.py | `5f0f3bcc123118f05b2bc6139b9748b04ff7ee22f10a5543d10b9ba145b5fe90` |
| config/earnings_manual.json | `c1a0f8117df471cfdf7cb1a2be7daa1d6a4a2581c5c703d4a7d28636e6680ba4` |
| config/earnings_financial_manual.json | `7feb36d2a226e29bada634386c41729dcb8aa92792807ee5c7e21f837c5bb7ad` |
| config/earnings_companies_reviewed.json | `cbe2aaf4faaf00da05273755a234e8a884f2be5c5d2975026cb1f941055309ea` |
| config/earnings_dates_reviewed.json | `95d3eaf20e881c857df6491e12a65f37a9cc25232e51353842227787f42a673e` |
| docs/audits/equity-earnings-coverage-activation-rollback-2026-11-04.md | `10fdd162d420159bb3351529ced352165487714bb1816731aa01054344608092` |

Zmiana dowolnego artefaktu, bazy, schematu lub danych po tym planie
unieważnia zgodę na ten hash. Nie aktualizować automatycznie planu podczas
apply. Dawny hash propozycji 89eae4e3… nie jest używany.

## 9. Prace użytkownika, pliki i sprzątanie

Zachowano byte-identycznie wszystkie 13 zastanych plików. CalendarPage,
Previous week, testy, README, globalny CSS i poprzednie audyty bez edycji.

| Chroniony plik | SHA-256 przed = po |
|---|---|
| docs/audits/calendar-event-impact-audit-2026-10-30.md | `35e876926cea3c82e3b2df837876d6fb3cabd82ba55db67a4de7ad06159f6f1d` |
| docs/audits/calendar-next-releases-priority-2026-10-29.md | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` |
| docs/audits/calendar-release-day-latency-2026-10-29.md | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` |
| docs/audits/equity-earnings-calendar-source-audit-2026-11-02.md | `a6db1f1a877aacb9bc1980608d20a1d1f1609023d64e1a11ef8699ec659b1434` |
| README.md | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` |
| frontend/src/brief/EconomyBrief.test.tsx | `bb5c2f6adac6d3c182e893e0d58fa32ff711aee9d7722feaad0d67ad7c598ed5` |
| frontend/src/brief/EconomyBrief.tsx | `017f87c9f580a10c7125e14cb0415f1556c2fcaa2724295f943eef26b82dfcc1` |
| frontend/src/brief/SourceCheckStatus.test.tsx | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` |
| frontend/src/brief/SourceCheckStatus.tsx | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` |
| frontend/src/calendar/CalendarPage.test.tsx | `4e62ca7c6345190a79048dfaa09dd6178e76e141f3e6695607c4eba5edf637d9` |
| frontend/src/calendar/CalendarPage.tsx | `27b776030fb6b63ff915f7e52f3502e5d8defcaa8f5c577e5be7043f16418b91` |
| frontend/src/calendar/calendarAgenda.ts | `57c84376346095d0beb65b3535105cf21dea2221c8705c85d0e004a0d1ece5f0` |
| frontend/src/styles.css | `40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c` |

Dodano tylko pięć plików: runner, dwa nowe testy, osobny plan rollback
i ten raport. Dotychczasowy kod E2A/E2B/E2C, konfiguracje danych,
zależności, CI, K2, Overview i R1–R3 pozostają bez zmian.
Git: **9 modified / 9 untracked**, indeks pusty, main i HEAD bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend i formatowania globalnego.

Snapshoty, pełna kopia, manifesty, plan i logi są ignorowane w data/raw.
Własne losowe bazy usunięto; własny kontener i jego anonimowy wolumen
usunięto po kontroli pełnego ID, etykiety i pozostawionych baz. Normalny
macrolens_postgres pozostał uruchomiony. Brak diagnostycznych lease.

## 10. Plan do osobnej zgody i bezpieczne wznowienie

Plan: `data/raw/earnings-coverage-activation-2026-11-04/activation-plan.json`.

**Pełny SHA-256 kanonicznego JSON:**

`3a7ce0f993a8aae54261bea33aa7fb0c80705f8da86bb46c0b6f23b419043603`

**ready_for_apply=true, ale apply na normalnej bazie NIE WYKONANO.**
Backend pozostaje wyłączony, aby snapshot nie utracił ważności.
Przed późniejszym apply ponownie sprawdzić całą tożsamość, dane, schemat,
artefakty i kopię. Jakakolwiek różnica zatrzymuje procedurę i wymaga nowego
przeglądu oraz osobnej zgody, bez obchodzenia guardów.

Po osobnej zgodzie i udanym COMMIT: sprawdzić liczniki, idempotencję,
pełne 13 tabel makro i wszystkie pierwotne wiersze E2A/E2B **przed**
uruchomieniem backendu. Następnie z katalogu projektu uruchomić zwykły
backend według README (`.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload`),
z zachowanym .env i domyślnym portem 8000. Vite wznowić przez `npm run dev`
w frontend, bez override API. Sprawdzić health, rzeczywiste API, Calendar
na localhost:5173, wszystkie firmy/datowane eventy i istniejące Actual,
EN/PL, desktop/mobile, Makro/Wszystkie. Nie przytrzymywać lease podczas
restartu. Zwykłe zapisy makro po restarcie są osobną aktywnością.

Przerwanie okna serwisowego przez uruchomienie backendu przed aktywacją
może unieważnić snapshot; wtedy potrzebny nowy plan. Nie wykonano teraz
restartu. Nie pobierano SEC/IR, nie dodano nowych Actual/Forecast ani E2D.

## 11. Wykonanie po wyraźnym zatwierdzeniu — 04.11.2026

Użytkownik zatwierdził wyłącznie plan
`3a7ce0f993a8aae54261bea33aa7fb0c80705f8da86bb46c0b6f23b419043603`
na localhost:5432/macrolens, rolą macrolens, OID 16384, klaster
7682090371041935398. Nie przeliczano ani nie zastępowano planu.

### Ostatnia kontrola i transakcja

Ponownie potwierdzono PostgreSQL 17, dokładną tożsamość celu, wszystkie
21 hash/count, pierwotne wiersze Earnings, obie sygnatury schematów,
starą definicję CHECK, zamrożone artefakty, format/rozmiar/SHA backupu
i SHA oraz treść dowodu pełnego restore. Nie było częściowego E2C,
innych klientów SQL, advisory locks lub działającego backendu zapisującego.
Odczyty miały read_only=on. Wszystkie 13 chronionych plików i pusty
indeks ponownie sprawdzono. Kontrole przeszły bez zmiany artefaktów.

**Apply: created, COMMIT poprawny.** Jedna transakcja SERIALIZABLE objęła
tylko zatwierdzony CHECK oraz 245 nowych wierszy: 50 emitentów, 52 aliasy,
27 okresów, 27 wydarzeń, 35 evidence i 54 confirmations. Nie utworzono
nowych tabel. Nie dodano nowych Actual lub Forecast.

| Tabela | Potwierdzony stan po COMMIT |
|---|---:|
| earnings_companies | 53 |
| earnings_company_aliases | 55 |
| earnings_periods | 37 |
| earnings_events | 37 |
| earnings_source_evidence | 40 |
| earnings_date_confirmations | 66 |
| earnings_financial_documents | 6 |
| earnings_financial_observations | 12 |

**Idempotencja: already_initialized.** Ponowienie tego samego planu nie
zmieniło żadnego pełnego snapshotu, wersji lub timestampu. Nie wykonano
rollbacku po udanym COMMIT.

Przed restartem niezależny odczyt potwierdził identyczność wszystkich
13 tabel makro z zatwierdzonym snapshotem oraz wszystkich pierwotnych
wierszy ośmiu tabel Earnings jako podzbioru rozszerzonych danych.
Obie tabele finansowe mają identyczne pełne hashe. Dokładnie jedna
zmiana schematu odpowiada zatwierdzonemu CHECK. GOOG/GOOGL i BRK.B/BRK-B
zachowują po jednym emitencie. Pełne nowe wiersze odpowiadają referencji,
w tym FY/kwartały, daty, precyzje, strefy i dowody wszystkich 27 eventów.
Łącznie po transakcji: 21 tabel / **2 925 096 rekordów**.

Lokalny receipt: `data/raw/earnings-coverage-activation-2026-11-04/apply-receipt.json`,
SHA-256 `0b6a42a61d868250a09e0d72f19d331efe419ed806a304b3c7e36e91a588fb95`.
Dowód integralności sprzed restartu: `integrity-before-restart.json`,
SHA-256 `003fb780830074332ebcdf7975bd56139a37e9405acc5c2edfbce0ff06a5b7b3`.
Nie publikowano tych plików i nie dodano ich do Git.

### Wznowiona normalna aplikacja

Dopiero po kontroli integralności uruchomiono zwykły Uvicorn
`app.api.main:app --reload` na 127.0.0.1:8000 i Vite na localhost:5173.
PID launchera backendu 18828, reloadera 18088, rzeczywistego workera
**19404**; Vite **15772**. Katalog workera to C:\Projects\macrolens.
Z jego procesu odczytano tylko niesekretne DB_HOST/PORT/NAME/USER:
localhost / 5432 / macrolens / macrolens. Nie wypisywano hasła lub .env.
Nie użyto izolowanego API, CORS wrappera, fixture odpowiedzi lub innej bazy.
Nie zmieniono konfiguracji R1–R3 i nie przytrzymywano diagnostycznego lease.

**41 bezpośrednich GET zakończyło się HTTP 200.** Sprawdzono health,
53 unikalnych emitentów, pełną listę, szczegóły wszystkich 34 datowanych
eventów, aliasy GOOG/GOOGL, stare API makro i wspólny endpoint domen.
Wszystkie 27 nowych terminów porównano z lokalnym ledgerem: okresy,
period_end, URL, osobne release/call, source timezone i dokładne UTC.
Sześć raportów finansowych zachowuje źródłowe kwoty, jednostki i metodologię.
Makro 02–08.11 zwróciło **16 wydarzeń**, widok Wszystkie zawiera obie domeny.

Zakres **01.05–31.12.2026** zwraca **34 datowane wydarzenia**, w tym
**27 nowych**, plus 3 undated zachowane w API, ale ukryte w Calendar.
Poprzedni tydzień 26.10–01.11 ma 6 wierszy, a 02–08.11 ma 5.
Brak wydarzenia dla 23 firm bez zweryfikowanej daty nie oznacza braku
tych firm w SQL; wszystkie 53 są w rejestrze API.

### Chrome na normalnym Vite i rzeczywistym API

**259 kontroli / 28 zakończonych odpowiedzi API 200, zero błędów
JavaScript, console.error i HTTP 503.** EN/PL, desktop 1366 px i mobile
390 px. Potwierdzono wszystkie 27 nowych wierszy w zakresie maj–grudzień,
w tym Apple, Microsoft, Alphabet, Meta, AMD, Qualcomm, ARM i Snowflake;
wszystkie nowe Actual są puste, a Forecast wszędzie pozostaje `—`.
Nie ma checkboxów tickerów, undated lub nieogłoszonych Q4 w tabeli.

NVDA 17.11: **ok. 22:20 — wyniki**, call **23:00**, oba Actual null.
INTC Q3: revenue **16 513 mln USD**, diluted EPS **0,60 USD**, AMC **21:00+**
i call **22:00**. AMZN Q3: revenue **201 944 mln USD**, EPS **1,89 USD**,
nieznana godzina release i osobny call **22:00**. Zachowane pozostałe
raporty E2B, bez surprise lub beat/miss.

Przeszły Makro/Wyniki spółek/Wszystkie, zakresy historyczne i przyszłe,
jeden nagłówek 29.10, źródła, Escape/focus, brak zbędnego refetch Earnings,
wewnętrzny scroll tabeli na telefonie i brak overflow całej strony.
Obejrzano zrzuty desktop EN i mobile PL. To nie jest pełny audyt WCAG.
Nie podstawiano odpowiedzi. Chrome nie wykonał żądań do wydawców.

Pierwszy pomocniczy test bezpośredniego API porównywał tekst `14:00`
z poprawnym SQL/API `14:00:00`. Poprawiono tylko ignorowany helper,
aby porównywał wartości czasu, i powtórzono cały zestaw 41 GET z sukcesem.
Nie edytowano kodu aplikacji ani nie zaliczono pierwszej próby jako sukcesu.

Końcowy odczyt po UI potwierdził identyczne osiem tabel Earnings względem
stanu po COMMIT, bez dodatkowych rekordów lub wersji. Do tego odczytu
także wszystkie 13 tabel makro pozostały identyczne; przyszłe zwykłe zapisy
po restarcie są dozwolone i nie stanowią zmiany transakcji aktywacji.
Nie pozostawiono blokad lub sesji diagnostycznych. Własny Chrome zamknięto.

### Końcowy stan

**E2C działa w normalnej aplikacji: http://localhost:5173/#/calendar.**
Backend i Vite pozostawiono uruchomione. Nie powstał automatyczny feed;
kolejne daty i korekty nadal wymagają zweryfikowanych manualnych rekordów.
Nie uruchomiono SEC/IR scrapingu, E2D lub nowego importu Actual.

Zmieniono tylko ten raport; runner, importer, dane i pozostałe zamrożone
artefakty zachowują zatwierdzone hashe. Wszystkie 13 chronionych plików
użytkownika jest byte-identycznych. Git: **9 modified / 9 untracked**,
indeks pusty; main i HEAD 3537b829a6eb84900f9db8e8218d72d9535c8f52
bez zmian. Bez stagingu, commita, pusha, resetu, clean lub amend.
Receipts, kontrole, logi, helpery i zrzuty pozostają ignorowane w data/raw.

## 12. Zamknięcie Git E2C Activation — 04.11.2026

Na osobne zlecenie użytkownika przygotowano commit
**Add safe earnings coverage activation**: pięć plików tego etapu i minimalny
krok CI `PostgreSQL Earnings coverage activation and recovery`, zachowujący
dziewięć wcześniejszych walidacji. Runner produkcyjny i rollback nie były
zmieniane. Test dopuszcza także job-local service Actions przez pełny ID,
wyłącznie przy roli macrolens_ci, kontrolnej bazie CI i hoście loopback.
Zwykła macrolens nadal nie jest bazą kontrolną testu.

Dokładna kopia indeksu: **340 zgodnych blob IDs**, bez E2D i wcześniejszych
prac użytkownika. Pełne wyniki staging-only: **1300 backend passed, 55,43 s**,
**662 frontend passed / 31 plików**, typecheck/build poprawne (407,04 kB),
PostgreSQL **10/10**, actionlint i oba
whitespace checks poprawne. PostgreSQL wykonał rzeczywisty backup/restore,
rollback CHECK+seed, bramki celu/zgody/artefaktów i idempotencję na własnym
serwisie PostgreSQL 17, loopback 55469. Sprawdzono ścieżkę service ID CI.
Pierwszy helper SQL trafił na kontrolę ownership Git w kopii; poprawiono
wyłącznie process-local safe.directory tej kopii, bez zmiany globalnej
konfiguracji lub testów. Cały przebieg 10/10 wykonano ponownie z kodem 0.

Przejrzano pełny staged diff, ścieżki i sekrety. Sześć plików jest całym
zakresem pierwszego commita; nie ma data/raw, .env, logów lub kopii danych.
Wszystkie 13 chronionych plików użytkownika pozostaje byte-identycznych.
Nie wykonywano aktywacji, importu, DDL lub rollbacku normalnej bazy.
Nowy odczyt read-only potwierdził tożsamość i brak obu tabel E2D; zwykły
backend i Vite pozostają uruchomione. Historyczne wyniki sekcji 1–11
nie są nowymi pomiarami zamknięcia. SHA commitów, URL pusha i zakończone
wyniki Actions będą w odpowiedzi końcowej, bez dodatkowego commita dla
metadanych po pushu. Nie aktywowano E2D i nie rozpoczęto kolejnego etapu.
