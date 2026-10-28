# MacroLens — etap 2A: dodatkowe odczyty Retail Sales

Kontrola: **28.10.2026**, gałąź `main`, HEAD `42d0fe6`. Bez stagingu,
commita i pusha. Zachowano cztery wcześniejsze zmiany użytkownika; ich SHA-256
pozostały identyczne. Punktem odniesienia były audyty pokrycia i ciągłości 1B.

## Zakres i oficjalne definicje

Istniejący raport **Advance Monthly Sales for Retail and Food Services**, FRED
release **9**, ma nadal jeden harmonogram i jedną tożsamość wydarzenia.
Zachowano `RSAFS:mom`; dodano `RSFSXMV:mom` oraz obliczaną miarę
`RETAIL_CONTROL:mom`. Ostatni identyfikator jest identyfikatorem miary API,
nie rzekomą serią FRED ani osobną serią obserwacji w bazie.

| Seria poziomu FRED | Dokładny zakres w tabelach MARTS | Rola |
| --- | --- | --- |
| [RSFSXMV](https://fred.stlouisfed.org/series/RSFSXMV) | Advance Retail Sales: Retail Trade and Food Services, Excluding Motor Vehicle and Parts Dealers | Ex Autos; baza grupy kontrolnej, bez NAICS 441 |
| [RSGASS](https://fred.stlouisfed.org/series/RSGASS) | Advance Retail Sales: Gasoline Stations | Odjęcie NAICS 447 |
| [RSBMGESD](https://fred.stlouisfed.org/series/RSBMGESD) | Advance Retail Sales: Building Materials, Garden Equipment and Supplies Dealers | Odjęcie całej kategorii 444, nie tylko 4441 |
| [RSFSDP](https://fred.stlouisfed.org/series/RSFSDP) | Advance Retail Sales: Food Services and Drinking Places | Odjęcie NAICS 722 |

Wszystkie cztery serie: **Monthly, Seasonally Adjusted, Millions of Dollars**,
źródło pierwotne US Census Bureau, ten sam raport advance co RSAFS. Są to
nominalne poziomy, bez korekty o inflację. Wyłączenie ex Autos obejmuje
dealerów pojazdów i części, a nie tylko sprzedaż nowych samochodów. Gastronomia
pozostaje w ex Autos. Najnowszy miesiąc jest advance; wcześniejsze wartości
podlegają rewizjom. Nie zastąpiono tych serii wersjami NSA ani pełnego MRTS.
Metadane sprawdzono w rzeczywistym FRED; koordynator odrzuca dla nowych serii
niezgodny identyfikator, tytuł, jednostkę, sezonowość lub częstotliwość.

Definicję rynkowej grupy kontrolnej potwierdza m.in. własna analiza
[PNC Economics](https://www.pnc.com/content/dam/pnc-com/pdf/aboutpnc/EconomicReports/EconomicUpdates/2026/PNC_Economics_Research_Retail_Sales_14_May_2026.pdf).
Zakres kategorii i addytywność sprawdzono w tabeli 1
[bieżącego raportu Census](https://www.census.gov/retail/marts/www/marts_current.pdf)
oraz [opisie odsezonowania Census](https://www.census.gov/retail/marts/www/timeseries.html).
Kody wyżej są kodami użytymi w tych tabelach MARTS.

Nie znaleziono zweryfikowanej gotowej serii FRED z dokładnie tymi czterema
wyłączeniami. `RSXFS` oznacza retail bez gastronomii, a nie Control Group;
ex Autos and Gas również nie jest właściwym zamiennikiem.
[Retail-control method BEA](https://www.bea.gov/help/faq/519) opisuje dodatkowe
procedury szacowania PCE. Nasz agregat nie jest tym oszacowaniem PCE ani
samodzielną miarą wkładu do GDP.

## Obliczenia i zgodność wersji

```text
Ex Autos MoM[t] = 100 × (RSFSXMV[t] / RSFSXMV[t−1] − 1)
Control[t] = RSFSXMV[t] − RSGASS[t] − RSBMGESD[t] − RSFSDP[t]
Control MoM[t] = 100 × (Control[t] / Control[t−1] − 1)
```

Nie odejmuje się dynamik procentowych. Kategoria 441 jest już wyłączona
z RSFSXMV; nie odejmujemy jej ponownie. Pozostałe trzy wyłączenia są rozłączne.
Wspólna istniejąca funkcja transformacji oblicza m/m z poziomów na jawnej
siatce miesięcznej. Nowa transformacja nie łączy miesięcy przez lukę i wymaga
dodatniego mianownika. Nie zmieniono formuł istniejącego RSAFS ani innych miar.

Grupa kontrolna wymaga dla obu miesięcy wszystkich czterech skończonych,
nieujemnych komponentów, dodatniego agregatu i wspólnego `vintage_date`
z istniejącego źródła `fred_snapshot`. Nie miesza komponentów ALFRED i FRED
ani zapisanych wersji z różnych dni. Brak komponentu, miesiąca, poprawnego
mianownika lub wspólnej wersji daje pustą wartość i konkretny kod przyczyny.
API i szczegóły pokazują składniki, ich URL-e, okresy, wersję, poziomy agregatu
oraz wzór oddzielnie dla Actual i Previous.

To kontrola wspólnej **dziennej wersji bieżącej**, nie gwarancja identycznej
chwili odczytu czterech odpowiedzi HTTP ani historia rewizji intraday.
Publikacja FRED aktualizuje komponenty w różnych minutach; sam timestamp
nie stanowi dowodu dostępności nowego okresu.

## Kontrolowane pobranie i walidacja ekonomiczna

Przez istniejący klient FRED pobrano tylko cztery nowe serie od **01.04.2026**:
po sześć poziomów, do września, razem **24 obserwacje**. Przed zapisem sprawdzono
metadane. Zastosowano dotychczasowe RAW, walidację, upsert obserwacji,
`computed_features`, źródła kontroli i wspólną blokadę koordynatora.
Mapowania zweryfikowano przez FRED series/release: wszystkie wskazały release 9.
Nie uruchamiano ingestion innych grup, ALFRED ani resetu bazy.

Niezależnie pobrano oficjalne bieżące pliki SA Census wyłącznie do porównania:
[ex Autos](https://www.census.gov/retail/marts/www/adv44Y72.txt),
[gasoline](https://www.census.gov/retail/marts/www/adv44700.txt),
[building/garden](https://www.census.gov/retail/marts/www/adv44400.txt),
[food services](https://www.census.gov/retail/marts/www/adv72200.txt).
**Każdy z 24 poziomów był identyczny z FRED.** Tych pełnych plików Census
nie importowano do bazy. RAW i ich URL, czas pobrania i SHA-256 pozostały lokalnie
w ignorowanym `data/raw/retail-measures-2026-10-28/`.

| Okres | Ex Autos: poprzedni → bieżący poziom, mln USD | Ex Autos m/m | Control: poprzedni → bieżący poziom, mln USD | Control m/m |
| --- | ---: | ---: | ---: | ---: |
| V 2026 | 587764 → 593513 | +0,978114% | 391561 → 394935 | +0,861679% |
| VI 2026 | 593513 → 591943 | −0,264527% | 394935 → 395838 | +0,228645% |
| VII 2026 | 591943 → 591337 | −0,102375% | 395838 → 394943 | −0,226103% |
| VIII 2026 | 591337 → 599797 | +1,430656% | 394943 → 399642 | +1,189792% |
| IX 2026 | 599797 → 605188 | +0,898804% | 399642 → 400184 | +0,135621% |

Dla każdego wiersza zastosowano `100 × (bieżący / poprzedni − 1)`.
Różnica względem niezależnego przeliczenia poziomów z bieżących plików Census
wynosi **0 pkt proc.** dla obu miar, z dokładnością obliczeń zmiennoprzecinkowych.
Control m/m jest tu rekonstrukcją z oficjalnych poziomów, nie rzekomo
publikowaną gotową serią Census.

W bieżącym PDF Census ex Autos za IX/VIII/VII podano odpowiednio
**0,9%, 1,4%, −0,1%**. Różnice niezaokrąglonego MacroLens wynoszą odpowiednio
**−0,001196, +0,030656, −0,002375 pkt proc.** i mieszczą się w zaokrągleniu
do jednego miejsca. Własna analiza
[Conference Board z 15.10](https://www.conference-board.org/research/global-economy-briefs/retail-sales-insights-sept-2026)
podaje Control za IX **0,1%**; wynik 0,135621% różni się o +0,035621 pkt proc.
i po takim samym zaokrągleniu daje 0,1%. UI MacroLens zachowuje dotychczasową
precyzję dwóch miejsc, czyli 0,14%.

### Rewizje: porównanie z rzeczywistymi starszymi dokumentami

Pobrano wyłącznie trzy dokumenty wskazanych miesięcy, podlinkowane w
[oficjalnym archiwum](https://www.census.gov/retail/marts/historic_releases.html).
Zweryfikowano ich własną datę, godzinę i miesiąc w nagłówku oraz zgodność
miesiąca z treścią. Zapisano je jako dowody istniejących wydarzeń w lokalnym
magazynie dowodów; nie zapisano ich liczb jako syntetycznych first printów.

| Dokument | Ex Autos m/m z poziomów tego dokumentu | Control m/m z poziomów tego dokumentu | Bieżące Ex Autos / Control |
| --- | ---: | ---: | ---: |
| [VI, wydany 16.07](https://www2.census.gov/retail/releases/historical/marts/adv2606.pdf) | −0,153837% | +0,551152% | −0,264527% / +0,228645% |
| [VII, wydany 14.08](https://www2.census.gov/retail/releases/historical/marts/adv2607.pdf) | −0,306048% | −0,483761% | −0,102375% / −0,226103% |
| [VIII, wydany 16.09](https://www2.census.gov/retail/releases/historical/marts/adv2608.pdf) | +1,392044% | +1,361518% | +1,430656% / +1,189792% |

Są to różne wersje poziomów, a nie błąd odejmowania m/m. Bieżący raport Census
zawiera jawne zawiadomienie o rocznej rewizji **28.09.2026**. Np. lipcowy Control
w dokumencie sierpniowym wynika z 416159 / 418182 mln USD; bieżące poziomy
wynoszą 394943 / 395838. Nie miesza się tych dwóch par. Wyniki kalendarza
opisano jako current-vintage, nie jako liczby znane w chwili historycznej publikacji.

## Rzeczywiste API: Actual i Previous

Previous nadal oznacza **m/m za poprzedni miesiąc**, nie poprzedni poziom
sprzedaży i nie wcześniejszy szacunek tego samego miesiąca.

| Publikacja / okres | Ex Autos Actual | Ex Autos Previous | Control Actual | Control Previous |
| --- | ---: | ---: | ---: | ---: |
| 16.07 / VI | −0,264527% | +0,978114% | +0,228645% | +0,861679% |
| 14.08 / VII | −0,102375% | −0,264527% | −0,226103% | +0,228645% |
| 16.09 / VIII | +1,430656% | −0,102375% | +1,189792% | −0,226103% |
| 15.10 / IX | +0,898804% | +1,430656% | +0,135621% | +1,189792% |
| **17.11 / X — przyszła publikacja** | **—** | **+0,898804%** | **—** | **+0,135621%** |

Najbliższy termin: **17.11.2026, 08:30 America/New_York = 14:30 Europe/Warsaw**,
potwierdzony w istniejącym harmonogramie oraz zapowiedzi bieżącego raportu.
Wspólne Forecast i porównanie do prognozy pozostają puste. Zachowano również
headline RSAFS: dla 15.10 Actual 0,770841%, Previous 1,288780%; dla 17.11
Actual pusty, Previous 0,770841%.

Actual wymaga istniejącego potwierdzenia raportu i okresu, dostępnej obserwacji
oraz sprawdzeń świeżości. Control dodatkowo wymaga świeżych komponentów
i potwierdzonych aktualizacji dostawcy dla wszystkich czterech serii.
Sam upływ terminu, stary komunikat lub zmieniony timestamp nie wystarczają.
Nowe miary nie są przypisywane etapowi full MRTS.

## Odświeżanie, interfejs i ograniczenia

Nowe komponenty należą do istniejącego katalogu i mapowania release 9.
Kalendarz korzysta z dotychczasowego koordynatora; nie ma nowej usługi ani
pollingu. Zwykły job respektuje wspólną blokadę, budżet, cooldown, rollback
i publikację cache. Po zmianie komponentu wyrównuje pozostałe snapshoty;
przy braku zmian nie pobiera ponownie obserwacji. Niekompletna aktualizacja
nie daje pozornie kompletnego Control. Wersja adaptera dowodów wzrosła do 7.

Grupa kontrolna jest liczona z zapisanych komponentów podczas odczytu,
więc nie ma niezależnego cache ani nieaktualnej tabeli własnych obserwacji.
Nie dodano jej do MCI/PIT ani kart Overview. Zachowano limit czterech
wydarzeń Overview, wspólne gwiazdki, kategorię, filtry, sortowanie i odliczanie.
Trzy zwykłe wiersze miar mają dotychczasowe procenty i neutralne różnice
w punktach procentowych. Nie dodano stylów ani stałego podświetlenia.

Brak konsensusu pozostaje jawny. Nie uzyskano historii first printów nowych
serii; starsze Actual mogą zawierać późniejsze rewizje. Wspólna dzienna wersja
nie rozwiązuje wszystkich ograniczeń intraday. Za kwiecień brakuje pobranego
marca, więc m/m i kolejne Previous wymagające tego miesiąca pozostają puste.
Trzy historyczne dokumenty dołączono kontrolowanie; nie uruchomiono ogólnego
crawlera historii. Ograniczenia BLS 403, przyszłych harmonogramów, SEP i ISM
z wcześniejszych etapów pozostają bez zmian.

## Walidacja i stan Git

- Pełny backend: **769 passed**. Pełny frontend: **536 passed**, 22 pliki,
  z blokadą sieci zgodną z CI. Bez pomijania testów i podnoszenia timeoutów.
- Production build: **passed**. Zachowano ostrzeżenie Vite: główny pakiet
  **509,97 kB** ponad 500 kB. Nie zmieniano progu. Build wykrył też zbyt szeroko
  wywnioskowany typ nowej fixture; doprecyzowano go do `CalendarMeasure`.
- `git diff --check`: **passed**.
- Offline testy obejmują dobór i metadane serii, m/m, luki, zero/ujemny mianownik,
  skład i rozłączność wyłączeń, brak komponentu, różne okresy/wersje/źródła,
  rewizje, stare snapshoty po terminie, przyszły odczyt, idempotentny import,
  odrębny etap raportu, trzy miary jednego wydarzenia, neutralne różnice,
  EN/PL, źródła i fokus. Dotychczasowe testy zachowano.
- Rzeczywisty powtórny import tych samych RAW: **24 → 24 obserwacje,
  zero duplikatów**, bez nowych żądań dostawców.
- Chrome z rzeczywistym API, bez fixture'ów odpowiedzi: **24 scenariusze**,
  EN/PL, **1366/390 px**, pięć dat tabeli API i Overview; w końcowym przebiegu
  **56 odpowiedzi HTTP 200** (wcześniejsze przebiegi: 55–56),
  zero wyjątków JavaScript i poziomego overflow. Sprawdzono szczegóły,
  odtworzenie komponentów, filtr ★★★, Escape/powrót fokusu, jednostki,
  przyszłe puste Actual i sześć kart/limit czterech wydarzeń Overview.
  Obejrzano zrzuty desktop/mobile. Podczas kontroli utrzymywano wspólną blokadę,
  aby żądania aplikacji nie uruchamiały innych importerów.
- Nowy test PL wykrył błędne kodowanie dopisanych tłumaczeń. Naprawiono UTF-8;
  nie pominięto testu ani nie zwiększono timeoutu.

Zastane i zachowane bez zmian treści: `README.md`,
`frontend/src/brief/SourceCheckStatus.tsx`,
`frontend/src/brief/SourceCheckStatus.test.tsx`, `frontend/src/styles.css`.

Pełna lista plików zmienionych/dodanych w tym etapie:

- `app/analytics/calendar_evidence.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/features.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/retail_measures.py` — nowy
- `app/ingestion/sync_calendar_periods.py`
- `config/series.yaml`
- `frontend/src/api/macrolens.ts`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/calendarPresentation.ts`
- `frontend/src/i18n/pl.json`
- `tests/test_calendar_retail_measures.py` — nowy
- ten raport — nowy

RAW, dane bazy, dowody lokalne, logi, profile Chrome i zrzuty pozostają ignorowane.
Nie zmieniono statycznego `config/calendar_period_evidence.json`, wydarzeń Fed,
innych rodzin publikacji ani metodologii MCI/PIT. Bez commita i pusha.

Końcowy working tree: **15 modified, 3 untracked**, w tym cztery zastane pliki.
Żaden plik nie jest staged. Gałąź i HEAD pozostają `main` / `42d0fe6`.

Ręczna kontrola: Calendar → Date range → 15.10.2026 (IX), następnie
17.11.2026 (X). Sprawdź trzy wiersze o wspólnej godzinie 14:30, puste przyszłe
Actual/Forecast, Previous oraz szczegóły grupy kontrolnej i cztery źródła
komponentów. Przełącz EN/PL; filtr ★★★ powinien ukryć cały raport ★★.

## Kontrola zamknięcia etapu — 28.10.2026

Przed commitem ponownie przejrzano wszystkie zmiany. Do commita wybrano
wyłącznie 14 plików tego etapu, w tym ten raport; cztery wcześniejsze pliki
pozostawiono poza stagingiem. Potwierdzono zachowanie ich treści SHA-256,
brak dodatkowych zmian definicji wcześniejszych serii oraz zgodność 24 poziomów
z zapisanymi niezależnymi tabelami Census, bez ponownego pobierania danych.
Nie zmieniano metodologii, nie wykonywano dodatkowego ingestion ani zmian bazy.

Pełna ponowna walidacja: backend **769 passed**, frontend **536 passed**,
production build i obie kontrole whitespace (`git diff --check`, także staged)
zakończone pomyślnie. Dodatkowo sprawdzono frontend na osobnej kopii dokładnej
zawartości stagingu, bez czterech wcześniejszych zmian użytkownika: **536 passed**
i poprawny build. Ten wariant zachowuje dotychczasowe szczegóły sprawdzenia
Overview, dlatego jego główny pakiet ma **512,01 kB**; ostrzeżenie ponad 500 kB
pozostaje jawne, bez zmiany progu.

Pierwszy dodatkowy przebieg tej kopii miał jeden błąd istniejącego testu
nawigacji MCI: po kliknięciu pozostał poprzedni widok. Izolowany zestaw MCI
przeszedł **8/8**, a ponowny pełny przebieg **536/536**, bez zmian kodu,
pomijania testów i zwiększania timeoutów. Jednorazowy problem nie został
odtworzony; jego przyczyna nie jest potwierdzona. Nie zmieniano modułu MCI
w ramach zamknięcia Retail Sales. Wyniki GitHub Actions po pushu należy
potwierdzić oddzielnie; lokalna walidacja nie jest wynikiem zdalnego workflow.
