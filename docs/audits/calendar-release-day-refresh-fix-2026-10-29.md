# MacroLens — etap R1: odświeżanie i diagnostyka publikacji makro

Kontrola **29.10.2026**, Europe/Warsaw, `C:\Projects\macrolens`.
Gałąź `main`, HEAD **`6f31b99005e6941141de52f604fb780927538be9`**.
Naprawiono dwa błędy wskazane w niezmienionym
[audycie opóźnienia](calendar-release-day-latency-2026-10-29.md).
Dodano diagnostykę konkretnej miary w istniejących szczegółach Calendar.
**Bez stagingu, commita i pusha.** Bez nowego importera BEA, specjalnego
szybkiego odpytywania FRED, migracji, zmian MCI/PIT i globalnych interwałów.

## 1. Potwierdzone przyczyny i zakres naprawy

Zastany hook `frontend/src/brief/useOverviewRefresh.ts` zapisywał `nextCheck`,
lecz po zakończeniu joba nie planował kolejnej próby. Stale widoczna karta
mogła czekać na focus, visibilitychange lub ponowne wejście. Istniał natomiast
prawidłowy mechanizm pobrania Calendar po wykryciu zmiany `publication_id`.

`parse_bea_result` w `sync_calendar_periods.py` akceptował datę tylko z
`article:published_time` lub `time[datetime]`. Zachowany prawdziwy dokument
GDP Advance Q3 ma zamiast nich nagłówek embargo, przez co kończył walidację
ValueError. Naprawa nie zmienia bindingu: GDP Second/Third/Updated nadal
wymagają własnego receipt; Advance zachowuje dotychczasowe reguły.

Brak GDP około 13:53 w incydencie ma także osobny dowód: o 13:52:18 FRED
zwrócił metadane kończące się na Q2. Q3 pobrano później. R1 nie usuwa tego
ograniczenia kanału FRED i nie rozstrzyga, czy endpoint obserwacji miał wówczas
Q3 wcześniej niż endpoint metadanych. Nie zmieniono obliczeń GDP lub PCE.

## 2. Timer istniejącego hooka

Zastosowano **jeden anulowalny `setTimeout`**, bez `setInterval` i bez nowego
pollera dostawców. Po stanie terminalnym hook planuje próbę według
backendowego `next_check_at`. Jeżeli termin jest znany już przy wejściu,
nie wykonuje wcześniejszego POST. Zakończenie complete/partial/idle/error
jest obsługiwane tą samą ścieżką, z terminem wyznaczonym przez backend.

Zachowanie:

- `inFlight` scala timer, focus i visibilitychange; w ramach hooka nie ma
  równoległych identycznych żądań. Zwykły rerender nie uruchamia nowej próby.
- Running odpytuje wyłącznie istniejący status GET. Minimalny odstęp 2 s
  obowiązuje również przy serii zdarzeń focus; nie powstaje drugi POST joba.
- Hidden usuwa timer i nie rozpoczyna nowego żądania. Już wysłana odpowiedź
  może się zakończyć; nie powoduje dalszych prób w ukrytej karcie. Powrót
  sprawdza zaległy dozwolony termin albo ponownie ustawia timer na przyszłość.
- Brak, niepoprawny lub przeszły termin w terminalnej odpowiedzi nie tworzy
  pętli zerowych retry: stosowany jest bezpieczny odstęp 15 minut. Błąd sieci
  również planuje próbę po 15 minutach. Dłuższy jawny backoff jest zachowany.
- Unmount i zmiana operacji/zakresu anulują timer oraz AbortController.
  Kontrola `alive` chroni zarówno odpowiedź statusu, jak i późny reload starego
  zakresu przed podmianą nowego widoku.
- Zmiana `publication_id` nadal wywołuje reload danych; stary widok pozostaje
  do jego zakończenia. Zapamiętanie załadowanej rewizji zapobiega zbędnemu GET
  tej samej generacji. Nowszy stan refresh zwrócony z reloadem aktualizuje
  również termin i stan hooka, zamiast pozostawiać starszy cooldown.

Nie zmieniono domyślnych **900 s** koordynatora, retry, interwału wolnych
harmonogramów **21600 s**, request budget, locka ani atomowego zapisu bazy.
Timer zapewnia wykonanie dozwolonej kontroli przy otwartej widocznej karcie;
nie wymusza odświeżenia serwera przed jego terminem. Uśpienie systemu,
throttling przeglądarki, sieć i działający job nadal mogą opóźnić próbę.
To nie jest gwarancja Actual o planowanej minucie publikacji.

## 3. Parser embargo BEA

Parser akceptuje tylko HTTPS z hosta `bea.gov`/`www.bea.gov` i ścieżką
`/news/`, własny tytuł GDP, zgodny kwartał/rok i etap oczekiwanego wydarzenia.
Nowa gałąź ogranicza się do elementów nagłówka wydawcy
`release-embargo` / `field--name-field-release-date`.
Nie przeszukuje całego artykułu w poszukiwaniu dowolnej daty.

Nagłówek musi podawać pełne embargo: datę, dzień tygodnia, godzinę, AM/PM
i EST/EDT. Zegar jest porównywany z oczekiwanym wydarzeniem (domyślnie
08:30 dla tego parsera), weekday z datą, a skrót strefy z IANA
`America/New_York` **dla tej daty**. Nie stosuje stałego offsetu całorocznego.
Data i etap muszą odpowiadać proof. Jeśli obecne są metadane i elementy time,
wszystkie są sprawdzane; sprzeczność dat lub godzin odrzuca dowód.

Zachowano starsze struktury z `published_time` i date-only metadata.
Gdy oficjalny dokument podaje pełny zegar, wynik zawiera `announced_at` UTC,
`release_time` i `source_timezone`. Nie nadaje się fikcyjnej godziny starym
metadanym zawierającym wyłącznie datę. Nie używa się fetched_at jako daty
publikacji. Zapis receipt nadal następuje wyłącznie po poprawnej walidacji;
błąd zachowuje wcześniejszy poprawny dowód i status partial/error źródła.

### Sprawdzenie na rzeczywistym zachowanym materiale

Ponownie sparsowano bez HTTP oryginalny
`data/raw/calendar_periods/20261029T125048Z-d80204f2b46245b4855809ff8d1a52d0/18.html`.
To ten sam materiał z SHA-256
`b51d2f8f5bb721a5b37d17426a7512dcbfce1949aeb1e33b3ff28c823fcaaa30`.
Parser potwierdził **29.10.2026, Q3, Advance, 08:30 EDT** i
**`2026-10-29T12:30:00+00:00`**. Zachowano oryginalny retrieved_at
`2026-10-29T12:50:48.150653+00:00` z istniejącego receipt, bez przypisywania
diagnostycznemu odczytowi pliku kolejnego udanego pobrania od dostawcy.
Wyniku nie zapisano do produkcyjnego snapshotu ani bazy.

## 4. Diagnostyka konkretnej miary

Dodano małą sekcję `ReadingAvailability` w dotychczasowych szczegółach miary.
Tabela, kolumny i CSS pozostają bez zmian; sekcja ma etykietę dostępną dla
czytnika i tłumaczenie EN/PL. Chronionego SourceCheckStatus nie zmieniano.
Zachowano globalną semantykę „sprawdzono część źródeł”.

Wykorzystano istniejące pola Calendar `check.sources`, per-seria
`last_finished_at`, scope, wynik joba, `next_check_at`, `data_revision`
i provenance miary. Rozszerzono tylko typy TS już zwracanych pól.
Bez nowego zapytania do dostawcy, centrum diagnostycznego lub tabel SQL.

Jedno małe addytywne pole, **`observation_fetch_status`**, trafia do
dotychczasowego scope kontroli FRED i jej wyniku:

- `metadata_unchanged`: obserwacji nie pobrano, bo nie zmieniły się sprawdzane
  metadane/sygnatura/transformacje. UI wyraźnie zaznacza, że nie dowodzi to
  braku nowszego okresu w endpointcie obserwacji.
- `fetched`: wykonano pobranie obserwacji. Nie jest to automatycznie
  potwierdzenie Actual za oczekiwany okres — o tym nadal decyduje binding.

Pole jest zapisywane przez **następny zwykły dozwolony refresh**, nie backfill.
Dawne kontrole nie otrzymały go retrospektywnie. Istniejące
`observations_received` może potwierdzać wcześniejsze pobranie, a `outcome`
unchanged mówi o braku zmiany serii w ostatnim jobie. Przy braku takiego dowodu
informację o konkretnym sposobie pobrania pomija się.

Szczegóły pokazują, jeśli istnieją wiarygodne metadane:

- status i czas kontroli **tej serii**, niezależne od globalnego checked_at;
- błąd/skipped/cached ostatniej próby oraz zachowanie zapisanych wyników;
- najnowszy okres **według metadanych dostawcy**, oczekiwany okres raportu
  i oryginalny znacznik provider last_updated;
- błąd walidacji własnego dokumentu GDP dopasowany dokładnym `report_url`
  albo brak zapisanego potwierdzonego dokumentu;
- rozróżnienie niepotwierdzonego Actual od dostępnego wyniku, wersję
  current-vintage i rzeczywistą datę wersji;
- przyszły termin następnej dozwolonej kontroli, gdy backend go podał
  i nie trwa job. To uprawnienie do próby, nie obietnica nowego wyniku;
- identyfikator wyświetlanej generacji. Czas jej publikacji jest wyświetlany
  tylko przy zgodnym publication_id i zakończonym complete/partial. Czas
  błędu joba zachowującego starą generację nie udaje czasu jej publikacji.

Dotychczasowa przyczyna pustego Actual, okresy, źródło i provenance pozostają
obok sekcji. Brak metadanych właściwej serii nie powoduje użycia czasu innej
miary. `ingested_at` nie jest wykorzystywany jako moment publikacji generacji.

Nowy parser nie usuwa automatycznie starego zapisanego błędu BEA. Podczas
kontroli UI stary błąd był nadal uczciwie widoczny przy dostępnym Actual GDP.
Nie uruchamiano ingestion tylko po to, aby zmienić ten status na sukces.

## 5. Testy offline i sekwencja dnia publikacji

Backend: **25 nowych przypadków** w `test_release_day_refresh_fix.py` oraz
rozszerzenie istniejącego testu zapisującego wynik kontroli FRED.
Testy obejmują embargo-only, EST/EDT, IANA, weekday, rok/kwartał/etap,
zły wydawca/raport, konflikt metadanych, brak daty, starszy HTML, zapis receipt
i zachowanie wcześniejszego dowodu po błędzie. HTTP to MockTransport;
nie kopiowano całego dokumentu do fixture.

Syntetyczna sekwencja 29.10 sprawdza GDP Q3 po 13:30, lokalne Q2 mimo udanej
kontroli i dostępnych PCE/Claims, poprawne Previous, pusty Forecast, późniejsze
przyjęcie Q3 i current-vintage. Sam upływ czasu, provider success, dokument,
brak zmiany hasha lub inny okres nie wytwarzają brakującego Actual.
Nie zmieniono istniejących testów atomowości koordynatora ani reguł bindingu.

Frontend: hook ma teraz **21 testów** (wcześniej 5), w tym fake timers,
complete/partial/idle/error, bierna widoczna karta, cooldown, hidden/powrót,
zbieg focus i timera, polling running, backoff, niepoprawny termin,
sieć, unmount, nieaktualny zakres i nowy termin z reloadu. Przebieg z błędem
sieci również dochodzi do kolejnej ograniczonej próby bez ręcznego odświeżenia.

**7 testów** diagnostyki sprawdza EN/PL, czas własnej serii zamiast globalnego,
niezmienione metadane, dokument, brak danych, matching generation oraz
error/skipped/cached. **2 testy Calendar EN/PL** przechodzą ze starego GDP
do opublikowanego Q3 przez kontrolowany status i nową generację: Actual
pozostaje pusty przed commit, a następnie zmienia się bez focus/reload strony.
Sprawdzają też Escape i powrót fokusu. Ta kontrolowana sekwencja nie używa
rzeczywistego produkcyjnego importera ani bazy.

Pierwszy przebieg nowych testów React utknął przez fixture tworzącą nowy
callback przy każdym renderze hooka. Poprawiono stabilność callbacku w fixture;
nie zwiększano timeoutów ani nie pomijano testów. Testy Vite wymagały dostępu
do pliku tymczasowego konfiguracji poza ograniczeniami sandboxa; ponowienie
z odpowiednim dostępem przeszło. Nie był to błąd aplikacji.

## 6. Pełna walidacja

| Kontrola | Rzeczywisty wynik |
| --- | --- |
| `.venv\Scripts\python.exe -m pytest -q` | **1006 passed**, 50.88 s; wcześniejsze 981 + 25 przypadków |
| Pełny frontend, z `NODE_OPTIONS=--require=../.github/ci/no-network.cjs` | **594 passed**, **24 pliki**, końcowy przebieg 25.48 s |
| `npx tsc --noEmit` | **passed**, także osobno po końcowych zmianach |
| `npm run build` | **passed**, zawiera typecheck i Vite production build |
| Główny pakiet | **529.53 kB**, gzip **153.36 kB** |
| `git diff --check` | **passed** |

Ostrzeżenie Vite ponad **500 kB** pozostaje jawne. Nie zmieniano progu ani
strategii bundlowania. Nie uruchamiano optymalizacji Vite i PostgreSQL w CI.
Nie pomijano testów i nie zwiększano timeoutów; znany sporadyczny błąd nawigacji
MCI nie wystąpił w pełnych przebiegach. Po końcowym doprecyzowaniu hooka
powtórzono pełny frontend i build; wcześniejszy frontend również przeszedł
592/592 przed dodaniem dwóch końcowych przypadków.

## 7. Rzeczywista aplikacja i Chrome

Końcowy pełny przebieg: **16 scenariuszy**, EN/PL, **1366 i 390 px**,
**20 odpowiedzi API HTTP 200**, **zero wyjątków JavaScript i overflow**.
Sprawdzono Calendar za 29.10, GDP **3.37% / 3,37%**, headline PCE
**0.49% / 0,49%**, szczegóły nowej diagnostyki, okresy i current-vintage,
Escape/powrót fokusu, nawigację Calendar ↔ Overview, sześć kart i najwyżej
cztery wydarzenia Overview. Obejrzano zrzuty desktop EN i mobilny PL.

Nie podstawiano odpowiedzi API. Kontrola prawdziwego UI odbywała się pod
wspólną blokadą koordynatora `726530019`, utrzymywaną przez osobne połączenie
**read-only**. Normalne żądania aplikacji nie uruchamiały importerów.
Przed i po przebiegu porównano liczbę i max timestamp `source_check_runs`
oraz stan i publication_id koordynatora — **bez zmian podczas kontroli**.
Blokadę zwolniono. Nie inicjalizowano ani nie modyfikowano bazy użytkownika
na potrzeby walidacji; automatyczne testy blokują prawdziwą sieć/DB.

Pierwsza próba helpera Chrome używała wyłącznie angielskiego selektora GDP,
podczas gdy PL pokazuje PKB. Poprawiono ignorowany helper i wykonano pełne
przebiegi ponownie; końcowy wynik powyżej nie ma tego błędu. Diagnostyka,
helpery i zrzuty pozostają ignorowane w
`data/raw/refresh-fix-2026-10-29/`. Nie przeprowadzano 15-minutowego testu
timera z produkcyjnym ingestion: następne próby i zmiany generacji były
kontrolowane w testach React.

## 8. Przed/po i granice rezultatu

| Pytanie | Wynik R1 |
| --- | --- |
| Czy stale widoczna karta wykonuje następną dozwoloną próbę? | **Tak**, potwierdzone fake timers bez focus. |
| Czy prawdziwy zapisany GDP BEA przechodzi parser embargo? | **Tak**, Q3 Advance, 29.10, 08:30 EDT i zgodny UTC. |
| Czy można odróżnić sprawdzenie źródła od potwierdzenia Actual? | **Tak**, w szczegółach konkretnej miary; nie zmieniono semantyki nagłówka pokrycia. |
| Czy zachowano 15 minut? | **Tak**, bez zmian globalnych interwałów i bez szybkiego okna FRED. |
| Czy FRED nadal może opóźniać Actual? | **Tak**: metadane, obserwacje, rytm joba i atomowe zakończenie pozostają odrębne. |
| Czy zmierzono krótszą latencję nowej publikacji? | **Nie**. Usunięto potwierdzone błędy; nie obserwowano nowej publikacji na żywo. |

Nie przywrócono nieznanej historii pierwszych publikacji ani dokładnych chwil
dostępności intraday. R1 nie wyjaśnia retrospektywnie braku startu o 13:30,
nieznanej historii locka lub rozbieżności wcześniejszej decyzji
`publication_results_due` opisanej w audycie. Zachowano tamte ograniczenia.
Pozostają brak konsensusu, BLS 403, current-vintage i nierozstrzygnięte warunki
istniejącego modelu FRED/PostgreSQL/RAW/cache. Nie deklaruje się publicznej
gotowości całej aplikacji lub gwarancji wyniku w sekundę publikacji.

Następny krok wymaga osobnego zlecenia: ograniczony event-aware refresh może
zmniejszyć oczekiwanie pomiędzy próbami, ale nadal zależy od FRED. Jeżeli celem
jest wynik BEA bez tej zależności, właściwym kierunkiem jest osobny bezpośredni
adapter GDP/PIO z pełną walidacją etapu/okresu i provenance. Żadnego z tych
wariantów nie rozpoczęto w R1.

## 9. Pełna lista zmian i Git

Zmiany R1 — **13 plików**, bez stagingu:

- `app/analytics/overview_refresh.py` — addytywna diagnostyka pobrania FRED.
- `app/ingestion/sync_calendar_periods.py` — walidacja embargo BEA.
- `frontend/src/api/macrolens.ts` — typy istniejących metadanych i nowego pola scope.
- `frontend/src/brief/useOverviewRefresh.ts` — timer i obsługa stanów/zakresów.
- `frontend/src/brief/useOverviewRefresh.test.tsx` — regresje fake timers.
- `frontend/src/calendar/CalendarPage.tsx` — diagnostyka w szczegółach.
- `frontend/src/calendar/ReadingAvailability.tsx` — nowy mały komponent.
- `frontend/src/calendar/ReadingAvailability.test.tsx` — nowe testy szczegółów.
- `frontend/src/calendar/CalendarRefresh.test.tsx` — nowa sekwencja generacji EN/PL.
- `frontend/src/i18n/pl.json` — tłumaczenia diagnostyki.
- `tests/test_overview_refresh.py` — kontrola zapisanego statusu pobrania.
- `tests/test_release_day_refresh_fix.py` — nowe offline regresje BEA i wyników.
- `docs/audits/calendar-release-day-refresh-fix-2026-10-29.md` — ten raport.

Sześć chronionych plików ma identyczne SHA-256 przed/po. Cztery pozostają
modified, a dwa wcześniejsze raporty untracked, bez zmian treści:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`
- `docs/audits/calendar-next-releases-priority-2026-10-29.md`
- `docs/audits/calendar-release-day-latency-2026-10-29.md`

Końcowy zakres **12 modified, 7 untracked**, staging pusty:

```text
 M README.md
 M app/analytics/overview_refresh.py
 M app/ingestion/sync_calendar_periods.py
 M frontend/src/api/macrolens.ts
 M frontend/src/brief/SourceCheckStatus.test.tsx
 M frontend/src/brief/SourceCheckStatus.tsx
 M frontend/src/brief/useOverviewRefresh.test.tsx
 M frontend/src/brief/useOverviewRefresh.ts
 M frontend/src/calendar/CalendarPage.tsx
 M frontend/src/i18n/pl.json
 M frontend/src/styles.css
 M tests/test_overview_refresh.py
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
?? docs/audits/calendar-release-day-latency-2026-10-29.md
?? docs/audits/calendar-release-day-refresh-fix-2026-10-29.md
?? frontend/src/calendar/CalendarRefresh.test.tsx
?? frontend/src/calendar/ReadingAvailability.test.tsx
?? frontend/src/calendar/ReadingAvailability.tsx
?? tests/test_release_day_refresh_fix.py
```

Nie dodano sekretów, `.env`, lokalnych danych, RAW, logów, cache ani artefaktów
przeglądarki do zakresu Git. Bez commita, pusha i nowego GitHub Actions.

## 10. Kontrola zamknięcia R1 — 29.10.2026

Ponownie sprawdzono `main`, HEAD `6f31b99005e6941141de52f604fb780927538be9`,
pełny diff i wszystkie 13 plików R1. Nie znaleziono dodatkowych niezwiązanych
zmian. Sześć chronionych plików porównano SHA-256 i wyłączono ze stagingu.
Nie zmieniano logiki podczas zamknięcia, interwałów 900/21600 s, blokady,
budżetu żądań, bindingu GDP/PCE ani MCI/PIT. Deduplikacja rzeczywistych
importerów między kartami nadal korzysta z istniejącego locka PostgreSQL.

Przegląd potwierdził timer bez focus, obsługę hidden/backoff/race/unmount,
ochronę starego zakresu, reload wyłącznie nowej generacji oraz rozróżnienie
kontroli źródła od potwierdzenia Actual. Parser ponownie odczytał rzeczywisty
zachowany HTML GDP Q3 Advance: **2026-10-29T12:30:00+00:00**. Nie pobierano
nowych danych i nie czyszczono historycznego błędu przez ingestion.

Ponowna pełna walidacja working tree: **1006 backend passed** (62.69 s),
**594 frontend passed / 24 pliki**, osobny `npx tsc --noEmit`, production build
i whitespace poprawne. Ostrzeżenie Vite pozostaje: **529.53 kB** ponad 500 kB.
Nie pomijano testów i nie zmieniano timeoutów; błąd nawigacji MCI nie wystąpił.
W lokalnym backendzie nie wypisano ostrzeżenia Starlette/httpx; jego ewentualna
obecność w środowisku CI będzie raportowana odrębnie, bez ukrywania ostrzeżeń.

Dokładna izolowana kopia stagingu z resztą śledzonych zależności również
przeszła: **1006 backend passed** (41.06 s), **594 frontend passed / 24 pliki**,
osobny typecheck i production build. Kopia nie zawiera dwóch wcześniejszych
nieśledzonych audytów i korzysta z wersji README/SourceCheckStatus/styles z HEAD.
Jej pakiet ma **531.58 kB**, gzip **153.85 kB**; ostrzeżenie ponad 500 kB
pozostaje jawne. Testy nie wymagają wcześniejszych niezacommitowanych zmian.

Pierwszy proces backendu kopii, uruchomiony w ograniczonym sandboxie, doszedł
do końca listy testów, ale nie zakończył się i nie podał podsumowania.
Przerwano go i ponowiono identyczne pełne polecenie z szerszym dostępem do
plików; powtórzenie zakończyło się kodem 0 i wynikiem 1006 passed. Pierwszej
próby nie policzono jako sukcesu. Nie ustalono szczegółowej przyczyny jej
niezakończenia; nie zmieniano kodu, testów lub timeoutów w celu obejścia problemu.

Przejrzano cały staged diff i listę dokładnie **13 plików** z sekcji 9.
`git diff --check` i `git diff --cached --check` poprawne; sprawdzono wzorce
sekretów i wykluczenie danych lokalnych, RAW, logów oraz artefaktów Chrome.
Porównano staging z kopią, uwzględniając zwykłą normalizację LF/CRLF przez Git.
Sześć chronionych plików pozostaje poza stagingiem, z identycznymi SHA-256.
Po testach uzupełniono wyłącznie tę dokumentację wyników i jej kopię.

Planowany jeden commit: **`Fix release-day refresh scheduling and BEA publication evidence`**.
Przed zatwierdzeniem zdalny `origin/main` nadal wskazywał `6f31b99`.
Hash commita, wynik zwykłego pusha, link i zakończony wynik MacroLens CI
zostaną podane w końcowej odpowiedzi po ich uzyskaniu, bez dodatkowego commita
tylko dla tych informacji. Lokalne wyniki nie są deklaracją przyszłego sukcesu CI.
Nie uruchamiano ingestion ani nowego etapu. Ograniczenia FRED, current-vintage,
konsensusu i braku gwarancji latencji pozostają aktualne.
