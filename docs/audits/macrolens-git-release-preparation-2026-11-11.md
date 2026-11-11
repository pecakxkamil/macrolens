# MacroLens — audyt przygotowania lokalnych commitów

11.11.2026, Europe/Warsaw, `C:\Projects\macrolens`.

**STOP przed stagingiem i commitami. Nie spełniono wymaganej kontroli działającego
normalnego API i Vite: porty 8000 i 5173 nie nasłuchują, połączenie z API jest
odrzucane. PostgreSQL 5432 działa. Nie uruchamiano usług ani importerów w celu
obejścia tej kontroli. Nie wykonano żadnego commita, zmiany gałęzi ani pusha.**

## Stan i granice audytu

Na wejściu: main, HEAD `c42cf6c411c85a64927fe5c6b3cf98f9e906c871`,
33 modified / 78 untracked, 111 ścieżek, indeks pusty. Liczby odpowiadają
rzeczywistemu odczytowi Git, nie założeniu z wcześniejszego raportu.
Zapisano manifest SHA-256 501 zastanych plików, pełny dirty diff i status
w ignorowanym `data/raw/git-release-preparation-2026-11-11`.

Nie modyfikowano żadnego zastanego pliku aplikacji, testów, konfiguracji,
lokalnego tokenu lub planu. Jedynym nowym plikiem poza ignorowanym RAW jest
ten raport. Nie wykonano zapisu do normalnego PostgreSQL, DDL, APPLY,
aktywacji ani importu. Zapytania diagnostyczne miały wymuszone read-only.

## Ustalenia dotyczące odtwarzalności

Working tree zawiera kod wcześniej wdrożonych Calendar/UX, historii Previous,
autoryzacji F1 V2/V3 i adaptera BLS. Wszystkie 159 artefaktów obliczonego
manifestu odpowiada tokenowi version=3. Niezależne read-only SQL potwierdziło
autoryzację F1 oraz monitora Earnings i zgodność schematu z zatwierdzonym
planem BLS. W SQL jest jeden dokument `bls:employment`.

To potwierdza integralność zapisanej autoryzacji i kodu, **nie działanie
obecnie wyłączonych workerów**. Nie można dziś potwierdzić przez normalne API
sześciu Actual, 14 nowcastów, monitora i Calendar. Nie deklaruje się również
nowego automatycznego pobrania BLS ani aktywnej pętli Earnings.

Obecny HEAD nie odtwarza backendu V3. Brakuje w nim sześciu wymaganych plików:

- app/bls_employment_runtime.py
- app/database/forecast_f1_authorization_bls.py
- app/database/forecast_f1_authorization_v2.py
- app/database/install_bls_reviewed.py
- app/ingestion/bls_employment.py
- config/forecast_f1_runtime_manifest_v2.json

Trzeba także uwzględnić zmodyfikowane integracje w calendar_readings,
overview_refresh, activate_forecast_f1, forecast_f1_runtime i typach API.
Nie wolno commitować samego manifestu bez dokładnych zależności. BLS jest
wybudzany przez istniejący lifecycle Earnings i coordinator; kod pętli
Earnings jest już wersjonowany. Analiza istniejącego narzędzia zależności
objęła 533 krawędzie lokalnych importów i 469 miejsc dynamicznych odczytów,
SQL lub importów. Granicą pozostaje całe app/config, SQL, requirements i trzy
wersje bibliotek, a nie samo AST. Jawny manifest jest kompletny dla working tree.

Odkryto brak testów wdrożenia BLS w normalnym drzewie. Dokładne wersje z
zachowanej kopii review umieszczono **wyłącznie w izolowanym kandydacie**:

- tests/conftest.py — dodatkowa izolacja BLS dla niezwiązanych testów;
- tests/test_bls_employment.py — 24 przypadki adaptera;
- tests/fixtures/bls_employment_response.json — niewielki oficjalny batch offline;
- frontend/src/calendar/BlsProjection.test.tsx — cztery przypadki projekcji.

Nie instalowano tych plików w normalnym drzewie i nie zmieniano guardów.
Sama obecność testów w ignorowanym RAW nie zapewnia odtwarzalności przyszłego
commita: muszą trafić do jawnie przejrzanego zakresu razem z adapterem.

Kod można odtworzyć z kompletnego kandydata. Aktywnej produkcyjnej instancji
nie odtwarza sam Git: potrzebuje jej prawdziwych danych, lokalnych dokumentów,
łańcucha zatwierdzonych planów, policy, tokenu i dowodów. Należy przechowywać
je bezpiecznie poza repozytorium. Czysta instalacja nie otrzymuje domyślnego
uprawnienia importu; nowy target wymaga właściwej procedury i osobnej zgody.

## Walidacja i bezpieczeństwo

| Kontrola | Wynik |
|---|---|
| Pełny backend w izolowanym kandydacie | 1633 passed, 68,52 s |
| Pełny frontend zastanego working tree | 941 passed / 44 pliki, 64,38 s |
| Pełny frontend kandydata z testami BLS | 945 passed / 45 plików |
| TypeScript noEmit | passed |
| Production build normalnego frontendu | passed, Vite 4,20 s |
| Manifest backendu względem lokalnego tokenu V3 | 159/159 zgodne |
| Schemat, target, F1 i Earnings w read-only SQL | passed |
| Normalne API / Vite / runtime | BLOCKED — brak procesów i listenerów |
| Staging, gałąź i lokalne commity | niewykonane |

Nie uruchamiano walidacji SQL modyfikujących normalną bazę. Nie przedstawia
się wcześniejszych prób PG17 i Chrome z 06.11 jako nowo wykonanych.

Skan kandydatów poza wykluczonym F2: zero dopasowań do wartości lokalnych
sekretów i zero pasujących literałów poświadczeń według użytej reguły.
To ograniczony skan, nie dowód matematyczny braku sekretów. Przed stagingiem
nadal wymagany jest przegląd dokładnej zawartości indeksu. Nie tworzono
indeksu, więc nie ma diff --cached przygotowanego zakresu.

Wykluczone: całe data/raw, .env, tokeny aktywacyjne, receipts, plany normalnej
aktywacji zawierające dane środowiska, backupy, dumpy, logi, screenshoty,
.venv, node_modules i dist. .env.example zawiera przykładową konfigurację,
nie skopiowano do niego lokalnych poświadczeń. F2 nie został dodany ani
zmieniony. Mała fixture BLS w kandydacie służy testom parsera; nie jest feedem
produkcyjnym ani zamiennikiem provenance oryginalnego dokumentu.

Pierwsze próby przekierowania logów zatrzymały ograniczenia plikowe sandboxa;
nie uruchomiły testów. Powtórzono je ze zgodną konfiguracją. Pomocniczy odczyt
.env ze stdin wymagał jawnej ścieżki; powtórzony read-only SQL przeszedł.
Nie zaliczono tych nieudanych prób jako sukcesów kontroli.

## Podział przyszłych commitów i blokada

Zależności przemawiają za kolejnością: historia Earnings, autoryzacja F1 V2,
Calendar/UX oraz BLS/V3 z kompletnym manifestem i testami. F1 V1 i monitor
Earnings są już w bazowym HEAD — nie należy tworzyć pozornego ponownego commita.
Zmiany frontendu macroInsight/MacroTrend i typów BLS trzeba oddzielić od
wcześniejszego Calendar za pomocą zachowanych patchy i weryfikacji dokładnego
drzewa każdego commita. Nie wykonano selekcji hunków ani nie zadeklarowano
samodzielnej poprawności pośrednich commitów. Nie ustalono bez testu, że każdy
z proponowanych etapów da się niezależnie uruchomić.

Zgodnie z warunkiem użytkownika proces zatrzymano przed operacjami Git:
nie ma nowej gałęzi, commitów ani hashy do podania. Nie wykonano stagingu,
pusha, merge do main, reset, clean, amend, rebase, force lub formatowania.
Wszystkie wymienione dalej 111 ścieżek pozostają niezacommitowane; powód wspólny
to blokada kontroli runtime. Dodatkowo F2 jest wykluczony z zakresu, diagnostyka
i starsze audyty wymagają jawnego przypisania, a lokalne dane nigdy nie są
kandydatem do commita.

**Gałąź nie jest gotowa do pusha:** brak commitów kompletnych zależności,
niezweryfikowany runtime i niewykonane testy dokładnego przyszłego indeksu.
Po przywróceniu usług trzeba ponownie potwierdzić stan, a dopiero następnie
utworzyć roboczą gałąź i selektywne commity. Niniejszy raport nie jest zgodą
na import, ponowną aktywację, zmianę manifestu lub policy.

## Końcowy stan

Wszystkie 501 zastanych plików zachowano byte-identycznie. Usunięto tylko
własny junction node_modules w izolowanym kandydacie, zachowując docelowe
zależności. Dowody i kandydat pozostają ignorowane w katalogu audytu.
Końcowo **33 modified / 79 untracked**, pusty indeks, main/HEAD bez zmian.
Nie uruchamiano ani nie zatrzymywano normalnych usług.

## Pełna klasyfikacja zastanych zmian

Poniższy wykaz obejmuje wszystkie 111 ścieżek wejściowego statusu Git.
Nowy raport audytu jest dodatkową, 112. ścieżką statusu końcowego.

### Calendar i UX — dokumentacja (1)

- `README.md`

### BLS — backend, projekcja, integracja (11)

- `app/analytics/calendar_readings.py`
- `app/analytics/overview_refresh.py`
- `app/database/activate_forecast_f1.py`
- `app/forecast_f1_runtime.py`
- `frontend/src/api/macrolens.ts`
- `app/bls_employment_runtime.py`
- `app/database/install_bls_reviewed.py`
- `app/ingestion/bls_employment.py`
- `docs/audits/macrolens-bls-normal-activation-2026-11-06.md`
- `docs/audits/macrolens-bls-production-upgrade-preparation-2026-11-06.md`
- `docs/patches/macrolens-bls-production-upgrade-2026-11-06.patch`

### Calendar i UX — frontend/testy (51)

- `frontend/src/App.tsx`
- `frontend/src/brief/EconomyBrief.test.tsx`
- `frontend/src/brief/EconomyBrief.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/marketImpact.test.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarRefresh.test.tsx`
- `frontend/src/calendar/ComparisonTooltip.tsx`
- `frontend/src/calendar/EarningsCalendar.tsx`
- `frontend/src/calendar/EarningsDomains.test.tsx`
- `frontend/src/calendar/EarningsFinancials.test.tsx`
- `frontend/src/calendar/calendarAgenda.ts`
- `frontend/src/calendar/calendarComparisons.ts`
- `frontend/src/calendar/earnings.css`
- `frontend/src/calendar/earningsFinancialPresentation.ts`
- `frontend/src/charts/ChartsPage.test.tsx`
- `frontend/src/charts/ChartsPage.tsx`
- `frontend/src/i18n/language.test.tsx`
- `frontend/src/i18n/pl.json`
- `frontend/src/indicators/IndicatorsPage.test.tsx`
- `frontend/src/navigation/ExploreDataPage.tsx`
- `frontend/src/navigation/lazyLoading.test.tsx`
- `frontend/src/navigation/routes.test.tsx`
- `frontend/src/navigation/routes.ts`
- `frontend/src/styles.css`
- `frontend/src/calendar/MacroEconomicContext.tsx`
- `frontend/src/calendar/MacroEventCard.test.tsx`
- `frontend/src/calendar/MacroEventCard.tsx`
- `frontend/src/calendar/MacroTrend.tsx`
- `frontend/src/calendar/MissingValue.test.tsx`
- `frontend/src/calendar/MissingValue.tsx`
- `frontend/src/calendar/UnifiedCalendar.test.tsx`
- `frontend/src/calendar/UnifiedEarningsValues.test.tsx`
- `frontend/src/calendar/UnifiedEarningsValues.tsx`
- `frontend/src/calendar/changeDirection.test.tsx`
- `frontend/src/calendar/changeDirection.ts`
- `frontend/src/calendar/earningsCompanyNames.test.ts`
- `frontend/src/calendar/earningsCompanyNames.ts`
- `frontend/src/calendar/earningsComparison.ts`
- `frontend/src/calendar/macroEventCard.css`
- `frontend/src/calendar/macroInsight.ts`
- `frontend/src/calendar/macroInsightFamilies.ts`
- `frontend/src/calendar/macroInsights.test.ts`
- `frontend/src/calendar/macroMarketProfiles.test.ts`
- `frontend/src/calendar/macroMarketProfiles.ts`
- `frontend/src/calendar/macroTrendData.ts`
- `frontend/src/calendar/unifiedCalendar.css`
- `frontend/src/calendar/unifiedCalendar.ts`
- `frontend/src/calendar/useEarningsCalendar.ts`

### F1 — autoryzacja V2/V3 i dokumentacja (9)

- `app/database/forecast_f1_authorization_bls.py`
- `app/database/forecast_f1_authorization_v2.py`
- `config/forecast_f1_runtime_manifest_v2.json`
- `docs/audits/macrolens-calendar-ui-f1-authorization-completed-2026-11-05.md`
- `docs/audits/macrolens-calendar-ui-f1-authorization-final-2026-11-05.md`
- `docs/audits/macrolens-forecast-f1-activation-completed-2026-11-05.md`
- `docs/audits/macrolens-forecast-f1-ui-authorization-plan-2026-11-05.md`
- `docs/patches/macrolens-calendar-ui-f1-authorization-v2-2026-11-05.patch`
- `tests/test_forecast_f1_authorization_v2.py`

### Dokumentacja historyczna — wymaga przypisania do zakresu (16)

- `docs/audits/calendar-event-impact-audit-2026-10-30.md`
- `docs/audits/calendar-next-releases-priority-2026-10-29.md`
- `docs/audits/calendar-release-day-latency-2026-10-29.md`
- `docs/audits/equity-earnings-calendar-source-audit-2026-11-02.md`
- `docs/audits/equity-earnings-previous-activation-completed-2026-11-04.md`
- `docs/audits/equity-earnings-previous-activation-v2-completed-2026-11-04.md`
- `docs/audits/macrolens-calendar-all-six-columns-2026-11-05.md`
- `docs/audits/macrolens-calendar-direction-colors-2026-11-06.md`
- `docs/audits/macrolens-calendar-event-insights-2026-11-06.md`
- `docs/audits/macrolens-calendar-market-context-axes-2026-11-06.md`
- `docs/audits/macrolens-calendar-ui-cleanup-2026-11-05.md`
- `docs/audits/macrolens-calendar-unified-all-2026-11-05.md`
- `docs/audits/macrolens-forecast-f2-2026-11-05.md`
- `docs/audits/macrolens-ui-readability-2026-11-06.md`
- `docs/audits/macrolens-unified-earnings-values-2026-11-06.md`
- `docs/patches/macrolens-calendar-ui-cleanup-2026-11-05.patch`

### Earnings — historia Previous (9)

- `docs/audits/equity-earnings-previous-backfill-completed-2026-11-06.md`
- `docs/audits/equity-earnings-previous-backfill-readiness-2026-11-05.md`
- `integrations/earnings_history_backfill/README.md`
- `integrations/earnings_history_backfill/__init__.py`
- `integrations/earnings_history_backfill/__main__.py`
- `integrations/earnings_history_backfill/activation.py`
- `integrations/earnings_history_backfill/reviewed.json`
- `tests/postgres_earnings_history_backfill_validation.py`
- `tests/test_earnings_history_backfill.py`

### Diagnostyka NFP — poza produkcyjnym adapterem (3)

- `docs/audits/macrolens-nfp-missing-actuals-2026-11-06.md`
- `integrations/nfp_release_diagnostics.py`
- `tests/test_nfp_release_diagnostics.py`

### F2 — wykluczone, nieaktywne (11)

- `integrations/forecast_f2/README.md`
- `integrations/forecast_f2/__init__.py`
- `integrations/forecast_f2/__main__.py`
- `integrations/forecast_f2/businessquant.py`
- `integrations/forecast_f2/local.env.example`
- `integrations/forecast_f2/policy.example.json`
- `integrations/forecast_f2/store.py`
- `integrations/forecast_f2/worker.py`
- `tests/fixtures/forecast_f2/estimates.json`
- `tests/postgres_forecast_f2_validation.py`
- `tests/test_forecast_f2.py`
