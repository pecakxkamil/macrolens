# MacroLens — H2: JavaScript i ładowanie frontendu

Weryfikacja **30.10.2026**, Europe/Warsaw, `C:\Projects\macrolens`.
`main`, HEAD **`ea66bf4383e75218b5abd141b25a674596a32533`** —
`Add PostgreSQL integration tests to CI`. **Bez stagingu, commita i pusha.**

Rzeczywisty transfer początkowy JS zmalał: Calendar około **15%**, Indicators
i Charts około **12%**, Research około **11%**. Overview ma niewielką oszczędność
transferu i więcej żądań; nie deklarujemy jednolitego przyspieszenia wszystkich
tras. Największy chunk zmalał z **545,95 do 407,85 kB** w parze commit-only.
Próg Vite pozostał bez zmian. Łączny gzip wszystkich chunków nieznacznie wzrósł.

## 1. Stan początkowy i porównywalne kopie

Potwierdzono HEAD, gałąź, pusty indeks oraz 4 modified / 2 untracked.
Zapisano SHA-256 sześciu chronionych plików. Przeczytano konfigurację Vite,
package.json/lockfile, main/App, Overview, Calendar, strony Explore/Research,
dialog i komponent wykresu, klienta API, i18n, hook odświeżania, testy i trzy
joby aktualnego CI. Nie przyjmowano wcześniejszych rozmiarów za nowy pomiar.

Przed zmianami wykonano pełne buildy working tree i czystego HEAD. Kopię HEAD
przygotowano przez archiwum Git, bez resetu lub clean. Osobna kopia HEAD + H2
zawiera dokładnie planowane zmiany H2 i pozostałe śledzone zależności z HEAD.
Nie zawiera wcześniejszych zmian README/SourceCheckStatus/CSS ani dwóch
nieśledzonych audytów. Porównano bajty wszystkich 13 plików kodu/testów H2
z tą kopią. Working tree zachowuje chronione pliki użytkownika.

Środowisko: **Node 20.9.0**, **Vite 6.4.3**, React/ReactDOM **18.3.1**,
TypeScript **5.9.3**, Recharts **3.10.1**. Bez zmian dependencies, lockfile,
konfiguracji Vite lub CI. Główne polecenia:

```powershell
# W frontend każdej z odpowiednich kopii:
npm run build
npx tsc --noEmit
$env:NODE_OPTIONS='--require=../.github/ci/no-network.cjs'
npm test

# W katalogu głównym:
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Analizę wykonano istniejącym Vite/Rollup: ignorowany `analyze.mjs` wywołuje
`vite.build`, zbiera `generateBundle`, `chunk.modules`, `imports`,
`dynamicImports` i `getModuleInfo`. Po zapisie odczytuje rzeczywiste bajty
plików i liczy gzip poziomem 6. Nie instalowano analizatora.

```text
node data/raw/frontend-h2-2026-10-30/analyze.mjs frontend data/raw/frontend-h2-2026-10-30/after-wt
node data/raw/frontend-h2-2026-10-30/analyze.mjs data/raw/frontend-h2-2026-10-30/head-h2/frontend data/raw/frontend-h2-2026-10-30/after-head
```

Analogiczne wywołania dla wersji sprzed edycji zachowały `baseline-wt`
i `baseline-head`. Te baseline nie były przebudowywane zmienionym kodem.

## 2. Rzeczywisty graf i źródło rozmiaru

Baseline main nie zawierał Recharts. Największymi modułami main według
Rollup `renderedLength` były: pl.json **258910 B**, ReactDOM **133838 B**,
economicExplanationCopy **33006 B**, briefModel **27045 B**, EconomyBrief
**20675 B**, economicExplanations **14568 B**, metricMetadata **11155 B**,
readingComparisons **10019 B**, economicInterpretation **8560 B**, React
**7672 B**, runtime API **7132 B**. Są to długości modułów przed końcową
minifikacją chunku, nie osobne gzip ani liczby addytywne do finalnego pliku.

Wcześniejszy graf:

```text
main → App → EconomyBrief → model, interpretacje, wyjaśnienia
                           → ReadingChartDialog --lazy→ TimeSeriesChart → Recharts
App --lazy→ Calendar
App --lazy→ Explore --lazy→ Indicators / Charts
App --lazy→ Research --lazy→ Relationships / MCI / MarketComparison
economicInterpretation → economicExplanations → duża kopia wyjaśnień
```

Statyczny import Overview wciągał jego model i wyjaśnienia również przy
bezpośrednim wejściu do Calendar/Explore/Research. Natomiast wykres Overview
już wcześniej był odroczony. Nie przypisujemy H2 stworzenia tej granicy.
API w bundlu zawiera kod runtime; importy samych typów nie tworzą runtime
interfejsów lub dodatkowych modułów. TypeScript nie jest zależnością klienta.

Po zmianie:

```text
main → App, React/ReactDOM, i18n, nawigacja, ChunkBoundary
App --lazy→ EconomyBrief → model, readingFacts, interpretacje
                        → współdzielone format / tooltip / provenance / chartData
EconomyBrief --Explain→ ReadingExplanation → ciężkie wyjaśnienia
ReadingChartDialog --otwarcie→ TimeSeriesChart → Recharts
App --lazy→ pozostałe dotychczasowe trasy
```

Main nadal zawiera jeden słownik PL; po H2 jego `renderedLength` to
259060 B, ReactDOM 133838 B. Nie wdrożono asynchronicznego systemu tłumaczeń.
Przy EN nie powstaje już nieużywany indeks Map/Set/RegExp polskich fraz;
jest tworzony raz przy pierwszym tłumaczeniu PL. Synchroniczne API i18n,
ten sam słownik, normalizacja i cache tłumaczeń pozostają zachowane.

Sprawdzono identyfikatory modułów we wszystkich chunkach: **zero duplikatów**
w obu baseline i obu H2, w tym React, ReactDOM, Recharts, i18n i API.
Analiza silnie spójnych składowych statycznego grafu zachowuje cztery
istniejące cykle wewnątrz node_modules: trzy pary Recharts selektor/komponent
Bar/Scatter/Line i d3-interpolate. **Brak cykli modułów źródłowych aplikacji**
i nowych cykli statycznych. Chunk wyjaśnień korzysta ze wspólnego kodu
Overview, które w tym momencie jest już załadowane.

Vite preloaduje statyczne zależności aktualnie wybranej trasy. Chrome
potwierdził brak ReadingExplanation i obu chunków wykresu przy wejściu na
Overview z wyłączonym Explain. Nie ma prefetchu wszystkich tras.

## 3. Minimalny zakres implementacji

- EconomyBrief korzysta z React.lazy w istniejącym Suspense App. Loading
  ma `role=status`. Nowa granica błędu pokazuje EN/PL i Retry przez ponowne
  załadowanie strony; zmiana trasy pozwala wyjść z błędnej sekcji.
- ReadingExplanation ładuje się po włączeniu Explain. Lokalny loading
  i komunikat błędu nie zastępują ani nie ukrywają wartości ekonomicznych.
- Lekkie `readingVariant`, `flowFact`, zbiory i `flowFacts` przeniesiono do
  readingFacts. Porównano przeniesione funkcje i literal danych z HEAD:
  bez zmian treści. Reeksporty zachowują dotychczasowych odbiorców.
- economicInterpretation importuje ten lekki moduł. Dzięki temu sam lazy
  tooltip nie pozostawia dużych wyjaśnień w początkowym grafie.
- Indeks polskich tłumaczeń powstaje dopiero przy użyciu PL. Dodano tylko
  tłumaczenie nowego komunikatu błędu, bez drugiego systemu i18n.

Nie zmieniano formatowania liczb, obliczeń, API JSON, danych, UI/CSS lub
R1/R2/R3. Nie zastosowano manualChunks, ogólnego vendor chunku, zwiększenia
chunkSizeWarningLimit, nowych bibliotek, prefetchu ani sztucznego opóźnienia.
Rollup sam wydzielił cztery współdzielone chunki oprócz dwóch nowych granic
lazy. Nie rozdrabniano ręcznie małych modułów. Samo przeniesienie Recharts
nie dałoby zysku Overview, ponieważ już nie był tam pobierany na starcie.
Szerszy podział słownika wymagałby zmiany synchronicznego modelu i18n;
pozostawiono go poza tym zakresem.

## 4. Cały build i chunki

Wszystkie rozmiary w tabelach są w **bajtach**, kB oznacza 1000 B.
Gzip to suma niezależnie kompresowanych plików JS poziomem 6, bez CSS/HTML.

| Wersja | Pliki JS | Suma raw | Suma gzip | Największy raw / gzip | Dynamic entry: liczba / raw |
| --- | ---: | ---: | ---: | ---: | ---: |
| HEAD baseline | 12 | 1073354 | 316876 | 545947 / 158481 | 9 / 154989 |
| HEAD + H2 | 18 | 1077132 | 322032 | 407847 / 121085 | 11 / 254205 |
| WT baseline | 12 | 1071307 | 316402 | 543900 / 158019 | 9 / 154989 |
| WT + H2 | 18 | 1075048 | 321321 | 407847 / 121083 | 11 / 252135 |

`Dynamic entry` to flaga Rollup, bez ich statycznych zależności. Recharts
jest statyczną zależnością lazy modułów, więc sam nie ma tej flagi; realny
koszt interakcji uwzględnia go poniżej. Łączny gzip wzrósł o **5156 B / 1,63%**
commit-only i **4919 B / 1,55%** WT. Fragmentacja ma koszt kompresji i wrapperów.
Nie przedstawiamy tego jako spadku rozmiaru całej aplikacji.

Pełna lista chunków, bez losowych hashy w nazwach; wartości raw / gzip:

| Chunk | Baseline HEAD | H2 HEAD | H2 WT |
| --- | ---: | ---: | ---: |
| index | 545947 / 158481 | 407847 / 121085 | 407847 / 121083 |
| LineChart | 370606 / 108913 | 370640 / 108926 | 370640 / 108925 |
| EconomyBrief | w index | 64729 / 19611 | 62659 / 18898 |
| MarketComparisonPage | 56919 / 16838 | 56990 / 16870 | 56990 / 16870 |
| CalendarPage | 42888 / 12630 | 42961 / 12657 | 42961 / 12656 |
| ReadingExplanation | w index | 33786 / 8163 | 33786 / 8163 |
| BeaEvidence | w index | 22621 / 8235 | 22607 / 8226 |
| RelationshipsPage | 15653 / 5618 | 15763 / 5666 | 15763 / 5666 |
| MacroIndexPage | 14164 / 4636 | 14235 / 4663 | 14235 / 4664 |
| InfoTooltip | w index | 12619 / 3723 | 12619 / 3723 |
| ChartsPage | 10030 / 3241 | 10096 / 3270 | 10096 / 3272 |
| IndicatorsPage | 9632 / 2972 | 9708 / 2998 | 9708 / 2999 |
| format | w index | 6392 / 1942 | 6392 / 1943 |
| TimeSeriesChart | 2872 / 1423 | 2933 / 1451 | 2933 / 1453 |
| indicatorMetadata | 1812 / 786 | 1846 / 804 | 1846 / 804 |
| ExploreDataPage | 1452 / 680 | 1519 / 707 | 1519 / 711 |
| ResearchPage | 1379 / 658 | 1485 / 709 | 1485 / 711 |
| chartData | w index | 962 / 552 | 962 / 554 |

Baseline WT ma index 543900/158019; pozostałe raw są takie jak baseline HEAD.
Jego gzip: LineChart 108910, MarketComparison 16838, Calendar 12630,
Relationships 5616, MacroIndex 4635, Charts 3241, Indicators 2970,
TimeSeriesChart 1423, indicatorMetadata 786, Explore 678, Research 656.
Różnic HEAD/WT nie przypisuje się H2: wynikają z wcześniejszych zmian użytkownika.

## 5. Chrome production preview: metoda

Użyto prawdziwego `vite preview --host 127.0.0.1 --port <port> --strictPort
--outDir <zachowany build>` oraz Chrome **156.0.8078.74**, headless/CDP.
Porty 4175/4177: HEAD przed/po; 4176/4178: WT przed/po. Prawdziwy lokalny
backend czytał PostgreSQL. Ignorowany wrapper dodał wyłącznie CORS dla
portów preview; nie podmieniał tras, danych lub odpowiedzi API.

Każda trasa: **3 cold i 3 warm**, EN, Explain off, 1366×1000, DPR 1,
bez throttlingu CPU/sieci. Przeplatano wszystkie cztery warianty dla każdej
próby; razem **120 wejść**. Cold czyścił cache i wyłączał go. Warm włączał
cache i ponawiał wejście. Po gotowości zbierano jeszcze 200 ms ruchu.
Wcześniejsze próby podczas równoległych testów nie są wynikami końcowymi.
Końcowy benchmark odbył się bez równoległych testów lub buildów.

Raw/gzip pochodzi z faktycznych pobranych plików. Transfer pochodzi z CDP
`Network.loadingFinished.encodedDataLength`: odpowiedzi gzip z narzutem HTTP,
nie suma rozmiarów z dysku. Nie obejmuje CSS, HTML i JSON API. Warm Vite
revaliduje pliki ETag; w tej próbie było **179 B na plik**, bez ponownego
pełnego transferu jego treści. Liczba plików/żądań JS warm pozostaje taka
jak cold; nie twierdzimy, że warm nie wykonuje żądań.

## 6. Początkowy zestaw JS per trasa

Commit-only, cold. Największym pobranym chunkiem każdej trasy jest main:
545947 B przed, 407847 B po. Liczba dodatkowych plików to kolumna JS minus 1.

| Trasa / wersja | JS | Raw | Gzip | Transfer cold | Transfer warm |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overview przed | 1 | 545947 | 158481 | 158962 | 179 |
| Overview H2 | 6 | 515170 | 155148 | 157828 | 1074 |
| Calendar przed | 2 | 588835 | 171111 | 171964 | 358 |
| Calendar H2 | 4 | 479821 | 143919 | 145490 | 716 |
| Indicators przed | 6 | 932321 | 273255 | 275667 | 1074 |
| Indicators H2 | 8 | 801847 | 238465 | 241954 | 1432 |
| Charts przed | 5 | 930907 | 272738 | 274781 | 895 |
| Charts H2 | 7 | 800389 | 237933 | 241053 | 1253 |
| Research przed | 5 | 935397 | 274456 | 276500 | 895 |
| Research H2 | 8 | 817554 | 243407 | 246899 | 1432 |

Working tree, cold; największy pobrany chunk każdej trasy: 543900 → 407847 B.

| Trasa / wersja | JS | Raw | Gzip | Transfer cold | Transfer warm |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overview przed | 1 | 543900 | 158019 | 158499 | 179 |
| Overview H2 | 6 | 513086 | 154427 | 157105 | 1074 |
| Calendar przed | 2 | 586788 | 170649 | 171501 | 358 |
| Calendar H2 | 4 | 479807 | 143908 | 145479 | 716 |
| Indicators przed | 6 | 930274 | 272786 | 275197 | 1074 |
| Indicators H2 | 8 | 801847 | 238472 | 241959 | 1432 |
| Charts przed | 5 | 928860 | 272271 | 274313 | 895 |
| Charts H2 | 7 | 800389 | 237941 | 241059 | 1253 |
| Research przed | 5 | 933350 | 273987 | 276030 | 895 |
| Research H2 | 8 | 817554 | 243409 | 246899 | 1432 |

Krytyczny zestaw Overview po H2: main, EconomyBrief, BeaEvidence, format,
InfoTooltip i chartData. Calendar: main, CalendarPage, format i BeaEvidence.
Indicators/Charts/Research dodatkowo pobierają własne lazy strony i potrzebny
graf wykresów. Recharts jest tam używany; nie jest niepotrzebnym prefetch.

Overview oszczędza zaledwie **1134 B transferu / 0,71%** commit-only oraz
1394 B / 0,88% WT. Główna korzyść lazy Overview dotyczy pozostałych tras,
które przestają pobierać jego model. Domyślna trasa dostaje dodatkowy etap
odkrywania importu i pięć żądań, równoleglonych przez preloader Vite.
Na wysokim RTT ten koszt może przeważyć niewielki zysk transferu Overview.
Nie dodano kolejnych granic lazy do już odroczonego dialogu wykresu.

Powyższe wyniki startowe dotyczą Explain off. Przy zapisanej preferencji
Explain on moduł wyjaśnień jest potrzebny od razu po montażu Overview;
nie obiecujemy wtedy tego samego zestawu początkowego ani oszczędności.
Koszt pierwszego włączenia Explain zmierzono osobno poniżej; nie wykonano
osobnego benchmarku cold z zapisaną preferencją on.

## 7. Czasy i ich granice

Mediany ms, przed → H2. Gotowość oznacza sześć kart Overview, wpis Calendar,
SVG wykresu Indicators/Charts i kontrolki Research; nie FCP/LCP/TTI.
Research w benchmarku mierzy gotowość kontrolek, nie koniec obliczania porównań.
Pełny wykres i podsumowanie danych sprawdzono oddzielnie w końcowym UI.

| Trasa | HEAD cold | HEAD warm | WT cold | WT warm | HEAD ScriptDuration | WT ScriptDuration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Overview | 518 → 472 | 487 → 475 | 502 → 478 | 490 → 461 | 133,4 → 126,6 | 125,5 → 127,9 |
| Calendar | 815 → 813 | 828 → 827 | 807 → 823 | 834 → 821 | 68,2 → 65,6 | 70,1 → 65,7 |
| Indicators | 452 → 471 | 435 → 425 | 489 → 458 | 444 → 437 | 133,5 → 133,6 | 133,3 → 128,7 |
| Charts | 409 → 445 | 383 → 434 | 395 → 378 | 436 → 399 | 198,9 → 200,2 | 203,6 → 181,9 |
| Research | 396 → 404 | 376 → 377 | 400 → 380 | 407 → 372 | 49,6 → 39,1 | 55,3 → 41,6 |

ScriptDuration to osobna metryka wykonania skryptów CDP, cold, zebrana po
gotowości +200 ms. Nie jest ilością skompilowanych bajtów ani TBT.
Nie każda trasa wykonuje się szybciej. Charts HEAD w tej serii ma gorszą
medianę gotowości o 36 ms cold i 51 ms warm, mimo mniejszego transferu.
Cold zakresy nakładają się: baseline **404–565 ms**, H2 **375–462 ms**;
w WT kierunek median jest przeciwny. Trzy próby nie ustanawiają trwałej
regresji ani gwarancji przyspieszenia. Nie dobierano tylko korzystnych wyników.

Czasy gotowości zawierają odpowiedzi lokalnego API; nie przypisujemy ich
latencji bundlowi. Sieć loopback jest bardzo szybka. Nie zmierzono FCP,
LCP, TBT, wysokiego RTT, słabego telefonu lub nowej publikacji makro na żywo.
Uzasadnieniem zmian jest wykazany spadek pobieranych bajtów na ważnych trasach,
usunięcie niepotrzebnego kodu z ich grafu i zachowana funkcjonalność,
nie obietnica jednakowego zysku czasowego na każdym urządzeniu.

## 8. Koszt po interakcji i nawigacji

Nowe pliki ponad wcześniej załadowany zestaw; cold Calendar poprzedza w tej
próbie pierwsze wejście na Overview. Wartości: liczba / raw / gzip / transfer.

| Interakcja | HEAD przed | HEAD H2 | WT przed | WT H2 |
| --- | ---: | ---: | ---: | ---: |
| Wykres Overview i zakresy | 2 / 373478 / 110336 / 111157 | 2 / 373573 / 110377 / 111198 | 2 / 373478 / 110333 / 111154 | 2 / 373573 / 110378 / 111199 |
| Włączenie Explain | 0 / 0 / 0 / 0 | 1 / 33786 / 8163 / 8535 | 0 / 0 / 0 / 0 | 1 / 33786 / 8163 / 8535 |
| Calendar → Overview | 0 / 0 / 0 / 0 | 3 / 78310 / 23886 / 25367 | 0 / 0 / 0 / 0 | 3 / 76240 / 23175 / 24654 |
| Powrót Overview → odwiedzony Calendar | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

Największy nowy plik wykresu to LineChart: 370606 → 370640 B; pozostały to
TimeSeriesChart. Nie ma zysku jego transferu w H2; zachowano wcześniejsze
odroczenie. Dla Explain największy plik ma 33786 B. Calendar → Overview
odracza EconomyBrief (64729 B HEAD / 62659 B WT), InfoTooltip i chartData.
To jawnie przeniesiony koszt pierwszej wizyty, nie usunięte funkcje.
Włączenie Explain i zmiana języka nie dodają GET brief.

## 9. R1/R2/R3, regresje i prawdziwe UI

Nie edytowano useOverviewRefresh lub backendu. Zachowano jeden timer,
next_check_at, hidden/focus, polling running, abort, ochronę starego zakresu,
reload nowego publication_id, cleanup i deduplikację koordynatora.
Nowe testy sprawdzają cold Calendar bez importu Overview, loading Suspense,
porzucony pending import, dwa prawidłowe odczyty po dwóch mountach bez POST
przed terminem, błąd API/Retry oraz odrzucony chunk EN/PL i wyjście na inną
trasę. Kontrolowany Promise modeluje pobierany moduł, bez sztucznego timera sieci.

Regresja z rzeczywistym hookiem R1: backendowy deadline T+120 s, przejście
przez Calendar po 60 s, remount Overview z tym samym terminem, **jeden POST**
bea_release_aware w pierwotnym terminie, reload nowej generacji i jej widoczne
wydarzenie GDP. Unmount usuwa dalsze próby. Nie obniżano backendowych 900/21600 s
i nie zmieniano punktów, limitów, locka lub backoff R3. Jak wcześniej, sieć,
pobieranie modułu i throttling mogą opóźnić montaż i próbę; nie jest to SLA.

Końcowy Chrome: **53 zapisane scenariusze**, prawdziwy production preview/API,
EN/PL, **1366 i 390 px**, bez wyjątków JavaScript/console.error i poziomego
overflow. Sprawdzono siedem BEA z 29.10, precision=1, dwa mixed_sources,
GDP 3,4/2,2 o 13:30 PL, Forecast null i przyszłe puste Actual 25.11.
Zachowano sześć kart i limit czterech wydarzeń; source evidence i tooltip BEA.

Sprawdzono wykresy 1Y/3Y/5Y/Max, current-vintage, Explain i treść tooltipów,
Escape/fokus, zmianę języka bez F5, bezpośrednie trasy, rzeczywisty F5,
Calendar → Overview → Explore → Research, Back/Forward, szybką zmianę tras
i rzeczywiste hidden/visible. Doprecyzowano helper, aby Research przed F5
oczekiwał pełnego wykresu i podsumowania danych, nie samych kontrolek;
końcowy pełny przebieg przeszedł ponownie. Obejrzano zrzuty desktop EN
Overview i mobile PL Overview/Calendar. Nie używano fixture odpowiedzi API.

W końcowych zapisach faz UI odebrano **182 odpowiedzi HTTP 200**. Cztery
żądania nie miały odpowiedzi w chwili rekordu przy zmianach tras, dwa z nich
miały jawny canceled; nie zaliczono ich jako udanych odpowiedzi. Zakończone
odpowiedzi nie miały błędnego HTTP. Błąd historii/Retry i błędy API/chunków
sprawdzają testy offline, bez powodowania awarii prawdziwego serwera.

Wszystkie kontrole preview odbyły się pod advisory lock **726530019**,
utrzymywanym przez osobne połączenie read-only. Potwierdzono
transaction_read_only=on; własny API używał PGOPTIONS read-only. Przed/po
porównano count/max source_check_runs i stan/publication_id koordynatora:
**identyczne**. Lock zwolniono i zatrzymano tylko własne API/preview/Chrome.
Nie wykonano ingestion, DDL, inicjalizacji, backfillu ani kontaktu z wydawcami.

## 10. Pełna walidacja

| Kontrola H2 | Wynik |
| --- | --- |
| Pełny backend offline | **1123 passed**, 60,02 s |
| Pełny frontend WT z blokadą sieci CI | **610 passed / 26 plików**, 25,97 s |
| Pełny frontend dokładnej kopii HEAD + H2 | **610 passed / 26 plików** |
| Osobny TypeScript typecheck, obie wersje | passed |
| Production build, obie wersje | passed, największy **407,85 kB** |
| Production preview / prawdziwe API | passed, 53 scenariusze |
| Porównawczy benchmark | 120 wejść, oba porównania |
| git diff --check | passed |

Pięć nowych przypadków frontendowych ponad 605; wszystkie stare testy
zachowano, w tym R1/R3, źródła, ekonomia, wykresy i MCI. Nie zwiększano
timeoutów i nie pomijano testów. Nie zmieniano kodu lub zależności backendu,
więc czterech skryptów PostgreSQL nie uruchamiano ponownie w H2. Ich zielone
H1 nie są przedstawiane jako nowe wyniki. Nie uruchamiano GitHub Actions.

Baseline buildy jawnie ostrzegały o przekroczeniu 500 kB. Po H2 żaden chunk
nie przekracza progu; ostrzeżenie ustąpiło wskutek zmiany grafu, nie konfiguracji.
Nie wyciszano Starlette/httpx i nie aktualizowano zależności. Sporadyczny błąd
nawigacji MCI nie wystąpił w końcowych pełnych przebiegach.

Nowe granice asynchroniczne wymagały dopasowania dwóch starych testów:
oczekiwania na noty po Explain oraz na pierwszy efekt pobierania Overview
przed sprawdzeniem, że zmiana języka nie pobiera danych. Asercje zachowano.
Jedna równoległa próba testów/buildów przekroczyła DOM wait przy zimnej
kompilacji not; ich moduł jest teraz kompilowany podczas kolekcji tego testu,
jak istniejące ciężkie trasy w testach i18n. Cold import nadal kontrolują
osobne testy i rzeczywisty preview. Pierwsza próba kopiowania testu z błędnym
katalogiem nie zmieniła kopii; poprawiono ścieżkę i potwierdzono końcowe bajty.
Nieudanych prób nie policzono jako sukcesu i nie zwiększano timeoutów.

## 11. Zakres H2, ochrona i końcowy Git

**14 plików H2**, 9 modified i 5 nowych:

- frontend/src/App.tsx
- frontend/src/brief/EconomyBrief.tsx
- frontend/src/brief/EconomyBrief.test.tsx
- frontend/src/brief/economicExplanationCopy.ts
- frontend/src/brief/economicExplanations.ts
- frontend/src/brief/economicInterpretation.ts
- frontend/src/brief/ReadingExplanation.tsx — nowy.
- frontend/src/brief/readingFacts.ts — nowy.
- frontend/src/i18n/language.ts
- frontend/src/i18n/language.test.tsx
- frontend/src/i18n/pl.json
- frontend/src/navigation/ChunkBoundary.tsx — nowy.
- frontend/src/navigation/lazyLoading.test.tsx — nowy.
- docs/audits/frontend-vite-bundle-optimization-2026-10-30.md — ten raport.

Chronione SHA-256 przed = po, poza zakresem H2:

| Plik | SHA-256 |
| --- | --- |
| README.md | 7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b |
| frontend/src/brief/SourceCheckStatus.tsx | 65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900 |
| frontend/src/brief/SourceCheckStatus.test.tsx | bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf |
| frontend/src/styles.css | 7696bd5cac8c8bb3792f86d23e588c97f1fd87a5aef407a9f141ceb07b9b20e0 |
| docs/audits/calendar-next-releases-priority-2026-10-29.md | e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839 |
| docs/audits/calendar-release-day-latency-2026-10-29.md | e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b |

Końcowy zakres: **13 modified / 7 untracked**, pusty staging, HEAD/main bez zmian.

```text
 M README.md
 M frontend/src/App.tsx
 M frontend/src/brief/EconomyBrief.test.tsx
 M frontend/src/brief/EconomyBrief.tsx
 M frontend/src/brief/SourceCheckStatus.test.tsx
 M frontend/src/brief/SourceCheckStatus.tsx
 M frontend/src/brief/economicExplanationCopy.ts
 M frontend/src/brief/economicExplanations.ts
 M frontend/src/brief/economicInterpretation.ts
 M frontend/src/i18n/language.test.tsx
 M frontend/src/i18n/language.ts
 M frontend/src/i18n/pl.json
 M frontend/src/styles.css
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
?? docs/audits/calendar-release-day-latency-2026-10-29.md
?? docs/audits/frontend-vite-bundle-optimization-2026-10-30.md
?? frontend/src/brief/ReadingExplanation.tsx
?? frontend/src/brief/readingFacts.ts
?? frontend/src/navigation/ChunkBoundary.tsx
?? frontend/src/navigation/lazyLoading.test.tsx
```

Metadane grafu, cztery buildy, pomiary JSON, logi, helpery, profile i zrzuty
pozostają ignorowane w `data/raw/frontend-h2-2026-10-30/`. Nie dodano ich,
sekretów, .env lub danych bazy do zakresu repozytorium. Backend, schema,
requirements/lockfile, Compose, CI i chroniony CSS pozostają bez zmian.
Bez stagingu, commita, pusha, resetu, clean lub zmian historii.
Nie rozpoczęto kolejnego etapu ani nie zmierzono latencji nowej publikacji.

## 12. Kontrola zamknięcia H2 — 30.10.2026

Ponownie potwierdzono main, bazowy HEAD ea66bf4383e75218b5abd141b25a674596a32533,
13 modified / 7 untracked i początkowo pusty indeks. Sześć chronionych
SHA-256 zgadza się z tabelą wyżej. Przejrzano diff, wszystkie nowe moduły
i testy oraz zachowane metadane grafu i pomiarów. Zgodność plików buildu
i wszystkich 30 próbek cold commit-only z wartościami w raporcie sprawdzono
bez ponawiania całego benchmarku. Kod optymalizacji nie zmienił się podczas
zamknięcia; zachowano także ograniczenia czasów, wysokiego RTT i kosztu gzip.

Staging obejmuje dokładnie 14 plików H2 z sekcji 11. Wyeksportowano cały
indeks do odrębnej kopii, bez wcześniejszych zmian użytkownika. Zgodność
eksportu/working tree z blobami indeksu potwierdzono przez Git, z normalizacją
LF/CRLF. Nie zależy on od chronionych SourceCheckStatus/CSS. Przejrzano cały
staged diff, nazwy i wzorce sekretów; brak .env, RAW, helperów, logów,
buildów lub zmian backendu/schema/workflow. Obie kontrole whitespace przeszły.

### Ponowne pełne testy i Node 22

| Kontrola zamknięcia | Working tree, Node 20.9.0 | Dokładny staging, Node 22.23.4 |
| --- | --- | --- |
| Pełny backend offline | **1123 passed**, 57,34 s | **1123 passed**, 61,18 s |
| Pełny frontend z blokadą sieci CI | **610 passed / 26 plików**, 27,04 s | **610 passed / 26 plików**, 43,34 s |
| Osobny TypeScript typecheck | passed | passed |
| Production build | passed | passed |
| Największy chunk raw / gzip | 407847 / 121083 B | 407847 / 121099 B |

Node **22.23.4** pobrano jako przenośne win-x64 z oficjalnego nodejs.org,
zweryfikowano opublikowany SHA-256 archiwum i uruchomiono wyłącznie w
ignorowanym katalogu. Nie zmieniono instalacji hosta, dependencies/lockfile
lub CI. To lokalny Windows, nie deklaracja wyniku runnera Ubuntu.

Node 22 staging: **18 plików JS**, suma raw **1077132 B**, suma gzip
**322324 B**. Wszystkie bajty JS, nazwy/hash i statyczne/dynamiczne krawędzie
importów są identyczne z HEAD + H2 na Node 20; zero duplikowanych modułów.
Różnica gzip względem 322032 B z Node 20 wynika z kompresji innej wersji
runtime, nie zmiany grafu. Wcześniejsze tabele transferu pozostają pomiarami
Node 20, a nie nowym benchmarkiem Node 22. Nie pojawiło się ostrzeżenie
Rollup ani Vite ponad 500 kB. Próg niezmieniony; Starlette/httpx nie wyciszano.
Nie pomijano testów, nie zwiększano timeoutów; MCI nie zgłosiło sporadycznego
błędu. Czterech skryptów PostgreSQL nie uruchamiano lokalnie ponownie.

### Końcowy preview i odzyskiwanie po błędzie chunku

Produkcja dokładnego stagingu, serwowana przez Node 22: **35 scenariuszy**
Chrome EN/PL, 1366/390 px, rzeczywiste API bez fixture odpowiedzi.
Powtórzono Overview/Calendar/Explore/Research, dane BEA, precision/mixed_sources,
puste przyszłe Actual i Forecast, źródła, sześć kart, zakresy wykresów,
Explain, Escape/fokus, F5, Back/Forward, szybką nawigację i hidden/visible.
Brak nieoczekiwanych wyjątków JS, console.error lub poziomego overflow.
Nadal brak Recharts przy zwykłym Overview oraz wyjaśnień przy Explain off.
Calendar → Overview dociąga odroczone moduły. Istniejące regresje R1/R3,
w tym T+120 s i remount po 60 s z jednym POST, przeszły ponownie w pełnym zestawie.

Dodatkowo **6 scenariuszy odzyskiwania**, po trzy EN/PL:

- Zapamiętane Explain on: 22 działające noty, sześć kart, jeden GET brief,
  brak przedwczesnego wykresu i zbędnego odczytu po przełączeniu Explain.
- Kontrolowany HTTP 404 wyłącznie dla chunku EconomyBrief: przetłumaczony
  komunikat, bez automatycznej pętli przeładowań; przejście do Calendar działa.
  Po ponownym wejściu odrzucony import pozostaje błędem do świadomego Retry.
  Przywrócenie zasobu i kliknięcie prawdziwego Retry ładuje nowy dokument
  i sześć kart. W każdym języku zablokowano jedno żądanie chunku.
- HTTP 404 opcjonalnego ReadingExplanation zachowuje karty i liczby,
  pokazuje komunikaty statusu, a ręczne odświeżenie po przywróceniu zasobu
  odtwarza 22 noty i zapamiętaną preferencję.

404 modeluje brak starego chunku po wdrożeniu, bez zmiany plików produkcyjnych
i bez podmieniania API. Oczekiwane błędy importu w tych próbach odróżniono
od normalnego smoke; po odzyskaniu brak błędów JS. Nie jest to test polityk
cache/CDN faktycznego wdrożenia: jeśli nowy dokument lub zasób nadal są
niedostępne, ręczne Retry nie gwarantuje odzyskania, lecz nie tworzy autopętli.

Obie nowe kontrole przeglądarkowe odbyły się pod dotychczasowym lockiem
przez read-only połączenie; własny API również miał wymuszone read-only.
Count/max kontroli i stan/publication_id przed/po pozostały identyczne.
Zwolniono lock i zatrzymano własne procesy. Nie wykonywano ingestion,
DDL lub inicjalizacji bazy, kontaktu z wydawcami albo zmian danych ekonomicznych.

### Commit i informacje po pushu

Zatwierdzany jeden commit: **Optimize frontend bundle with lazy-loaded overview**.
Zdalny origin/main przed zatwierdzeniem nadal wskazywał ea66bf4.
Po walidacji zmieniono tylko tę dokumentację, jej staging i kopię; kod jest
identyczny z walidowanym indeksem. Sześć chronionych plików pozostaje poza
stagingiem, byte-identycznie. Ostrzeżenia LF→CRLF są normalizacją Git,
nie błędem whitespace. Nie wykonano resetu, clean, amend lub force push.

Pełny hash, wynik zwykłego pusha i rzeczywisty URL oraz zakończone wyniki
trzech jobów zostaną podane w zewnętrznym raporcie Codexa po ich uzyskaniu.
Nie deklaruje się przyszłego sukcesu CI na podstawie walidacji lokalnej.
Nie powstanie dodatkowy commit wyłącznie dla tych informacji. Nie rozpoczęto
kolejnego etapu; pozostają wszystkie opisane ograniczenia pomiarów H2.
