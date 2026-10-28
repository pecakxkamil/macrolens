# MacroLens — etap 2C: dodatkowe odczyty Employment Situation

Weryfikacja: **28.10.2026**, gałąź `main`, HEAD
`437cc05e7bbe4a67b3940a1fe03797b809bf0186`. Bez stagingu, commita i pusha.
Punktem odniesienia były mapowania i audyty 1A/1B, Retail 2A oraz Core PPI 2B.
Cztery wcześniejsze zmiany użytkownika zachowano bez zmiany treści, co
potwierdzono SHA-256 przed i po pracy.

## Definicje, metadane i stan początkowy

| FRED | Pełna nazwa FRED | Źródło | BLS ID | Jednostka | Sezonowość |
| --- | --- | --- | --- | --- | --- |
| [CIVPART](https://fred.stlouisfed.org/series/CIVPART) | Labor Force Participation Rate | CPS, gospodarstwa domowe | LNS11300000 | Percent | Seasonally Adjusted |
| [U6RATE](https://fred.stlouisfed.org/series/U6RATE) | Total Unemployed, Plus All Persons Marginally Attached to the Labor Force, Plus Total Employed Part Time for Economic Reasons, as a Percent of the Civilian Labor Force Plus All Persons Marginally Attached to the Labor Force (U-6) | CPS, gospodarstwa domowe | LNS13327709 | Percent | Seasonally Adjusted |
| [AWHAETP](https://fred.stlouisfed.org/series/AWHAETP) | Average Weekly Hours of All Employees, Total Private | CES, pracodawcy | CES0500000002 | Hours | Seasonally Adjusted |

Wszystkie trzy są miesięczne, publikowane przez BLS w Employment Situation.
Sprawdzono rzeczywiste metadane i FRED series/release: **release 50**.
Walidator w istniejącym odświeżaniu sprawdza ID, dokładną nazwę, jednostkę,
częstotliwość i SA. Związek CPS/CES oraz kod BLS potwierdzono w opisach serii
i odpowiednich tabelach raportu. Nie przypisano całego raportu do jednego badania.

- CIVPART: cywilna siła robocza jako odsetek cywilnej ludności w wieku 16+
  poza instytucjami zbiorowego zamieszkania. To poziom stopy aktywności.
- U-6: bezrobotni + marginalnie związani z rynkiem pracy + pracujący w niepełnym
  wymiarze z przyczyn ekonomicznych, podzieleni przez cywilną siłę roboczą
  powiększoną o marginalnie związanych. Osoby marginalnie związane chcą i mogą
  pracować, szukały pracy w ciągu 12 miesięcy, ale nie w ostatnich 4 tygodniach.
  U-6 nie jest U-3, UNEMPLOY ani stopą zatrudnienia.
- AWHAETP: przeciętne tygodniowe opłacone godziny wszystkich pracowników
  prywatnych sektorów pozarolniczych. Nie jest serią production/nonsupervisory,
  samym przemysłem ani nadgodzinami. Godziny opłacone mogą obejmować płatne
  nieobecności; nie należy utożsamiać ich wyłącznie z czasem faktycznie przepracowanym.

Początkowy odczyt PostgreSQL był read-only. CIVPART i UNEMPLOY miały po
**2831 obserwacji/wersji**, od I 1948 do IX 2026, z mapowaniem release 50.
U6RATE i AWHAETP nie istniały w lokalnej bazie ani katalogu.
Wykorzystano istniejącą CIVPART i zachowano jej dotychczasowe transformacje.
UNEMPLOY nie dodano do wierszy tego etapu.

## Dane i istniejący pipeline

Przez istniejącego klienta FRED pobrano tylko nowe serie U6RATE/AWHAETP
od **01.05.2026**: po pięć poziomów do IX, razem **10 obserwacji**.
Dla CIVPART sprawdzono metadane i release, bez pobierania obserwacji.
Zastosowano istniejące RAW, walidację, upsert, katalog, computed_features
(`level` dla nowych serii), source_check_runs i wspólną blokadę koordynatora.
Import użył zapisanej odpowiedzi z kontrolowanego pobrania tego samego audytu;
scope kontroli zachowuje sposób pobrania i rzeczywisty `fetched_at`.
Nie przedstawiono odczytu pliku lokalnego jako kolejnego żądania do dostawcy.

Porównanie pełnych wierszy obserwacji CIVPART, PAYEMS, UNRATE,
CES0500000003 i UNEMPLOY przed i po imporcie, także `ingested_at`, dało
identyczny SHA-256. Nie pobierano ALFRED ani innych rodzin publikacji.
RAW/importowe provenance i diagnostyka audytu pozostają ignorowane w
`data/raw/employment-measures-2026-10-28/` oraz standardowym `data/raw/fred/`.
Nie zapisano sekretów w zmianach repozytorium.

## Poziomy, różnice i wersje

W kalendarzu wszystkie trzy miary mają transformację **raw**:

```text
Actual = poziom za potwierdzony miesiąc raportu
Previous = poziom za bezpośrednio poprzedni miesiąc
Difference = Actual - Previous
```

CIVPART i U6RATE wyświetlają procentowe poziomy, a różnice w pkt proc.
AWHAETP wyświetla godziny tygodniowo, a różnice w godzinach.
Nie zastosowano MoM do poziomów stóp ani godzin. Nie interpoluje się braków,
nie używa najnowszej pary zamiast właściwych miesięcy i nie kopiuje Previous
do Forecast. Skończony poziom zero jest zachowany; wartości ujemne i stopy
poza 0–100 są odrzucane. Brak własnej obserwacji pozostaje brakiem tej serii.

Trzy odczyty kalendarza korzystają z zapisanych snapshotów FRED i mają
**current-vintage**, z osobną datą wersji w provenance Actual i Previous.
Nie wytworzono historycznych first printów ani nie połączono ich z ALFRED.
Porównanie poziomów z osobnych miesięcy nie jest ilorazem ani agregatem
komponentów; jawne daty ich wersji pozostają dostępne w szczegółach.
Dotychczasowa logika historycznych NFP/U-3/earnings pozostała odrębna i niezmieniona.

## Niezależne porównanie z BLS

Przeczytano oficjalne raporty:
[VI, 02.07](https://www.bls.gov/news.release/archives/empsit_07022026.htm),
[VII, 07.08](https://www.bls.gov/news.release/archives/empsit_08072026.htm),
[VIII, 04.09](https://www.bls.gov/news.release/archives/empsit_09042026.htm),
[IX, 02.10](https://www.bls.gov/news.release/archives/empsit_10022026.htm).
Użyto ogółem, SA: tabeli A-1/podsumowania A dla udziału w sile roboczej,
A-15 dla U-6 oraz B-2 Total private/All employees dla godzin. Zweryfikowano
również bieżące [A-1](https://www.bls.gov/news.release/empsit.t01.htm),
[A-15](https://www.bls.gov/news.release/empsit.t15.htm) i
[B-2](https://www.bls.gov/news.release/empsit.t18.htm) za IX 2026.

Bezpośredni klient HTTP BLS ponownie otrzymał **403**. Odpowiedź i jej hash
zapisano jako diagnostykę błędu, bez twierdzenia, że potwierdza tabelę.
Oficjalne materiały były dostępne przez narzędzie WWW, bez obchodzenia blokady.
Dopisano dwa ograniczone potwierdzenia okresu VI/VII do statycznej konfiguracji:
URL raportu, nagłówek 08:30 ET, data i miesiąc, czas przeglądu,
`one_time_official_review`, bez fikcyjnego RAW/hash udanego pobrania BLS.
Dotychczasowe wpisy pozostawiono identyczne. Nie utworzono nowych rodzin,
terminów lub osobnych wydarzeń dla CIVPART, U-6 ani godzin.

Tabela łączy odczyt lokalnej bazy i rzeczywistego API. `DB = Actual` oznacza
poziom bez transformacji procentowej. `Δ` to Actual − Previous; ostatnia
kolumna jest osobnym porównaniem DB − BLS. Każdy nowy Actual/Previous ma
status current-vintage; wartości BLS są z raportu właściwego miesiąca.

| Okres / publikacja | Seria | DB = Actual | BLS | Previous | Jednostka poziomu | Δ (pkt proc. / godz.) | DB − BLS |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| VI / 02.07.2026 | CIVPART | 61.5 | 61.5 | 61.8 | % | −0.3 | 0 |
| VI / 02.07.2026 | U6RATE | 7.9 | 7.9 | 8.1 | % | −0.2 | 0 |
| VI / 02.07.2026 | AWHAETP | 34.3 | 34.3 | 34.3 | godz./tydzień | 0 | 0 |
| VII / 07.08.2026 | CIVPART | 61.4 | 61.4 | 61.5 | % | −0.1 | 0 |
| VII / 07.08.2026 | U6RATE | 7.9 | 7.9 | 7.9 | % | 0 | 0 |
| VII / 07.08.2026 | AWHAETP | 34.3 | 34.3 | 34.3 | godz./tydzień | 0 | 0 |
| VIII / 04.09.2026 | CIVPART | 61.6 | 61.6 | 61.4 | % | +0.2 | 0 |
| VIII / 04.09.2026 | U6RATE | 7.7 | 7.7 | 7.9 | % | −0.2 | 0 |
| VIII / 04.09.2026 | AWHAETP | 34.4 | 34.4 | 34.3 | godz./tydzień | +0.1 | 0 |
| IX / 02.10.2026 | CIVPART | 61.8 | 61.8 | 61.6 | % | +0.2 | 0 |
| IX / 02.10.2026 | U6RATE | 7.6 | 7.6 | 7.7 | % | −0.1 | 0 |
| IX / 02.10.2026 | AWHAETP | 34.4 | 34.4 | 34.4 | godz./tydzień | 0 | 0 |

Zgodność tych 12 poziomów nie jest dowodem braku rewizji całych serii.
CES rewiduje miesięczne szacunki i czynniki sezonowe; B-2 oznacza ostatnie
miesiące jako preliminary. CPS podlega innym procedurom, w tym zmianom
kontroli populacji w styczniu. Nie utożsamiamy mechanizmów CPS i CES.
Nie importowano kompletu historycznych dokumentów/wersji ani danych NSA.

## Jedno wydarzenie i przyszła publikacja

Release 50 zachowuje kolejność NFP, U-3, earnings, po których pokazuje
CIVPART, U6RATE i AWHAETP. Jest jeden identyfikator wydarzenia, jedna data,
godzina i miesiąc, dotychczasowe ★★★ i kategoria labor. Miary mają własne
definicje, źródła, jednostki i statusy. Stary dowód harmonogramu nie jest
przepisywany tylko po to, aby dodać listę nowych serii: poszerzana jest
projekcja odczytu oraz osobne wiązanie miar.

Zapowiedź raportu IX potwierdza następny raport za X:
**06.11.2026, 08:30 America/New_York = 14:30 Europe/Warsaw** (IANA).
Rzeczywisty API zwraca okres X i Previous IX:

| Seria | Actual | Previous | Forecast | Powód pustego Actual |
| --- | --- | --- | --- | --- |
| CIVPART | — | 61.8% | — | not_yet_published |
| U6RATE | — | 7.6% | — | not_yet_published |
| AWHAETP | — | 34.4 godz. | — | not_yet_published |

Konsensus to `not_integrated`. Brak porównania do prognozy. Historyczny brak
obserwacji lub potwierdzenia publikacji ma osobny kod, bez zastępowania wartości.

## Automatyzacja, cache i UI

Nowe serie weszły do istniejącego katalogu i mapowania release 50; CIVPART
wykorzystano ponownie. Zwykły koordynator obejmuje skonfigurowane serie,
z dotychczasową blokadą PostgreSQL, budżetem, cooldown, walidacją metadanych,
upsertem, rollbackiem i atomową publikacją. Nie dodano usługi ani pollingu.
Wersja adaptera okresów wzrosła do 9. Błąd dostawcy nie kasuje ostatnich
poprawnych danych; ponowny import zachowuje klucze obserwacji.

Przypisanie Actual każdej nowej miary wymaga dokładnej obserwacji za potwierdzony
miesiąc, snapshotu nie wcześniejszego niż publikacja oraz niezależnego
`last_updated` tej serii, uwzględniającego znaną godzinę. Sam nowy timestamp,
upływ terminu lub nowy PAYEMS nie wystarcza. Przy częściowej aktualizacji
pozostałe miary nadal mają pusty Actual z konkretną przyczyną. Poziom Previous
za właściwy poprzedni miesiąc pozostaje dostępny niezależnie.

Odczyt kalendarza korzysta z zapisanych danych i nie kontaktuje się z dostawcami.
Rzeczywiste API po dodaniu mapowań i projekcji pokazuje wszystkie sześć miar;
nie wymagało ręcznego podmieniania cache ani odpowiedzi. Nowe serie nie
zmieniają składu kart Overview, limitu czterech wydarzeń ani MCI/PIT.

EN/PL pokazuje procenty oraz `hours`/`godz.`. Szczegóły zawierają CPS/CES,
kod BLS, SA, definicję, źródło, okres i wersję. Nie dodano kolumn ani CSS.
Różnice nowych miar są neutralne, bez nowych reguł korzystne/niekorzystne.
Zachowano sortowanie, filtrowanie, countdown, układ mobilny i klawiaturę.

## Walidacja

- Pełny backend: **837 passed**. W tym **30 nowych przypadków**: katalog i
  ponowne użycie CIVPART, nazwy/SA/jednostki, CPS/CES, raw i poziomy, zero,
  braki miesięcy, niepoprawne dane, rewizje, przyszłe i opóźnione publikacje,
  niezależna świeżość, sześć miar, zachowanie starego dowodu i NFP/U-3/earnings,
  idempotentny importer U6RATE/AWHAETP. Wszystkie wcześniejsze testy zachowano.
- Pełny frontend: **540 passed**, 22 pliki, z blokadą sieci zgodną z CI.
  Nowe dwa przypadki EN/PL sprawdzają poziomy, pkt proc./godziny,
  neutralność porównań oraz kod CES w szczegółach.
- Production build: **passed**. Pozostaje ostrzeżenie Vite o głównym pakiecie
  **515.34 kB** ponad 500 kB. Nie zmieniono progu.
- Rzeczywiste API i Chrome bez fixture'ów odpowiedzi: **24 scenariusze**,
  EN/PL, **1366 i 390 px**, pięć dat VI–X oraz Overview. Końcowy przebieg:
  **55 odpowiedzi API HTTP 200**, zero wyjątków JavaScript i overflow.
  Sprawdzono nowe poziomy i Previous, sześć wierszy raportu, źródła/CES,
  szczegóły, przyszły brak Actual i prognozy, filtr ★★★, Escape/powrót fokusu,
  sześć kart i najwyżej cztery wydarzenia Overview. Obejrzano zrzuty desktop/mobile.
- Podczas kontroli UI utrzymywano istniejącą wspólną blokadę koordynatora,
  więc żądania aplikacji nie uruchamiały innych importerów. Następnie ją zwolniono.
- Pierwsze testy nowych fixture wykryły brak `retrieved_at`; uzupełniono fixture.
  Pełny backend wykrył też przepisywanie historycznej listy serii przez
  rozszerzanie dowodów. Przeniesiono rozszerzenie do projekcji, zachowując
  oryginalne metadane. Dwa istniejące testy zachowania dowodów i nowy test
  sześciu serii potwierdzają poprawkę. Build wymusił doprecyzowanie typu nowej
  fixture TypeScript. Końcowe pełne testy i build są poprawne.
- Nie pomijano testów ani nie zwiększano timeoutów. Sporadyczny błąd
  nawigacji MCI z wcześniejszych etapów nie wystąpił w tym pełnym frontendzie;
  nie zmieniano MCI. `git diff --check`: **passed**.

## Ograniczenia i wykorzystanie danych

Pozostają **BLS 403**, ograniczony horyzont ręcznych dowodów i brak potwierdzenia
działającej automatycznej synchronizacji BLS. Automatyczne adaptery zachowują
ostatni poprawny harmonogram przy błędach; nie wyliczają brakujących okresów
z samego faktu istnienia serii. Sprawdzenie źródeł może pozostać częściowe
lub błędne dla zakresu kalendarza — UI nie przemianowuje go na pełny sukces
tylko dlatego, że trzy odczyty są dostępne.

Current-vintage może zawierać rewizje. Nie ma kompletnej historii first printów
ani potwierdzenia dokładnych chwil dostępności intraday. Nie ma konsensusu.
Nowe serie obejmują lokalnie tylko V–IX; wcześniejsze potrzebne okresy są puste.

Zachowano ograniczenia z audytu 2B: [BLS](https://www.bls.gov/bls/linksite.htm)
deklaruje domenę publiczną publikacji z opisanymi tam wyjątkami i prosi
o atrybucję. Niezależne [warunki FRED/API](https://fred.stlouisfed.org/legal/)
obejmują atrybucję, prawa właścicieli oraz ograniczenia m.in. przechowywania,
cache, archiwizacji i redystrybucji. Zgodność istniejącego modelu PostgreSQL/RAW/cache
z całością tych warunków pozostaje **nierozstrzygnięta**. Dostęp API nie oznacza
nieograniczonego prawa publicznego eksportu. Nie deklarujemy gotowości publicznego
demo ani rozwiązania kwestii licencyjnych; nie przebudowano źródeł przy tym etapie.

## Końcowy Git i ręczne sprawdzenie

Gałąź `main`, HEAD `437cc05e7bbe4a67b3940a1fe03797b809bf0186`.
**18 modified, 3 untracked**, nic staged. Bez commita i pusha.

Zastane i zachowane bez zmiany treści:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`

Pliki zmienione/dodane w tym etapie:

- `app/analytics/calendar_readings.py`
- `app/analytics/employment_measures.py` (nowy)
- `app/analytics/features.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/release_calendar.py`
- `app/ingestion/bls_schedule.py`
- `app/ingestion/sync_calendar_periods.py`
- `config/calendar_period_evidence.json`
- `config/series.yaml`
- `frontend/src/api/macrolens.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/calendarComparisons.ts`
- `frontend/src/calendar/calendarPresentation.ts`
- `frontend/src/i18n/pl.json`
- `tests/test_calendar_employment_measures.py` (nowy)
- ten raport (nowy)

RAW, lokalna baza, cache, logi i zrzuty pozostają ignorowane. Nie zmieniono
CPI, Retail, Core PPI, FOMC ani ISM, metodologii MCI/PIT, schematu bazy,
gwiazdek lub reguł Overview. Nie rozpoczęto kolejnego etapu.

Ręcznie: Calendar → Date range → **02.10.2026**, potem **06.11.2026**.
Sprawdź sześć wierszy jednego raportu, nowe definicje i źródła w szczegółach,
godziny zamiast procentowej dynamiki AWHAETP, puste przyszłe Actual/Forecast
i wrześniowe Previous. Przełącz EN/PL i filtr ★★★ — cały raport pozostaje widoczny.

## Kontrola zamknięcia etapu — 28.10.2026

Ponownie sprawdzono wszystkie 17 plików etapu, pełny diff oraz listę stagingu.
Cztery wcześniejsze zmiany użytkownika zachowano bez zmiany treści SHA-256
i pozostawiono poza stagingiem. Nie znaleziono innych niezwiązanych zmian.
Sprawdzono brak sekretów, lokalnych danych, RAW, cache i artefaktów w wybranych
plikach. Konfiguracja dowodów zawiera wyłącznie dwa zamierzone, ograniczone
potwierdzenia VI/VII; jej wcześniejsze wpisy pozostały identyczne.

W transakcji PostgreSQL tylko do odczytu ponownie uruchomiono istniejącą
projekcję kalendarza i binding miar. Potwierdzono sześć miar jednego wydarzenia,
wrześniowe Actual/Previous **61.8/61.6%, 7.6/7.7%, 34.4/34.4 godz.**, status
current-vintage i transformację raw. Dla 06.11 Actual/Forecast pozostały puste,
Previous odnosi się do IX. Bez nowego ingestion i bez żądań do dostawców.
Nie zmieniano metodologii ani kodu poza dokumentacją zamknięcia.

Pełna ponowna walidacja: **837 testów backendu**, **540 frontendu**,
poprawny production build oraz `git diff --check` (także staged).
Następnie przygotowano osobną kopię dokładnych staged plików frontendu
z pozostałymi śledzonymi zależnościami z HEAD. Bez czterech niezwiązanych
zmian użytkownika również uzyskano **540 passed** i poprawny build.
Sporadyczny problem nawigacji MCI nie wystąpił w żadnym z tych pełnych
przebiegów. Nie pomijano testów, nie zmieniano timeoutów ani modułu MCI.

Ostrzeżenie Vite pozostaje jawne: **515.34 kB** w working tree oraz
**517.39 kB** dla dokładnej zawartości stagingu. Różnica wynika z pozostawienia
wcześniejszych zmian SourceCheckStatus/styles poza commitem; wersja stagingu
zachowuje dotychczasowe szczegóły sprawdzenia Overview. Próg 500 kB niezmieniony.
Wynik nowego GitHub Actions po pushu wymaga osobnego potwierdzenia;
lokalne wyniki nie są deklaracją sukcesu CI. Ograniczenia BLS, wersji danych,
konsensusu, intraday i warunków FRED pozostają aktualne.
