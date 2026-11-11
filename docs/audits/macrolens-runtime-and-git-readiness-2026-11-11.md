# MacroLens — runtime i gotowość do selektywnych commitów

11.11.2026, Europe/Warsaw, `C:\Projects\macrolens`, main,
HEAD `c42cf6c411c85a64927fe5c6b3cf98f9e906c871`.

**READY FOR COMMITS — dla dokładnego zakresu i kolejności opisanych poniżej.
Normalne API i Vite działają. Nie wykonano stagingu, commita, merge, pusha
ani zmiany gałęzi. F2 oraz lokalne dane pozostają poza proponowanymi commitami.**

## Uruchomienie normalnego środowiska

Poprzedni brak odpowiedzi wynikał z braku uruchomionych procesów FastAPI
i Vite. Użytkownik potwierdził, że po otwarciu VS Code/Dockera ich nie
uruchamiał. Ponowna kontrola wykazała wolne porty 8000/5173, działający
kontener `macrolens_postgres`, obraz postgres:17, port 5432. Zwykły startup
przeszedł bez błędu — nie była potrzebna naprawa kodu.

Uruchomiono zapisane wcześniej komendy, z normalną konfiguracją projektu:

```powershell
# cwd C:\Projects\macrolens
.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
# cwd C:\Projects\macrolens\frontend
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Procesy uruchomiono w tle, z logami w ignorowanym katalogu etapu.
API shim PID 14400, reloader 36324, worker 9476; Vite PID 30044.
Nie uruchamiano duplikatów ani nie zatrzymywano obcych procesów.
Normalny target potwierdzono read-only: localhost:5432/macrolens, PG17,
macrolens, OID 16384, system_identifier 7682090371041935398.

Nie wykonano DDL, APPLY, ręcznego importu, resetowania bazy ani zmiany
tokenu/policy. Wszystkie diagnostyczne zapytania SQL były read-only.
Uruchomienie zwykłego lifecycle pozwoliło istniejącym autoryzowanym workerom
pracować: nie deklaruje się niezmienności całej działającej bazy.

## Normalne API, UI i dane

F1, monitor Earnings, Calendar oraz Earnings API odpowiedziały HTTP 200.
Pierwsze pomiary: odpowiednio około 0,02 / 0,03 / 0,80 / 0,11 s.

| Employment Situation za październik, 06.11 | Actual | Previous |
|---|---:|---:|
| NFP | 165 tys. | 60 tys. |
| U-3 | 4,1% | 4,2% |
| Wynagrodzenia godzinowe m/m | 0,4% | 0,3% |
| Aktywność zawodowa | 61,9% | 61,8% |
| U-6 | 7,9% | 7,6% |
| Tygodniowy czas pracy | 34,4 godz. | 34,4 godz. |

Każdą parę sprawdzono w prawdziwym API oraz Wszystko i Dane, osobno w PL/EN,
1366/390 px. Źródłem wybranym przez projekcję jest zachowany snapshot BLS,
capture 06.11 16:23:32 PL, SHA e60010…475dd. Previous jest z tego samego
dokumentu; NFP delta +105 tys., U-3 −0,1 pkt proc., AHE +0,1 pkt proc.,
aktywność +0,1 pkt proc., U-6 +0,3 pkt proc., godziny 0. Kolory odpowiadają
znakowi liczbowemu. Nie zmieniano danych, formuł ani UI.

FRED udostępnia już październik: alternatywa API ma NFP 165/60, wersję
06.11, as_of 11.11. Nie cofano jej do starego stanu. Osobny read-only SQL
potwierdził historyczne ALFRED 02.10: 159044−159015=**29 tys.**
Pozostaje ono zachowane w observation_vintages. Gdy bieżące FRED i BLS mają
ten sam Previous 60, UI nie pokazuje już wcześniejszego porównania 29/60;
zachowuje informację o jednym capture BLS i możliwych rewizjach.

Chrome: **87 kontroli, 24 odpowiedzi normalnego API HTTP 200** oraz cztery
odpowiedzi modułu Vite src/api/macrolens.ts HTTP 200, zero błędów JS,
console.error, HTTP 503 i żądań przeglądarki do dostawców. Sprawdzono
sześć/osiem kolumn Wszystko/Dane, źródło, dziewięć punktów wykresu NFP,
wartości, datę/godzinę, kolory, siedem kolumn Wyniki, osiem wydarzeń,
guidance NVIDIA, Market Cap, szczegóły i brak overflow. Obejrzano desktop PL
oraz mobilny wykres EN. Nie jest to pełny audyt WCAG.

Oddzielna obserwacja przez 70 sekund bez nawigacji potwierdziła **dwa GET
Earnings**, zachowaną zakładkę i liczbę wierszy. Nie wywoływano ręcznie POST
odświeżania; pozostawiono zwykłe zachowanie działającego frontendu.

## Forecast F1 V3 i Earnings

Manifest **159/159** zgodny z istniejącym tokenem version=3. Read-only SQL
potwierdził pełną autoryzację F1, monitora Earnings i zgodność schematu z
zatwierdzonym planem. Wszystkie 13 produkcyjnych plików dostawy BLS ma nadal
dokładne zatwierdzone bajty. Nie modyfikowano backendu lub manifestu.

F1 API: registered=true, activated=true, cooldown. Istniejący worker
przeprowadził poprawne odświeżenie Cleveland 11.11, po czym zachował cooldown.
Store zawiera obecnie **48 vintages: 44 nowcast i cztery guidance**.
Każdy z **20 pierwotnych payloadów** porównano z SQL i potwierdzono zachowanie.
Nie są to 48 odrębnych konsensusów.

W zakresie listopad–grudzień obecne API/UI pokazuje **10 bieżących nowcastów**.
Cztery CPI/Core CPI z datą 10.11 mają forecast_status
`release_cutoff_unconfirmed_or_passed`; nie są już aktualnymi prognozami.
Ich Actual pozostaje null w zastanym API. Nie zmieniano cutoff ani nie
rozszerzano tego zadania o naprawę innych publikacji. Nie deklaruje się
dzisiejszych 14 widocznych nowcastów na podstawie raportu z 06.11.

Earnings API: activated=true, loop_running=true, completed. Rzeczywisty
last_tick przesunął się z 12:10:23 do 12:15:23 PL. To istniejący zegar,
nie ręczny import lub nowy scheduler. BLS korzysta z zarejestrowanego
listenera tego lifecycle; nie wymuszano nowego HTTP poza oknem publikacji.
Nie jest to dowód pobrania przyszłego, jeszcze nieopublikowanego raportu.

Przykłady prawdziwego Earnings API, USD:

| Spółka | EPS / Previous | Revenue / Previous |
|---|---|---|
| AAPL Q4 FY2026 | 2,10 / 2,02 | 114 477 mln / 109 417 mln |
| AMD Q3 2026 | 1,46 / 1,38 | 13 377 mln / 11 536 mln |
| ARM Q2 FY2027 | 0,12 / 0,25 | 1 443 mln / 1 289 mln |
| QCOM Q4 FY2026 | 1,17 / 1,87 | 10 322 mln / 9 947 mln |

Market Cap zachowuje istniejące verified_snapshot tam, gdzie był dostępny
(np. AAPL/AMD/QCOM); ARM nadal ma null/not_activated. Nie pobierano ręcznie
kapitalizacji i nie uzupełniano null. F2 pozostaje nieaktywny.

## Uzupełnione testy i świeża walidacja

Z przejrzanej kopii `data/raw/bls-production-upgrade-2026-11-06/review`
przeniesiono dokładnie:

- tests/conftest.py — osiem dopisanych linii izolacji BLS dla innych testów;
  wcześniejszą zawartość i guard rzeczywistego HTTP/SQL zachowano;
- tests/test_bls_employment.py — 24 przypadki adaptera, projekcji, transportu,
  rewizji, wybudzania oraz pobrania przy niezmienionych metadanych;
- tests/fixtures/bls_employment_response.json — 6189 B, oryginalny oficjalny
  anonimowy batch sześciu serii, zachowany do testu offline;
- frontend/src/calendar/BlsProjection.test.tsx — cztery przypadki pochodzenia,
  Previous/revizji i wykresu jednej odpowiedzi.

Fixture nie zawiera konta, klucza ani danych prywatnych. Zachowano jej bajty
i pochodzenie; test nie przedstawia jej jako feedu produkcyjnego.
Nie kopiowano planów, tokenów, receipts, backupów lub pełnych HTML/PDF.

| Świeża kontrola | Wynik |
|---|---|
| Pełny backend ze zwykłego repozytorium | **1633 passed**, 66,21 s |
| Pełny frontend ze zwykłego repozytorium | **945 passed / 45 plików**, 62,90 s |
| TypeScript noEmit | passed |
| Production build | passed, Vite 4,83 s, największy chunk 407,05 kB |
| Manifest, schemat i autoryzacje read-only | passed |
| Chrome normalnego API/Vite, PL/EN desktop/mobile | 87 kontroli, passed |
| Rzeczywisty polling Calendar | passed, 70 s |
| Czysty eksport HEAD + proponowane pliki, bez F2/diagnozy NFP | **1586 backend passed**, 59,12 s |
| Ten sam czysty eksport: frontend/typecheck/build | **945 passed / 45**, 55,14 s; tsc/build passed |
| Samodzielne drzewo pierwszego commita, backend | **1576 passed**, 57,32 s |
| git diff --check | passed |

Nie przedstawia się testów z poprzedniego audytu jako nowych. Czysty eksport
nie zawiera .env, produkcyjnych danych RAW, tokenów lub sekretów. Zależności
Node udostępniono przez własny junction do istniejącego node_modules; nie
wykonano świeżego pobrania pakietów z Internetu. requirements, package.json
i lockfile pozostają wersjonowane i niezmienione. Nie deklaruje się testu
nowego systemu operacyjnego lub GitHub Actions.

Pierwszy helper Chrome z 06.11 zatrzymały dwa nieaktualne oczekiwania:
widoczny tekst 29/60 oraz dokładnie 14 aktualnych nowcastów. Przed zmianą
helpera sprawdzono SQL/API: first print zachowany, FRED dogonił BLS,
liczba prognoz zmieniła się przez cutoff i normalne rewizje. Poprawiono
wyłącznie helper; rzeczywiste wartości sześciu BLS i test SQL 29 pozostały
obowiązkowe. Pełny Chrome powtórzono. Nie zmieniano zegara aplikacji, danych
ani guardów w celu uzyskania sukcesu.

## Zależności, bezpieczeństwo i odtwarzalność

Audyt obejmuje wszystkie modified/untracked. Wymagane importy app/config
pozostają w jawnym manifeście. Czysty proponowany zakres zawiera wszystkie
sześć brakujących w HEAD plików backendu/manifestu V3, testy i konfiguracje.
Historia Earnings zależy od modułu autoryzacji V2 — dlatego jest proponowana
po commicie backendu. Testy całego czystego zakresu przeszły bez F2 i bez
diagnostycznego integrations/nfp_release_diagnostics.py.

Nie ma zależności kodu wykonywalnego od ignorowanej kopii `review` lub
narzędzi przygotowania z RAW. Istnieją **zamierzone zależności od lokalnych
danych/autoryzacji**: runtime token, oryginały dokumentów, dowody kalendarza
i wymagany przez autoryzację seed.raw_path. Pozostają one poza Git. W repo
nie wolno ich zastępować fixture lub wbudowaną aktywacją. Czyste środowisko
odtwarza kod i testy; odtworzenie aktywnej instancji wymaga bezpiecznego
backupu danych i autoryzacji albo odrębnie zatwierdzonej inicjalizacji.

Skan dokładnego proponowanego zakresu nie znalazł dopasowań do lokalnych
sekretów ani podejrzanych literałów poświadczeń według zastosowanej reguły.
Nie jest to gwarancja absolutna; przed przyszłym commitem należy ponownie
sprawdzić dokładny diff indeksu. Maszynowy wykaz ścieżek/SHA, wynik skanu,
odczyty i dowody są w ignorowanym katalogu etapu.

Wykluczone bezwarunkowo: data/raw, .env, aktywacyjne tokeny, backupy,
dumpy, receipts, logi, screenshoty, profile Chrome, .venv, node_modules,
dist oraz lokalne konfiguracje IDE. Raporty i patche do przeglądu zawierają
informacje o targetach/hashach, nie poświadczenia lub tokeny wykonawcze.
Nie wolno zastępować przeglądu źródeł mechanicznym git add całego drzewa.

## Proponowana kolejność commitów

### Wymagane zachowanie bajtów podczas checkout

Kontrola czystego eksportu wykryła dodatkową różnicę: repo ma
`core.autocrlf=true`, a manifest F1 obejmuje dokładne bajty. Domyślny eksport
zmieniał końce linii 66 plików względem aktywnego working tree. Same zielone
testy funkcjonalne nie wykrywałyby utraty takiej autoryzacji po checkout.

Dodano **wyłącznie .gitattributes** z jawnymi regułami dla wszystkich 156
chronionych ścieżek. Jednolite pliki mają przypięte eol=lf albo eol=crlf,
zgodne z działającą wersją. Trzy już istniejące pliki o mieszanych końcach
linii mają -text i muszą być zapisane w przyszłym commicie verbatim:

- app/analytics/overview_refresh_store.py
- app/database/overview_refresh.sql
- app/ingestion/request_budget.py

Nie zmieniono ich bajtów, nie formatowano ani nie normalizowano kodu.
Są dodatkowym zakresem pierwszego commita wyłącznie dla dokładnego zapisu
Git. Dla tych trzech ścieżek przyszły selektywny staging powinien jawnie
przeliczyć reguły atrybutów (np. git add --renormalize z dokładnie tymi trzema
nazwami, po osobnej kontroli); nie wykonywać renormalizacji całego drzewa.
Zwykły status może nadal korzystać z wcześniejszego cache stat dla tych
niezmienionych plików. Nie pomijać ich dlatego, że nie są oznaczone jako M.

Bez stagingu sprawdzono filtry Git dla **156/156** ścieżek oraz rzeczywisty
git cat-file --filters dla 143 niezmienionych plików HEAD: odtwarzają
zatwierdzone bajty. Pozostałe 13 ścieżek manifestu należy do proponowanego
zakresu backendu, w tym trzy pliki verbatim; są objęte listą commita
i kontrolą SHA. Kandydat do odtworzenia zawiera teraz dokładny
manifest aktywnego backendu. Nie zmieniano requirements.txt lub manifestu.

Dla nowej instalacji trzy biblioteki związane autoryzacją wymagają wersji
z obecnego środowiska: httpx 0.28.1, psycopg 3.2.13, pypdf 6.21.2. Należy
je przypiąć przy instalacji obok requirements.txt, a frontend instalować
z package-lock przez npm ci. Tego audytu nie należy traktować jako testu
najnowszych wersji bibliotek dopuszczanych przez dolne ograniczenia requirements.

**To propozycja, nie staging ani autoryzacja wykonania w tym etapie.**
Dokładne listy plików podano poniżej. Bez zmiany zawartości można użyć
pełnych plików w tym podziale; nie trzeba odtwarzać niezależnych hunków.

1. `Add guarded F1 V3 authorization and BLS employment ingestion`.
   Razem backend F1 V2/V3, BLS, manifest, wymagane typy API i testy backendu.
   Oddzielenie manifestu od jego modułów byłoby niebezpieczne. Czyste drzewo
   pierwszego commita przygotowano i sprawdzono osobno. Bezpieczny jako
   pierwszy lokalny commit po ponownej kontroli hasha/indeksu; nie aktywuje
   bazy ani nie zastępuje procedury wdrożeniowej.
2. `Add reviewed append-only earnings history backfill`.
   Importer siedmiu raportów, ledger, CLI, testy i dwa audyty. Wymaga commita 1
   ze względu na import forecast_f1_authorization_v2. Nie importuje danych
   podczas startupu. Bezpieczny po 1, nie jest zgodą na ponowny APPLY.
3. `Improve unified calendar and data exploration presentation`.
   Cały ukończony frontend, jego testy, README i odpowiednie audyty. Obejmuje
   również prezentację pochodzenia BLS i BlsProjection; opcjonalne typy
   dostarcza 1. Zachowuje wcześniejsze poprawki Przeglądu i Eksploracji.
   Bezpieczny po 1/2; cały finalny zakres frontendowy został przetestowany.
4. `Document verified activation history and release readiness`.
   Pozostałe audyty/patch BLS i autoryzacji oraz ten raport. Bezpieczny po
   poprzednich; żadnych RAW, tokenów i kopii dokumentów dostawców.

Zmieszane zmiany F1/BLS pozostają celowo razem w 1, a kolejne poprawki UI
w 3. Nie proponuje się ryzykownego odcinania połowy manifestu lub wspólnego
komponentu. Przed faktycznym commitem trzeba zapisać listę ścieżek,
git diff --cached --stat, pełny diff oraz kontrolę bezpieczeństwa. W razie
nowych bajtów lub zmian użytkownika konieczny jest ponowny przegląd.

## Końcowy stan i ograniczenia

Usługi pozostawiono działające pod http://127.0.0.1:8000 oraz
http://127.0.0.1:5173/#/calendar. Własny Chrome 9357 zakończono po kontroli
PID/argumentów; nie zamykano przeglądarki użytkownika. Własny junction
w kandydacie usunięto bez naruszania docelowych zależności.

Z 502 zastanych plików zmieniono tylko tests/conftest.py przez opisany
dodatek; **501 pozostało byte-identyczne**, w tym produkcyjny backend,
wcześniejsze UI, chronione prace i całe F2. Dodano trzy brakujące pliki
testów/fixture, .gitattributes oraz ten raport. Wszystkie 13 plików dostawy
produkcyjnej V3 zachowuje dotychczasowe, zatwierdzone bajty.

Git końcowo: **34 modified / 84 untracked**, indeks pusty, main i HEAD bez
zmian. Nie wykonano stagingu, commita, merge, pusha, reset, clean, amend,
rebase, force, nowej gałęzi ani globalnego formatowania.

**READY FOR COMMITS** oznacza gotowy, zweryfikowany zakres kodu do
selektywnego utrwalenia; nie oznacza już utworzonych commitów, przetestowanego
przyszłego SHA w CI ani zgody na publikację. Brak blokera dla przygotowania
tych commitów. Znane ograniczenia danych (m.in. cutoff CPI/null Actual,
niepełny Market Cap) zostały zachowane i nie są maskowane fikcyjnymi wartościami.

## Dokładne listy plików

Poniższy wykaz wraz z wykluczeniami klasyfikuje wszystkie ścieżki końcowego
statusu Git oraz trzy opisane pliki verbatim, które były już wersjonowane
i nie zmieniły bajtów. Pozostałe niezmienione pliki, np. requirements
i package-lock, nie wymagają ponownego dodawania.

### 1. F1 V2/V3 + BLS + integralnosc checkout (19 sciezek)

- `.gitattributes`
- `app/analytics/calendar_readings.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/overview_refresh_store.py`
- `app/bls_employment_runtime.py`
- `app/database/activate_forecast_f1.py`
- `app/database/forecast_f1_authorization_bls.py`
- `app/database/forecast_f1_authorization_v2.py`
- `app/database/install_bls_reviewed.py`
- `app/database/overview_refresh.sql`
- `app/forecast_f1_runtime.py`
- `app/ingestion/bls_employment.py`
- `app/ingestion/request_budget.py`
- `config/forecast_f1_runtime_manifest_v2.json`
- `frontend/src/api/macrolens.ts`
- `tests/conftest.py`
- `tests/fixtures/bls_employment_response.json`
- `tests/test_bls_employment.py`
- `tests/test_forecast_f1_authorization_v2.py`

### 2. Earnings history backfill (9 sciezek)

- `docs/audits/equity-earnings-previous-backfill-completed-2026-11-06.md`
- `docs/audits/equity-earnings-previous-backfill-readiness-2026-11-05.md`
- `integrations/earnings_history_backfill/README.md`
- `integrations/earnings_history_backfill/__init__.py`
- `integrations/earnings_history_backfill/__main__.py`
- `integrations/earnings_history_backfill/activation.py`
- `integrations/earnings_history_backfill/reviewed.json`
- `tests/postgres_earnings_history_backfill_validation.py`
- `tests/test_earnings_history_backfill.py`

### 3. Calendar, Przeglad i Eksploracja UI (66 sciezek)

- `README.md`
- `docs/audits/calendar-event-impact-audit-2026-10-30.md`
- `docs/audits/calendar-next-releases-priority-2026-10-29.md`
- `docs/audits/calendar-release-day-latency-2026-10-29.md`
- `docs/audits/equity-earnings-calendar-source-audit-2026-11-02.md`
- `docs/audits/macrolens-calendar-all-six-columns-2026-11-05.md`
- `docs/audits/macrolens-calendar-direction-colors-2026-11-06.md`
- `docs/audits/macrolens-calendar-event-insights-2026-11-06.md`
- `docs/audits/macrolens-calendar-market-context-axes-2026-11-06.md`
- `docs/audits/macrolens-calendar-ui-cleanup-2026-11-05.md`
- `docs/audits/macrolens-calendar-unified-all-2026-11-05.md`
- `docs/audits/macrolens-ui-readability-2026-11-06.md`
- `docs/audits/macrolens-unified-earnings-values-2026-11-06.md`
- `docs/patches/macrolens-calendar-ui-cleanup-2026-11-05.patch`
- `frontend/src/App.tsx`
- `frontend/src/brief/EconomyBrief.test.tsx`
- `frontend/src/brief/EconomyBrief.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/marketImpact.test.tsx`
- `frontend/src/calendar/BlsProjection.test.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarRefresh.test.tsx`
- `frontend/src/calendar/ComparisonTooltip.tsx`
- `frontend/src/calendar/EarningsCalendar.tsx`
- `frontend/src/calendar/EarningsDomains.test.tsx`
- `frontend/src/calendar/EarningsFinancials.test.tsx`
- `frontend/src/calendar/MacroEconomicContext.tsx`
- `frontend/src/calendar/MacroEventCard.test.tsx`
- `frontend/src/calendar/MacroEventCard.tsx`
- `frontend/src/calendar/MacroTrend.tsx`
- `frontend/src/calendar/MissingValue.test.tsx`
- `frontend/src/calendar/MissingValue.tsx`
- `frontend/src/calendar/UnifiedCalendar.test.tsx`
- `frontend/src/calendar/UnifiedEarningsValues.test.tsx`
- `frontend/src/calendar/UnifiedEarningsValues.tsx`
- `frontend/src/calendar/calendarAgenda.ts`
- `frontend/src/calendar/calendarComparisons.ts`
- `frontend/src/calendar/changeDirection.test.tsx`
- `frontend/src/calendar/changeDirection.ts`
- `frontend/src/calendar/earnings.css`
- `frontend/src/calendar/earningsCompanyNames.test.ts`
- `frontend/src/calendar/earningsCompanyNames.ts`
- `frontend/src/calendar/earningsComparison.ts`
- `frontend/src/calendar/earningsFinancialPresentation.ts`
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

### 4. Audyty i gotowosc wydania (13 sciezek)

- `docs/audits/equity-earnings-previous-activation-completed-2026-11-04.md`
- `docs/audits/equity-earnings-previous-activation-v2-completed-2026-11-04.md`
- `docs/audits/macrolens-bls-normal-activation-2026-11-06.md`
- `docs/audits/macrolens-bls-production-upgrade-preparation-2026-11-06.md`
- `docs/audits/macrolens-calendar-ui-f1-authorization-completed-2026-11-05.md`
- `docs/audits/macrolens-calendar-ui-f1-authorization-final-2026-11-05.md`
- `docs/audits/macrolens-forecast-f1-activation-completed-2026-11-05.md`
- `docs/audits/macrolens-forecast-f1-ui-authorization-plan-2026-11-05.md`
- `docs/audits/macrolens-git-release-preparation-2026-11-11.md`
- `docs/audits/macrolens-nfp-missing-actuals-2026-11-06.md`
- `docs/audits/macrolens-runtime-and-git-readiness-2026-11-11.md`
- `docs/patches/macrolens-bls-production-upgrade-2026-11-06.patch`
- `docs/patches/macrolens-calendar-ui-f1-authorization-v2-2026-11-05.patch`

### Poza commitami: F2 i diagnostyczny prototyp NFP

- `docs/audits/macrolens-forecast-f2-2026-11-05.md`
- `integrations/forecast_f2/README.md`
- `integrations/forecast_f2/__init__.py`
- `integrations/forecast_f2/__main__.py`
- `integrations/forecast_f2/businessquant.py`
- `integrations/forecast_f2/local.env.example`
- `integrations/forecast_f2/policy.example.json`
- `integrations/forecast_f2/store.py`
- `integrations/forecast_f2/worker.py`
- `integrations/nfp_release_diagnostics.py`
- `tests/fixtures/forecast_f2/estimates.json`
- `tests/postgres_forecast_f2_validation.py`
- `tests/test_forecast_f2.py`
- `tests/test_nfp_release_diagnostics.py`

Powody: F2 pozostaje nieaktywnym, osobnym zakresem; diagnostyczny parser NFP
nie jest zaleznoscia produkcyjnego adaptera. Zachowano wszystkie te pliki.
