# MacroLens — K2: jednolita klasyfikacja ważności wydarzeń

Weryfikacja **02.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`.
`main`, HEAD **`b89f744fe7c41f22203cf7ef59e3140367dfb53a`** —
`Optimize frontend bundle with lazy-loaded overview`.
Podstawa: lokalny audyt `calendar-event-impact-audit-2026-10-30.md`,
wykonany 2 listopada mimo wcześniejszej daty w nazwie. Ten nieśledzony
artefakt K1 pozostaje poza commitem K2; nie jest linkiem do pliku na GitHubie.
Poniższy inwentarz i sześć jawnych decyzji stanowią samodzielny kontrakt K2.

Wdrożono zatwierdzony wariant B: **dokładnie sześć rodzajów ★★ → ★★★**:
Retail 9, JOLTS 192, Claims 180, PPI 46, `fomc_minutes`, New Residential
Sales 97. Pozostałe 23 rodzaje zachowują ocenę. Inwentarz nadal obejmuje
29 rodzajów, w tym osobną G.17 annual revision: **11/17/1 → 17/11/1**
w kolejności ★★★/★★/★. To liczby rodzajów, nie dat, eventów lub miar.

Stan po implementacji, przed kontrolą zamknięcia poniżej: **bez stagingu,
commita i pusha.** Bez zmian danych ekonomicznych,
schematu, importerów, harmonogramów, zależności i polityk odświeżania.
Nie kontaktowano się z Investing ani wydawcami publikacji.

## Polityka i kontrakt API

Jedno źródło końcowej oceny to `app/analytics/calendar_market_impact.py`.
Wersja **`2026-11-k2-v1`** jest stała, niezależna od zegara serwera.
Zwykłe raporty rozpoznaje numeryczny `release_id`, dedykowane adaptery
rozpoznaje `event_type`. ISM wymaga jednej właściwej serii:
`ISM_MANUFACTURING_PMI` albo `ISM_SERVICES_PMI`; brak lub obecność obu
oznacza unknown. G.17 annual revision ma osobną regułę dzięki
`estimate_stage=annual_revision`. Tłumaczenie lub zmiana nazwy nie zmienia
oceny. Nie dodano osobnego FOMC Statement.

Do istniejącego eventu dodano:

| Pole | Kontrakt |
| --- | --- |
| `market_impact_stars` | 1, 2, 3 albo jawne null |
| `market_impact_policy_version` | `2026-11-k2-v1` |
| `market_impact_rule_id` | `release:<id>`, dedykowany typ, osobny ISM lub `release:13:annual_revision`; null dla unknown |
| `market_impact_scope` | `event` |

Dotychczasowe `importance` pozostaje i dla znanych reguł odpowiada ocenie
high/medium/low. Claims już miało backendowe high; pięć pozostałych
zatwierdzonych raportów otrzymuje high na wyjściu. Dawne klasy w adapterach
i funkcja zgodności nazw `release_importance` nie są już autorytetem
widocznych gwiazdek: centralna projekcja rozstrzyga odpowiedź przed
sortowaniem Calendar. Nie przepisuje się zapisanych dokumentów źródłowych.
Szczegóły release bez pola importance zachowują dotychczasowy kontrakt.

Odpowiedź Calendar, także z readings, zachowuje metadane podczas wiązania
miar. `read_brief` nakłada aktualną politykę również na odczytaną starą
generację Overview i jej `next_decision`. Nie zmienia cache, publication_id,
assembled_at, terminów refresh ani liczb. Dzięki temu wdrożenie nie wymaga
ingestion lub nowej generacji tylko dla gwiazdek.

Frontend `eventImportanceStars` odczytuje metadane API. Jawne null, także
przy legacy importance=high, pozostaje unknown. Tylko gdy pole w ogóle
nie istnieje, działa wąska zgodność ze starszym API/fixtures: high=3,
medium=2, low=1, pozostałe wartości=null. To nie druga tabela rodzin;
starsze API bez nowej polityki nie otrzymuje po stronie TS domyślonych
awansów po nazwie. Unknown w nowym API zachowuje ewentualną legacy klasę
importance, ale nie otrzymuje sztucznego ★★. Wszystkie 29 znanych rodzajów
ma rating.

## Pełny inwentarz

W kolumnie Overview ocena obowiązuje tylko po faktycznym wyborze wydarzenia.
Brak kwalifikacji nie oznacza braku wydarzenia w Calendar.

| Release / event_type | Obecnie (K1) | Po K2 | Backend po K2 | Calendar | Overview, jeśli kwalifikowane |
| --- | --- | --- | --- | --- | --- |
| 9 — Advance Monthly Sales for Retail and Food Services | ★★ | ★★★ | high | ★★★ | ★★★ |
| 10 — Consumer Price Index | ★★★ | ★★★ | high | ★★★ | ★★★ |
| 11 — Employment Cost Index | ★★ | ★★ | medium | ★★ | niekwalifikowane |
| 13 — G.17 Industrial Production and Capacity Utilization | ★★ | ★★ | medium | ★★ | niekwalifikowane |
| 18 — H.15 Selected Interest Rates | ★ | ★ | low | ★ | niekwalifikowane |
| 27 — New Residential Construction | ★★ | ★★ | medium | ★★ | niekwalifikowane |
| 46 — Producer Price Index | ★★ | ★★★ | high | ★★★ | niekwalifikowane |
| 50 — Employment Situation | ★★★ | ★★★ | high | ★★★ | ★★★ |
| 53 — Gross Domestic Product | ★★★ | ★★★ | high | ★★★ | ★★★ |
| 54 — Personal Income and Outlays | ★★★ | ★★★ | high | ★★★ | ★★★ |
| 95 — Manufacturer's Shipments, Inventories, and Orders (M3) Survey | ★★ | ★★ | medium | ★★ | niekwalifikowane |
| 97 — New Residential Sales | ★★ | ★★★ | high | ★★★ | niekwalifikowane |
| 180 — Unemployment Insurance Weekly Claims Report | ★★ | ★★★ | high | ★★★ | ★★★ |
| 190 — Primary Mortgage Market Survey | ★★ | ★★ | medium | ★★ | niekwalifikowane |
| 192 — Job Openings and Labor Turnover Survey | ★★ | ★★★ | high | ★★★ | niekwalifikowane |
| 219 — Chicago Fed National Activity Index | ★★ | ★★ | medium | ★★ | niekwalifikowane |
| 221 — Chicago Fed National Financial Conditions Index | ★★ | ★★ | medium | ★★ | niekwalifikowane |
| fomc_decision — FOMC policy decision | ★★★ | ★★★ | high | ★★★ | ★★★ |
| fomc_press_conference — FOMC Press Conference | ★★★ | ★★★ | high | ★★★ | ★★★ |
| fomc_sep — Fed Economic Projections (SEP) | ★★★ | ★★★ | high | ★★★ | ★★★ |
| fomc_minutes — FOMC Meeting Minutes | ★★ | ★★★ | high | ★★★ | ★★★ |
| ism_report / ISM_MANUFACTURING_PMI — ISM Manufacturing PMI | ★★★ | ★★★ | high | ★★★ | ★★★ |
| ism_report / ISM_SERVICES_PMI — ISM Services PMI | ★★★ | ★★★ | high | ★★★ | ★★★ |
| michigan_preliminary — Michigan Consumer Sentiment — Preliminary | ★★★ | ★★★ | high | ★★★ | ★★★ |
| michigan_final — Michigan Consumer Sentiment — Final | ★★ | ★★ | medium | ★★ | ★★ |
| adp_monthly — ADP National Employment Report | ★★★ | ★★★ | high | ★★★ | ★★★ |
| empire_state — Empire State Manufacturing Survey | ★★ | ★★ | medium | ★★ | ★★ |
| ft900 — U.S. Trade Balance — Goods and Services | ★★ | ★★ | medium | ★★ | ★★ |
| 13 / annual_revision — G.17 annual revision | ★★ | ★★ | medium | ★★ | niekwalifikowane |

Wszystkie GDP Advance/Second/Third/Updated pozostają ★★★. Nie przyjęto
propozycji obniżania etapów ani innych tematów B z K1. Backend przed K2
miał 12 high/16 medium/1 low; po K2 ma 17/11/1. Różnica wcześniejszych
liczb backend/frontend wynikała z obniżania Claims przez Tracked.

## Calendar, ranking, tożsamość i historia

Rating dotyczy **całego raportu**. PPI, Retail, Claims, CPI, Employment
i PIO zachowują dotychczasowe miary i wiersze; wszystkie dziedziczą ocenę
eventu. Nie utworzono ratingów measure-level, dodatkowych publikacji ani
duplikatów. Referencja użytkownika dotyczyła Initial Claims, headline PPI
i headline Retail, nie osobnego potwierdzenia Continuing, wszystkich PPI
lub niejednoznacznego Core Retail. Nie zmieniano definicji tych miar.

Filtry Calendar używają tej samej funkcji co rendering. Sześć rodzajów
wchodzi do ★★★ i wypada z ★★. Domyślny filtr 2+3 nadal je obejmuje;
reset obejmuje 1+2+3 i unknown. Kategorie, chronologiczne grupowanie,
czas Polski i wartości pozostają bez zmian. Zmiana importance może
zmienić kolejność równoczesnych wyników surowego API według istniejącego
sortowania; nie wprowadzono paginacji lub nowego mechanizmu sortowania.

**Ranking Overview pozostał identyczny**: te same 17 reguł, ich kolejność,
okno, deduplikacja i najwyżej cztery sloty. Retail, Claims i Minutes
zachowują kwalifikację i pokazują ★★★ po wyborze. JOLTS/PPI/New Home Sales
nie weszły automatycznie do rankingu. Po zmianie kwalifikuje się 14 rodzajów
★★★ i 3 rodzaje ★★; nie wszystkie 17 są widoczne jednocześnie.
Key/Tracked pozostają etykietami selekcji i nie ustalają gwiazdek.

`eventIdentity` nie wywołuje już `eventPriority`. Zachowano istniejące
przestrzenie nazw generycznych raportów przez stałe kanoniczne ID,
FOMC decision przez typ, ISM przez serię, a istniejące miesięczne i Fed
event_id bez zmian. Regresja 29 rodzajów porównuje dotychczasowe klucze
i kwalifikację oraz ich niezmienność po zmianie ratingu. API event_id,
klucze miar i deduplikacja Calendar nie zostały przebudowane.

Historia i przyszłość używają **aktualnej polityki**, nie ratingu as-of
z dnia publikacji. Nie odtwarza się dawnych ocen i nie zapisuje ich w SQL.
Rating pozostaje ten sam przed publikacją, przy null Actual, po rewizji,
zmianie Previous i zmianie źródła BEA/FRED. Forecast pozostaje nietknięty.

Eksport zachowuje atrybucję/provenance i dopisuje ocenę, zakres event oraz
wersję polityki. Notę o pierwszeństwie Key/Tracked zastąpiono opisem
rzeczywistej polityki; dodano PL i usunięto dwie nieużywane stare noty
tłumaczeń. Minimalistyczne wiersze Overview nie otrzymały opisów.

## Walidacja

| Kontrola | Faktyczny wynik |
| --- | --- |
| Pełny backend offline | **1163 passed**, 49,60 s; 1123 wcześniejsze + 40 nowych |
| Końcowe 40 regresji polityki, także niezależność od danych dla 29 rodzajów | **40 passed** |
| Pełny frontend z `NODE_OPTIONS=--require=../.github/ci/no-network.cjs` | **646 passed / 27 plików**, 25,81 s |
| Osobny `npx tsc --noEmit` | passed |
| Production build | passed; około 407,01 kB, bez ostrzeżenia ponad 500 kB |
| `git diff --check` | passed |

Nowy backend sprawdza 29 rodzajów, dokładnie sześć zmian, liczniki,
kanoniczne ID mimo zmienionej nazwy, unknown i niejednoznaczny ISM, etapy
GDP, daty/wartości/źródła, zgodność importance, projekcję starego cache
bez mutacji i rzeczywisty endpoint FastAPI z syntetycznym SQL bez zapisów.
Wspólna fixture kontraktu jest używana wyłącznie w testach Python/TS,
nie jest drugą produkcyjną tabelą ani częścią wejściowego bundla.

34 nowe testy frontendowe obejmują wszystkie 29 ocen i kluczy, sześć zmian,
brak nadpisania API przez ranking, jawne null i legacy fallback, filtry,
dziedziczenie, top cztery, niezmienną kwalifikację/kolejność i eksport.
EN/PL montują Calendar; filtrowanie/reset nie dodają GET. Zaktualizowano
także stare fixtures testu rankingu, aby zawierały kontrakt backendu.
Punktem wejściowym było 612 testów frontendowych, obejmujących dwie
wcześniejsze poprawki użytkownika ponad 610 z H2.

Pełny zestaw zachował regresje R1/R2/R3/H2: jeden timer i deadline,
hidden/focus/abort, remount lazy Overview, jeden POST w terminie R3,
reload nowej generacji, precision=1, mixed_sources i aktualne źródła.
Nie edytowano tych mechanizmów, interwałów 900/21600 s, punktów R3,
limitu, locka/backoff, obliczeń, API wartości, MCI/PIT, bundlingu lub CI.
Nie pomijano testów ani nie zwiększano timeoutów. Nie wyciszano
Starlette/httpx; końcowy lokalny backend nie wypisał tego ostrzeżenia.
Czterech rzeczywistych skryptów PostgreSQL nie powtarzano: kod bazy i ich
zależności nie zmieniły się. Nie uruchamiano GitHub Actions.

## Production preview i prawdziwe API

Końcowy Chrome: **24 scenariusze**, EN/PL z kontrolą rzeczywistego lang,
**1366/390 px**, bez fixture odpowiedzi API. Historyczne GET 01.09–31.10
zwróciło 119 eventów, w tym 19 wystąpień sześciu zmienionych rodzajów:
Retail 3, PPI 2, New Home Sales 2, Claims 9, JOLTS 2, Minutes 1.
Sprawdzono wszystkie ich wiersze w domyślnym filtrze, ★★★, wykluczenie
w ★★, reset, brak dodatkowego GET i unikalne ID wierszy.

Zakres przyszły 01.11–31.12 zwrócił 116 eventów. UI zachował puste przyszłe
GDP/PCE; nie pożyczył wcześniejszych wyników. Overview miał sześć kart,
dokładnie cztery minimalistyczne wydarzenia: ISM Manufacturing, ADP,
ISM Services i Employment Situation. Brak wcześniejszego pobrania Explain.
Brak wyjątków JS, console.error i poziomego overflow. Obejrzano zrzuty
desktop EN i mobile PL. Przeglądarka odebrała 16 odpowiedzi API HTTP 200;
osobno wykonano trzy diagnostyczne GET Calendar/history, Calendar/future
i brief. Nie są to pomiary reakcji rynku ani latencji nowej publikacji.

Własny API miał `PGOPTIONS=-c default_transaction_read_only=on`.
Osobne połączenie z read_only=True potwierdziło transaction_read_only=on
i utrzymywało advisory lock **726530019**. Count/max attempted_at
source_check_runs oraz status/publication_id koordynatora przed/po były
identyczne. Zwolniono lock i zatrzymano wyłącznie własne API/preview/Chrome.
Bez ingestion, nowych dokumentów wydawców, DDL, inicjalizacji i backfillu.

Port 8000 był zajęty przez istniejącą aplikację użytkownika; nie zatrzymywano
jej. Własny API używał 8001, preview 4178. Tylko diagnostyczny build miał
VITE_API_BASE_URL ustawione na 8001; konfiguracja projektu nie zmieniła się.
Wstępny helper wykrył kolizję 8000, następnie wymagał poprawy zmiany języka
przy nawigacji hash i dostępu do localStorage na about:blank. Poprawiono
wyłącznie ignorowaną diagnostykę i ponowiono pełny przebieg. Wcześniejszego
przebiegu z pozornymi etykietami PL nie przedstawia się jako walidacji PL.

Pierwsze nowe fixtures testowe miały błędny default import CalendarPage,
brak jawnych measures przy teście etykiet raportów oraz brak cleanup.
Poprawiono fixtures bez zmiany aplikacji, timeoutów lub usuwania asercji.

## Ochrona zastanego stanu i zakres K2

Stan początkowy: **9 modified / 3 untracked**, pusty indeks. Zapisano SHA-256
12 chronionych plików. Dziesięć zachowano byte-identycznie.
Użytkownik jawnie zatwierdził minimalny wyjątek dla dwóch testów po
ujawnieniu konfliktu z sekcją 4 zlecenia:

- CalendarPage.test.tsx: cztery asercje Claims/Minutes wymagające ★★★;
  fixture Michigan Final otrzymała poprawne medium, zachowując ★★.
- EconomyBrief.test.tsx: jedna asercja nowej noty zamiast dawnego
  pierwszeństwa Key/Tracked. Reszta wcześniejszych zmian jest zachowana.

Odtworzono pre-K2 bajty obu testów przez odwrócenie wyłącznie tych zmian;
ich SHA zgodziły się z początkiem K2. Zapisano w ignorowanej diagnostyce
wąskie patche do późniejszego oddzielenia prac. Nie dodawać całych tych
plików do przyszłego commita bez uwzględnienia wcześniejszych zmian.

| Chroniony plik | SHA-256 przed | SHA-256 po |
| --- | --- | --- |
| README.md | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` | identyczny |
| frontend/src/brief/SourceCheckStatus.tsx | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` | identyczny |
| frontend/src/brief/SourceCheckStatus.test.tsx | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` | identyczny |
| frontend/src/styles.css | `40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c` | identyczny |
| frontend/src/brief/EconomyBrief.tsx | `017f87c9f580a10c7125e14cb0415f1556c2fcaa2724295f943eef26b82dfcc1` | identyczny |
| frontend/src/brief/EconomyBrief.test.tsx | `ca7ce612e1479651a9e661be0dec3b5bb22681f2a8b60aa2dc88b24a63062a14` | `bb5c2f6adac6d3c182e893e0d58fa32ff711aee9d7722feaad0d67ad7c598ed5` — zatwierdzony wyjątek |
| frontend/src/calendar/CalendarPage.tsx | `92fe810add14ec6ba952be5fc12a8e1c2ddea7417891a98454af0a49d3d3d5c9` | identyczny |
| frontend/src/calendar/CalendarPage.test.tsx | `dad2bd206dce8e839acb4ae537e422874fe0ac03bee5c8f9a9f65e0531c2a671` | `4e62ca7c6345190a79048dfaa09dd6178e76e141f3e6695607c4eba5edf637d9` — zatwierdzony wyjątek |
| frontend/src/calendar/calendarAgenda.ts | `57c84376346095d0beb65b3535105cf21dea2221c8705c85d0e004a0d1ece5f0` | identyczny |
| docs/audits/calendar-next-releases-priority-2026-10-29.md | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` | identyczny |
| docs/audits/calendar-release-day-latency-2026-10-29.md | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` | identyczny |
| docs/audits/calendar-event-impact-audit-2026-10-30.md | `35e876926cea3c82e3b2df837876d6fb3cabd82ba55db67a4de7ad06159f6f1d` | identyczny |

**13 plików K2** (w tym dwa współdzielone pliki testów z jawnym wyjątkiem):

- `app/analytics/calendar_market_impact.py` — nowy.
- `app/analytics/release_calendar.py`.
- `app/analytics/overview_refresh.py` — wyłącznie projekcja przy odczycie.
- `frontend/src/api/macrolens.ts`.
- `frontend/src/brief/upcomingEvents.ts`.
- `frontend/src/brief/upcomingEvents.test.ts`.
- `frontend/src/brief/marketImpact.test.tsx` — nowy.
- `frontend/src/brief/__fixtures__/marketImpact.json` — nowy, tylko testy.
- `frontend/src/brief/EconomyBrief.test.tsx` — zatwierdzony wyjątek.
- `frontend/src/calendar/CalendarPage.test.tsx` — zatwierdzony wyjątek.
- `frontend/src/i18n/pl.json`.
- `tests/test_calendar_market_impact.py` — nowy.
- `docs/audits/calendar-event-impact-policy-k2-2026-11-02.md` — ten raport.

K1 pozostaje odrębnym, nieśledzonym artefaktem poza zakresem K2.
Logi, kopie, patche diagnostyczne, helpery, API JSON i zrzuty są ignorowane
w `data/raw/calendar-k2-2026-11-02/`. Bez sekretów, .env, bazy lub RAW wydawców
w zakresie Git. Końcowy status poniżej obejmuje także wcześniejsze prace.

**15 modified / 8 untracked**:

```text
 M README.md
 M app/analytics/overview_refresh.py
 M app/analytics/release_calendar.py
 M frontend/src/api/macrolens.ts
 M frontend/src/brief/EconomyBrief.test.tsx
 M frontend/src/brief/EconomyBrief.tsx
 M frontend/src/brief/SourceCheckStatus.test.tsx
 M frontend/src/brief/SourceCheckStatus.tsx
 M frontend/src/brief/upcomingEvents.test.ts
 M frontend/src/brief/upcomingEvents.ts
 M frontend/src/calendar/CalendarPage.test.tsx
 M frontend/src/calendar/CalendarPage.tsx
 M frontend/src/calendar/calendarAgenda.ts
 M frontend/src/i18n/pl.json
 M frontend/src/styles.css
?? app/analytics/calendar_market_impact.py
?? docs/audits/calendar-event-impact-audit-2026-10-30.md
?? docs/audits/calendar-event-impact-policy-k2-2026-11-02.md
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
?? docs/audits/calendar-release-day-latency-2026-10-29.md
?? frontend/src/brief/__fixtures__/
?? frontend/src/brief/marketImpact.test.tsx
?? tests/test_calendar_market_impact.py
```

Indeks pusty, main/HEAD bez zmian. Nie wykonano reset, clean, amend,
zmiany historii, stagingu, commita lub pusha.

## Granice wyniku

Oceny są własną zatwierdzoną polityką redakcyjną MacroLens ex ante,
nie oficjalnym ratingiem Investing, FRED lub wydawcy i nie modelem
wytrenowanym na reakcjach S&P 500/Nasdaq. Trzy gwiazdki nie przewidują
kierunku lub wielkości ruchu. Nie zintegrowano konsensusu/Forecast,
nowych rodzin C, Statement ani dodatkowych danych.
Pozostają current-vintage/captured snapshot, brak pełnych first printów
i gwarancji dostępności w sekundę publikacji. Nie deklaruje się sukcesu
przyszłego CI ani gotowości publicznej aplikacji.

## Kontrola zamknięcia K2 — 02.11.2026

Ponownie potwierdzono `main`, bazowy HEAD
`b89f744fe7c41f22203cf7ef59e3140367dfb53a`, **15 modified / 8 untracked**
i pusty początkowy indeks. Porównano wszystkie 12 bieżących SHA-256 ze
stanem po implementacji K2. Nie znaleziono dalszych zmian użytkownika.
Przejrzano cały zakres 13 plików, wszystkie reguły, API i cache projection,
frontend, fixture, testy oraz staged diff. Kod produkcyjny nie wymagał
poprawek podczas zamknięcia. Nadal dokładnie sześć rodzajów zmienia 2 → 3,
23 pozostają bez zmian, wynik wynosi 17/11/1, a wersja to `2026-11-k2-v1`.

W istniejącym teście liczników dopisano niezależną, ręcznie sprawdzoną
asercję zaakceptowanego zestawu 29 par rule_id/rating i literalnej wersji.
Nie jest generowana z fixture lub produkcyjnej tabeli. Wspólny błąd obu
tych źródeł naruszający zatwierdzony kontrakt ma teraz osobne zabezpieczenie.
Nie dodano drugiej tabeli runtime, nie zmieniono liczby 40 regresji K2
i nie osłabiono wcześniejszych asercji.

Faktyczny plik fixture ma **1057 linii**, a nie 941 podane w poleceniu
zamknięcia; nadal zawiera dokładnie 29 przypadków. Treść fixture nie
wymagała zmiany. Jej jedynymi importerami TS są dwa pliki testów, a Python
porównuje ją z polityką. Rzeczywisty graf Rollup kopii indeksu zawiera
483 moduły w wynikowych chunkach: brak fixture i modułów testowych.
Overview oraz Explain pozostają osobnymi chunkami lazy. Nie zmieniano H2,
Vite, progu ostrzeżenia, dependencies, lockfile lub konfiguracji workflow.

Poprawiono dokumentacyjne znaki zastępcze w tabelach. Lokalny raport K1
pozostaje poza indeksem i nie ma już prowadzącego do niego martwego linku.
Samodzielne podsumowanie sześciu decyzji i pełny inwentarz pozostają w K2.

### Izolacja dwóch współdzielonych testów

Przygotowano nowy minimalny patch względem **HEAD**, a nie pełnego working
tree. Ignorowane patche z implementacji były jedynie materiałem kontrolnym.
Zweryfikowano też niezależnie: zachowany pre-K2 plik + dokładnie uzgodnione
zamiany = aktualny working tree. Nie nadpisywano plików roboczych.

Indeks EconomyBrief.test.tsx różni się od HEAD **jedną asercją noty**.
Indeks CalendarPage.test.tsx różni się **czterema asercjami Claims/Minutes
i jednym ustawieniem importance w fixture Michigan Final**. Zastosowano
`git apply --cached`, bez dodawania całych współdzielonych plików.
Otrzymane bloby porównano z niezależnie wyliczoną zawartością HEAD + K2.

Unstaged diff nadal zawiera wcześniejsze prace: minimalistyczne wydarzenia,
usunięcie odległego FOMC z ekranu i zachowanie atrybucji w eksporcie w teście
Overview; poprzedni tydzień EN/PL i jego asercje dat w teście Calendar.
Ich powiązane komponenty, README, SourceCheckStatus i CSS są poza indeksem.
Wszystkie 12 sprawdzanych plików roboczych zachowało dokładne bajty z wejścia
do zamknięcia, również oba częściowo staged testy. Ich bieżące hashe to
kolumna „po” w tabeli ochrony powyżej; historyczna kolumna „przed” odnosi
się do początku implementacji K2, nie do początku zamknięcia.

### Nowa walidacja working tree i staging-only

Wyeksportowano **cały indeks — 294 śledzone pliki** do odrębnego katalogu.
Każdy plik porównano z blobem Git. Kopia zawiera HEAD oraz dokładny patch
indeksu, bez `.env`, RAW i trzech nieśledzonych wcześniejszych audytów,
w tym K1. Korzysta z wersji chronionych komponentów/CSS/README z HEAD
oraz dwóch testów z nałożonymi wyłącznie hunkami K2. Nie zastąpiono jej
testami working tree. Współdzielono wyłącznie istniejące node_modules;
źródła i fixtures pochodzą z eksportu indeksu.

| Nowa kontrola zamknięcia | Working tree | Dokładny indeks |
| --- | --- | --- |
| Pełny backend offline | **1163 passed**, 51,28 s | **1163 passed**, 65,49 s |
| Pełny frontend offline, Node 22.23.4 | **646 passed / 27 plików**, 45,92 s | **644 passed / 27 plików**, 29,95 s |
| Osobny TypeScript typecheck | passed | passed |
| Production build | passed | passed |
| Największy chunk raw / gzip, Node/zlib poziom 6 | **407007 / 120820 B** | **407007 / 120820 B** |

Różnica dwóch testów wynika wyłącznie z wcześniejszego, parametryzowanego
testu „previous week” EN/PL pozostawionego poza commitem. Staging-only
zachowuje wszystkie 610 testów H2 i 34 nowe K2; nie wymuszano liczby 646.
W obu pełnych zestawach przechodzą regresje R1/R2/R3/H2, 29 tożsamości,
filtry, ranking i brak dodatkowych odświeżeń z powodu gwiazdek.
Nie pomijano testów i nie zwiększano timeoutów. Dodatkowy wcześniejszy
backend working tree również przeszedł 1163; tabela podaje końcowy przebieg
z niezależną asercją kontraktu. Ostrzeżenie Starlette/httpx nie wystąpiło
w lokalnych wynikach Windows; nie było wyciszane. Nie powtarzano lokalnie
czterech skryptów PostgreSQL ani nie deklaruje się ich sukcesu przed CI.

Node 22.23.4 pochodzi z wcześniejszej zweryfikowanej przenośnej instalacji
w ignorowanym katalogu. Nie zmieniono instalacji hosta lub zależności.
Working tree build wskazywał własne API diagnostyczne na 8001; build indeksu
korzystał z domyślnego 8000. To wyłącznie zmienna środowiska procesu buildu,
bez zmiany kodu klienta lub konfiguracji. Żaden chunk nie przekracza 500 kB.

### Nowy smoke rzeczywistej aplikacji

Ponownie wykonano **24 scenariusze Chrome**, EN/PL, 1366/390 px, production
build Node 22 i prawdziwe lokalne API. Sprawdzono sześć nowych ocen na
historii wrzesień–październik, default, ★★★, ★★, reset i brak dodatkowego
GET od filtrów; przyszłe puste GDP/PCE, unikalne wiersze, sześć kart
Overview, najwyżej cztery wydarzenia oraz brak przedwczesnego Explain.
Przeglądarka odebrała **16 odpowiedzi API HTTP 200**. Brak wyjątków JS,
console.error i poziomego overflow. Nie podstawiano odpowiedzi API.

Własny API miał wymuszony PostgreSQL read-only, a osobne połączenie
read_only=True potwierdziło transaction_read_only=on i utrzymywało
advisory lock 726530019. Count/max kontroli oraz status/publication_id
koordynatora przed/po były identyczne. Lock zwolniono i zatrzymano tylko
własne procesy. Nie było ingestion, backfillu, inicjalizacji, DDL lub nowych
pobrań wydawców. Actual/Previous, Forecast null, okresy, precision i źródła
pozostały nietknięte. Poprzednie 24 scenariusze w sekcji implementacji
pozostają odrębnym wynikiem, nie podstawą nowej deklaracji smoke.

### Zakres zatwierdzenia

Indeks zawiera dokładnie **13 plików K2** z listy wyżej. Sprawdzono pełny
staged diff, nazwy, wzorce sekretów, brak `.env`, RAW/cache/logów/helperów,
raportu K1, workflow, schematu i zmian zależności. Obie kontrole whitespace
przeszły. Ostrzeżenia normalizacji LF/CRLF są zwykłą normalizacją Git,
nie błędami whitespace. Końcową dokumentację uzupełniono po testach;
jej staging i kopię zsynchronizowano bez zmian walidowanego kodu.

Planowany jeden commit: **`Unify economic calendar impact ratings`**.
Przed zatwierdzeniem `origin/main` wskazywał nadal bazowy `b89f744`.
Pełny SHA, wynik zwykłego pusha oraz rzeczywisty URL i zakończone wyniki
trzech jobów zostaną podane w zewnętrznym raporcie Codexa po ich uzyskaniu.
Lokalne wyniki nie są deklaracją sukcesu przyszłego CI. Nie powstanie
osobny commit wyłącznie dla dopisania tych informacji do dokumentu.
Nie rozpoczęto kolejnego etapu i nie zmieniono pozostałych 23 ocen.
