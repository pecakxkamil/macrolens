# MacroLens — Forecast F1 Activation: gotowość

Wykonano **05.11.2026, Europe/Warsaw**, C:\Projects\macrolens, main,
HEAD **5b31cdb1ea042cd10483f701c262b85a958efc08**.

**GOTOWE DO OSOBNEGO ZATWIERDZENIA. STOP PRZED NORMALNYM APPLY.**
W normalnej aplikacji zarejestrowano nieaktywną ścieżkę wybudzania F1:
registered=true, activated=false, awaiting_activation. Nie wykonano normalnego
DDL/importu, nie utworzono normalnego tokenu F1. Aktywację, runtime, restart
i UI sprawdzono na pełnym klonie. Monitor Earnings w normalnej bazie działa.
Nie wykorzystano wcześniejszych zgód E2E lub monitora jako zgody na F1.

## 1. Dokładny plan

Pełny kanoniczny SHA-256 nowego planu:

`33fb364f3f518a193d7d451c9dfad6f1d5e005eec2a67c8a01ab626c6c531289`

Plan: `data/raw/forecast-f1-activation-2026-11-05/normal-reviewed-final.json`.
Niezależne normalne CLI prepare i plan zwróciły ten sam pełny hash co próba
klonu po odjęciu wyłącznie różnic target/target_label. Target normalny:

- localhost:5432/macrolens, PostgreSQL 17, rola macrolens;
- OID 16384, cluster identifier 7682090371041935398.

Zakres to dokładnie istniejący DDL trzech tabel:
forecast_vintages, forecast_freezes, forecast_refresh_checks, ich constraints,
indeksy, forecast_f1_guard i osiem triggerów append-only/insert/no_truncate.
**Bajty forecast_f1_schema.sql są identyczne z wejściowym F1.**
Bez ALTER istniejących tabel, nowych eventów, okresów i emitentów.

Seed to dokładnie **20 istniejących obserwacji**: 16 model_nowcast Cleveland,
4 issuer_guidance, zero consensus. Payloady skopiowano z przejrzanego pilota,
bez świeżego rozszerzania danych. Ledger i jego fingerprint/SHA są zamrożone.
Guidance ma jedną obserwację EPS i trzy Revenue dla NVDA/QCOM/ARM.
Identyfikatory seedów są deterministyczne; SQL captured_at oznacza rzeczywisty
czas nowego zapisu, bez podszywania się pod dawny capture/first print.

Początkowo freeze jest pusty. Dwa początkowe wiersze refresh_checks to:
niezmienna activation-policy wiążąca pełny hash oraz seed_cooldown_not_new_http.
Ten drugi wiąże prawdziwy receipt poprzedniego capture, ale nie deklaruje
nowego HTTP podczas APPLY. Wyznacza minimum 24 h przed kolejną kontrolą.
Nie dodano czwartej tabeli policy. Runtime token powstaje dopiero osobno,
po prawidłowym COMMIT i niezależnej weryfikacji.

## 2. Zamrożone zależności i runner

Plan obejmuje **260 artefaktów i wersji bibliotek**: kod app/SQL, konfigurację,
frontend, requirements/package/lock oraz httpx/psycopg/pypdf. W szczególności
wiąże importer, runner, reader, formatter, ledger i politykę przyszłego
Cleveland dispatch. Każda zmiana tych artefaktów wymaga nowego prepare;
runner nie podmienia po cichu zaakceptowanego planu.

Zamrożono pełne definicje publicznego schematu, rzeczywiste pg_depend closure,
stany triggerów i indeksów. Jawnie uwzględniono odwołania PL/pgSQL i Python,
których sam pg_depend nie opisuje. Istotne dane referencyjne obejmują pełne
snapshoty sześciu tabel tożsamości/okresów/kalendarza Earnings oraz projekcję
CPI/PCE/GDP: identyfikator wydarzenia, dzień/czas/strefa, potwierdzony okres,
transformacja/SA/jednostka, etap publikacji i metadane serii.

Nie włącza się do kanonicznego hasha Actual/Previous, observations/features,
Overview ani source_check_runs. Nowe prawidłowe Actual monitora lub zwykłe
aktualizacje makro nie są automatycznie zmianą referencji F1. Zmiana właściwej
tożsamości, jednostki, częstotliwości, okresu, kalendarza lub schematu daje STOP.
Archiwum i dowód pełnego restore są sprawdzane osobno; nowy zgodny backup nie
musi zmieniać zatwierdzanego hasha z powodu niepowiązanych rekordów makro.

Runner `app/database/activate_forecast_f1.py` udostępnia prepare, plan, apply,
verify i osobne enable-runtime. Prepare/plan/verify są read-only; reference
DDL jest wykonywane wyłącznie na własnej izolacji z rollbackiem.
Apply wymaga osobnego pełnego hash_confirmation i target_confirmation,
zgodnego backup/restore i ponownej kontroli referencji po lockach.

Transakcja READ COMMITTED używa advisory 726530032/726530031, lock_timeout 5 s,
statement_timeout 120 s oraz krótkiego SHARE na sześciu tabelach referencyjnych
Earnings i series/release_dates/economic_releases. Te trzy tabele zawierają
referencje makro; ich dane nie są hashowane globalnie jako niezmienne.
Nie pobiera się makro lease 726530019 i nie blokuje observations, features,
Overview lub source checks. E2D może używać swojego locka 726530020 i row locks.

Po DDL/seed ponownie sprawdzane są katalogi, referencje i artefakty przed
COMMIT. Błąd wycofuje całą transakcję, razem z DDL i policy. Przy istniejącym
zgodnym store APPLY zwraca already_initialized przez read-only verify,
bez nowych wersji, wierszy lub timestampów. Częściowy/obcy store nie jest
naprawiany. Po COMMIT nie wykonuje się automatycznego restore/rollbacku.
Dawne initialize/append/dispatch nadal odrzucają normalną bazę; nowe uprawnienie
prowadzi przez osobny, kontrolowany runner/policy/token, a nie usunięcie guarda.

## 3. Backup i pełny klon

Świeży pg_dump custom: **32 116 442 B**, SHA-256:

`9b535ac741a02eeef847d642d7afa6d937697978a101cf3229a35dca7fa24fa9`

Odczyt normalnej bazy miał jeden REPEATABLE READ READ ONLY z
pg_export_snapshot; pg_dump używał tego samego eksportowanego snapshotu
oraz default_transaction_read_only. Nie zatrzymywano aplikacji ani nie
pobierano normalnego makro lease.

TOC i pełny restore na własnym PG17, loopback **55511**, zakończyły się
kodem 0. **26 tabel / 3 086 306 rekordów**, wszystkie pełne uporządkowane
binary COPY hash/count oraz oba katalogi zgodne z eksportowanym snapshotem.
Zero niezwalidowanych constraints. Dowód wiąże rzeczywisty normalny target,
SHA/rozmiar archiwum i pełne odtworzone dane.

Następnie z tego archiwum wykonano pełny klon oraz jego własny backup/restore
przed próbą. Osobny dowód referencji F1 wiąże projekcję referencyjną odczytaną
z odtworzonego archiwum. Nie podstawiano normalnej tożsamości pod klon.
Normalny i klonowy plan różniły się tylko rzeczywistym targetem/target_label.

Na klonie przeszły:

- prawdziwe SQL 1/0 przy dziesiątej obserwacji: razem wycofane DDL, policy i seed;
- prawidłowy APPLY: trzy nowe tabele, dokładnie 20 seedów i dwa początkowe checks;
- niezależne read-only verify pełnych payloadów/UUID/fingerprintów i katalogu;
- drugie APPLY: already_initialized, wszystkie dane/timestampy identyczne;
- STOP po zmianie częstotliwości CPI lub dodaniu nieprzejrzanego indeksu;
- rzeczywisty bounded lock timeout, bez wydłużania 5 s;
- dopuszczona zmiana results Overview bez zmiany hasha planu;
- jednoczesny zapis makro i idempotentny rzeczywisty writer E2D pod lockami F1;
- append-only, błędne approval/target, versioning i brak reaktywacji starej wersji;
- trwały cooldown po restarcie oraz awarii procesu po zapisie claim przed wynikiem HTTP;
- konkurencyjny osobny proces z prawdziwą autoryzacją klonu: busy, zero HTTP/importu.

Syntetyczne próby zmiany referencji/makro/schematu dotyczyły wyłącznie klonu
 i zostały cofnięte/przywrócone. Nie zaliczano ich do prawdziwych prognoz.
Przy aktywacji wszystkie **26 poprzednich tabel pozostały byte-identyczne**.
Test współbieżności używał idempotentnego writera E2D z przejrzanym ledgerem,
nie nowego raportu emitenta opublikowanego w trakcie testu. Oddzielne regresje
monitora sprawdzają jego pełny import/równoległość; w normalnym środowisku
jego autoryzacja i działanie również pozostają potwierdzone.

## 4. Źródła, prawa i przyszły dispatch

Zakres pozostaje lokalny, osobisty i niekomercyjny, zgodny z audytem F1.
[Cleveland dane](https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting)
i [warunki](https://www.clevelandfed.org/privacy) ponownie sprawdzono.
Zgoda banku na przypisane źródłowo wykorzystanie osobiste/edukacyjne/
niekomercyjne nie jest zgodą na publiczny komercyjny feed ani SLA API.
Nowcasty są podpisane typem, linkiem do banku i metodologią źródła.
Dopuszczenie niskiego ruchu do publicznego odczytu jest przejrzaną interpretacją
przeznaczenia danych z respektowaniem robots; robots samo nie nadaje licencji.

Przed każdą przyszłą próbą worker sprawdza robots i całą znormalizowaną
sekcję **Privacy and Terms of Use**. Jej zamrożony hash:

`c5283d1db7a07bf8e611cd24f72b810a658320726f5571c13bf0a30edcdb4d85`

Zmiana dowolnej klauzuli, niedostępne warunki lub odmowa dostępu powoduje
STOP pobierania danych. Pomijana jest wyłącznie otoczka strony/nawigacja/footer.
Timeout 25 s, limit dokumentu 5 MiB, brak obejść 403 i nieprzejrzanych redirectów.
Banków ani dostawców nie kontaktowano; nie tworzono kont i nie płacono.

Guidance pozostaje małymi przejrzanymi faktami z oficjalnych dokumentów:
[NVIDIA SEC](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/q2fy27pr.htm),
[QCOM SEC](https://www.sec.gov/Archives/edgar/data/804328/000080432826000085/qcom062826erex991.htm),
[ARM](https://investors.arm.com/static-files/0b5baa2e-fc47-4d05-b724-e49de7bd4356).
Nie dodano uniwersalnego parsera ani okresowego pobierania guidance.
Nie rozszerzono GDPNow, Investing.com, FinancialJuice, Alpha Vantage lub Finnhub.
Pełne źródła i ich rozróżnione uprawnienia pozostają w pierwotnym audycie F1.

Dispatch ma zamkniętą listę: Cleveland, model_nowcast, cztery wskaźniki,
MoM/YoY, SA, okresy październik/listopad 2026. **Nie dodaje automatycznie
nowych miesięcy ani emitentów.** Wyjście poza tę listę wymaga nowego zakresu.

Wykorzystuje istniejący coordinator.launch i zegar lifecycle Earnings.
Dodano opcjonalny listener uruchomień wyłącznie z modułu
app.earnings_monitor_runtime oraz jedną kontrolę przy starcie aplikacji.
Nie dodano drugiego timera, pętli, procesu schedulera lub pakietu zależności.
Żądania makro/Calendar nie uruchamiają tego listenera. Plik starego runtime
Earnings i wszystkie artefakty jego aktywnej policy zachowano bez zmian.
Dalsze wybudzanie zakłada aktywny dotychczasowy lifecycle Earnings, który
jest potwierdzony w normalnej aplikacji; nie deklaruje się osobnego zegara F1.

F1 ma własny token, niezmienną policy w checks, kontrolę załadowanego kodu,
reference data i katalogu, in-process busy oraz SQL lease 726530031.
**Claim z retry_at jest zatwierdzany przed HTTP.** Przerwanie po claim nie
pozwala na ponowne HTTP po restarcie w tym samym oknie. Minimum **24 h między
kontrolami, także po błędzie**; Retry-After/backoff nie skraca tej granicy.
Identyczne payloady nie dodają wersji; sama zmiana bajtów otoczki dokumentu
przy niezmiennych wartościach/dacie/metodologii również nie tworzy duplikatu.
Nowa rzeczywista rewizja zachowuje wcześniejsze wersje.

Freeze jest oddzielną operacją workera ze stored Actual i potwierdzonym
cutoff, nigdy skutkiem GET. Pozostaje max(published_at, SQL captured_at),
wybór sprzed cutoff, niezmienny snapshot lub null. Dla date-only Earnings
cutoff jest konserwatywnym początkiem dnia; makro używa potwierdzonego czasu
kalendarza. Nie deklaruje się dokładnego first print, gdy źródło go nie dowodzi.
QCOM dostaje null zamiast guidance poznanego po Actual. Po braku dowodu czasu
lub spójnej metodologii nie powstaje pozorne porównanie ani procentowy surprise.

## 5. Calendar i rzeczywisty runtime klonu

Po seedzie widoczne jest **14 nowcastów w istniejących wierszach makro**
i **jedna bieżąca prognoza Revenue NVIDIA Q3 FY2027**:

`105,84–110,16 mld USD · Guidance`

EPS Forecast NVIDIA pozostaje —. Nie zastosowano midpointu zakresu.
QCOM nie dostaje historycznej prognozy przed Actual, ARM Q3 nie otrzymuje
sztucznego eventu. Nadal 16 modelowych i 4 guidance w store, zero consensus.
CPI/Core CPI, MoM/YoY i SA/NSA nie są zamieniane; GDPNow Q4 nie trafia do Q3.
Actual, Previous, Market Cap i siedem kolumn Earnings zachowano.
Zmiana formatowania zakresu usuwa tylko powtórzoną jednostkę/walutę.

Osobny token z rzeczywistą tożsamością klonu włączono przez CLI enable-runtime.
Normalny token nigdy nie powstał. Startup przez istniejący launcher faktycznie
uruchomił F1 worker, który rozpoznał cooldown i nie pobierał ponownie źródła.
Dwa osobne procesy API 8053, przed i po rzeczywistym zakończeniu/restartcie,
zwróciły activated=true, cooldown, added=0, frozen=0. Nie jest to deklaracja
uruchomionego normalnego feedu. Próby HTTP/backoff/crash są testowane oddzielnie.

API klonu miało wymuszone default_transaction_read_only dla zwykłych połączeń
HTTP; osobno skonfigurowany worker zachował kontrolowaną możliwość zapisu do
tego samego rzeczywistego klonu. Kontrolny GET potwierdził transaction_read_only=on.
CORS dodano wyłącznie dla własnego preview. Nie podstawiano JSON/odpowiedzi SQL.
Po obu procesach i wszystkich GET/UI **29 pełnych tabel było byte-identyczne**.

Chrome, EN/PL, 1366/390 px: **207 kontroli / 8 odpowiedzi API 200**, zero
JS/console.error i żądań przeglądarki do wydawców. Wszystkie 14 wartości
porównano z API, sprawdzono typy/źródła, dokładny zakres guidance, brak
retrospektywnego QCOM/ARM, siedem kolumn, Current/Previous, wewnętrzny scroll
i brak overflow strony. Obejrzano desktop i przewiniętą część tabeli mobile.
Nie deklaruje się pełnego audytu WCAG.

## 6. Wyniki końcowe

| Kontrola | Wynik |
|---|---|
| Pełny backend offline | **1541 passed**, 64,45 s |
| Pełny frontend offline | **719 passed / 36 plików**, 48,49 s |
| TypeScript noEmit | passed |
| Production build | passed, Vite 5,58 s, największy chunk 407,04 kB |
| Wszystkie wcześniejsze PostgreSQL | **20/20 passed**, nowe przebiegi |
| Nowa pełna walidacja aktywacji F1 | passed; razem **21 walidacji** |
| Pełny świeży backup/restore i aktywacja klonu | passed |
| Read-only API, restart, współbieżny proces i Chrome | passed |
| Chronione pliki / pusty indeks / diff --check | passed |

Pierwsze próby pomocnicze zostały odrzucone: prepare wywołano po wcześniejszym
UPDATE w tej samej transakcji, a podczas rozwoju zmieniono artefakty między
normalnym prepare i próbą klonu. Poprawiono test oraz dokończono zamrażanie
kodu, zamiast osłabiać guardy. Kontrolę warunków rozszerzono na całą sekcję
polityki, po czym wygenerowano nowy plan i powtórzono pełną próbę. Nieudanych
prób i wcześniejszych hashy nie zaliczono do gotowości. Końcowy hash powyżej
odpowiada przetestowanemu kodowi. Nie uruchamiano GitHub Actions ani nie
utożsamiano lokalnych wyników z CI przyszłego commita.

## 7. Normalne środowisko i ochrona prac

Na początku: **23 modified / 34 untracked**, pusty indeks. Zapisano manifest
SHA i pełny diff 57 zastanych plików. Zmieniono z nich osiem koniecznych
plików API/F1/formatter/testów: **pozostałe 49 byte-identyczne**, w tym
wszystkie **13 chronionych prac użytkownika** i wcześniejsze audyty.
CalendarPage, Brief, globalny CSS, Actual, History i Market Cap bez zmian etapu.
Nie zmieniono oryginalnego DDL F1, zależności, lockfile lub CI.

Normalna baza końcowo nadal **26 tabel / 3 086 306 rekordów**. Wszystkie
**26 pełnych snapshotów i oba katalogi są identyczne** z eksportowanym
backupem w tym konkretnym oknie; nie wymagano zatrzymania pracy makro.
Wszystkie 13 tabel Earnings, także policy/checks monitora, zachowano.
E2D 29/50, History 23 raporty / 45 metryk. Nie ma żadnej tabeli F1.
Monitor status: loop_running=true, activated=true, completed, checked=0.
Jego token/policy i artefakty potwierdzono niezależnym read-only SQL.

Market Cap nadal 49/53, cache SHA-256:
`94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799`.
Bez importu kapitalizacji lub zmiany polityki 7/45 dni. Normalne API/Vite
pozostały dostępne; autoreload odczytał nowy kod. Nie zatrzymywano ich ręcznie.
Normalny F1 status nadal registered=true, activated=false, awaiting_activation,
bez tokenu, HTTP do Cleveland lub zapisów F1.

Własne API/preview/Chrome zakończono. Klony/restore bazy usunięto, własny PG17
z anonimowym wolumenem usunięto po sprawdzeniu pełnego ID
848ecafb5f440b48fc72837964e0256472bbd45869c17f98ef68e82dc4412d7b,
etykiety forecast-f1-activation-2026-11-05, braku klientów i baz poza control/
postgres/template. Normalny PostgreSQL 5432, API 8000 i Vite 5173 działają.
Backupy, plany, receipts, zrzuty, helpery i logi pozostają ignorowane w
 data/raw/forecast-f1-activation-2026-11-05, bez pełnych dokumentów w Git.

## 8. Zakres plików i przyszły commit

Ten etap zmienił dziewięć istniejących plików (coordinator, API/main,
trzy moduły F1, conftest i dwa pliki formattera) oraz dodał osiem nowych
(runner, bindings/runtime, dwa ledgery/policy, dwa testy i ten raport).
Poniżej precyzyjny pakiet **28 ścieżek całego F1 + F1 Activation**:

- app/analytics/calendar_agenda.py
- app/api/earnings.py
- frontend/src/api/macrolens.ts
- frontend/src/calendar/CalendarPage.tsx
- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/earningsTypes.ts
- tests/conftest.py
- tests/test_earnings_dates.py
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
- app/database/activate_forecast_f1.py
- app/forecast_f1_bindings.py
- app/forecast_f1_runtime.py
- config/forecast_f1_activation_ledger.json
- config/forecast_f1_dispatch_policy.json
- tests/test_forecast_f1_activation.py
- tests/postgres_forecast_f1_activation_validation.py
- docs/audits/macrolens-forecast-f1-activation-readiness-2026-11-05.md
- app/analytics/overview_refresh.py
- app/api/main.py

To wykaz zakresu, nie wykonany staging ani polecenie git add całych brudnych
plików. W CalendarPage i innych plikach współdzielonych przyszły staging musi
wybrać tylko hunki F1, zachowując wcześniejsze prace użytkownika poza commitem.
Wcześniejsze niezacommitowane zależności monitora Earnings i prezentacji sesji
muszą zostać osobno uporządkowane przed wydzielonym commitem F1. Nie dodano
ich tutaj do zakresu pod pozorem domknięcia zależności. Dokładną kopię przyszłego
indeksu trzeba przetestować osobno. Jeśli takie zamknięcie zmieni zamrożony
artefakt, aktualny apply zatrzyma się i będzie potrzebny nowy plan/hash.

Maszynowy wykaz SHA dla tego pakietu i manifest wejściowy są w ignorowanym RAW.
Końcowo **24 modified / 42 untracked**, indeks pusty, main/HEAD bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend, force lub formatowania globalnego.

## 9. STOP i późniejsze wykonanie

Nie ma technicznego blokera dla kontrolowanej aktywacji testowanego lokalnego
zakresu na aktualnym stanie. **Brakuje osobnej zgody na powyższy pełny hash**;
nie jest ona domniemana ze zlecenia przygotowania lub poprzednich aktywacji.
Nie wykonano normalnego APPLY ani enable-runtime.

Później należy ponownie wykonać read-only prepare/plan i sprawdzić aktualność
backup/restore oraz referencji. Przy zmianach nie podmienia się zatwierdzonego
planu: STOP i nowy hash. Po osobnym zatwierdzeniu: apply dokładnego planu,
niezależne verify, kontrola 20 seedów, dwóch checks i starego stanu, dopiero
potem jawne enable-runtime dla normalnego targetu oraz API/Chrome i kontrola
kolejnych wybudzeń. Nie uruchamiać reference DDL na normalnej bazie.
Nie ma automatycznego cofania po COMMIT; wymagałoby to osobnej decyzji.

F1 pozostaje fundamentem prognoz modelowych/guidance, a nie pełnym konsensusem
Investing.com. GDP, nowe miesiące/emitenci, automatyczny guidance i konsensus
pozostają poza tym planem.
