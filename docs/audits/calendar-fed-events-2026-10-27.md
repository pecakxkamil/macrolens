# MacroLens — konferencje FOMC, Minutes i SEP

Wdrożenie i weryfikacja: **27.10.2026**. Stan wyjściowy: `main`, HEAD
`be0800d`. Zachowano zastane zmiany README, SourceCheckStatus, jego testu,
styles.css i wcześniejszy raport pokrycia. Bez commita i pusha.

## Zakres i model

Istniejący importer `sync_fomc_calendar.py` zapisuje teraz w tym samym
harmonogramie trzy dodatkowe typy:

- `fomc_press_conference` — Konferencja prasowa FOMC, redakcyjne ★★★;
- `fomc_minutes` — Protokół FOMC, redakcyjne ★★;
- `fomc_sep` — Projekcje gospodarcze Fed (SEP), redakcyjne ★★★.

Decyzja `fomc_decision` i jej odczyty pozostają odrębne. Techniczne dzienne daty
FRED „FOMC Press Release” nadal są wykluczone. Dot plot jest częścią SEP,
bez osobnego wydarzenia ani dodatkowego odliczania.

Nowe identyfikatory łączą rok, kolejność regularnego posiedzenia w rocznym
harmonogramie i rodzaj wydarzenia. Przesunięcie daty lub godziny tego samego
posiedzenia nie zmienia identyfikatora powiązanego wydarzenia. API zawiera
`meeting_id`, daty początku/końca posiedzenia, osobne źródła daty/godziny,
`date_status`, `time_status`, `source_timezone`, `document_url`,
`document_status` oraz provenance harmonogramu: URL, czas pobrania i SHA-256 RAW.
Zmiany terminu/dokumentu zachowują poprzednią wersję w `history`; stare RAW
nie są usuwane. Zmiana struktury rocznej listy, np. wstawienie dodatkowego
regularnego posiedzenia przed istniejącymi, wymaga przeglądu tożsamości;
nieplanowane/notation meetings nie są automatycznie importowane.

Nowe typy mają `expects_numeric_result=false`, pustą listę `series` i `measures`.
Binding pomija dla nich obliczenia FRED/ALFRED i wartości Actual/Previous/Forecast.
Nie generuje komunikatów o brakującym wyniku liczbowym. FastAPI używa już
odpowiedzi słownikowej, bez osobnego modelu Pydantic kalendarza; rozszerzono
rzeczywisty kontrakt i typ `CalendarEvent` TypeScript. Nie potrzebowano migracji.

## Oficjalne źródła i osobne dowody

Wszystkie poniższe źródła sprawdzono 27.10.2026:

- [Roczny kalendarz FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm):
  posiedzenia 2026/2027, oznaczenie SEP gwiazdką, odnośniki do opublikowanych
  materiałów oraz daty publikacji historycznych Minutes.
- [Wrzesień](https://www.federalreserve.gov/newsevents/2026-september.htm):
  niezależny wiersz konferencji 16.09 o 14:30 czasu wydawcy.
- [Październik](https://www.federalreserve.gov/newsevents/2026-october.htm):
  decyzja 28.10 o 14:00, konferencja o 14:30 i Minutes 07.10 o 14:00
  dotyczące posiedzenia 15–16.09.
- [Listopad](https://www.federalreserve.gov/newsevents/2026-november.htm):
  Minutes 18.11 o 14:00, jawnie przypisane posiedzeniu 27–28.10.
- [Grudzień](https://www.federalreserve.gov/newsevents/2026-december.htm):
  decyzja 09.12 o 14:00, konferencja o 14:30 i Minutes 30.12 o 14:00
  dotyczące posiedzenia 08–09.12.

Strefa wydawcy: **America/New_York**. Konwersja do **Europe/Warsaw** korzysta
z IANA. 28.10 różnica wynosi pięć godzin, a 18.11, 09.12 i 30.12 sześć godzin.
Parser Minutes czyta konkretny termin i opis powiązanego posiedzenia; nie
generuje dat z odstępu trzech tygodni. Sprawdza miesiąc/rok strony, rodzaj
wiersza oraz jednoznaczność. Konfliktujące wiersze powodują błąd zamiast
arbitralnego wyboru. Godzina decyzji nie jest dowodem godziny SEP.

## Zapisany harmonogram i rzeczywiste API

Kontrolowana synchronizacja istniejącym importerem rozpoczęła się
**2026-10-27T19:00:57.659160+00:00**. Zapisano 28 wydarzeń: 16 decyzji,
3 konferencje, 3 Minutes i 6 SEP. Cztery z sześciu SEP dotyczą 2027 i mają
datę wynikającą z opublikowanego kalendarza, bez potwierdzonej godziny.
Nie wygenerowano konferencji 2027 z założenia o cykliczności.
Zakres nowych historycznych wydarzeń ograniczono do poprzedniego miesiąca;
przejście roku uwzględnia grudzień dla styczniowych Minutes. Bez odległego backfillu.

| Wydarzenie | Data | Godzina PL | Posiedzenie | Potwierdzenie | Dokument przy kontroli |
| --- | --- | --- | --- | --- | --- |
| Decyzja FOMC | 28.10.2026 | 19:00 | 27–28.10 | Data i niezależny zegar decyzji | Przyszły wynik nadal pusty |
| Konferencja FOMC | 28.10.2026 | 19:30 | 27–28.10 | Osobny wiersz miesięcznego kalendarza | Brak opublikowanych materiałów w rocznej liście |
| Minutes | 18.11.2026 | 20:00 | 27–28.10 | Konkretny termin i opis posiedzenia | Brak odnośnika do opublikowanego protokołu |
| Decyzja FOMC | 09.12.2026 | 20:00 | 08–09.12 | Data i zegar decyzji | Przyszły wynik nadal pusty |
| Konferencja FOMC | 09.12.2026 | 20:30 | 08–09.12 | Osobny wiersz miesięcznego kalendarza | Brak opublikowanych materiałów w rocznej liście |
| SEP | 09.12.2026 | **Niepotwierdzona** | 08–09.12 | Data z oznaczenia SEP; brak osobnego dowodu zegara | Brak odnośnika do opublikowanych projekcji |
| Minutes | 30.12.2026 | 20:00 | 08–09.12 | Konkretny termin i opis posiedzenia | Brak odnośnika do opublikowanego protokołu |
| Konferencja historyczna | 16.09.2026 | 20:30 | 15–16.09 | Roczny i miesięczny kalendarz | [Materiały konferencji](https://www.federalreserve.gov/monetarypolicy/fomcpresconf20260916.htm) |
| SEP historyczne | 16.09.2026 | **Niepotwierdzona** | 15–16.09 | Data i dokument; link nie ustala zegara publikacji | [Projekcje](https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm) |
| Minutes historyczne | 07.10.2026 | 20:00 | 15–16.09 | Dokładna data/godzina i opis posiedzenia | [Protokół](https://www.federalreserve.gov/monetarypolicy/fomcminutes20260916.htm) |

`document_status=available` oznacza odnośnik do materiałów konkretnego
wydarzenia opublikowany w oficjalnym rocznym kalendarzu. Nie oznacza pobrania
i sparsowania transkryptu, czasu pierwszej publikacji dokumentu ani gotowości
wszystkich późniejszych załączników. Ogólny link „live broadcast” nie jest
uznawany za opublikowany transkrypt. Brak odnośnika do dokumentu nie podważa
potwierdzonego terminu ani nie oznacza, że minione wydarzenie się nie odbyło.

Po synchronizacji przebudowano lokalną publikację Overview z zapisanych danych:
`2599ce74-338c-426c-a36c-8434bfa832ca`. Użyto istniejącej wspólnej blokady
koordynatora i ograniczonego budżetu żądań. Była to jawna jednorazowa kontrola
nowego zakresu integracji, nie przyspieszenie automatycznego interwału.
Zapisano czas tej próby w istniejących wersjach źródła Fed, więc kolejny zwykły
job respektuje odstęp od niej. Nie pobierano innych dostawców ani obserwacji.
Nie zmieniano ALFRED, transformacji, MCI/PIT ani metodologii current-vintage.

Rzeczywisty `GET /api/v1/calendar?...&include_readings=true` zwrócił HTTP 200
dla 28.10, 18.11, 09.12, 30.12 oraz historycznego zakresu 16.09–07.10.
Konferencje/Minutes/SEP mają puste miary, a decyzje zachowały odczyt target range
i dotychczasową metodologię Previous. SEP z niepotwierdzoną godziną ma UTC `null`.

## Automatyzacja, cache i błędy

Nowe wydarzenia korzystają z istniejącego `fed:calendar` w koordynatorze:
bez osobnej usługi/pollingu, z dotychczasowym cooldown, budżetem żądań i wspólną
blokadą. Po zwykłej synchronizacji koordynator buduje spójną nową publikację
Overview; odczyt Calendar korzysta z zapisanego pliku, bez połączeń do Fed.

Plik harmonogramu jest zastępowany atomowo. Ponowny identyczny import nie
duplikuje wydarzeń. Zmiany daty/godziny aktualizują to samo wydarzenie i zapisują
wersję poprzednią. Błąd głównego kalendarza nie zastępuje ostatniego poprawnego
pliku; błąd lub skrócona miesięczna strona nie usuwa potwierdzonych wydarzeń
i zegarów. RAW zachowuje także błędną odpowiedź, URL, czas i status HTTP.

Metadane kontroli rozróżniają `event_confirmed`, `schedule_changed`,
`document_available`, błędy poszczególnych stron, niepotwierdzone zegary
i brak dokumentu. Nieudane pobranie pozostaje nieudanym sprawdzeniem także
wtedy, gdy UI może nadal pokazać wcześniej potwierdzony termin. Harmonogram
może być częściowy z powodu przyszłych niepotwierdzonych godzin; nie jest to
błąd brakującego odczytu liczbowego. Zachowano kompatybilny istniejący kod
statusu `decision_times_unavailable`; szczegółowy zakres obejmuje nowe typy.

## Interfejs i Overview

Ta sama semantyczna tabela i istniejący układ mobilny. W pięciu polach liczbowych
nowych wydarzeń pojawia się neutralne „—”; szczegóły mówią „nie dotyczy”,
bez komunikatów Awaiting data lub brakującego konsensusu. Nazwy i opisy mają
tłumaczenia EN/PL. Szczegóły pokazują powiązanie z posiedzeniem, źródła,
strefę, status daty/godziny, dokument i provenance harmonogramu.

Wszystkie nowe typy należą do istniejącej kategorii Fed/financial conditions.
Gwiazdki korzystają ze wspólnej konfiguracji redakcyjnej w `upcomingEvents.ts`;
nie są oceną Fed. Filtr ★★★ ukrywa Minutes. Decyzja i konferencja pozostają
osobnymi wierszami i tożsamościami. UI sortuje chronologicznie; wydarzenie bez
godziny pozostaje na swoim dniu, po wydarzeniach z godzinami. Odliczanie pomija
niepotwierdzoną godzinę. Nie przywrócono stałego podświetlenia najbliższego wiersza.

Overview nadal wybiera najwyżej cztery wydarzenia w swoim oknie. Dodano tylko
priorytety nowych typów do istniejących reguł; dotychczasowa kolejność pozostałych
publikacji i limit pozostają zachowane. Osobny next FOMC decision nadal wybiera
wyłącznie decyzję, także po jej godzinie i przed następującą konferencją.

## Walidacja

- Pełny backend: **716 passed**. Pełny frontend: **532 passed**, 22 pliki.
  Bez pomijania testów lub podnoszenia timeoutów. Testy są offline: syntetyczne
  fixture'y HTML, MockTransport, fałszywe połączenia i istniejące blokady sieci/DB.
- Nowe testy: niezależne typy/zegary, powiązanie Minutes, SEP bez październikowego
  duplikatu, brak osobnego dot plot, DST marzec/październik/grudzień, przejście
  roku, niepotwierdzona godzina, dokument przed/po zmianie listy, idempotencja,
  zmiana terminu i posiedzenia, błąd dostawcy i zachowanie poprzedniej wersji,
  brak transformacji liczbowych, dotychczasowe decyzje, rzeczywisty kontrakt
  FastAPI w TestClient, filtry, Escape/fokus i cztery pozycje Overview.
- Production build: **passed**. Pozostało ostrzeżenie Vite o głównym pakiecie:
  **507,04 kB**, ponad próg ostrzegawczy 500 kB. Nie zmieniano progu.
- Prawdziwy Chrome i lokalne API, bez fixture'ów odpowiedzi: **EN/PL, 1366/390 px**,
  wszystkie cztery przyszłe daty kontrolne, wrzesień/07.10, szczegóły, źródła,
  filtr ★★★, Escape i powrót fokusu oraz Overview. **24 scenariusze**, 56 odpowiedzi
  API HTTP 200, brak wyjątków JavaScript i poziomego overflow strony, także
  po otwarciu szczegółów. Obejrzano zrzuty desktop/mobile. Testy filtrów kategorii
  i wykluczenia nieznanego zegara z countdown są również w automatycznych fixture'ach.
- Podczas kontroli UI utrzymywano wspólną blokadę odświeżania. Rzeczywiste
  żądania aplikacji były obsługiwane przez API, ale nie uruchamiały innych
  importerów. Nie podstawiano danych ani odpowiedzi koordynatora.
- SHA-256 provenance wszystkich nowych wydarzeń odpowiada zachowanym plikom RAW.
- `git diff --check`: passed. Pierwsze uruchomienie Vite w sandboxie nie mogło
  utworzyć tymczasowego pliku konfiguracji (EPERM); pełne testy i build wykonano
  skutecznie z uprawnieniami do jego utworzenia. Nie zmieniano konfiguracji testów.

## Ograniczenia i ręczne sprawdzenie

Nie znaleziono osobnego dowodu godziny grudniowego ani wrześniowego SEP;
pozostają bez zegara i bez countdown. Przyszłe 2027 daty SEP są jawne,
ale godziny i konferencje wymagają osobnych zapowiedzi. Dane harmonogramu mogą
się zmienić. Publiczna lista dokumentów nie ustala czasu późniejszego transkryptu.
Nie dodano parsera treści projekcji/dot plot ani liczbowych interpretacji Minutes.

Otwórz Calendar → Date range, wybierz kolejno 28.10, 18.11, 09.12 i 30.12.2026.
Sprawdź osobne godziny decyzji/konferencji, zegar „—” przy SEP, szczegóły i linki.
Włącz „Tylko ★★★”: Minutes powinny zniknąć; konferencje i SEP pozostać.
W aktualnym Overview konferencja 28.10 jest odrębna od decyzji; limit wynosi cztery.

Nie dodano ADP, Michigan, innych PMI, przemówień, Beige Book, SLOOS ani nowych
miar. Nie naprawiano harmonogramów BLS/M3/Housing na 2027. Istniejące ograniczenia
BLS 403, ISM, brak konsensusu oraz current-vintage pozostają bez zmian.

## Końcowy stan Git — pełna lista niezacommitowanych plików

Zastane, zachowane:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`
- `docs/audits/calendar-coverage-2026-10-27.md` (untracked)

Zmienione w tym etapie:

- `app/analytics/calendar_agenda.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/fomc_calendar.py`
- `app/analytics/overview_check_scope.py`
- `app/analytics/overview_refresh.py`
- `app/ingestion/sync_fomc_calendar.py`
- `frontend/src/api/macrolens.ts`
- `frontend/src/brief/briefModel.ts`
- `frontend/src/brief/upcomingEvents.ts`
- `frontend/src/brief/upcomingEvents.test.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/calendarAgenda.ts`
- `frontend/src/i18n/pl.json`
- `tests/test_fomc_calendar.py`
- `tests/test_fed_events.py` (untracked)
- ten dokument: `docs/audits/calendar-fed-events-2026-10-27.md` (untracked)

Razem: **19 modified, 3 untracked**. RAW, lokalny harmonogram, cache, profil
przeglądarki i zrzuty pozostają ignorowane. Nie wykonano stagingu, commita,
pusha, resetu, clean ani zmian istniejących commitów.
