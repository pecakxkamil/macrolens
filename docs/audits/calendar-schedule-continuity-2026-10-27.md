# MacroLens — ciągłość przyszłych harmonogramów, etap 1B

Zakres odniesienia: **27.10.2026–25.01.2027 (90 dni naprzód)** oraz dodatkowo
**do 31.01.2027**. Kontrolowane pobranie harmonogramów: 27.10; walidację domknięto
po wznowieniu 28.10. Nazwa dokumentu zachowuje datę etapu wskazaną w zadaniu.
Gałąź `main`, HEAD `be0800d`. Bez commita, pusha, stagingu, resetu i clean.

## Przyczyna i naprawa

Brak styczniowych dat nie wynikał wyłącznie z niepełnej listy FRED:

1. SQL zwracał szablony publikacji bez daty FRED tylko dla siedmiu identyfikatorów
   BLS/Retail/G.17. Dla M3, NRC i pozostałych grup z pustym styczniowym zakresem
   nie było nawet szablonu, do którego można dołączyć dowód wydawcy.
2. `apply_bls_schedule` projektował tylko BLS i Retail/G.17. Dowody M3 07.01
   i NRC 20.01 istniały, ale nie mogły samodzielnie utworzyć wydarzeń.
3. Wcześniejsze dowody BLS miały ograniczony horyzont. Samo rozszerzenie SQL
   nie mogło potwierdzić brakujących miesięcy/godzin.
4. Ogólna tożsamość `(release_id, reference_period)` nie wystarczała do zachowania
   jednocześnie advance/full M3, initial/revised permits i etapów GDP. Część
   adapterów zastępowała całą listę źródła, tracąc nieobecne w krótszej odpowiedzi
   okresy zamiast zachowywać ich dowody.

Naprawiono istniejącą projekcję, bez drugiego kalendarza i bez nowych rodzin:

- SQL pobiera szablony wszystkich aktywnych, skonfigurowanych mapowań; brak
  daty nie tworzy sam z siebie wydarzenia.
- Wspólny selektor obejmuje dotychczasowe BLS oraz istniejące publikacje
  Census, BEA i Chicago Fed. Odrzuca nieobsługiwane rodziny i szacowane metody.
- Tożsamość oficjalnej publikacji zawiera grupę, potwierdzony okres i etap.
  `event_id=release:<id>:<period>:<stage>` nie zmienia się po przesunięciu terminu.
  Nadpisanie klucza FRED `(release_id, release_date)` deduplikuje tę samą datę.
- Starsze daty tego samego logicznego raportu są usuwane z aktywnej projekcji
  po udokumentowanym przesunięciu, a poprzednie dowody pozostają w historii.
- Reguła DOL tworzy daty wyłącznie w swoim potwierdzonym zakresie, z wyjątkami
  i anulowaniem zwykłych czwartków. ICSA i CCSA zachowują osobne tygodnie.
- Miesięczne G.17 zachowuje istniejącą udokumentowaną regułę okresu. Osobny,
  jawnie opisany w źródle termin **rocznej rewizji 24.11 o 12:00 NY / 18:00 PL**
  jest również widoczny w tej samej grupie. Nie otrzymuje pojedynczego miesięcznego
  Actual/Previous ani wymyślonego okresu; korzysta z istniejącej obsługi wydarzeń
  bez wyniku liczbowego. Nie jest nową grupą ani nową miarą.

Pozostawiono nazwę funkcji `apply_bls_schedule` dla zgodności istniejących
wywołań i testów. Nie zmieniono konfiguracji serii, gwiazdek, transformacji,
zasad liczbowego Actual/Previous, MCI/PIT ani istniejącej integracji ISM/FOMC.

## Oficjalne dowody i BLS 403

Sprawdzono następujące oficjalne strony, bez obchodzenia blokad:

- [BLS — styczeń 2027](https://www.bls.gov/schedule/2027/01_sched_list.htm)
- BLS: [Employment](https://www.bls.gov/schedule/news_release/empsit.htm),
  [CPI](https://www.bls.gov/schedule/news_release/cpi.htm),
  [PPI](https://www.bls.gov/schedule/news_release/ppi.htm),
  [ECI](https://www.bls.gov/schedule/news_release/eci.htm),
  [JOLTS](https://www.bls.gov/schedule/news_release/jolts.htm)
- [Census M3](https://www.census.gov/manufacturing/m3/release_schedule.html)
- [Census SOC/NRC, revised permits i new home sales](https://www.census.gov/construction/soc/schedule.html)
- [Retail](https://www.census.gov/retail/release_schedule.html),
  [G.17](https://www.federalreserve.gov/releases/g17/default.htm) i jego
  [metodologia okresu](https://www.federalreserve.gov/releases/g17/OMB/2026/OMB_2026.htm)
- [BEA](https://www.bea.gov/news/schedule/full) i
  [Chicago Fed](https://www.chicagofed.org/research/data/data-release-calendar)

Bezpośredni klient HTTP ponownie otrzymał **403** dla styczniowej strony BLS.
Oficjalne tabele były czytelne przez narzędzie WWW. Dodano **11 jednorazowo
sprawdzonych wierszy** w `config/calendar_period_evidence.json`: Employment,
CPI i PPI XI–I oraz ECI 30.10 i 29.01. Dowód zawiera URL, datę, okres, godzinę,
strefę NY, czas sprawdzenia **2026-10-27T19:56:05+00:00**, ograniczony zakres
przeglądu, `confirmation_type=one_time_official_review` i opis dostępu.
Styczniowe terminy są dodatkowo zgodne z miesięczną listą BLS.

Nie przypisano tym wierszom fikcyjnego RAW/hash ani sukcesu automatycznego
pobrania. Zapisana odpowiedź 403 jest diagnostyką błędu, nie dokumentem
potwierdzającym harmonogram. Automatyczne adaptery BLS nadal zachowują ostatnie
poprawne dowody po błędzie; nie deklarujemy działającej automatycznej synchronizacji.
Nie importowano całego rocznika 2027 tylko dlatego, że część tabel jest szersza.
JOLTS na odczytanej stronie kończy się publikacją 01.12; stycznia nie wyliczono.

Istniejące adaptery Census/BEA/Chicago/Retail/G.17 wykonały kontrolę
**2026-10-27T19:57:06.663146+00:00**. Wszystkie siedem żądań harmonogramów
(wliczając metodologię G.17) zakończyło się poprawnym rozpoznaniem źródła.
Zachowano rzeczywiste bajty odpowiedzi, SHA-256, URL, czas, status HTTP i ścieżkę RAW.
Roczny termin G.17 odczytano ponownie z tego samego zapisanego RAW, bez nowego pobrania.

Kontrola była ograniczona do wskazanych wydawców i harmonogramów, z
`include_results=False`. Jej metadane są **partial / publisher_scope_partial**,
ponieważ nie potwierdza automatycznie BLS ani całego zakresu zwykłego joba.
Nie przedstawiono pobrania wybranych stron jako pełnego sprawdzenia kalendarza.

## Potwierdzone terminy w rzeczywistej projekcji

Wszystkie godziny PL przeliczono przez IANA `America/New_York` → `Europe/Warsaw`.

| Publikacja / etap | Data | NY | PL | Potwierdzony okres |
| --- | --- | --- | --- | --- |
| M3 full | 07.01.2027 | 10:00 | **16:00** | XI 2026 |
| Employment Situation | 08.01.2027 | 08:30 | **14:30** | XII 2026 |
| CPI | 13.01.2027 | 08:30 | **14:30** | XII 2026 |
| PPI | 14.01.2027 | 08:30 | **14:30** | XII 2026 |
| Retail advance | 15.01.2027 | 08:30 | 14:30 | XII 2026, istniało wcześniej |
| G.17 monthly | 15.01.2027 | 09:15 | 15:15 | XII 2026, istniało wcześniej |
| NRC — starts i initial permits | 20.01.2027 | 08:30 | **14:30** | XII 2026 |
| Revised permits | 27.01.2027 | 08:00 | **14:00** | XII 2026, wyłącznie PERMIT |
| M3 advance | 27.01.2027 | 08:30 | 14:30 | XII 2026 |
| New Home Sales | 27.01.2027 | 10:00 | 16:00 | XII 2026 |
| ECI | 29.01.2027 | 08:30 | **14:30** | IV kw. 2026 |
| Initial / Continuing Claims | 07, 14, 21, 28.01.2027 | 08:30 | 14:30 | Dwa odrębne tygodnie według udokumentowanej reguły DOL |

M3 advance/full i housing initial/revised mają osobne identyfikatory i etapy.
Rewizja PERMIT nie otrzymuje wiersza HOUST. „Poprzednio” nadal oznacza poprzedni
miesiąc, a nie wcześniejszy szacunek tego samego miesiąca; SAAR pozostaje bez zmian.
Dotychczasowe odrębne zasady kolejnych szacunków GDP nie zostały zmienione.

**Wszystkie styczniowe Actual i prognozy miar makro pozostają puste.**
Previous dla pięciu głównych dat też jest obecnie pusty: wymagane odczyty za
X/XI 2026 nie zostały jeszcze zapisane. Nie zastąpiono ich najnowszym odczytem
z Overview. Rzeczywisty listopadowy NFP nadal ma dostępne Previous, a fixture'y
sprawdzają poprawne porównanie z właściwym miesiącem oraz zachowanie zera.

## Inwentaryzacja 20 istniejących grup

„Wydawca” i „API” poniżej oznaczają ostatnią potwierdzoną/pokazaną datę
**w badanym rozszerzonym oknie do 31.01.2027**, nie ostatnią datę na świecie.
Kolumna DB to ostatnia zapisana data FRED w całej lokalnej `release_dates`.
Tę tabelę odczytano w transakcji `read_only=True`, `SHOW transaction_read_only=on`.
Nie wpisywano do niej brakujących dat; tworzy je projekcja dowodów.

| Grupa | Ostatnia data DB FRED | Ostatni potwierdzony termin wydawcy w oknie | Ostatni termin API | Luka / przyczyna |
| --- | --- | --- | --- | --- |
| Employment Situation | 04.12.2026 | 08.01.2027 | 08.01.2027 | Naprawiono okres/godzinę i brak daty FRED; BLS jednorazowo |
| CPI | 10.12.2026 | 13.01.2027 | 13.01.2027 | Jak wyżej; bez generowania kolejnych miesięcy |
| PPI | 15.12.2026 | 14.01.2027 | 14.01.2027 | Naprawiono brak daty FRED; BLS jednorazowo |
| ECI | 30.10.2026 | 29.01.2027 | 29.01.2027 | Dodano IV kwartał, poza pierwotnym 90-dniowym oknem |
| JOLTS | 01.12.2026 | 01.12.2026 | 01.12.2026 | Brak potwierdzonego stycznia w odczytanym harmonogramie, nie luka overlay |
| Claims | 31.12.2026 | 28.01.2027 | 28.01.2027 | Naprawiono projekcję udokumentowanej reguły; osobne tygodnie i wyjątki |
| Retail Sales | 16.12.2026 | 15.01.2027 | 15.01.2027 | Dotychczasowy overlay zachowany; bez dodatkowych miar |
| G.17 | 16.12.2026 | 15.01.2027 | 15.01.2027 | Monthly zachowane; dodatkowo jawny termin rocznej rewizji 24.11 bez pojedynczego odczytu |
| GDP | 23.12.2026 | 23.12.2026 | 23.12.2026 | Odczytana tabela BEA obejmuje 2026; stycznia nie zgadywano |
| Personal Income and Outlays | 23.12.2026 | 23.12.2026 | 23.12.2026 | Jak wyżej; brak nowego potwierdzonego styczniowego okresu/terminu |
| M3 | 23.12.2026 | 27.01.2027 | 27.01.2027 | Naprawiono whitelist szablonów i overlay, zachowano advance/full |
| NRC / revised permits | 23.12.2026 | 27.01.2027 | 27.01.2027 | Naprawiono whitelist/overlay, initial 20.01 i PERMIT-only 27.01 |
| New Home Sales | 23.12.2026 | 27.01.2027 | 27.01.2027 | Naprawiono tę samą ogólną lukę projekcji SOC |
| CFNAI | 21.12.2026 | 21.12.2026 | 21.12.2026 | Zapisany/odczytany harmonogram Chicago kończy się w XII; bez wnioskowania z miesięcznej częstotliwości |
| NFCI | 30.12.2026 | 30.12.2026 | 30.12.2026 | Brak potwierdzonej listy/okresów styczniowych; nie zastosowano samej częstotliwości tygodniowej |
| PMMS | 31.12.2026 | 31.12.2026 | 31.12.2026 | Oficjalny dostępny kalendarz PMMS obejmuje 2026; dotychczasowe ograniczenia bindingu/godzin pozostają |
| H.15 | 31.12.2026 | 31.12.2026 | 31.12.2026 | Miesięczny kalendarz Fed potwierdza XII; nie uzyskano styczniowego dowodu. Brak mapowania okresu/odczytu pozostaje |
| FOMC — rodzina decyzji i wydarzeń 1A | poza FRED | 27.01.2027 | 27.01.2027 | Data decyzji zachowana, styczniowa godzina niepotwierdzona. Konferencje/Minutes/SEP bez regresji |
| ISM Manufacturing | poza FRED | 01.12.2026 | 01.12.2026 | Dostępny potwierdzony rocznik 2026; brak dowodu 2027, nie luka nowego overlay |
| ISM Services | poza FRED | 03.12.2026 | 03.12.2026 | Jak wyżej |

Źródła dodatkowych granic: zapisane dowody FOMC/ISM z poprzednich etapów,
[PMMS publication calendar](https://www.freddiemac.com/pmms/docs/PMMS_Publication_Calendar.pdf)
oraz [grudniowy kalendarz Fed](https://www.federalreserve.gov/newsevents/2026-december.htm).
Tabela nie deklaruje, że poza odczytanymi źródłami nie istnieje inny harmonogram.

Automatyczne porównanie wybranych oficjalnych wierszy okresów z rzeczywistym API
wykazało **zero pominiętych potwierdzonych terminów** w zakresie 27.10–31.01.
To kompletność względem dostępnych zapisanych dowodów, nie gwarancja pełnego
pokrycia wszystkich przyszłych publikacji. API ma **137 wydarzeń** w tym oknie,
w tym 16 styczniowych; liczby obejmują także rutynowe H.15 i nie są miarą jakości.

## Konflikty, historia i automatyzacja

Reguły pierwszeństwa są jawne. BLS zachowuje dotychczasową kolejność:
konkretna tabela raportu, miesięczna lista, oficjalny feed, dowody przeglądu.
Dla pozostałych grup potwierdzony raport ma pierwszeństwo przed harmonogramem,
a harmonogram przed dowodem jednorazowym/regułą G.17. Aktualizacja tego samego
URL i tej samej tożsamości archiwizuje poprzednią wersję.

Sprzeczne równorzędne dowody nie są rozstrzygane datą pobrania: projekcja
oficjalnego wydarzenia jest wstrzymana, konflikt trafia do metadanych API.
Jeśli pozostała data FRED, jest jawnie oznaczona konfliktem, bez przypisania
oficjalnej godziny/okresu. W danych kontrolnych nie wystąpiły nierozstrzygnięte
konflikty; testy obejmują oba warianty rozstrzygania.

Adaptery wszystkich obsługiwanych wydawców upsertują tożsamości etapów zamiast
zastępować całą listę źródła. Krótszy harmonogram, 403/503 i błąd parsera nie
kasują ostatnich poprawnych okresów. Historia przesunięć trafia do
`publisher_history`/`bls_history`; rzeczywiste odpowiedzi RAW pozostają zachowane.

Nowa projekcja korzysta z istniejącego koordynatora, wspólnego advisory lock,
budżetu żądań, cooldown i atomowego pliku dowodów. Wersja adaptera wzrosła do 6,
aby stary cache nie udawał przetworzenia nowego zakresu. Zwykły job po synchronizacji
publikuje spójną nową generację Overview; nie dodano usługi ani pollingu.
Zakresowe metadane `calendar:periods` obejmują teraz także projekcje Census/BEA/Chicago.

Kontrolę wykonano przez rozszerzenie istniejącego `sync_periods` o wybór źródeł
i tryb harmonogramów bez wyników. Nie pobierano obserwacji, plików wynikowych M3,
historycznych DOL ani statementów Fed w tej kontroli. Poprawiono również filtr
zwykłego pobierania decyzji Fed: po etapie 1A wyłącznie `fomc_decision` może
uruchamiać parser statementu, nie data konferencji czy Minutes.

Cache Overview przebudowano z już zapisanych danych pod wspólną blokadą.
Ostatnia lokalna generacja użyta do kontroli:
`baa9fb07-d897-4a11-92dd-2844b9e35170`.

## Walidacja i ograniczenia

- Backend: **732 passed**; frontend: **534 passed** w 22 plikach.
  Wszystkie dotychczasowe testy zachowane. Bez pomijania testów i zwiększania timeoutów.
- Nowe offline fixture'y obejmują szablon bez daty FRED, deduplikację, konflikty,
  przesunięcie daty, idempotencję, krótszą odpowiedź, błąd źródła, BLS 403,
  pochodzenie jednorazowe, przejście roku, M3 advance/full, PERMIT-only revision,
  osobne tygodnie Claims, puste przyszłe Actual/Forecast, poprawne Previous i zero,
  odrzucenie szacowanych metod, datę rocznej rewizji bez wymyślonego wyniku.
- Dotychczasowe testy IANA/DST, FOMC i ISM przeszły. Rzeczywiste API nadal zwraca
  poprzednie ISM 54,5/54,9 pkt bez przyszłych Actual, Minutes 18.11 o 20:00 PL
  i konferencję 09.12 o 20:30 PL z pustymi miarami liczbowymi.
- Production build: **passed**, pozostało ostrzeżenie Vite o głównym pakiecie
  **507,82 kB** ponad 500 kB; progu nie zmieniano.
- Chrome bez fixture'ów odpowiedzi: **EN/PL, 1366 i 390 px**, 44 scenariusze,
  136 odpowiedzi rzeczywistego API HTTP 200, brak wyjątków JavaScript i overflow.
  Sprawdzono pięć wymaganych dat, 27/29.01, grudniowy full M3, listopadowe Previous,
  G.17 annual revision, źródła, szczegóły, filtr ★★★, Escape/fokus i limit czterech
  pozycji Overview. Obejrzano zrzuty desktop/mobile.
- Kontrola przeglądarki odbyła się pod wspólną blokadą, więc normalne POST aplikacji
  nie uruchomiły importerów innych dostawców. Nie podstawiano odpowiedzi API.
- W końcowej serii testów ujawniono zimne importy prawdziwych zagnieżdżonych tras
  Charts i Research/MCI podczas oczekiwania na DOM. Testy tras i MCI ładują teraz
  te rzeczywiste zależności podczas zbierania testów, tak jak istniejący test Charts.
  Nie dodano mocków aplikacji, nie zmieniono logiki MCI i nie zwiększono timeoutów.
  Końcowy pełny frontend przeszedł.
- Po wznowieniu usługi były wyłączone. Uruchomiono istniejący Docker Desktop,
  istniejący kontener `macrolens_postgres`, backend i Vite. Bez tworzenia/resetowania
  bazy i wolumenów. Pomocniczy Chrome używał osobnego ignorowanego profilu.
- `git diff --check`: passed. Ostrzeżenia Git o przyszłej normalizacji LF→CRLF
  w trzech plikach nie są błędami whitespace. Hashami potwierdzono zachowanie
  wcześniejszych README, SourceCheckStatus, styles.css, audytów oraz testów Fed.

Nie gwarantujemy pełnych 90 dni dla grup, których dostępny harmonogram kończy się
w grudniu. Nie działają automatyczne pobrania BLS mimo jednorazowego uzupełnienia.
Current-vintage nadal może zawierać rewizje; nie utworzono historii first printów,
konsensusu ani fikcyjnych prognoz. Nie zmieniono praw i ograniczeń ISM.

## Końcowy Git — wszystkie niezacommitowane pliki

Zastane i zachowane bez zmiany treści w tym etapie:

- `README.md`
- `app/analytics/fomc_calendar.py`
- `app/analytics/overview_check_scope.py`
- `app/analytics/overview_refresh.py`
- `app/ingestion/sync_fomc_calendar.py`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/brief/briefModel.ts`
- `frontend/src/brief/upcomingEvents.ts`
- `frontend/src/brief/upcomingEvents.test.ts`
- `frontend/src/calendar/calendarAgenda.ts`
- `frontend/src/styles.css`
- `tests/test_fomc_calendar.py`
- `tests/test_fed_events.py` (nowy z poprzedniego etapu)
- `docs/audits/calendar-coverage-2026-10-27.md` (nowy z poprzedniego etapu)
- `docs/audits/calendar-fed-events-2026-10-27.md` (nowy z poprzedniego etapu)

Zmodyfikowane/dodane w etapie 1B, z zachowaniem wcześniejszych zmian współdzielonych plików:

- `app/analytics/calendar_agenda.py`
- `app/analytics/calendar_evidence.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/release_calendar.py`
- `app/ingestion/bls_schedule.py`
- `app/ingestion/sync_calendar_periods.py`
- `config/calendar_period_evidence.json`
- `frontend/src/api/macrolens.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/i18n/pl.json`
- `frontend/src/navigation/routes.test.tsx`
- `frontend/src/macro-index/MacroIndexPage.test.tsx`
- `tests/test_calendar_schedule_continuity.py` (nowy)
- ten raport (nowy)

Razem: **26 modified, 5 untracked**. RAW, cache, lokalne dane i artefakty Chrome
pozostają ignorowane. Bez commita i pusha. Nie rozpoczęto kolejnej integracji.
