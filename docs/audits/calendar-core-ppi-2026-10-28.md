# MacroLens — etap 2B: Core PPI

Kontrola **28.10.2026**, `main`, HEAD `a1ed01068caea36ce3f3a624715084cd90d92870`.
Bez stagingu, commita i pusha. Zachowano treść czterech wcześniejszych zmian
użytkownika; porównanie SHA-256 zakończyło się zgodnością.

## Serie i definicje

Każda seria ma oficjalny prefiks nazwy FRED **Producer Price Index by Commodity:**.
Wszystkie są miesięcznymi poziomami BLS, przypisanymi przez FRED series/release
do istniejącej publikacji **Producer Price Index, release 46**.
Metadane sprawdzono na stronach serii oraz w rzeczywistej odpowiedzi API.

| Dokładna pozostała część nazwy FRED | SA do m/m | NSA do r/r | Baza indeksu |
| --- | --- | --- | --- |
| Final Demand | [PPIFIS](https://fred.stlouisfed.org/series/PPIFIS) | [PPIFID](https://fred.stlouisfed.org/series/PPIFID) | Nov 2009=100 |
| Final Demand: Final Demand Less Foods and Energy | [PPIFES](https://fred.stlouisfed.org/series/PPIFES) | [PPICOR](https://fred.stlouisfed.org/series/PPICOR) | Apr 2010=100 |
| Final Demand: Final Demand Less Foods, Energy, and Trade Services | [WPSFD49116](https://fred.stlouisfed.org/series/WPSFD49116) | [WPUFD49116](https://fred.stlouisfed.org/series/WPUFD49116) | Aug 2013=100 |

SA oznacza Seasonally Adjusted; NSA — Not Seasonally Adjusted. Walidator
odrzuca inną nazwę, ID, sezonowość, częstotliwość lub jednostkę bazową.
PPI mierzy ceny otrzymywane przez producentów. Wariant bez żywności i energii
nadal obejmuje usługi handlowe; ich wyłączenie tworzy odrębną miarę.
Indeksy usług handlowych opisują marże hurtowe i detaliczne. Opisy nie
przypisują zmianom automatycznej reakcji Fed ani giełdy.

## Transformacje i wersje

Wspólne `calculate_features` oblicza:

```text
MoM[t] = 100 * (SA[t] / SA[t-1] - 1)
YoY[t] = 100 * (NSA[t] / NSA[t-12] - 1)
```

Każdy iloraz korzysta z jednej serii, jednej bazy i właściwych miesięcy.
Brak interpolacji i sumowania m/m. Nowe miary wymagają dodatnich, skończonych
poziomów i zgodnego `vintage_date` ze źródła `fred_snapshot` dla obu końców.
Brak miesiąca, poziomu lub wspólnej wersji daje pustą wartość z przyczyną.
Nie miesza się ALFRED z FRED. Formuła i zapisane wyniki istniejącego PPIFIS
pozostały niezmienione; dodatkowe zabezpieczenia dotyczą pięciu nowych serii.

Wyniki nowych serii mają status **current-vintage**. Nie powstała historia
first printów. Zgodność dziennej wersji nie dowodzi dostępności intraday.
Previous oznacza dynamikę poprzedniego miesiąca, osobno m/m i r/r.

## Dane, harmonogram i automatyzacja

Wstępna kontrola lokalnej PostgreSQL wykazała istniejący headline PPIFIS
(406 obserwacji do IX 2026), bez pięciu nowych serii. Kontrolowane pobranie
przez istniejącego klienta FRED objęło dwie serie SA od IV 2026 (2 × 6)
oraz trzy NSA od IV 2025 (3 × 18): **66 obserwacji** do IX 2026.
Metadane PPIFIS sprawdzono, bez ponownego ingestion jego obserwacji.
Porównanie pełnych wierszy PPIFIS przed i po zapisie, także `ingested_at`,
potwierdziło brak zmiany. Użyto istniejących RAW, walidacji, upsertu,
computed_features, mapowań release 46, transakcji i wspólnej blokady.
Nie pobierano ALFRED ani pozostałych rodzin publikacji.

Odpowiedzi i kontrolne payloady API pozostają ignorowane w
`data/raw/core-ppi-2026-10-28/`; rzeczywisty importer zachowuje standardowe RAW.
Nie zapisano kluczy API w repozytorium. Bezpośrednie żądanie BLS nadal
zwróciło **403**; zapis błędu nie stanowi potwierdzenia raportu.
Oficjalne tabele przeczytano narzędziem WWW. Dopisano wyłącznie dwa
jednorazowo przejrzane nagłówki istniejących raportów VI/VII do konfiguracji
dowodów: URL, data, okres, 08:30 NY i rzeczywisty czas przeglądu,
bez fikcyjnego RAW/hash. Pozostałe wpisy konfiguracji są identyczne.
Nie utworzono osobnego harmonogramu ani wydarzeń dla nowych miar.

Nowe serie podlegają istniejącemu koordynatorowi, blokadzie PostgreSQL,
budżetowi, cooldown, obsłudze błędów i atomowej publikacji. Wersja adaptera
okresów wzrosła do 8. Dostępność każdej nowej serii wymaga potwierdzonego
okresu, dokładnej obserwacji, odpowiednio świeżego snapshotu i aktualizacji
dostawcy nie wcześniejszej niż publikacja. Aktualizacja innej serii lub
sam upływ terminu nie uzupełnia wyniku. Krótki offset FRED `-05` jest
normalizowany do `-05:00`, także dla lokalnego Pythona 3.9.

## Niezależna kontrola BLS

Porównano [tabelę 3 SA](https://www.bls.gov/news.release/ppi.t03.htm),
[tabelę 1 zmian](https://www.bls.gov/news.release/ppi.t01.htm) oraz archiwa
[VI](https://www.bls.gov/news.release/archives/ppi_07152026.htm),
[VII](https://www.bls.gov/news.release/archives/ppi_08132026.htm),
[VIII](https://www.bls.gov/news.release/archives/ppi_09102026.htm) i
[IX](https://www.bls.gov/news.release/archives/ppi_10152026.htm).
Kontrola nie polegała wyłącznie na przejściu testów.

W tabeli 3 raportu IX poziomy V–IX wynoszą odpowiednio:

| SA | V | VI | VII | VIII | IX |
| --- | ---: | ---: | ---: | ---: | ---: |
| PPIFIS | 156.874 | 156.683 | 156.924 | 157.662 | 159.780 |
| PPIFES | 153.577 | 154.198 | 154.735 | 155.115 | 156.172 |
| WPSFD49116 | 142.242 | 142.468 | 143.182 | 143.555 | 144.255 |

Wszystkie te poziomy odpowiadają zapisanym danym FRED. Przeliczone m/m dla
VI–IX zgadzają się z tabelą 1 raportu IX po zaokrągleniu do jednego miejsca:
headline −0.1 / +0.2 / +0.5 / +1.3; ex F/E +0.4 / +0.3 / +0.2 / +0.7;
ex F/E/trade +0.2 / +0.5 / +0.3 / +0.5. Nie są to wszystkie pierwotne odczyty.

Poniższe wartości BLS pochodzą z raportu danego miesiąca. Różnice to
niezaokrąglony current-vintage minus opublikowana liczba, w pkt proc.
Dla r/r kontrola BLS dotyczy publikowanej rocznej dynamiki NSA, a nie
niezależnie odtworzonej kompletnej historycznej tabeli poziomów NSA.
Pary poziomów NSA w dalszej tabeli pochodzą z FRED; nie przedstawiamy ich
jako drugiego, niezależnego zbioru BLS ani historii pierwszych publikacji.

<!-- generated numeric tables follow -->

| Period | SA / NSA | Current m/m | BLS m/m | Difference pp | Current r/r | BLS r/r | Difference pp |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-06-01 | PPIFIS / PPIFID | -0.121754% | -0.3% | +0.178246 | 5.589970% | 5.5% | +0.089970 |
| 2026-06-01 | PPIFES / PPICOR | 0.404357% | 0.2% | +0.204357 | 4.807483% | 4.7% | +0.107483 |
| 2026-06-01 | WPSFD49116 / WPUFD49116 | 0.158884% | 0.1% | +0.058884 | 5.043328% | 5.1% | -0.056672 |
| 2026-07-01 | PPIFIS / PPIFID | 0.153814% | 0.0% | +0.153814 | 4.936023% | 4.7% | +0.236023 |
| 2026-07-01 | PPIFES / PPICOR | 0.348254% | 0.2% | +0.148254 | 4.353866% | 4.2% | +0.153866 |
| 2026-07-01 | WPSFD49116 / WPUFD49116 | 0.501165% | 0.4% | +0.101165 | 4.856691% | 4.7% | +0.156691 |
| 2026-08-01 | PPIFIS / PPIFID | 0.470291% | 0.4% | +0.070291 | 5.612648% | 5.4% | +0.212648 |
| 2026-08-01 | PPIFES / PPICOR | 0.245581% | 0.2% | +0.045581 | 4.805560% | 4.6% | +0.205560 |
| 2026-08-01 | WPSFD49116 / WPUFD49116 | 0.260508% | 0.3% | -0.039492 | 4.767955% | 4.7% | +0.067955 |
| 2026-09-01 | PPIFIS / PPIFID | 1.343380% | 1.3% | +0.043380 | 6.337775% | 6.3% | +0.037775 |
| 2026-09-01 | PPIFES / PPICOR | 0.681430% | 0.7% | -0.018570 | 4.969638% | 5.0% | -0.030362 |
| 2026-09-01 | WPSFD49116 / WPUFD49116 | 0.487618% | 0.5% | -0.012382 | 5.041563% | 5.0% | +0.041563 |

### Exact input pairs and historical API values

| Release | Series | Rate | Comparison level / period | Current level / period | Actual % | Previous rate % |
| --- | --- | --- | --- | --- | ---: | ---: |
| 2026-07-15 | PPIFID | yoy | 148.838 / 2025-06-01 | 157.158 / 2026-06-01 | 5.589970 | 5.923451 |
| 2026-07-15 | PPIFES | mom | 153.577 / 2026-05-01 | 154.198 / 2026-06-01 | 0.404357 | -0.011068 |
| 2026-07-15 | PPICOR | yoy | 147.312 / 2025-06-01 | 154.394 / 2026-06-01 | 4.807483 | 4.502563 |
| 2026-07-15 | WPSFD49116 | mom | 142.242 / 2026-05-01 | 142.468 / 2026-06-01 | 0.158884 | 0.772217 |
| 2026-07-15 | WPUFD49116 | yoy | 135.823 / 2025-06-01 | 142.673 / 2026-06-01 | 5.043328 | 5.027685 |
| 2026-08-13 | PPIFID | yoy | 149.898 / 2025-07-01 | 157.297 / 2026-07-01 | 4.936023 | 5.589970 |
| 2026-08-13 | PPIFES | mom | 154.198 / 2026-06-01 | 154.735 / 2026-07-01 | 0.348254 | 0.404357 |
| 2026-08-13 | PPICOR | yoy | 148.282 / 2025-07-01 | 154.738 / 2026-07-01 | 4.353866 | 4.807483 |
| 2026-08-13 | WPSFD49116 | mom | 142.468 / 2026-06-01 | 143.182 / 2026-07-01 | 0.501165 | 0.158884 |
| 2026-08-13 | WPUFD49116 | yoy | 136.698 / 2025-07-01 | 143.337 / 2026-07-01 | 4.856691 | 5.043328 |
| 2026-09-10 | PPIFID | yoy | 149.466 / 2025-08-01 | 157.855 / 2026-08-01 | 5.612648 | 4.936023 |
| 2026-09-10 | PPIFES | mom | 154.735 / 2026-07-01 | 155.115 / 2026-08-01 | 0.245581 | 0.348254 |
| 2026-09-10 | PPICOR | yoy | 147.912 / 2025-08-01 | 155.02 / 2026-08-01 | 4.805560 | 4.353866 |
| 2026-09-10 | WPSFD49116 | mom | 143.182 / 2026-07-01 | 143.555 / 2026-08-01 | 0.260508 | 0.501165 |
| 2026-09-10 | WPUFD49116 | yoy | 136.956 / 2025-08-01 | 143.486 / 2026-08-01 | 4.767955 | 4.856691 |
| 2026-10-15 | PPIFID | yoy | 150.1 / 2025-09-01 | 159.613 / 2026-09-01 | 6.337775 | 5.612648 |
| 2026-10-15 | PPIFES | mom | 155.115 / 2026-08-01 | 156.172 / 2026-09-01 | 0.681430 | 0.245581 |
| 2026-10-15 | PPICOR | yoy | 148.542 / 2025-09-01 | 155.924 / 2026-09-01 | 4.969638 | 4.805560 |
| 2026-10-15 | WPSFD49116 | mom | 143.555 / 2026-08-01 | 144.255 / 2026-09-01 | 0.487618 | 0.260508 |
| 2026-10-15 | WPUFD49116 | yoy | 137.021 / 2025-09-01 | 143.929 / 2026-09-01 | 5.041563 | 4.767955 |

### Headline API unchanged

| Release | Actual m/m % | Previous m/m % |
| --- | ---: | ---: |
| 2026-07-15 | -0.121754 | 0.520950 |
| 2026-08-13 | 0.153814 | -0.121754 |
| 2026-09-10 | 0.470291 | 0.153814 |
| 2026-10-15 | 1.343380 | 0.470291 |

### Rewizje i zaokrąglenia

Raport IX jawnie informuje o rewizjach V–VIII wskutek późnych odpowiedzi
i korekt respondentów. Przykładowo PPIFES w pierwotnym raporcie VI miał
153.689 → 153.996, a obecnie 153.577 → 154.198; w pierwotnym VII
154.076 → 154.450, a obecnie 154.198 → 154.735. To konkretne zmiany
poziomów, więc nie należy dopasowywać current-vintage do dawnych procentów.
Różnice wcześniejszych r/r również obejmują zmienione wersje; nie rozstrzygamy
wkładu każdej rewizji bez kompletu dawnych poziomów NSA.

Za IX różnice względem BLS dla obu core m/m wynoszą odpowiednio
−0.018570 i −0.012382 pkt proc., a r/r −0.030362 i +0.041563 pkt proc.
Wszystkie mieszczą się w zaokrągleniu BLS do jednego miejsca.
W interfejsie są dwa miejsca: **0.68% / 4.97%** oraz **0.49% / 5.04%**.
Nie wpisano tych wyników na sztywno do obliczeń.

## Publikacja przyszła i interfejs

Zapowiedź raportu IX potwierdza **13.11.2026 o 08:30 America/New_York**,
czyli **14:30 Europe/Warsaw**, dla X 2026. W rzeczywistym API:

| Miara | Actual m/m / r/r | Previous m/m | Previous r/r NSA | Forecast |
| --- | --- | ---: | ---: | --- |
| Headline | — / — | 1.343380% | 6.337775% | — |
| Bez żywności i energii | — / — | 0.681430% | 4.969638% | — |
| Bez żywności, energii i usług handlowych | — / — | 0.487618% | 5.041563% | — |

Każdy Actual ma `not_yet_published`; okres X, Previous IX, konsensus
`not_integrated`. Jedno wydarzenie release 46 ma trzy podstawowe miary m/m;
każda zawiera własny obiekt `year_over_year`, z osobnym statusem i provenance.
R/r NSA pokazuje się mniejszym tekstem w istniejących komórkach Actual/Previous
i w szczegółach. Nie dodano kolumn, wydarzeń, gwiazdek ani kolorowania.
Szczegóły pokazują definicje, bazy, SA/NSA, formuły, źródła, okresy i wersje.
Układ CPI, Retail, countdown, filtry i limit czterech wydarzeń Overview zachowano.
Nowe miary nie trafiły do kart Overview ani MCI/PIT.

## Warunki wykorzystania i eksportu

[BLS](https://www.bls.gov/bls/linksite.htm) deklaruje domenę publiczną swoich
publikacji z wyjątkami dla wcześniej chronionych fotografii i ilustracji;
prosi o wskazanie BLS jako źródła. Te serie mają oznaczenie public-domain
na FRED. Nie zmienia to niezależnych
[warunków usługi i API FRED](https://fred.stlouisfed.org/legal/).

Warunki FRED wymagają atrybucji, zachowania oznaczeń, informacji o braku
endorsement i przestrzegania praw właściciela danych. Zawierają również
ograniczenia użycia komercyjnego i — w części API, Prohibitions (l) —
przechowywania/cache/archiwizacji i przekazywania przechowanych treści.
Istniejący projekt korzysta z lokalnej bazy i RAW: ten audyt **nie potwierdza
zgodności tego modelu z całością aktualnych warunków FRED** ani nie udziela
zgody na publiczne demo, redystrybucję czy eksport całej bazy. Przed publicznym
udostępnieniem trzeba rozstrzygnąć te warunki dla sposobu pozyskania i użycia.
Nie zmieniano istniejącego eksportu ani integracji na nowe źródło w tym etapie.

## Walidacja

- Pełny backend: **807 passed**. W tym 38 nowych testów PPI: dokładne serie,
  SA/NSA i bazy, formuły, miesiące, mianowniki, wersje, rewizje, niezależność
  częściowych aktualizacji, stare snapshoty, brak dowodu, przyszłe puste wartości,
  Previous, idempotentny importer wszystkich pięciu nowych serii i headline.
- Pełny frontend: **538 passed**, 22 pliki; blokada sieci zgodna z CI.
  Dwa nowe przypadki EN/PL sprawdzają trzy wiersze i niezależny status r/r.
  Wszystkie wcześniejsze testy zachowane; bez pomijania i zwiększania timeoutów.
- Production build: **passed**. Jawne ostrzeżenie Vite: główny pakiet
  **512.85 kB**, ponad 500 kB. Nie zmieniono progu.
- Rzeczywiste API: pięć dat tabel, wszystkie trzy miary i pary r/r.
  Chrome bez fixture'ów odpowiedzi: **24 scenariusze**, EN/PL, **1366/390 px**,
  **56 odpowiedzi API HTTP 200**, zero wyjątków JavaScript i overflow.
  Sprawdzono historię VI–IX, 13.11, Actual/Previous, jednostki, źródła,
  szczegóły, filtr ★★★, Escape/powrót fokusu i Overview (6 kart, ≤4 wydarzenia).
  Obejrzano zrzuty desktop/mobile. Pierwsza próba helpera zrzutów używała
  selektora elementu Retail nieobecnego w szczegółach PPI; poprawiono wyłącznie
  ignorowany helper i wykonano pełny przebieg ponownie.
- Podczas kontroli rzeczywistej aplikacji utrzymywano wspólną blokadę
  koordynatora, aby żądania UI nie uruchamiały innych importerów. Blokadę
  zwolniono po kontroli. Nie podstawiano odpowiedzi API.
- `git diff --check`: **passed**; brak stagingu, commita i pusha.

Pozostają BLS 403 i ograniczone ręcznie potwierdzone okresy, brak konsensusu,
current-vintage i niepełna historia wersji, ograniczenia intraday oraz warunki
FRED opisane wyżej. Zakres SA IV–IX wymaga wcześniejszego miesiąca dla m/m IV;
nie zastąpiono brakującego marca innym odczytem. Nie rozpoczęto następnego etapu.

## Końcowy Git

`main` / `a1ed01068caea36ce3f3a624715084cd90d92870`.
**17 modified, 3 untracked**, nic staged.

Zastane i zachowane bez zmiany treści:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`

Zmiany tego etapu:

- `app/analytics/calendar_evidence.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/features.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/ppi_measures.py` (nowy)
- `app/ingestion/bls_schedule.py`
- `app/ingestion/sync_calendar_periods.py`
- `config/calendar_period_evidence.json`
- `config/series.yaml`
- `frontend/src/api/macrolens.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/calendarPresentation.ts`
- `frontend/src/i18n/pl.json`
- `tests/test_calendar_core_ppi.py` (nowy)
- ten raport (nowy)

RAW, lokalne dane PostgreSQL, cache, logi i zrzuty pozostają ignorowane.
Ręcznie: Calendar → Date range → 15.10.2026, następnie 13.11.2026.
Sprawdź trzy wiersze PPI, pomocnicze r/r NSA i szczegóły obu definicji core.
Przełącz EN/PL. Filtr ★★★ ukrywa PPI (dotychczasowe ★★).

## Kontrola zamknięcia etapu — 28.10.2026

Ponownie przejrzano pełny diff, 16 plików etapu i zależności. Nie zmieniano
obliczeń: potwierdzono pary SA/NSA, bazy, właściwe miesiące i wersje,
niezależne statusy oraz wrześniowe zaokrąglenia na zapisanych dowodach.
Nie wykonywano dodatkowego ingestion ani odświeżania bazy. Cztery wcześniejsze
pliki użytkownika zachowano bez zmiany treści i wyłączono z planowanego commita.
Sprawdzono brak sekretów i artefaktów w wybranym zakresie.

Ponowna pełna walidacja working tree: **807 testów backendu**, **538 frontendu**,
production build i `git diff --check` poprawne. Dodatkowo frontend sprawdzono
na kopii HEAD z dokładnie planowanymi zmianami etapu, bez czterech wcześniejszych
zmian użytkownika: **538 passed** i poprawny build. Ta kopia zachowuje istniejące
szczegóły sprawdzenia Overview, stąd główny pakiet **514.90 kB**, wobec
**512.85 kB** w working tree. Oba buildy zachowują ostrzeżenie ponad 500 kB.

Pierwsza dodatkowa kopia nie zawierała współdzielonej fixture spoza `frontend`;
uzupełniono ją dokładnym plikiem z HEAD. Następny przebieg ujawnił jeden błąd
istniejącego testu nawigacji MCI: po kliknięciu pozostał widok Compare Data.
Izolowany zestaw MCI przeszedł **8/8**, ponowny pełny frontend **538/538**.
Przyczyna sporadycznego błędu nawigacji nie została potwierdzona. Nie zmieniano
kodu MCI, testów ani timeoutów i nie pomijano żadnego testu.

Planowany commit obejmuje wyłącznie 16 plików wymienionych w sekcji zmian
etapu. Wynik GitHub Actions po pushu wymaga oddzielnego potwierdzenia;
lokalne wyniki nie są deklaracją zdalnego sukcesu. Wszystkie ograniczenia
BLS, wersji, konsensusu, intraday i warunków FRED pozostają aktualne.
