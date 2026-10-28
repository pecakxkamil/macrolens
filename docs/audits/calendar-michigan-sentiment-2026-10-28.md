# MacroLens — etap 3A: University of Michigan Consumer Sentiment

Weryfikacja: **28.10.2026**, `main`, HEAD
`d77a10cffee9373e5bc5ada549bd3aec8b23aa08`. Wdrożono **kalendarz i metadane
oficjalnych odnośników, bez integracji wyników liczbowych**. Bez stagingu,
commita i pusha. Zachowano cztery wcześniejsze zmiany użytkownika; ich SHA-256
przed i po pracy są identyczne.

## Źródła i potwierdzone terminy

[Informacje o badaniu](https://data.sca.isr.umich.edu/survey-info.php) jawnie
odsyłają do harmonogramów
[2026](https://data.sca.isr.umich.edu/fetchdoc.php?docid=79628) i
[2027](https://data.sca.isr.umich.edu/fetchdoc.php?docid=81621).
Oba dokumenty zostały rzeczywiście pobrane i sparsowane: **24 wydarzenia na rok,
48 łącznie**, od 09.01.2026 do 17.12.2027. Nie zastosowano reguły piątków.
Przykładowo Final za marzec 2027 przypada **w czwartek 25 marca**.
Dokumenty roczne nie podają godziny publikacji.

[Strona główna](https://www.sca.isr.umich.edu/) zapowiada konkretnie
06.11.2026, Preliminary za listopad, o **10:00 ET**. Tylko temu wydarzeniu
przypisano zegar: IANA `America/New_York` → UTC **15:00** →
`Europe/Warsaw` **16:00**. Nie przeniesiono tej godziny na inne daty.
Obejrzane wrześniowe raporty również nie potwierdziły własnej godziny.

| Etap | Data | Miesiąc badania | Godzina PL | Odnośnik do dokumentu przy kontroli |
| --- | --- | --- | --- | --- |
| Preliminary | 11.09.2026 | IX 2026 | Niepotwierdzona | [Raport w archiwum](https://data.sca.isr.umich.edu/fetchdoc.php?docid=81974) |
| Final | 25.09.2026 | IX 2026 | Niepotwierdzona | [Raport w archiwum](https://data.sca.isr.umich.edu/fetchdoc.php?docid=82114) |
| Preliminary | 09.10.2026 | X 2026 | Niepotwierdzona | Brak zweryfikowanego linku do tego etapu |
| Final | 23.10.2026 | X 2026 | Niepotwierdzona | [Bieżące podsumowanie](https://www.sca.isr.umich.edu/), link zmienny |
| Preliminary | 06.11.2026 | XI 2026 | **16:00** | Brak zweryfikowanego linku do przyszłego raportu |
| Final | 20.11.2026 | XI 2026 | Niepotwierdzona | Jak wyżej |
| Preliminary | 04.12.2026 | XII 2026 | Niepotwierdzona | Jak wyżej |
| Final | 18.12.2026 | XII 2026 | Niepotwierdzona | Jak wyżej |

Dla każdego wiersza Actual, Previous i Forecast są `null`. API rozróżnia
potwierdzoną datę, niepotwierdzoną godzinę, dostępność odnośnika oraz
`result_integration_status=publisher_permission_required` / `result_status=restricted`.
Brak linku do październikowego Preliminary nie dowodzi, że publikacja się nie odbyła.
Nie jest opisywany jako oczekiwanie na publikację.

Pełny potwierdzony rok 2027:

| Miesiąc badania | Preliminary | Final |
| --- | --- | --- |
| I | 08.01 | 22.01 |
| II | 12.02 | 26.02 |
| III | 12.03 | **25.03** |
| IV | 09.04 | 23.04 |
| V | 07.05 | 21.05 |
| VI | 11.06 | 25.06 |
| VII | 16.07 | 30.07 |
| VIII | 13.08 | 27.08 |
| IX | 10.09 | 24.09 |
| X | 08.10 | 22.10 |
| XI | 05.11 | 19.11 |
| XII | 03.12 | 17.12 |

Wszystkie godziny 2027 pozostają niepotwierdzone. API dla 2028 zwraca
`not_published_in_checked_sources`, bez wygenerowanych wydarzeń. To stan
sprawdzonych źródeł, a nie twierdzenie o nieistnieniu jakiegokolwiek innego dokumentu.

## Dostępność wyników i warunki wykorzystania

Sprawdzono oficjalne [warunki Michigan](https://data.sca.isr.umich.edu/agreement.php)
**28.10.2026**. Dane podlegają prawom University of Michigan. Wydawca wskazuje
CC-BY-NC-ND dla określonych badań i ściśle wewnętrznego użycia oraz prosi
o atrybucję „Surveys of Consumers, Survey Research Center, University of Michigan”.
Przy redystrybucji przez platformę/dashboard i zastosowaniach komercyjnych
kieruje do kontaktu w sprawie licencji.

| Scenariusz | Podstawa i ograniczenie | Wniosek dla wyników MacroLens |
| --- | --- | --- |
| A. Prywatnie, lokalnie | Ściśle wewnętrzne, niekomercyjne użycie może mieścić się we wskazanej licencji, z jej warunkami i atrybucją. | Nie jest to bezwarunkowa zgoda na każdy sposób przechowywania, przetwarzania i późniejszego udostępnienia. Nie dodano importera. |
| B. Publiczne portfolio | Publiczny dashboard rozpowszechnia liczby; warunki przewidują kontakt z wydawcą. | Nie potwierdzono jednoznacznego uprawnienia; potrzebne wyjaśnienie/zgoda. |
| C. Publiczne API lub eksport | To redystrybucja danych, odrębna od czytania strony. | Brak potwierdzonej podstawy dla takiego udostępniania; konieczne ustalenie licencji. |
| D. Komercyjnie | Sprzedaż, produkt danych i komercyjne wykorzystanie wymagają uzgodnienia z wydawcą. | Nie deklarujemy uprawnienia ani gotowości komercyjnego demo. |

Nie wysyłano korespondencji i nie uzyskano osobnego pozwolenia.
Przyjęto wariant kalendarza i linków, bez liczb. To decyzja zakresowa,
nie opinia potwierdzająca zgodność prawną całej aplikacji.

[FAQ](https://data.sca.isr.umich.edu/faq.php) odróżnia aktualizację strony głównej
w terminie raportu od późniejszej dostępności w serwisie danych, cztery tygodnie
po końcowej publikacji miesiąca. To różne kanały dostępności.
[UMCSENT](https://fred.stlouisfed.org/series/UMCSENT) na FRED ma wskazane
prawa autorskie i miesięczne opóźnienie na żądanie wydawcy;
[MICH](https://fred.stlouisfed.org/series/MICH) również zastrzega opóźnioną
dostępność najnowszego wyniku. Nie dodano tych serii do katalogu ani bazy.
Żadnej z nich nie użyto jako historycznego Preliminary lub bieżącego first printu.

## Definicje planowanych miar — bez integracji liczb

[Oficjalny opis obliczania indeksów](https://data.sca.isr.umich.edu/fetchdoc.php?docid=24770)
rozróżnia:

- **Index of Consumer Sentiment**: indeks z pięciu pytań o finanse gospodarstwa,
  perspektywy gospodarcze i warunki zakupów dóbr trwałych; baza I kw. 1966 = 100.
  To punkty indeksu, nie odsetek optymistycznych respondentów.
- **Current Economic Conditions**: odrębny indeks bieżących finansów gospodarstwa
  i warunków zakupów dóbr trwałych.
- **Consumer Expectations**: indeks oczekiwanych finansów gospodarstwa oraz
  krótko- i długoterminowych perspektyw gospodarczych. Nie jest miarą oczekiwań cenowych.

[Metodologia oczekiwań cenowych](https://data.sca.isr.umich.edu/fetchdoc.php?docid=75433)
oraz [codebook](https://data.sca.isr.umich.edu/fetchdoc.php?docid=75439), str. 8,
odróżniają **medianę** od średniej:

- Year-Ahead Inflation Expectations: mediana oczekiwanej procentowej zmiany cen
  w ciągu następnych **12 miesięcy** (`PX1_MED`).
- Long-Run Inflation Expectations: mediana oczekiwanej rocznej zmiany cen
  w horyzoncie **następnych 5–10 lat** (`PX5_MED`), nie dokładnie pięć lat.

Żadna z pięciu miar nie ma tutaj obserwacji, transformacji ani nowego cache.
Przyszła ewentualna integracja prezentowałaby poziomy i właściwe jednostki,
bez automatycznej dynamiki m/m. Previous oznaczałoby poprzedni miesiąc,
nie niejawne porównanie Final z Preliminary tego samego miesiąca.
Forecast pozostaje pusty: brak zweryfikowanego konsensusu.

## Model, provenance i automatyzacja

Identyfikatory `michigan:YYYY-MM:preliminary` i `michigan:YYYY-MM:final`
oznaczają dwa etapy jednego miesiąca. Przesunięcie terminu nie zmienia ID.
API zachowuje `expects_numeric_result=true`, bez fikcyjnych liczbowych miar:
raport pozostaje liczbowy mimo niewdrożonej integracji jego wyników.
Binding omija FRED/ALFRED dla tych wydarzeń i nie pożycza danych z innych raportów.

Adapter `sync_michigan_calendar.py` korzysta z istniejącego koordynatora,
wspólnej blokady PostgreSQL, budżetu żądań i dotychczasowego wolnego interwału
(domyślnie 6 godzin), bez nowej usługi i pollingu. Zwykły job pobiera jawnie
podlinkowane roczne harmonogramy, metadane archiwum oraz zapowiedź na stronie
głównej. Nie pobiera PDF-ów raportów liczbowych. Po błędzie zachowuje ostatnie
poprawne dowody i rejestruje nieudaną próbę; kolejne próby respektują interwał.

Zapis jest atomowy. Idempotentny import nie duplikuje wydarzeń ani historii.
Zmiany daty, zegara lub linku zapisują poprzedni stan w `history`.
Krótsza lista/błąd źródła nie usuwa poprawnych wcześniejszych terminów.
Niezmieniona tabela roczna nie cofa nowszej jawnej zapowiedzi, gdy kolejne
pobranie strony głównej zawiedzie. Faktyczna zmiana daty w tabeli rocznej
unieważnia stary dowód godziny. Uszkodzony snapshot odrzucany jest w całości.

Kontrolowane pobranie rozpoczęto **2026-10-28T15:53:29.914865+00:00**.
Pięć żądań metadanych zakończyło się HTTP 200. Faktyczny SHA-256 PDF 2026:
`e182338606db89a6a6bd999a15e6dd9f65946f86ed7646cf05c20cc108cdfae1`;
PDF 2027:
`abc30043f4144c9ad971f418355a7cea7ca01a8f67209f1113f739701f579620`.
Wcześniejsze cztery diagnostyczne pobrania obejmowały wyłącznie te harmonogramy
i strony ich list, bez importowania raportów wynikowych.

`config/michigan_calendar_evidence.json` zawiera przejrzany zestaw faktów
z rzeczywistymi URL-ami, czasem, statusem HTTP i hashami odpowiedzi. Lokalne
RAW pozostają ignorowane. Treść strony głównej, zawierającej wyniki,
przetwarzana jest przejściowo wyłącznie w celu odczytu zapowiedzi/nagłówka:
**nie jest zapisywana**. Zachowano hash faktycznej odpowiedzi i jawne
`response_body_retained=false`, bez fikcyjnej ścieżki do jej RAW.

Archiwum potwierdza własny miesiąc/etap linku. Link do bieżącej strony za X Final
oznaczono `current_summary_link`: jest zmienny, nie jest archiwalnym dokumentem.
Po zmianie nagłówka nie pozostaje odnośnikiem do starego miesiąca.
Sam upływ terminu nie potwierdza dokumentu, wyniku ani prawa użycia liczb.

Podczas kontroli respektowano już uruchomiony zwykły job: pierwsza próba
przejęcia wspólnej blokady nie uruchomiła konkurencyjnego importera.
Własny przebieg dotyczył wyłącznie metadanych Michigan. Nie wykonano ingestion
obserwacji ani ALFRED. Metadane próby zapisano w istniejącym stanie koordynatora.
Cache Overview przebudowano ze zgromadzonych danych; końcowa generacja:
`b2383e44-1a14-4450-b672-26ed389e1171`.

## Interfejs i weryfikacja

Kalendarz ma jeden wiersz na etap, potwierdzony miesiąc przy nazwie i link
„Dane u wydawcy”. Szczegóły pokazują ograniczenie, warunki, dokument i źródła.
Nie pokazują pięciu pustych wierszy ani komunikatu „nie dotyczy” dla raportu
liczbowego. Kategorie: istniejąca Consumer, w filtrach „Growth and consumer”.
Wspólne gwiazdki redakcyjne: Preliminary ★★★, Final ★★. To klasyfikacja
MacroLens, nie ocena Michigan. Nie dodano CSS, kolumn ani reguł kolorowania.
Odliczanie wyklucza niepotwierdzone godziny; na dniu z inną wcześniejszą
publikacją nadal dotyczy najbliższej potwierdzonej grupy.
Overview zachowuje sześć kart i wybór najwyżej czterech wydarzeń.

- Backend: **855 passed**; frontend: **549 passed**, 22 pliki, blokada sieci
  zgodna z CI. Wszystkie wcześniejsze testy zachowane.
- Production build: poprawny. Pozostaje ostrzeżenie Vite o głównym pakiecie
  **519,14 kB**, powyżej **500 kB**; progu nie zmieniano.
- Nowe fixture'y są offline: syntetyczne PDF-y, lista dat oficjalnego
  harmonogramu i HTML zawierający wyłącznie metadane. Obejmują oba lata,
  etapy, stabilność ID, przesunięcie, powtórny import, brak kolejnego roku,
  zegary IANA/DST, dokumenty, awarie, zachowanie poprzedniej wersji,
  cooldown, zakres kontroli i blokadę wyników UMCSENT/MICH.
- Starsze testy konkretnych źródeł otrzymały izolację nowego, niezwiązanego
  źródła Michigan, analogiczną do istniejącej izolacji ISM. Nie osłabiono
  globalnych blokad sieci i bazy.
- Rzeczywiste API: osiem wskazanych dat, 25.03.2027 oraz brak wygenerowanego
  2028; poprawne etapy/miesiące, wszystkie liczby puste, bez fałszywego first printu.
- Chrome bez fixture'ów API: **36 scenariuszy**, EN/PL, **1366 i 390 px**,
  osiem dat i Overview. Końcowy przebieg: **80 odpowiedzi API HTTP 200**
  (poprzedni: 79), brak wyjątków JavaScript
  i poziomego overflow. Sprawdzono zegar, linki, ograniczenia, filtr ★★★,
  szczegóły, Escape i powrót fokusu; obejrzano zrzuty desktop/mobile.
  Bieżące siedmiodniowe okno Overview nie zawiera jeszcze 06.11; prezentację
  Michigan w jego przyszłym oknie sprawdzają osobne testy EN/PL, razem
  z oficjalnym odnośnikiem, miesiącem i zachowaniem sześciu kart.
- Jedna pełna próba frontendu ujawniła znany sporadyczny błąd nawigacji MCI:
  po kliknięciu pozostał Compare Data. Izolowany zestaw przeszedł **8/8**,
  ponowny pełny przebieg **549/549**. Przyczyna nie została potwierdzona.
  Nie zmieniano MCI, testów MCI ani timeoutów. Początkowe błędy nowych fixture'ów
  (kolejność etapów, nazwa okresu i reprezentacja braku countdown) poprawiono;
  żaden test nie został pominięty.
- `git diff --check`: poprawny. Git ostrzega o przyszłej normalizacji LF→CRLF
  w dwóch testach; nie jest to błąd whitespace.

Nie uruchamiano GitHub Actions: bez commita i pusha. Pozostają niepotwierdzone
godziny, ograniczona dostępność historycznych linków, brak licencji na integrację
wyników i brak konsensusu. Nie utworzono historii first printów.
Dotychczasowe BLS 403, current-vintage, ograniczenia intraday i nierozstrzygnięte
warunki modelu FRED/PostgreSQL/RAW/cache pozostają bez zmian.
Nie zmieniono istniejących odczytów Employment, Retail, Core PPI, FOMC ani ISM,
MCI/PIT, schematu bazy ani pozostałych rodzin.

## Końcowy Git i ręczna kontrola

`main` / `d77a10cffee9373e5bc5ada549bd3aec8b23aa08`.
**26 modified, 6 untracked**, nic staged. Bez commita, pusha, resetu i clean.

Zastane, zachowane bez zmiany treści:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`

Zmiany tego etapu:

- `app/analytics/calendar_agenda.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/michigan_calendar.py` — nowy
- `app/analytics/overview_refresh.py`
- `app/analytics/release_calendar.py`
- `app/analytics/source_checks.py`
- `app/ingestion/sync_michigan_calendar.py` — nowy
- `config/michigan_calendar_evidence.json` — nowy
- `frontend/src/api/macrolens.ts`
- `frontend/src/brief/EconomyBrief.tsx`
- `frontend/src/brief/EconomyBrief.test.tsx`
- `frontend/src/brief/briefModel.ts`
- `frontend/src/brief/upcomingEvents.ts`
- `frontend/src/brief/upcomingEvents.test.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/calendarAgenda.ts`
- `frontend/src/calendar/calendarPresentation.ts`
- `frontend/src/i18n/pl.json`
- `tests/fixtures/michigan_release_dates.json` — nowy
- `tests/test_michigan_calendar.py` — nowy
- `tests/test_bls_schedule.py`
- `tests/test_calendar_schedule_continuity.py`
- `tests/test_ism_calendar.py`
- `tests/test_overview_refresh.py`
- `tests/test_release_calendar.py`
- `tests/test_source_checks.py`
- ten raport — nowy

RAW, lokalne dane, cache, logi, profile Chrome i zrzuty pozostają ignorowane.
Ręcznie: Calendar → Date range → 06.11.2026, potem 20.11.2026. Sprawdź różne
etapy tego samego miesiąca, tylko pierwszy zegar 16:00, link i szczegóły,
filtr ★★★ (Final znika), EN/PL i Escape. Dla 23.10 link prowadzi do zmiennego
podsumowania, a nie archiwum. Nie rozpoczęto kolejnego etapu.


## Kontrola zamknięcia etapu — 28.10.2026

Ponownie przejrzano pełny diff, wszystkie 28 plików etapu oraz konfigurację
dowodów. Cztery wcześniejsze pliki użytkownika zachowały identyczne SHA-256
i są wyłączone z commita. Nie znaleziono innych niezwiązanych zmian.
Potwierdzono 24 wydarzenia na każdy rok, wyjątek 25.03.2027, osobne etapy,
puste wartości liczbowe i jedyny potwierdzony zegar 06.11. Zachowane RAW
odpowiadają rzeczywistym hashom w konfiguracji; nie pobierano nowych danych.

Doprecyzowano etykietę linku prowadzącego wyłącznie do ogólnego spisu:
„Raporty wydawcy” zamiast „Dane u wydawcy”, w Calendar i Overview.
Etykieta danych pozostaje przy zweryfikowanym odnośniku do dokumentu/podsumowania;
zmienny charakter bieżącej strony nadal jest jawny w szczegółach.
Daty i oficjalne odnośniki **nie stanowią licencji na publikację wyników Michigan**.
Nie dodano importera, wyników ani nowych funkcji i nie zmieniono metodologii.

Ponowna pełna walidacja working tree: backend **855 passed**, frontend
**549 passed**. W tym przebiegu nie wystąpił wcześniej opisany sporadyczny błąd
nawigacji MCI. Zachowano wszystkie testy i dotychczasowe timeouty.
Wynik nowego GitHub Actions po pushu wymaga oddzielnego potwierdzenia.


Production build working tree przeszedł; pakiet główny **519,21 kB**.
Po przygotowaniu i przeglądzie stagingu sprawdzono też jego dokładną kopię
z pozostałymi śledzonymi zależnościami: **549 passed** i poprawny build,
pakiet **521,25 kB**. Kopia nie zawiera czterech wcześniejszych zmian;
zachowuje szczegóły sprawdzenia Overview z HEAD. Ostrzeżenie ponad 500 kB
pozostaje jawne, bez zmiany progu. Także w tym przebiegu nie wystąpił błąd MCI.
Obie kontrole whitespace, także staged, przeszły. Zatwierdzany zakres to
28 plików tego etapu wymienionych wyżej; bez sekretów, lokalnych danych i RAW.
Sprawdzono ponownie wszystkie 18 archiwalnych odnośników względem zapisanej
oficjalnej listy: miesiąc i etap są zgodne. Nie wykonywano dodatkowego ingestion.
