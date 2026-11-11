# MacroLens — diagnostyka opóźnienia Actual w dniu publikacji

Audyt **29.10.2026**, Europe/Warsaw, repozytorium `C:\Projects\macrolens`.
`main`, HEAD **`6f31b99005e6941141de52f604fb780927538be9`**.
Wyłącznie diagnostyka i ten dokument. Bez zmian logiki, konfiguracji, bazy,
ingestion, stagingu, commita i pusha. Odczyty PostgreSQL z `read_only=True`;
`SHOW transaction_read_only` zwróciło `on`. Nie uruchamiano koordynatora,
inicjalizatora bazy, Chrome ani POST refresh. Sprawdzono istniejące RAW,
metadane i rzeczywiste GET API. Pięć zastanych plików zachowano SHA-256.

**Wniosek:** brak GDP około 13:53 ma potwierdzoną przyczynę po stronie
sprawdzonego kanału FRED: odpowiedź metadanych o **13:52:18** nadal kończyła
się na Q2, ze starym `last_updated`. Aplikacja wykonała kontrolę GDP;
nie pominęła tej serii. Q3 pobrano w następnym zadaniu i opublikowano
o **14:09:56**. Nie jest to jednak wyłącznie problem dostawcy: cykl na żądanie,
15-minutowe oczekiwanie, czas całego zadania i brak samoczynnego ponowienia
w widocznej karcie mogą dodatkowo wydłużać dostępność. Osobno wykryto
rzeczywisty błąd parsera dowodu GDP BEA; **nie blokował on Advance w tym
incydencie**, bo ten etap nie wymaga receipt wyniku w obecnym bindingu.

## 1. Podstawa i granice dowodów

Przeczytano `overview_refresh.py`, `overview_refresh_store.py`,
`source_checks.py` w obu lokalizacjach, `request_budget.py`, klienta FRED,
importer, `calendar_evidence.py`, `calendar_readings.py`, `calendar_agenda.py`,
`sync_calendar_periods.py`, trasy API, `CalendarPage.tsx`,
`useOverviewRefresh.ts` i jego testy. Przejrzano wcześniejsze audyty FT900
i Empire oraz zachowane materiały diagnostyczne.

W PostgreSQL sprawdzono `source_check_runs`, `overview_refresh_state`,
`overview_publications` i właściwe `observation_vintages`. Zapisane kontrole
obejmują okres od 26.10; stan koordynatora przechowuje tylko ostatnie zadanie,
a publikacje zachowują najwyżej osiem generacji. Nie ma trwałego dziennika
każdego POST, odmowy locka, decyzji cooldown, zmiany widoczności karty ani
każdej odpowiedzi Calendar wysłanej użytkownikowi.

29.10 Warszawa ma CET (UTC+1), Nowy Jork EDT (UTC−4).
Okno **13:15–14:30 PL = 12:15–13:30 UTC**. Wszystkie godziny bez oznaczenia
strefy w dalszych tabelach są polskie. Offset FRED `-05` należy odczytywać
jako podany offset −05:00, a nie zamieniać go na dzisiejszą strefę Nowego Jorku.

Odczyt diagnostyczny zakończono około **15:53 PL**. Nie odpytywano ponownie
FRED API: „ostatnie dane FRED” poniżej oznaczają rzeczywiście zachowaną
odpowiedź i lokalny stan po jej przyjęciu, nie niezależny aktualny odczyt
serwisu ani dowód chwili jego pierwszej dostępności.

## 2. Chronologia incydentu

| Godzina PL, 29.10 | Zapisany fakt / interpretacja |
| --- | --- |
| 13:15–13:30 | Brak kontroli ośmiu badanych serii w `source_check_runs` w tej części okna. Nie ma dowodu, że UI wtedy zażądało zadania. |
| **13:30** | Oficjalna publikacja GDP Q3 Advance, PIO za IX i tygodniowych Claims: 08:30 EDT = 12:30 UTC. |
| 13:34:23 | `last_updated` FRED ICSA/CCSA: `07:34:23-05`, odczytany dopiero w późniejszej kontroli. Nie jest to pomiar pierwszej dostępności. |
| 13:43:33–56 | Analogiczne znaczniki FRED dla pięciu serii PIO. |
| **13:50:48.150653** | Początek zadania, zachowany także jako wspólny znacznik przekazywany adapterowi okresów. |
| 13:50:50–56 | Udana kontrola CCSA, 3120 rekordów odpowiedzi. |
| 13:52:14–17 | Udana kontrola DSPIC96, 813 rekordów. |
| **13:52:18.013019–18.498891** | Udana kontrola GDPC1; `observation_end=2026-04-01`, `last_updated=2026-09-30 07:53:55-05`. Brak `observations_received`: obserwacji nie pobrano, metadane nie wykazały zmiany. |
| 13:52:19–26 | ICSA, 3121 rekordów. |
| 13:52:29–31 | PCEC96, 813 rekordów. |
| 13:52:31–34 | PCEPI, 813 rekordów. |
| 13:52:34–38 | PCEPILFE, 813 rekordów; ta sama seria obsługuje m/m i r/r. |
| 13:52:42–45 | PSAVERT, 813 rekordów. |
| 13:52:52–13:53:31 | Udana kontrola kalendarza FRED. |
| 13:53:35.593555–42.498392 | `calendar:periods`: partial. Harmonogram BEA i dokument Claims odczytane; parser dokumentu GDP zwrócił ValueError. Część prób BLS pozostała błędna/cached. |
| **13:53:53.486357** | Publikacja generacji `a9771cb4-7a37-4596-8590-56e7dd844073`; PIO i Claims mogły być już widoczne po zatwierdzeniu transakcji. GDP Q3 w lokalnych obserwacjach nadal brak. |
| **14:03:15** | Nowy zapisany później znacznik FRED GDP `2026-10-29 08:03:15-05`. Sam znacznik nie wyznacza dokładnej chwili udostępnienia endpointu obserwacji. |
| 14:09:19.464050 | Początek transakcji kolejnego zadania, widoczny jako `ingested_at` nowych wierszy GDP. |
| **14:09:29.954149–31.681684** | Kontrola GDPC1 widzi Q3 (`2026-07-01`) i nowy `last_updated`; pobrano 319 rekordów. RAW utworzono 14:09:31.184784. |
| **14:09:56.825063** | Generacja `dc86aab2-df78-476f-9e3c-f4f82ee17126` zawiera już nowe dane; poziomy dają GDP 3.369619%, po zaokrągleniu BEA 3.4%. |
| 14:25:36.963875–14:26:15.155326 | Kolejna kontrola: badane FRED success/unchanged, wolne zasoby cached. Generacja `450c0203-27e1-49e5-8546-d8644782b135`, status koordynatora partial. |

Między pierwszą a drugą publikacją jest **16 min 3 s**: 15 minut po
zakończeniu pierwszego zadania, czas do faktycznego następnego żądania
i wykonanie kolejnej kontroli. Od godziny oficjalnej publikacji do drugiej
generacji upłynęło **39 min 57 s**. Nie można przypisać całego tego czasu FRED.

Ważne: `ingested_at` ma typ `timestamp without time zone`; sesja PostgreSQL
ma `Etc/UTC`. Importer używa `CURRENT_TIMESTAMP`, czyli czasu **początku
transakcji**, nie czasu wykonania każdego INSERT ani COMMIT. Dlatego wiersze
PCE/Claims mają `12:50:48.238658`, choć pobierano je później; GDP ma
`13:09:19.464050`, choć żądanie wykonano po 13:09:29 UTC. Widoczność danych
wiąże się z zatwierdzeniem generacji, nie z tym polem.

Nie ma historycznego payloadu Calendar z dokładnie 13:53 ani logu przeglądarki
użytkownika. Cache Overview zachował harmonogram, a nie komplet dawnych miar
Calendar. Brak Q3 w pierwszym zadaniu wynika bezpośrednio z ówczesnych metadanych;
konkretny kod `observation_missing` jest wnioskiem z bindingu dla brakującego
Q3, nie odnalezioną odpowiedzią HTTP z 13:53.

## 3. Miary, okresy i aktualny GET API

Wszystkie trzy rodziny mają 29.10 potwierdzone 08:30 `America/New_York`,
czyli **13:30 PL**. Dowód BEA to własny harmonogram i datowane komunikaty;
Claims ma zachowany własny PDF z nagłówkiem i osobnymi tygodniami.
`release_id` jest identyfikatorem publikacji FRED, nie numerem komunikatu BEA.

| Miara | FRED / release | Okres Actual → Previous | Transformacja | Aktualne Actual / Previous |
| --- | --- | --- | --- | --- |
| Real GDP Q3 Advance | GDPC1 / 53 | 2026-07-01 → 2026-04-01 | `100*((Q3/Q2)^4-1)`, q/q SAAR | **3.369619% / 2.220208%** |
| Headline PCE m/m | PCEPI / 54 | IX → VIII 2026 | iloraz miesięcznych indeksów SA, ×100 minus 100 | **0.490840% / 0.323203%** |
| Core PCE m/m | PCEPILFE / 54 | IX → VIII 2026 | m/m indeksu SA | **0.316502% / 0.262009%** |
| Core PCE r/r | PCEPILFE / 54 | IX → VIII 2026 | każdy miesiąc względem tego samego miesiąca rok wcześniej, SA | **3.121160% / 3.034442%** |
| Real PCE | PCEC96 / 54 | IX → VIII 2026 | m/m realnego poziomu SAAR | **0.015317% / 0.549691%** |
| Real disposable personal income | DSPIC96 / 54 | IX → VIII 2026 | m/m realnego poziomu SAAR | **−0.272043% / 0.011404%** |
| Personal saving rate | PSAVERT / 54 | IX → VIII 2026 | poziom stopy; bez m/m | **3.8% / 4.0%** |
| Initial Claims | ICSA / 180 | 24.10 → 17.10.2026 | poziom SA, osoby/wnioski według serii | **194000 / 195000** |
| Continuing Claims | CCSA / 180 | 17.10 → 10.10.2026 | poziom SA | **1701000 / 1722000** |

Rzeczywiste `GET /api/v1/calendar?start_date=2026-10-29&end_date=2026-10-29&include_readings=true`
zwróciło **HTTP 200**, te wartości i generację `450c0203-27e1-49e5-8546-d8644782b135`.
Obecnie każda z dziewięciu miar ma dostępny Actual, brak przyczyny pustki,
`current_vintage`, pusty Forecast i `consensus_status=not_integrated`.
W momencie incydentu pewny jest brak nowego GDPC1 w pierwszej kontroli;
nie przedstawia się obecnej dostępności jako stanu o 13:53.

### Wejścia liczbowe zachowanego snapshotu

| Seria | Właściwe poziomy wejściowe |
| --- | --- |
| GDPC1 | Q2 24408.011 → Q3 24611.077 mld chained 2017 USD, SAAR; poziom nie jest stopą 3.4% |
| PCEPI | VIII 131.611 → IX 132.257; indeks, nie procent |
| PCEPILFE | VIII 130.489 → IX 130.902; IX 2025 126.940 dla r/r |
| PCEC96 | VIII 16975.0 → IX 16977.6 mld chained 2017 USD, SAAR |
| DSPIC96 | VIII 18416.2 → IX 18366.1 mld chained 2017 USD, SAAR |
| PSAVERT | VIII 4.0 → IX 3.8, procent DPI |
| ICSA / CCSA | Pary tygodni i poziomy z powyższej tabeli; nie zamieniono tygodni obu serii |

Przy obliczaniu Previous m/m potrzebny jest jeszcze VII, a GDP Previous — Q1;
odczyt korzysta z pełnej właściwej pary, nie z odejmowania stóp. Realne poziomy
SAAR nie oznaczają, że miesięczną dynamikę PCEC96/DSPIC96 należy annualizować.
PCE kwartalny SAAR w komunikacie GDP nie jest wrześniowym PCE m/m.

## 4. Metadane każdej serii

Wszystkie poniższe serie miały **success** w trzech kolejnych zadaniach;
żadna nie miała zachowanej nieudanej kontroli FRED w całej odczytanej historii
`source_check_runs`. To brak zapisanego błędu, nie gwarancja braku wszelkich
problemów poza obserwowanym zakresem. Core m/m i r/r współdzielą jedną kontrolę.

| Seria | Zapisany provider `last_updated` | Koniec obserwacji | Ostatni success: start → koniec PL |
| --- | --- | --- | --- |
| GDPC1 | 2026-10-29 08:03:15-05 | 2026-07-01 | 14:25:47.929975 → 14:25:48.735141 |
| PCEPI | 2026-10-29 07:43:37-05 | 2026-09-01 | 14:25:54.465824 → 14:25:54.973454 |
| PCEPILFE | 2026-10-29 07:43:35-05 | 2026-09-01 | 14:25:55.029667 → 14:25:55.882358 |
| PCEC96 | 2026-10-29 07:43:33-05 | 2026-09-01 | 14:25:53.880109 → 14:25:54.404218 |
| DSPIC96 | 2026-10-29 07:43:56-05 | 2026-09-01 | 14:25:46.614555 → 14:25:47.309189 |
| PSAVERT | 2026-10-29 07:43:55-05 | 2026-09-01 | 14:25:58.922038 → 14:25:59.536772 |
| ICSA | 2026-10-29 07:34:23-05 | 2026-10-24 | 14:25:49.898945 → 14:25:50.786677 |
| CCSA | 2026-10-29 07:34:23-05 | 2026-10-17 | 14:25:38.185289 → 14:25:38.533755 |

Wszystkie najnowsze obserwacje mają `vintage_date=2026-10-29`,
`source=fred_snapshot`. GDP zapisano z transakcyjnym `ingested_at`
13:09:19.464050 UTC, pozostałe z 12:50:48.238658 UTC. Faktyczne pliki RAW FRED
mają czasy pobrania w nazwach, np. GDPC1 `20261029T130931184784Z`,
PCEPI `20261029T125232847588Z`, PCEPILFE `20261029T125236712789Z`.
To snapshot dnia, nie dokładna historyczna chwila pierwszego wydania.

Okresy i etap GDP są potwierdzone w zapisanym harmonogramie BEA
(`official_schedule`, GDP `advance`, Q3 = 2026-07-01; PIO IX = 2026-09-01).
Claims ma `official_release`, osobno ICSA 24.10 i CCSA 17.10.
Dokument GDP ma błąd walidacji, a nie brak ustalonego kwartału.

## 5. Koordynator, pobieranie i publikacja

| Mechanizm | Rzeczywiste zachowanie kodu |
| --- | --- |
| `OVERVIEW_REFRESH_INTERVAL_SECONDS` | Domyślnie **900 s**, liczone od zakończenia. |
| `OVERVIEW_REFRESH_RETRY_SECONDS` | Domyślnie 900 s; efektywnie co najmniej zwykły interwał. |
| `OVERVIEW_CALENDAR_INTERVAL_SECONDS` | Domyślnie **21600 s = 6 h**, minimum 900; dotyczy wolnych harmonogramów, nie kontroli metadanych wszystkich FRED. |
| Budżet | `OVERVIEW_REFRESH_TIMEOUT_SECONDS` domyślnie **600 s**; odstęp FRED **0.6 s**; SQL statement timeout 60 s. Budżet jest czasowy, nie liczbą żądań. |
| HTTP | FRED timeout 20 s; klient okresów 20 s. HTTP 429 lub budżetowy `TimeoutError` przerywa resztę FRED i oznacza skipped/provider_backoff; inne błędy są zapisywane i pętla może iść dalej. |
| Cooldown | `next_check_at` oraz odstęp od `completed_at`; nie ma specjalnego szybkiego okna dla GDP/PCE. Brak odczytu `Retry-After` w kliencie FRED. |
| Advisory lock | Wspólny `726530019`; odmowa zwraca zapisany stan, bez trwałego zapisu odmowy. Bez konkurencyjnego importera. |
| Publikacja | Udane serie i features zatwierdzane wspólnie z nową generacją; awarie źródeł mają savepoint, awaria całego zadania pozostawia wcześniejszą publikację. |

W `.env` i środowisku procesu diagnostycznego cztery wymienione ustawienia
nie miały nadpisania. Nie odczytywano środowiska uruchomionego wcześniej
procesu serwera; 15-minutowe odstępy są również zgodne z zachowanymi generacjami.

Każde uruchomione zadanie pyta metadane wszystkich wymaganych FRED
(z zakresem Calendar — także skonfigurowanych dodatkowych serii), w kolejności
alfabetycznej. Nie pobiera jednak zawsze obserwacji. `refresh_fred` sprawdza
zmianę `last_updated`, lokalnej sygnatury i listy transformacji. Dopiero zmiana
wywołuje pobranie bieżącej historii od najwcześniejszej lokalnej obserwacji.
Dlatego kontrola GDP o 13:52 była success/unchanged, bez downloadu obserwacji.
Nie było w niej błędu/skip ani sześciogodzinnego blokowania GDPC1.

Gdy dostawca opóźni metadane względem obserwacji, ten warunek może opóźnić
pobranie nowego okresu. **Nie sprawdzono endpointu obserwacji o 13:52**, więc
nie wiadomo, czy Q3 był już wtedy dostępny mimo starych metadanych.
Nie należy tego hipotetycznego rozjazdu ogłaszać dowiedzionym błędem FRED.

`publication_results_due` może wymusić wcześniejszą kontrolę dowodów dla
wybranych rodzin, w tym GDP 53 i Claims 180; PIO 54 nie ma na tej liście.
To nie uruchamia samodzielnego zadania i nie skraca globalnego cooldown.
Po pierwszej próbie ponowienie brakującego GDP receipt zależy od sygnału
`posted` z metadanych i upływu interwału. Podczas kontroli rozpoczętej około
14:09:19 od poprzedniej próby okresów o 13:50:48 minęło więcej niż 15 minut,
ale od **jej zakończenia 13:53:42 mniej niż 15 minut**. Funkcja sprawdza stan
`prior.attempted_at` zapisany początkiem zadania; przy nowym posted powinna
zwrócić True. Mimo tego końcowy stan zachowuje wcześniejszy attempted_at
okresów i wynik cached w późniejszym zadaniu. Sam obecny kod i końcowy stan
nie wystarczają do odtworzenia wszystkich wejściowych `events/evidence`
tej konkretnej decyzji; przyczyny tego braku ponowienia nie uznajemy za ustaloną.
Kontrolne wywołanie czystej funkcji z zachowanymi obecnymi dowodami,
wersją GDPC1 i zegarem 14:09:19 zwraca **True**. Nie uruchamia importera.
Ta rozbieżność wymaga zapisu wejść decyzji lub kontroli wersji kodu działającego
w tamtym procesie; nie wolno automatycznie wyjaśniać jej sześcioma godzinami.

W oknie incydentu nie ma zapisanego error FRED, 429, timeout ani provider_backoff
dla badanych serii. Kod zapisuje ogólny `refresh_failed`, więc brak jawnego
kodu 429 w innych dawnych błędach nie byłby pełnym dowodem; tutaj istotne są
konkretne udane odpowiedzi z właściwych chwil.

Nie można ustalić, dlaczego pierwsze zadanie po 13:30 ruszyło dopiero 13:50.
Koordynator jest uruchamiany żądaniem, a nie niezależnym zegarem publikacji.
Wcześniejsze audyty zawierają kontrolowane utrzymywanie locka podczas UI;
nie ma zapisu jego przedziału obejmującego ten incydent. Nie przypisujemy
mu opóźnienia bez takiego dowodu. Podczas diagnostyki lock nie był zajęty.

## 6. Konkretny błąd dowodu GDP BEA i warunki bindingu

Zachowany HTML:
`data/raw/calendar_periods/20261029T125048Z-d80204f2b46245b4855809ff8d1a52d0/18.html`.
HTTP **200**, rzeczywisty SHA-256
`b51d2f8f5bb721a5b37d17426a7512dcbfce1949aeb1e33b3ff28c823fcaaa30`;
hash zweryfikowano ponownie. Nagłówki H1 zawierają zarówno „News Release”,
jak i właściwy tytuł GDP Advance Q3 2026. Parser prawidłowo znajduje tytuł,
kwartał i etap, ale szuka daty wyłącznie w `article:published_time` lub
`time[datetime]`. **W tym rzeczywistym HTML nie ma żadnego z tych pól**.
Jest natomiast jednoznaczny tekst embargo: 08:30 EDT, Thursday, October 29, 2026.
Uruchomienie istniejącego czystego parsera na zapisanych bajtach odtworzyło
`ValueError: BEA result date/period/stage not confirmed`.

To błąd dopasowania parsera do rzeczywistego oficjalnego dokumentu, nie
awaria dostępności BEA i nie dowód, że raport się nie ukazał. Zapis
`calendar:periods` ma partial / `publisher_source_unavailable`, a w `scope.sources`
konkretny URL BEA z ValueError; nie ma udanego receipt GDP.

`calendar_readings.bind_events` wymaga własnego receipt dla GDP **second,
third, updated**, ale nie Advance. Dla tego Advance potwierdzony harmonogram,
właściwy kwartalny poziom i aktualizacja dostawcy z dnia publikacji wystarczyły,
aby później pokazać 3.369619%. Naprawa samego parsera nie dałaby liczby o 13:53,
gdy lokalnie nie było Q3, i nie omija zależności od FRED. Usuwa jednak realny
błąd statusu i przyszłe ryzyko blokady innych etapów.

Obecna ogólna bramka current-vintage GDP/PIO porównuje datę `last_updated`,
nie pełną chwilę publikacji jak nowe dedykowane adaptery. W ewentualnej
naprawie nie wolno osłabiać walidacji do „dzisiaj” lub samego zegara:
potrzebne są właściwy okres, etap i dowód źródła. To ryzyko ogólnej logiki,
nie dowód fałszywego Actual w opisanym incydencie.

## 7. Frontend i znaczenie „sprawdzono część źródeł”

`useBackgroundRefresh` pyta o start na wejściu. Gdy zadanie jest running,
odpytuje jego status co 2 s. Po zakończeniu, jeśli `publication_id` różni się
od `data_revision`, wykonuje `operations.load`, a Calendar pobiera ponownie
GET z `include_readings=true`. Kod **ma mechanizm przełączenia na nową generację**;
nie wykazano, że stale renderuje poprzednią po poprawnie wykrytym zakończeniu.

Jest jednak luka samoczynnego ponawiania: po complete/partial/idle hook zapisuje
`nextCheck`, ale **nie planuje timera na tę chwilę**. Następna próba wymaga
focus, visibilitychange lub ponownego montowania. Karta stale widoczna może
pozostać na starej generacji także po upływie 15 minut. Backend sam nie
uruchamia zadania o godzinie publikacji. Istniejący test sprawdza kolejny
focus po 900 s, nie bierne pozostawienie widocznej karty. Nie ma logu zdarzeń
użytkownika pozwalającego dowieść, że to wywołało dzisiejsze pierwsze 20 minut.

Calendar czyta obserwacje i dowody w spójnej transakcji REPEATABLE READ;
nie przechowuje pełnego odczytu Calendar w cache Overview. Znacznik generacji
służy także frontendowi do decyzji o ponownym GET. Metadane kontroli FRED
zapisywane są niezależnym połączeniem: sukces pojedynczego check może istnieć
przed zatwierdzeniem zbiorczej transakcji obserwacji. Nie dowodzi wtedy
dostępności Actual dla czytelnika.

Semantyka pól:

- `check.status`: kompletność sprawdzenia wymaganych zasobów i ich zakresu,
  a nie kompletność wyników nowych publikacji. Udana odpowiedź FRED ze starym
  `observation_end` nadal jest udanym availability check.
- `checked_at`: konserwatywnie najstarszy dostępny czas kontroli pokrycia
  wymaganych zasobów; nie czas najnowszego wyniku, ostatniego joba lub kursu.
  Przy partial może dotyczyć tylko podzbioru źródeł.
- `checked_count` / `required_count`: w agregacie Overview liczba zasobów z
  udanym dowodem pokrycia względem liczby wymaganych. Nie liczba dzisiejszych
  Actual. Obecne zachowane Overview ma **40/42**, partial, checked_at
  **11:38:58 PL**, mimo zakończenia zadania o 14:26.
- Calendar używa osobnego `scoped_check`: `sources`, `range_status`,
  `required_resources` i minimum checked_at. **Nie zwraca tych dwóch count**;
  nie wolno przypisać mu 40/42 z Overview. Obecny GET dla dnia i tygodnia ma
  partial, checked_at **13:53:31.977853 PL**, a `calendar:periods` partial
  bez udanej kontroli pokrycia. Inne wymagane zasoby mają range_status success.
- Status serii `success` i wynik joba `unchanged` oznaczają poprawną kontrolę
  bez zmiany danych. `cached` oznacza wykorzystanie kontroli w interwale;
  `skipped` brak próby, np. po backoff; `error` nieudaną próbę.
- Status koordynatora `partial` obejmuje źródła niepełne/błędne i pokrycie
  całego Overview; nie jest synonimem błędu GDP. Ostatni wynik miał FRED success,
  wolne zasoby cached i nadal niepełne pokrycie.
- Data najnowszej obserwacji jest okresem statystycznym (`observation_date`),
  a `vintage_date` datą wersji. Żadna nie jest czasem ukończenia refresh.

Zgłoszonej przez użytkownika etykiety „13:50” nie odtworzono z historycznej
odpowiedzi UI. Taki czas występuje w znaczniku początku zadania oraz
`checked_at` poszczególnych dowodów okresów, które adapter stempluje wspólnym
czasem startu, choć pobiera je później. Nie jest to wystarczający dowód,
z którego dokładnie pola tamta etykieta pochodziła. Obecny kod nagłówka
Calendar korzysta z `check.checked_at`, a nie po prostu z `refresh.attempted_at`.

Komunikat „sprawdzono część źródeł” jest prawdziwy w sensie pokrycia, lecz
sam nie informuje, czy sprawdzono GDP, czy FRED miał Q3 i czy commit już
udostępnił dane. Proponowane szczegóły konkretnego wiersza:

> GDP Q3 Advance: brak nowej obserwacji. Ostatnia kontrola FRED: 13:52:18;
> ostatni potwierdzony okres: Q2. Wersja danych: [rzeczywista data wersji].
> Dokument BEA: dostępny, weryfikacja daty zakończona błędem parsera.
> Następna kontrola: [termin backendu]; Actual nie został potwierdzony.

Po aktualizacji trzeba pokazać osobno okres Q3, wersję current-vintage,
czas zakończenia kontroli i czas publikacji generacji. Nie nazywać tego
first print ani gwarantowaną aktualnością na minutę publikacji.

## 8. Bezpośrednie oficjalne źródła BEA

[Harmonogram BEA](https://www.bea.gov/news/schedule/full) potwierdza oba
raporty 29.10 o 08:30. Własny [GDP Advance Q3](https://www.bea.gov/news/2026/gdp-advance-estimate-3rd-quarter-2026)
potwierdza **3.4% q/q SAAR**, poprzednie **2.2%**, kwartał i etap. Zawiera
czytelną tabelę HTML oraz odnośniki do pełnego PDF, porównań XLSX i historii
wersji. Tabele interaktywne mogą być później zastąpione; wydawca wskazuje archiwum.

[PIO September](https://www.bea.gov/news/2026/personal-income-and-outlays-september-2026)
podaje headline PCE m/m **0.5%**, core **0.3%**, core r/r **3.1%**, real PCE
**0.0% po zaokrągleniu** (tekst: wzrost poniżej 0.1%), real DPI **−0.3%**
i saving rate **3.8%**. Są zgodne z zaokrągleniem wyników lokalnych. Raport
odróżnia miesięczne zmiany, roczne zmiany oraz poziom saving rate; opisuje
rewizje VII/VIII. Nie wolno użyć nominalnego DPI lub PCE zamiast realnego.

Sprawdzono w pamięci cztery bezpośrednie odpowiedzi: dwa powyższe HTML oraz
rzeczywiście podlinkowane [GDP Historical Comparisons XLSX](https://www.bea.gov/sites/default/files/2026-10/hist3q26-adv.xlsx)
i [PIO Historical Comparisons XLSX](https://www.bea.gov/sites/default/files/2026-10/pi0926-hist.xlsx).
Wszystkie **HTTP 200** około **15:52:37 PL**. Pliki XLSX mają prawidłowy ZIP/XML,
odpowiednio **16747 i 14018 bajtów**. Rozpoznane tytuły potwierdzają materiały
porównań historycznych: **nie są automatycznie pełnym źródłem wszystkich
poziomów**, które można bez kontroli zastąpić za Exhibit 1 lub za tabele NIPA.
Treści nie zapisano; nie powstał importer ani obserwacje.

Nagłówki HTML: Last-Modified 14:44:47/54 UTC; XLSX: 11:11:26/11:07:32 UTC,
także ETag obecny. Część czasów plików wyprzedza godzinę publikacji; **nie
oznacza to, że były publicznie dostępne przed embargo**. Nagłówek modyfikacji
nie jest chwilą pierwszego dostępu ani dowodem wersji statystycznej.
Nie obserwowano tych endpointów na żywo o 13:30 i brak SLA ich równoczesnej
aktualizacji. Pierwsza próba HTTP z sandboxa miała ConnectError; diagnostyczne
odczyty po uzyskaniu dostępu sieciowego przeszły. Nie przypisano tego BEA.

[Oficjalne API BEA](https://apps.bea.gov/api/signup/) i jego
[instrukcja](https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf)
opisują NIPA oraz format JSON/XML, z kluczem uzyskanym przez rejestrację.
Nie rejestrowano konta i nie wykonywano zapytań z cudzym kluczem. Kandydaci
do jawnego mapowania to GDP tabela 1.1.1, PIO 2.6, real PCE 2.8.1/2.8.6,
ceny PCE 2.8.7 i dynamiki roczne 2.8.11 — odnośniki pochodzą z raportów.
Identyfikatory API/linie/SA i jednostki trzeba zweryfikować metadanymi przed
implementacją; nie deklarujemy tutaj przetestowanego feedu API.

Bezpośredni parser własnego HTML/PDF może pozyskać opublikowane, zaokrąglone
wyniki bez czekania na FRED; API/tabele umożliwiają dokładniejsze wejścia.
Te kanały wymagają uzgodnienia miesiąca/kwartału, etapu, jednostek i wersji.
Zmiana zaokrąglonego 3.4 na wyliczone 3.369619 nie może być ukrytą zmianą
źródła lub traktowaniem tych liczb jako identycznej dokładności. Własny receipt
powinien zachowywać URL, bajty/hash, fetched_at, datę/etap i dokładność wyniku.
Kolejne Second/Third i rewizje Previous muszą mieć odrębną tożsamość dowodu.

[BEA FAQ 147](https://www.bea.gov/help/faq/147) dopuszcza użycie i reprodukcję
własnych materiałów public-domain, o ile nie wskazano inaczej, i prosi o
atrybucję. To lepsza podstawa bezpośredniego źródła niż założenie, że dostęp
FRED usuwa wszystkie warunki. Nadal należy respektować wyjątki, zasady API,
źródło, własne modyfikacje i brak endorsement. Nie rozstrzyga to istniejącego
modelu FRED/PostgreSQL/RAW/cache ani publicznej gotowości całego MacroLens.

Nie użyto Investing jako źródła danych ani konsensusu. Jego zgłoszone 3.4%
jest tylko kontekstem użytkownika; wynik niezależnie potwierdzono w BEA.

## 9. Porównanie wariantów i minimalne zalecenie

| Wariant | Co skraca / czego nie gwarantuje | Provenance, first print i ryzyko Actual | Koszt i zakres | Wymagane testy |
| --- | --- | --- | --- | --- |
| **A. Naprawa istniejących błędów** | Timer na `next_check_at` dla widocznej karty usuwa zależność od kolejnego focus. Parser daty z własnego nagłówka embargo usuwa ValueError BEA. Nie przyspiesza publikacji FRED; sama naprawa parsera nie odblokuje brakującego Q3. | Zachować etap/kwartał/datę/strefę; nie zastępować dowodu samym dniem pobrania. Nie wytwarza historii first print. | Hook + testy oraz parser + fixture oficjalnej struktury; diagnostyka konkretnej miary. Timer przestrzega backendu, bez nowego szybkiego pollera. | Bierna widoczna karta, hidden/unmount, race generacji, daty tylko w embargo, obcy kwartał/etap/data i konflikt źródeł. |
| **B. Ograniczone ponawianie po publikacji** | W krótkim oknie pytać tylko GDPC1 / właściwe PIO / Claims, gdy brakuje nowego okresu; kontrolowany download nawet przy niezmienionych metadanych może wykryć rozjazd endpointów. Nie gwarantuje, że dostawca ma już wynik. | Nowy okres i własne potwierdzenie raportu/etapu wymagane; sam timestamp/hash nie wystarcza. FRED snapshot nadal current-vintage, nie first print. | W istniejącym jobie, wspólny lock, limit prób, expiry okna i 429/backoff. Osobna decyzja o krótszym odstępie; nie obniżać globalnie wszystkich interwałów. Jedna próba metadanych = 1 żądanie na serię, z obserwacjami co najmniej 2; obecnie pełna lokalna historia może kosztować więcej i wymaga paginacji. | Metadata stare / observations nowe, oba stare, częściowy PIO, same rewizje, zły etap, cooldown, 429, brak konsensusu, koniec okna. |
| **C. Bezpośredni BEA GDP/PIO** | Usuwa czekanie na pośrednictwo FRED dla BEA; przy dostępnej stronie może dać opublikowany wynik wcześniej. Nie gwarantuje aktualizacji HTML/API w sekundę publikacji, nie rozwiązuje Claims. | Własne źródło/receipts i wersje; jawna dokładność komunikatu, uzgodnienie z tabelami. Prospektywne przechwycenie od wdrożenia, bez syntetycznej historii first print. Największe ryzyko to zły etap/okres, nominalne zamiast realnych i kwartalne PCE zamiast miesięcznego. | Nowy adapter/binding pod istniejącym koordynatorem i magazynem dokumentów; bez nowej usługi. Zwykle harmonogram + 1–2 własne raporty i ograniczone tabele/API; dokładny budżet zależy od wybranego kanału. | HTML/PDF/API, zaokrąglenia, etapy, rewizje i archiwum, sprzeczne kanały, rollback/idempotencja, prawa/atrybucja i brak FRED fallbacku udającego BEA. |

**Zalecana kolejność:** osobno zlecona, mała naprawa **A**, z per-miara
diagnostyką, następnie decyzja o ograniczonym **B**, jeżeli priorytetem jest
szybsze śledzenie FRED. Jeżeli wymaganiem jest oficjalny wynik bez zależności
od opóźnienia FRED, potrzebne jest **C**, a nie sama zmiana 15 minut na mniejszą
liczbę. A i B nie mogą zapewnić 3.4% przed udostępnieniem właściwych danych
przez ten kanał. Żadnego wariantu nie wdrożono w tym audycie.

## 10. Plan testów publikacyjnych offline

1. Zegar IANA: 29.10.2026 08:30 EDT = 13:30 PL; oddzielnie tygodnie DST,
   bez zmieniania historycznych offsetów FRED `-05` na strefę NY.
2. Sekwencja: przed terminem, 13:52 GDP metadata Q2, później Q3; zachować
   pusty Actual, prawidłowe Previous i brak Forecast. Odrębne PIO/Claims.
3. Symulacja opóźnionych metadanych: obserwacje Q3 już istnieją, metadane
   stare; ograniczone ponowienie nie importuje innych rodzin ani ALFRED.
4. Rzeczywista struktura GDP HTML: data wyłącznie w embargo; kontrola
   kwartału, Advance/Second/Third, weekday, zegara i strefy; brak/konflikt dat
   oznacza brak potwierdzenia, bez fallbacku do daty żądania.
5. Osobne warunki Advance i kolejnych etapów. Nowy timestamp przy starym
   kwartale/dokumencie nie tworzy Actual; nowa rewizja Q2 nie jest Q3.
6. PIO: indeksy cen vs nominalne/realne poziomy, m/m vs r/r vs kwartalne SAAR,
   saving rate jako poziom. Wymagane dokładne miesiące i spójne wersje par.
7. Claims: tygodnie 24.10 i 17.10, osobne Previous, rewizje i wyjątki dat.
8. Atomowość: sukces source_check przed commit nie publikuje częściowej
   generacji. Opóźniony inny dostawca/rollback pozostawia poprzednią generację.
9. Cooldown, request budget, 429/Retry-After, timeout, zajęty lock, crash/restart,
   limit prób po publikacji i wyjście z okna. Brak lawiny po focus wielu kart.
10. React z fake timers: karta stale widoczna przez następny termin, hidden,
    focus, unmount/abort, opóźnione odpowiedzi, zmiana zakresu i atomowy reload
    po nowym publication_id; żadnej konieczności ręcznego przeładowania.
11. Statusy: success/unchanged ze starym observation_end, partial pokrycia,
    cached/skipped/error; etykieta kontroli nie staje się „wynik aktualny”.
12. Dla C: poziomy/zaokrąglone komunikaty, brakujące kanały, własne wersje,
    idempotencja, prawidłowe receipts/RAW/rollback i obowiązki atrybucji.

To plan, nie nowo wykonany zestaw testów. Pełnych testów backendu/frontendu,
buildu i CI nie uruchamiano: produkcyjny kod nie został zmieniony. Wykonano
read-only SQL, porównanie wejść RAW z API, odtworzenie ValueError istniejącym
parserem oraz ograniczoną kontrolę oficjalnych źródeł w pamięci.

## 11. Nierozstrzygnięte kwestie i końcowy Git

Nie ustalono pierwszej chwili dostępności Q3 w FRED observations, przyczyny
braku wcześniejszego żądania refresh, historii locka w chwili publikacji ani
zdarzeń focus/reload i dokładnego payloadu użytkownika o 13:53. Nie odtworzono
etykiety 13:50 z dawnej odpowiedzi. Nie ma dowodu SLA BEA/FRED ani kompletnej
historii intraday. Wskazane błędy aplikacji są potwierdzone kodem i zapisanym
HTML; ich dokładnego udziału w czasie widocznym dla użytkownika nie zawyżamy.

Pozostają current-vintage, rewizje, brak konsensusu i pełnej historii first print,
BLS 403 i nierozstrzygnięte warunki istniejącego FRED/PostgreSQL/RAW/cache.
Nie deklaruje się publicznej gotowości aplikacji. Nie rozpoczęto Vite optimization,
PostgreSQL w CI, nowego importera ani zmiany częstotliwości.

Końcowy kontrolowany zakres: **jeden nowy dokument tego audytu**;
HEAD `6f31b99005e6941141de52f604fb780927538be9`, gałąź `main`, staging pusty.

```text
 M README.md
 M frontend/src/brief/SourceCheckStatus.test.tsx
 M frontend/src/brief/SourceCheckStatus.tsx
 M frontend/src/styles.css
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
?? docs/audits/calendar-release-day-latency-2026-10-29.md
```

Pięć wcześniejszych plików pozostaje byte-identycznych względem początku
diagnozy. Nie zapisano nowych RAW, skryptów pomocniczych, sekretów ani danych
z diagnostycznych pobrań BEA. Bez stagingu, commita, pusha i zmian bazy.
