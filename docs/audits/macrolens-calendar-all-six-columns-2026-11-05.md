# MacroLens — sześć kolumn we wspólnym Wszystko

05.11.2026, Europe/Warsaw, C:\Projects\macrolens, main,
HEAD c42cf6c411c85a64927fe5c6b3cf98f9e906c871.

**Zmiana działa bezpośrednio na http://127.0.0.1:5173/#/calendar.**
Wszystko ma dokładnie sześć kolumn:
Godzina | Wydarzenie | Ważność | Aktualny | vs poprzedni | Poprzednio.
EN: Time | Event | Importance | Actual | vs previous | Previous.

Kolumny Forecast/vs forecast nie są renderowane w nagłówku, colgroup ani
wierszach All. Nie ukryto ich przez CSS i nie pozostawiono pustej szerokości.
Kolumna wydarzenia ma 44% zamiast 34%; pozostałe miejsce poszerza odczyty.
Nagłówki dat i rozwijane szczegóły mają colSpan=6. Nagłówek daty jest oznaczony
scope=rowgroup, aby nie był traktowany jako dodatkowy nagłówek kolumny.
Na telefonie Actual i Previous zajmują całą szerokość drugiego rzędu,
a porównanie trzeci. Zmiany CSS dotyczą wyłącznie tabeli All.

Zachowano jedną tabelę, wspólne daty i chronologię makro/Earnings, nieznane
godziny na końcu dnia, 22:00+, kryterium ★★★ od 200 mld USD, poprawione nazwy,
filtry i domyślne Wszystko. Kliknięcie Earnings przechodzi do pełnych Wyników
z zachowaniem zakresu. Wiersze Earnings mają neutralne — w trzech polach
liczbowych; nie przypisano im Actual/Previous ani fikcyjnych porównań.

**Dane** zachowują osiem kolumn i prognozy makro. **Wyniki** zachowują siedem
kolumn finansowych, Actual/Previous/Forecast/Market Cap oraz źródła.
Nie zmieniono fetcherów, pollingu, sortowania, danych ani pełnej tabeli Earnings.

## Sprawdzenie

| Kontrola | Wynik |
|---|---|
| Pełny frontend offline, dwa workery | **794 passed / 38 plików**, 82.60 s |
| TypeScript noEmit | passed |
| Production build | passed, 5.32 s, największy chunk 407.04 kB |
| Normalny Chrome PL/EN, 1366/390 px | **160 kontroli / 16 GET API 200** |
| PostgreSQL read-only przed/po | **16 pełnych snapshotów i katalogi identyczne** |
| F1 V2 | **155 artefaktów zgodnych**, activated=true, cooldown |
| Indeks / whitespace / ochrona prac | passed |

Chrome korzystał z rzeczywistego Vite 5173/API 8000/SQL 5432 bez fixture.
Sprawdził dokładne sześć nagłówków i sześć fizycznych komórek/colgroup,
brak pól prognoz w All, wspólne dni i chronologię, AMD 03.11,
ARM/QCOM 04.11, NVIDIA 17.11, 22:00+, gwiazdki, przejście do szczegółów,
osiem kolumn i **14 widocznych nowcastów w Dane**, siedem kolumn oraz
guidance NVIDIA i oficjalny link AMD w Wynikach. Brak overflow strony,
błędów JS/console.error, HTTP 503 i żądań przeglądarki do wydawców.
Obejrzano desktop EN i mobile PL. Nie deklaruje się pełnego audytu WCAG.

Testy starego układu makro wybierają teraz jawnie Dane, zachowując asercje
prognoz/porównań; osobne testy All sprawdzają sześć kolumn, neutralne pola
Earnings i colSpan szczegółów. Pierwsze przebiegi wykazały stare oczekiwania
ośmiu kolumn oraz nieprawidłowy selektor pomocniczego Chrome dla nowcastów;
poprawiono testy/helper zgodnie z istniejącym DOM, bez pomijania asercji.
Istniejący chroniony test objaśnień Overview nie przeszedł przy dużej
równoległości. Pełny zestaw powtórzono z dwoma workerami według istniejącego
polecenia README: wszystkie testy przeszły. Nie zmieniono tego testu,
timeoutów ani guardów sieciowych. Nieudanych przebiegów nie zaliczono.

## Dane i ochrona prac

Wszystkie kontrolne połączenia SQL miały wymuszone READ ONLY/REPEATABLE READ.
Nie wykonano SQL WRITE, DDL, migracji, APPLY, zmiany policy/tokenu ani
autoryzacji F1 V2. Pełne 16 tabel Earnings/Forecast, timestampy i oba katalogi
są identyczne przed i po UI. Forecast zachował 20 vintages, sześć freezes,
trzy checks oraz niezmienione źródła. F2 pozostaje nieaktywne.
F1 activated=true/cooldown; monitor Earnings activated=true/completed.
Zwykłe odświeżanie makro pozostało aktywne, bez zmian konfiguracji.

Zapisano manifest wszystkich 458 zastanych plików i pełny dirty diff.
**454 pliki zachowano byte-identycznie**, w tym F2, backend, globalny CSS,
pełne Earnings, ForecastValue, API i wcześniejsze audyty. Cztery konieczne
pliki zmieniono z zachowaniem wcześniejszych hunków:

- frontend/src/calendar/CalendarPage.tsx
- frontend/src/calendar/unifiedCalendar.css
- frontend/src/calendar/UnifiedCalendar.test.tsx
- frontend/src/calendar/CalendarPage.test.tsx

Doszedł tylko ten raport. Pozostałe chronione prace użytkownika zachowano;
w CalendarPage i jego testach dodano wyłącznie zmiany tego etapu.
Manifesty, snapshoty, logi i screenshoty pozostają ignorowane w
data/raw/calendar-all-six-columns-2026-11-05.

Własny Chrome 9309 zakończono po sprawdzeniu PID i argumentów. Normalne
PostgreSQL/API/Vite pozostawiono działające. Końcowo **17 modified /
36 untracked plików**, indeks pusty, main/HEAD bez zmian. Bez stagingu,
commita, pusha, reset/clean/amend/force i globalnego formatowania.
