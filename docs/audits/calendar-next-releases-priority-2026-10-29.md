# MacroLens — kolejne publikacje USA i dostępność oficjalnego Actual

Audyt **29.10.2026**, Europe/Warsaw. Repozytorium `C:\Projects\macrolens`,
`main`, HEAD `0147d6e1fc64d3c5e317f724e8f264fb119760b8` —
`Add official ADP employment release calendar`.

**Rekomendacja: Empire State Manufacturing Survey, kalendarz + Actual głównego
General Business Conditions Index SA, bez FRED jako pośrednika.** Dostępne CSV
i raporty umożliwiają kontrolę wyniku, a warunki NY Fed wyraźniej opisują
przechowywanie i dystrybucję niż warunki Philadelphia Fed. Nie jest to potwierdzenie
gwarantowanej latencji ani zgoda prawna dla całej aplikacji. Nie rozpoczęto integracji.

## 1. Zakres i ochrona istniejącego stanu

Przejrzano audyty [pokrycia](calendar-coverage-2026-10-27.md),
[ciągłości 1B](calendar-schedule-continuity-2026-10-27.md),
[Retail](calendar-retail-measures-2026-10-28.md),
[Core PPI](calendar-core-ppi-2026-10-28.md),
[Employment](calendar-employment-measures-2026-10-28.md),
[Michigan](calendar-michigan-sentiment-2026-10-28.md) i
[ADP](calendar-adp-employment-2026-10-28.md). Ich liczby i ograniczenia są
historycznymi wynikami konkretnych kontroli, a nie automatycznie stanem dzisiejszym.

Sprawdzono katalog `config/series.yaml`, `SPECS` w `calendar_readings.py`,
`release_calendar.py`, `calendar_agenda.py`, trasy w `app/api/main.py`,
adaptery harmonogramów, lokalne dowody oraz koordynator `overview_refresh.py`.
Odczyt PostgreSQL odbył się z `connection.read_only=True`;
`SHOW transaction_read_only` zwróciło **on**. Wykonano SELECT i istniejącą
projekcję `list_calendar_events`, bez zapisu i bez uruchamiania koordynatora.
Nie korzystano z UI wywołującego odświeżanie.

Nie zmieniono kodu, konfiguracji, testów, bazy, RAW ani cache. Odpowiedzi
diagnostyczne przetwarzano w pamięci, bez zapisywania pobranych zbiorów.
Jedynym nowym plikiem jest ten raport. Cztery zastane pliki użytkownika mają
identyczne SHA-256 jak przed audytem; nie wykonano stagingu, commita ani pusha.

## 2. Obecne pokrycie i rzeczywiste luki

Katalog zawiera **45 serii**; `SPECS` ma **17 identyfikatorów publikacji FRED**:
9, 10, 11, 13, 18, 27, 46, 50, 53, 54, 95, 97, 180, 190, 192, 219, 221.
Istnieją też osobne integracje FOMC, ISM, Michigan i ADP. Dla okna
01.09.2026–31.01.2027 rzeczywista projekcja zwróciła **245 wydarzeń i 27
różnych nazw**. To inwentaryzacja tego okna, nie wskaźnik kompletności rynku.

| Obszar | Już obsługiwany zakres — nie proponujemy go ponownie |
| --- | --- |
| Praca | Employment: NFP, U-3, earnings oraz CIVPART, U6RATE i AWHAETP; JOLTS; Claims; ECI |
| Inflacja | CPI headline/core; PCE; PPI headline i oba core m/m, z osobnymi r/r NSA |
| Wzrost/konsument | GDP, Personal Income and Outlays, Retail headline/ex Autos/Control, M3, G.17, CFNAI |
| Housing/finanse | Starts, permits i ich etapy, New Home Sales, NFCI; H.15 i PMMS z wcześniejszymi ograniczeniami bindingu |
| Fed i badania | Decyzje FOMC, konferencje, Minutes, SEP, ISM Manufacturing/Services |
| Niedawne dodatki | Michigan Preliminary/Final oraz miesięczny ADP: daty/metadane/linki, **bez liczb** |

| Kandydat | Nowe wydarzenie? | Istnieje tylko seria lub częściowa integracja? |
| --- | --- | --- |
| Philadelphia MBOS | Tak, rzeczywista luka | Brak w katalogu, dowodach i projekcji; brak powiązanego raportu w lokalnych `economic_releases` |
| Empire State | Tak | Jak wyżej; brak lokalnej serii tego badania |
| FT900 Trade | Tak | `BOPGSTB` nie istnieje lokalnie; GDP i M3 nie zastępują FT900 |
| Productivity and Costs | Tak | `OPHNFB` i `ULCNFB` nie istnieją lokalnie; ECI i godziny CES nie są tą publikacją |
| Conference Board Confidence | Tak | Michigan i wskaźniki konsumpcji nie są tym badaniem; brak integracji/katalogu |
| S&P Global US PMI | Tak | Istniejące ISM są odrębnym wydawcą i metodologią; brak integracji Flash/Final S&P |

Sprawdzono listę lokalnych grup i katalog oraz wyszukano nazwy i identyfikatory
w kodzie/konfiguracji. Brak nowych kandydatów nie jest wnioskiem wyłącznie
z siedmiodniowego widoku Overview.

Rzeczywisty kontrakt to odpowiedź słownikowa FastAPI:
`GET /api/v1/calendar?start_date=...&end_date=...&include_readings=true`;
zawiera wydarzenia i osobne miary ze statusami, okresami i provenance.
Bez `include_readings` używa sprawdzonej powyżej projekcji. Nie uruchamiano
w audycie HTTP odświeżania ani nie deklarujemy nowego testu przeglądarkowego.

## 3. Oficjalne źródła i niewielka kontrola techniczna

### A. Philadelphia Fed Manufacturing Business Outlook Survey

[Strona MBOS](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/manufacturing-business-outlook-survey)
podaje **19.11 i 17.12.2026 o 08:30**. [Raport X](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/mbos-2026-10)
potwierdza **15.10.2026, 08:30 ET**, okres X i tabelę Current/Previous:

| Miara SA | IX → X 2026 | Jednostka |
| --- | --- | --- |
| Current General Business Activity | 37,8 → 20,9 | pkt indeksu |
| New Orders | 29,2 → 4,3 | pkt indeksu |
| Employment / Number of Employees | 11,8 → 9,1 | pkt indeksu |
| Prices Paid | 48,6 → 43,2 | pkt indeksu |
| Future General Activity | 52,9 → 33,0 | pkt indeksu; horyzont sześciu miesięcy |

Bezpośredni [CSV indeksów SA](https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/MBOS/Historical-Data/Diffusion-Indexes/bos_dif.csv?sc_lang=en)
zwrócił HTTP 200, `text/csv`, 77 915 bajtów. Nagłówek:
`DATE,GAC,NOC,SHC,UOC,DTC,IVC,PPC,PRC,NEC,AWC,GAF,...`.
Wiersz `Oct-26` potwierdza powyższe wartości; `Sep-26` daje Previous.
Strona oferuje także XLS/TXT oraz szerszy zestaw SA/NSA z komponentami;
nie pobierano wszystkich formatów ani archiwum historii. Daty `May-68` itd.
wymagają jawnego parsera miesiąca i kontrolowanego stulecia.

[FAQ MBOS](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/mbos-faqs)
wyjaśnia indeks jako różnicę udziałów wzrost/spadek, zakres −100…100 i próg 0.
Wynik nie jest procentową zmianą produkcji. W kalendarzu: poziom, Previous
poprzedniego miesiąca, różnica w punktach; bez m/m i bez progu 50 właściwego PMI.
FAQ opisuje publikację zwykle w trzeci czwartek o 08:30 ET z wyjątkami,
**TXT bieżącego raportu przed pozostałymi plikami** i możliwe opóźnienie dostępu.
Terminy kolejnego roku zwykle pojawiają się w listopadzie. Nie potwierdzono
rocznej listy 2027 w sprawdzonym kalendarzu; nie wygenerowano jej z reguły.
Roczne przeliczenie sezonowości może zmieniać historyczne pliki wobec dawnych PDF.

[Kalendarz z filtrem](https://www.philadelphiafed.org/calendar-of-events?release=manufacturing-business-outlook-survey)
w odczycie tekstowym nie dał kompletnej tabeli MBOS; terminy XI/XII są jawne
na stronie samego badania. Nie uznano widocznych na ogólnej stronie świąt
lub blackout FOMC w 2027 za harmonogram MBOS.

### B. Empire State Manufacturing Survey

[Strona badania](https://www.newyorkfed.org/survey/empire/empiresurvey_overview)
ma konkretne daty **15.09, 15.10, 16.11 i 15.12.2026** oraz zegar
08:30 lub krótko po nim. [Kalendarz ekonomiczny NY Fed](https://www.newyorkfed.org/research/calendars/nationalecon_cal)
określa strefę jako Eastern Time i pokazuje Empire 15.10 o 08:30.
Ogólny [kalendarz regionalny](https://www.newyorkfed.org/regional-economy/calendar)
nie zastępuje listy przy badaniu. W tych źródłach nie znaleziono dat 2027.

Pobrano w pamięci bezpośrednie oficjalne CSV:
[SA](https://www.newyorkfed.org/medialibrary/media/survey/empire/data/esms_seasonallyadjusted_diffusion.csv)
— HTTP 200, 36 351 bajtów; [NSA](https://www.newyorkfed.org/medialibrary/media/survey/empire/data/esms_notseasonallyadjusted_diffusion.csv)
— HTTP 200, 36 440 bajtów. `GACDISA` to Current, `GAFDISA` to Future;
`GACDINA` jest odrębną wersją NSA. Nie wolno podstawiać żadnej z nich za inną.
`ND` oznacza brak, nie zero. `surveyDate=2026-10-31` oznacza miesiąc X,
**nie przyszłą datę publikacji**; normalizacja do początku miesiąca jest konieczna.

| Dokument i okres | Główny Current SA | Previous SA | Future SA — osobny wskaźnik |
| --- | ---: | ---: | ---: |
| [Raport IX, 15.09](https://www.newyorkfed.org/medialibrary/media/survey/empire/empire2026/2026_09-empire-state-manufacturing-survey.pdf) | 7,6 | 20,6 (VIII) | 29,0 |
| [Raport X, 15.10](https://www.newyorkfed.org/medialibrary/media/survey/empire/empire2026/2026_10_empire-state-manufacturing-survey.pdf) | 25,5 | 7,6 (IX) | 21,0 |

PDF-y i CSV są zgodne w tej próbie; nie dowodzi to braku rewizji całej historii.
Strona opisuje styczniowe przeliczenia sezonowości. Indeks jest poziomem
dyfuzyjnym: brak procentu, m/m i syntetycznego nagłówka z innych subindeksów.
Możliwe jest bezpośrednie zasilanie bez FRED. Czas publikacji nie jest SLA CSV;
nie przeprowadzono obserwacji na żywo w minucie nowej publikacji.

### C. U.S. International Trade in Goods and Services — FT900

[Census schedule](https://www.census.gov/foreign-trade/schedule.html)
potwierdza **04.11.2026 / IX, 08.12 / X, 07.01.2027 / XI**,
wszystkie o **08:30 Eastern**. [BEA full schedule](https://www.bea.gov/news/schedule/full)
niezależnie potwierdza XI/XII; odczytana tabela BEA obejmuje 2026.

Pozostałe opublikowane terminy Census w 2027:

| Data publikacji | Okres |
| --- | --- |
| 04.02 | XII 2026 |
| 09.03 | I 2027 |
| 06.04 | II |
| 05.05 | III |
| 09.06 | IV |
| 07.07 | V |
| 05.08 | VI |
| 08.09 | VII |
| 06.10 | VIII |
| 04.11 | IX |
| 07.12 | X |

Dla XI/XII 2027 harmonogram ma TBD; nie dopisano dat 2028.
W tej samej stronie **Advance Economic Indicators ma osobną tabelę i inne
terminy**. Jego dane goods-only nie mogą potwierdzać Actual pełnego FT900.

[Bieżący FT900](https://www.census.gov/foreign-trade/Press-Release/current_press_release/index.html)
oferuje PDF, ZIP XLSX i osobny
[Exhibit 1 XLSX](https://www.census.gov/foreign-trade/Press-Release/current_press_release/exh1.xlsx).
Ten jeden arkusz pobrano: HTTP 200, 246 338 bajtów, prawidłowy ZIP/XML XLSX.
Zawiera bilans, eksport i import osobno dla goods/services/total; kwoty SA
w **mln USD**, oznaczenia `(R)` dla rewizji. Wiersz VIII 2026:
balance −105 572, exports 315 182, imports 420 754; ich różnica daje bilans.

[Raport BEA, 06.10, za VIII](https://www.bea.gov/news/2026/us-international-trade-goods-and-services-august-2026)
potwierdza deficyt 105,6 mld USD i poprzedni, zrewidowany lipcowy 92,8 mld.
Deficyt jako dodatnia wielkość w tekście nie zmienia znaku salda: aplikacja
powinna pokazać **−105,572 mld USD**, nie +105,572. Dane są nominalne,
odsezonowane, na bazie bilansu płatniczego; nie są wkładem eksportu netto
do realnego GDP. Goods-only Census basis i real goods to odrębne pozycje.

[BOPGSTB](https://fred.stlouisfed.org/series/BOPGSTB) ma właściwą definicję,
Monthly, SA, Millions of Dollars; VIII −105 572, VII −92 826.
FRED może służyć porównaniu, lecz nie daje gwarancji dostępności w terminie Census.
Bezpośredni arkusz/raport usuwa zależność od jego pośrednictwa. Rewizje miesięczne
i roczne wymagają odróżnienia dokumentu publikacji od bieżącej historii.

### D. Productivity and Costs — BLS

[Harmonogram raportu](https://www.bls.gov/schedule/news_release/prod2.htm)
potwierdza **05.11.2026 Q3 preliminary, 08.12 Q3 revised, 04.02.2027 Q4 preliminary**,
08:30 ET. Dalsze jawne terminy 2027: 04.03 Q4 revised, 06.05 Q1 preliminary,
03.06 Q1 revised, 05.08 Q2 preliminary, 02.09 Q2 revised, 04.11 Q3 preliminary,
07.12 Q3 revised. Dwa etapy tego samego kwartału nie są nowymi kwartałami.

[Raport BLS Q2 revised](https://www.bls.gov/news.release/prod2.nr0.htm),
03.09.2026 o 08:30 ET: Nonfarm Business labor productivity **+1,4%**,
unit labor costs **+1,2%**; obie kwartalne zmiany są SA annualized.
Raport zawiera omówienie rewizji i tabele; strona jest maszynowo czytelna
przez narzędzie WWW. Bezpośredni klient harmonogramu ponownie otrzymał
**HTTP 403**; nie obchodzono blokady i nie potwierdzono regularnego dostępu
lokalnego klienta do nowych raportów wynikowych.

[OPHNFB](https://fred.stlouisfed.org/series/OPHNFB) i
[ULCNFB](https://fred.stlouisfed.org/series/ULCNFB) są kwartalnymi poziomami SA,
**Index 2017=100**, a nie gotowymi kwartalnymi procentami. Pierwszy mierzy
realny output na godzinę; drugi koszt pracy na jednostkę outputu.
[BLS Productivity](https://www.bls.gov/productivity/) i raport rozróżniają
wydajność, output, godziny i koszty; nie należy używać godzin AWHAETP
jako zamiennika produktywności całego nonfarm business.

Poprawne ewentualne przeliczenie: `100 × ((I[q]/I[q−1])^4 − 1)`.
Zwykłe `100 × (I[q]/I[q−1] − 1)` nie jest annualized. Każda para wymaga
tej samej wersji i bazy. Preliminary/revised potrzebują osobnej tożsamości
etapu i dowodu dokumentu; porównanie rewizji tego samego Q powinno być jawne,
a Previous poprzedniego Q — osobne. To decyzja modelu do przyszłego wdrożenia.
Dzisiejszy szereg FRED nie odtwarza historycznego first printu.

### E. The Conference Board Consumer Confidence

[Oficjalna strona](https://www.conference-board.org/topics/consumer-confidence/)
zwróciła HTTP 200. Komunikat z **27.10.2026** zawiera X: Consumer Confidence
**91,7** (1985=100), poprzedni IX **84,2 po rewizji**; Present Situation
**120,4**, Expectations **72,6**. Widać także sprostowanie treści komunikatu.
Jest to HTML z wynikiem, lecz nie potwierdzono stabilnego darmowego CSV/API
pełnej historii ani wspólnej chwili aktualizacji wszystkich kanałów.

Ten sam komunikat jawnie zapowiada **24.11.2026 o 10:00 ET** i opisuje
ogólną regułę ostatniego wtorku miesiąca. Interaktywny Economic Indicator
Calendar nie dostarczył w odczycie HTTP jawnej listy przyszłych dat.
**Nie potwierdzono osobno terminu grudniowego ani rocznika 2027**;
nie wyprowadzono ich z reguły bez sprawdzenia wyjątków. Nie przypisano
automatycznie przyszłemu raportowi okresu z samej częstotliwości.
Present Situation dotyczy bieżących warunków biznesu i pracy; Expectations
oczekiwań dochodów, biznesu i pracy. Nie są to indeksy Michigan.

### F. S&P Global Flash US PMI

[FAQ S&P](https://www.spglobal.com/market-intelligence/en/solutions/products/resources/pmi-faq)
rozróżnia Manufacturing, Services i Composite oraz Flash i Final. Flash
bazuje zwykle na 85–90% odpowiedzi, około tydzień przed Final. FAQ opisuje
ogólny rytm Final: manufacturing w pierwszy, services/composite w trzeci
dzień roboczy. To opis wydawcy, **nie zweryfikowany kalendarz wyjątków USA**.

[Oficjalna analiza X, 23.10.2026](https://www.spglobal.com/market-intelligence/en/news-insights/research/2026/10/us-flash-pmi-signals-sustained-strong-growth-but-also-further-inflation-uplift-in-october)
podaje Composite Flash **57,6**, wobec **58,4** we IX. Dostępność tej liczby
nie potwierdza bezpłatnego strumienia wszystkich trzech głównych miar.
[ReleaseDates](https://www.pmi.spglobal.com/Public/Release/ReleaseDates)
zwraca **403** zarówno przez klient HTTP, jak i WWW; link do bieżącego
komunikatu z analizy również zwrócił 403. Nie zweryfikowano przyszłych
konkretnych dat/godzin Flash ani Final i nie wpisano kalendarzy innych firm
jako dowodu S&P. Godziny 09:45 ET nie oznaczono tu jako potwierdzonej.

[Oficjalna strona produktu](https://www.spglobal.com/marketintelligence/en/mi/products/pmi.html)
opisuje subskrypcję danych i zastrzeżenia reprodukcji. Nie znaleziono jasnej
bezpłatnej licencji na stałe przechowywanie i prezentowanie liczb w dashboardzie.
Manufacturing PMI, Manufacturing Output i Composite nie są zamiennikami.
Indeks PMI ma inną konstrukcję/skale niż regionalne diffusion indexes;
nie przenosimy między nimi progów ani kolorowania.

## 4. Cztery kryteria — osobne ustalenia i poziom pewności

W = wysoka pewność odczytanej treści/pojedynczej odpowiedzi; Ś = średnia;
N = niska/brak dowodu. Pewność nie oznacza SLA ani gwarancji prawnej.

| Publikacja | Kryterium | Stan i źródło | Pewność / brakujący dowód |
| --- | --- | --- | --- |
| Philadelphia | Harmonogram | [MBOS](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/manufacturing-business-outlook-survey): konkretne XI/XII, ET z raportu/FAQ | W dla 2026; brak listy wyjątków 2027 |
| Philadelphia | Actual | CSV GAC zgodny z raportem X | W dla sprawdzonego miesiąca; nie cały historyczny first print |
| Philadelphia | Świeżość | [FAQ](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/mbos-faqs): TXT najpierw, kolejne formaty później | Ś; brak liczbowego SLA i pomiaru w minucie publikacji |
| Philadelphia | Warunki | [Appropriate Use](https://www.philadelphiafed.org/about-us/privacy-notice): cele informacyjne, edukacyjne, badawcze; zastrzeżenia copyright | W co do tekstu; publiczne API/eksport nie mają tu wyraźnej licencji |
| Empire | Harmonogram | [Badanie](https://www.newyorkfed.org/survey/empire/empiresurvey_overview) + [ET calendar](https://www.newyorkfed.org/research/calendars/nationalecon_cal) | W dla XI/XII i zegara; brak 2027 |
| Empire | Actual | CSV GACDISA i raporty IX/X zgodne | W dla próby; konieczna walidacja kolejnych miesięcy |
| Empire | Świeżość | Wydawca: o 08:30 lub krótko po; dzisiejsze CSV działa | Ś; brak SLA CSV i obserwacji nowej publikacji |
| Empire | Warunki | [NY Fed Terms](https://www.newyorkfed.org/privacy/termsofuse) wprost obejmują download/store/distribute | W dla podstawy tekstowej; obowiązki muszą zostać wdrożone |
| FT900 | Harmonogram | [Census](https://www.census.gov/foreign-trade/schedule.html), [BEA](https://www.bea.gov/news/schedule/full) | W; Census do raportu za X 2027, dalej TBD |
| FT900 | Actual | Exhibit 1 XLSX, osobny komunikat BEA | W dla VIII; format i znak sprawdzone |
| FT900 | Świeżość | Raport ma godzinę 08:30, arkusz jest dostępny obecnie | Ś; brak dowodu równoczesnej aktualizacji XLSX/HTML |
| FT900 | Warunki | [BEA FAQ 147](https://www.bea.gov/help/faq/147): domena publiczna, o ile nie zaznaczono inaczej | W dla deklaracji BEA; trzeba zachować atrybucję i wyjątki |
| Productivity | Harmonogram | [BLS prod2](https://www.bls.gov/schedule/news_release/prod2.htm), kwartały i etapy | W przez WWW; klient 403 |
| Productivity | Actual | [BLS Q2 revised](https://www.bls.gov/news.release/prod2.nr0.htm) czytelny przez WWW | W dla raportu; lokalna automatyzacja niewykazana |
| Productivity | Świeżość | Godzina raportu znana, FRED nie zapewnia terminowego pośrednictwa | N dla automatycznego potwierdzenia nowego Actual przy 403 |
| Productivity | Warunki | [BLS copyright](https://www.bls.gov/opub/copyright-information.htm) dopuszcza użycie public-domain z atrybucją | W dla BLS; niezależne warunki FRED pozostają |
| Confidence | Harmonogram | [Komunikat TCB](https://www.conference-board.org/topics/consumer-confidence/): 24.11 10:00 ET | W dla tej zapowiedzi; N dla XII/2027 |
| Confidence | Actual | Publiczny HTML X ma trzy indeksy i zrewidowane Previous | W dla dzisiejszego HTML; N dla darmowego stabilnego API |
| Confidence | Świeżość | Deklarowana godzina publikacji, brak pomiaru aktualizacji strony | Ś/N; korekty i zmienny dokument |
| Confidence | Warunki | [TCB Terms](https://www.conference-board.org/contact/terms-of-use) ograniczają bazę/reprodukcję | W dla ograniczeń; brak uprawnienia dashboardu/API |
| S&P PMI | Harmonogram | ReleaseDates 403; FAQ podaje jedynie rytm | N dla konkretnych przyszłych dat i godzin |
| S&P PMI | Actual | Analiza X zawiera Composite; komunikat i dostęp maszynowy zablokowane | Ś dla pojedynczego faktu; N dla regularnego feedu |
| S&P PMI | Świeżość | Publikacje bezpłatne nie są SLA subskrypcyjnego strumienia | N dla bezpłatnej automatyzacji |
| S&P PMI | Warunki | [Produkt PMI](https://www.spglobal.com/marketintelligence/en/mi/products/pmi.html): subskrypcja, ograniczenia reprodukcji | W dla zastrzeżeń; brak licencji bezpłatnej integracji |

### Warunki dla prywatnej aplikacji, demo, API i eksportu

Poniższe oceny dotyczą odczytanych materiałów; nie są poradą ani gwarancją prawną.
Nie wysyłano zapytań do wydawców i nie uzyskano indywidualnych zgód.

| Wydawca / źródło | Prywatnie, lokalna baza | Publiczne demo | API / eksport |
| --- | --- | --- | --- |
| Philadelphia Fed | Cele informacyjne/badawcze wskazane; zakres trwałego gromadzenia konkretnego zbioru wymaga wyjaśnienia | Nierozstrzygnięte przy zastrzeżeniach treści chronionych | Brak wyraźnej licencji redystrybucyjnej w sprawdzonych materiałach |
| NY Fed | Warunkowa podstawa dla pobierania i przechowywania na użytek osobisty/biznesowy | Warunkowa podstawa dystrybucji, z oznaczeniami | Warunkowa podstawa także dla kopii/eksportu, z dalszymi warunkami użycia |
| Census/BEA FT900 | Bezpośrednie dane BEA objęte deklaracją public-domain, z wyjątkami | Taka sama podstawa dla własnych danych wydawcy | Taka sama podstawa, bez przenoszenia praw do cudzych materiałów/znaków |
| BLS | Public-domain publikacji z wyjątkami dotyczącymi ilustracji | Taka sama podstawa | Taka sama podstawa dla danych BLS |
| TCB | Wąski wyjątek jednej kopii do osobistego niekomercyjnego użycia; nie potwierdza stałego feedu do PostgreSQL | Wymaga ustalenia licencji | Baza, dystrybucja i dalsze użycie objęte ograniczeniami |
| S&P Global | Nie potwierdzono prawa do stałego gromadzenia wyników | Nierozstrzygnięte/zgoda | Nie potwierdzono prawa do redystrybucji |

NY Fed wymaga zachowania copyright/source identifiers, właściwej atrybucji,
oznaczania własnych modyfikacji, przekazywania warunków kolejnym odbiorcom
i braku sugerowania endorsement. Nie stosować bardziej restrykcyjnej licencji
do przekazywanej treści NY Fed. Trzeba sprawdzić wyłączenia dla treści osób
trzecich i szczególnych kategorii; Empire nie jest referencyjną stopą SOFR
ani Staff Report. Te obowiązki są warunkiem przyszłej integracji, nie wykonanym
elementem tego audytu. [Pełne Terms NY Fed](https://www.newyorkfed.org/privacy/termsofuse).

TCB wprost ogranicza m.in. wydobywanie do bazy, dystrybucję i tworzenie
pochodnych, z wąskimi wyjątkami oraz umowami subskrypcyjnymi. Publiczny komunikat
nie znosi tych warunków. [Terms TCB](https://www.conference-board.org/contact/terms-of-use).

Żadna z powyższych ocen nie rozstrzyga zgodności istniejącej bazy/RAW/cache
MacroLens z niezależnymi [warunkami FRED](https://fred.stlouisfed.org/legal/terms/).
Przyszłe bezpośrednie pobieranie od wydawcy ogranicza tę zależność dla nowej
serii, ale nie naprawia ani nie legalizuje pozostałych integracji projektu.

## 5. Terminy i konwersja czasu

Strefa ET oznacza `America/New_York`; PL to `Europe/Warsaw`, z IANA.
Nie używać stałego UTC−5 ani stałej różnicy sześciu godzin przez cały rok.

| Raport | Data | Okres / etap | Zegar wydawcy i podstawa | PL |
| --- | --- | --- | --- | --- |
| Philadelphia | 15.10.2026 | X, historyczny | 08:30 ET, własny raport X | 14:30 |
| Philadelphia | 19.11.2026 | XI | 08:30, lista MBOS + ET z FAQ | 14:30 |
| Philadelphia | 17.12.2026 | XII | Jak wyżej | 14:30 |
| Empire | 15.09 / 15.10.2026 | IX / X, historyczne | 08:30 ET, strona + kalendarz NY Fed | 14:30 |
| Empire | 16.11 / 15.12.2026 | XI / XII | Ta sama jawna lista i zegar badania | 14:30 |
| FT900 | 04.11.2026 | IX | 08:30 Eastern, Census | 14:30 |
| FT900 | 08.12.2026 | X | Jak wyżej | 14:30 |
| FT900 | 07.01.2027 | XI 2026 | Jak wyżej | 14:30 |
| Productivity | 05.11.2026 | Q3 preliminary | 08:30 ET, BLS prod2 | 14:30 |
| Productivity | 08.12.2026 | Q3 revised | Jak wyżej | 14:30 |
| Productivity | 04.02.2027 | Q4 preliminary | Jak wyżej | 14:30 |
| TCB Confidence | 24.11.2026 | Okres do osobnego potwierdzenia w raporcie | 10:00 ET, zapowiedź w komunikacie X | 16:00 |
| S&P Flash/Final | Przyszłe daty niepotwierdzone w audycie | Oddzielne etapy i miary | ReleaseDates/komunikat 403 | — |

Przykłady z potwierdzonych dat: FT900 **09.03.2027 08:30 NY = 14:30 PL**,
podobnie 06.04; Productivity 04.03.2027 również 14:30 PL. USA przechodzą
w 2027 na czas letni dopiero 14 marca. Syntetyczna kontrola rozbieżnego
tygodnia: 16.03.2027 08:30 NY = 13:30 PL; **nie jest to termin dodany do
harmonogramu**. To konwersje IANA, nie dowody istnienia wydarzenia.

## 6. Tabela porównawcza i kolejność

| Kolejność | Publikacja / wydawca | Istnieje w MacroLens? | Częstotliwość, najbliższy potwierdzony termin | Główna miara / Actual | Automatyzacja i koszt konkretnej pracy | Wersje i prawa | Wartość intraday |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | Empire / NY Fed | Nie | Miesięczna; 16.11, 15.12, 08:30 ET | GACDISA; CSV + własny PDF | Parser dat/kolumn CSV, metadane raportu, nowy adapter pod istniejący lock/cache/status; testy ND i końca miesiąca; bez płatnego API | Roczne rewizje; jasna warunkowa licencja przechowywania/dystrybucji | Wczesny regionalny sygnał bieżącego miesiąca; cen/pracy jako kontekst |
| **2** | FT900 / Census i BEA | Nie | Miesięczna; 04.11, 08.12, 07.01, 08:30 ET | Bilans total SA, mln USD; XLSX + HTML | Parser Exhibit 1, nagłówki rok/miesiąc, R, BOP basis; rozdzielenie advance/full; wspólny koordynator | Bieżące/roczne rewizje; bezpośrednia public-domain podstawa BEA | Twarde dane wzrostu/handlu, dłuższe opóźnienie niż survey; kontekst GDP |
| **3** | Philadelphia MBOS / Philadelphia Fed | Nie | Miesięczna; 19.11, 17.12, 08:30 ET | GAC SA; CSV + report/TXT | Parser tekstu dostępnego przed CSV, uzgodnienie kanałów, dowody dat i wersji; wyjaśnienie praw publicznego użycia | Sezonowe rewizje; zakres redystrybucji mniej jednoznaczny | Użyteczny regionalny przemysł, ceny i zatrudnienie; nie reprezentuje wszystkich usług |
| **4** | Productivity / BLS | Nie | Kwartalna, preliminary/revised; 05.11 i 08.12, 08:30 ET | Productivity i ULC SAAR | Transformacja i wersje, etap Q, tabela BLS; realna bariera HTTP 403 i niezależnego potwierdzania nowych wyników | Liczby BLS public-domain; FRED osobne warunki/current-vintage | ULC i wydajność jako kontekst presji kosztowej; częste rewizje |
| **5** | Consumer Confidence / TCB | Nie | Miesięczna; 24.11, 10:00 ET | Confidence + Present/Expectations; HTML | Parser zmiennego komunikatu możliwy, lecz brak potwierdzonej licencji feedu i darmowej historii | Rewizje Previous i korekty komunikatu; licencja do ustalenia | Konsument i postrzeganie pracy; inne pytania niż Michigan |
| **6** | Flash US PMI / S&P Global | Nie; ISM to inny raport | Miesięczna, Flash/Final; przyszłe daty bez potwierdzenia | Manufacturing/Services/Composite; publiczne wybrane liczby | Najpierw uprawnienia i dostęp do kalendarza/feedu; obecne 403; darmowy komunikat nie zapewnia całości | Flash → Final to etap tego samego miesiąca; restrykcyjna dystrybucja | Szeroki i wczesny sygnał biznesowy, potencjalnie bardzo przydatny, lecz obecnie słabo wykonalny |

Kolejność jest oceną wykonalności następnego etapu projektu, **nie rankingiem
siły reakcji indeksów giełdowych**. Nie wykonywano badania stóp zwrotu ES/NQ,
estymacji wpływu zaskoczeń ani pomiaru opóźnień wydawców.

| Publikacja | Wzrost | Inflacja | Praca | Możliwy kanał Fed / S&P 500 i Nasdaq | Proponowana ważność |
| --- | --- | --- | --- | --- | --- |
| Empire | Bieżąca aktywność/nowe zamówienia | Prices paid/received, odrębne od headline | Regionalny employment | Kombinacja wzrostu i cen może zmieniać ocenę polityki i rentowności | **★★**, umiarkowana pewność; regionalna próba, nie ogólnokrajowy NFP/ISM |
| Philadelphia | Przemysł regionalny i oczekiwania | Prices paid/received | Employment i workweek | Podobny kontekst, zwłaszcza zgodność/rozbieżność z innymi surveys | **★★**, umiarkowana |
| FT900 | Eksport/import i nominalny bilans | Nie jest samodzielną miarą inflacji | Pośrednio | Zmienia ocenę handlu i wzrostu, ale saldo nie jest wkładem realnego net exports | **★★**, umiarkowana |
| Productivity/ULC | Output na godzinę | Koszt jednostki outputu | Godziny i koszty, nie liczba nowych miejsc pracy | Może zmieniać ocenę kosztów/inflacji bez prostego przełożenia na decyzję Fed | **★★**, umiarkowana |
| TCB Confidence | Skłonność/oczekiwania konsumenta | Oczekiwania cenowe są osobną miarą | Subiektywne postrzeganie dostępności pracy | Kontekst popytu, nie automatyczna zapowiedź sprzedaży lub Fed | **★★**, umiarkowana |
| S&P Flash | Manufacturing + duży obszar usług | Koszty/ceny | Zatrudnienie w badaniu | Wczesny szeroki sygnał aktywności i cen | **★★★ Flash**, **★★ Final**; umiarkowana/niższa pewność bez badania reakcji |

To propozycje redakcyjne, nie oceny dostawców. Nie zapisano ich do konfiguracji.
W każdym przypadku znaczenie zaskoczenia zależy od konsensusu i otoczenia.
MacroLens **nie ma konsensusu**; Forecast i porównanie Actual−Forecast muszą
pozostać puste. Różnica wobec Previous nie może udawać zaskoczenia wobec rynku.
Wyższy indeks nie oznacza mechanicznie wzrostu Nasdaq: reakcja może zależeć
od równoczesnej zmiany rentowności, cen i oczekiwań co do Fed.

## 7. Zalecany następny zakres — bez implementacji

Wybrać **Empire State: kalendarz + Actual**, początkowo tylko General Business
Conditions SA. Techniczna próba jest pozytywna, więc nie ma powodu powtarzać
wariantu samych dat i pustych wyników z ADP/Michigan. Nie gwarantuje to wyniku
w sekundę publikacji: integracja ma jawnie obsługiwać brak/stary dokument
i niedostępny jeszcze CSV.

W przyszłym osobno zleconym etapie należy wykorzystać istniejący koordynator,
advisory lock, budżet żądań, cooldown, atomowe publikacje, statusy i tabele
wersji. Nowy bezpośredni adapter i binding są potrzebne: obecne ogólne miary
FRED i specjalna obsługa ISM nie oznaczają, że wystarczy dopisać ID do YAML.
Nie tworzyć równoległej usługi ani oznaczać danych NY Fed jako `fred_snapshot`.

Warunki odbioru przyszłego wdrożenia: zgodność miesiąca raportu i CSV,
odróżnienie GACDISA/GAFDISA/NSA, Previous właściwego miesiąca, brak Future
jako zamiennika Current, zachowanie ND/zera/ujemnych indeksów, rzeczywisty
URL/czas/hash/własna wersja i dokument, idempotencja, odrzucenie starszego
pliku, jawne current-vintage historii oraz obowiązki atrybucji/dalszych warunków.
Współczesny plik pełnej historii nie tworzy historycznych first printów.
Zapisywanie prospective wersji dopiero od wdrożenia jest odrębną decyzją;
nie wykonano go tutaj.

W porównaniu z Philadelphia decyduje jaśniejszy tekst praw i prosty CSV
bez konieczności opierania pierwszej fazy na TXT publikowanym przed innymi
formatami. FT900 ma mocną podstawę i dłuższy harmonogram, lecz wymaga
większej kontroli jednostek/baz/etapów oraz opisuje starszy miesiąc.
Productivity ma dodatkową barierę 403; prywatni wydawcy mają nierozstrzygnięte
uprawnienia do liczb. Wniosek może się zmienić po sprawdzeniu rzeczywistej
latencji lub zmianie warunków wydawców.

## 8. Nierozstrzygnięte kwestie i granice kontroli

1. Brak pomiaru dostępu CSV/TXT/XLSX w chwili kolejnej publikacji. Udane
   pobranie historycznego pliku nie jest gwarancją intraday.
2. Brak potwierdzonych list 2027 Empire/Philadelphia w sprawdzonych źródłach.
   Philadelphia podaje zwykły termin udostępnienia rocznika, nie daty zastępcze.
3. Nie potwierdzono XII/2027 TCB ani przyszłych konkretnych dat/godzin S&P.
   Nie użyto agregatorów jako oficjalnego dowodu i nie obchodzono 403.
4. NYC CSV i Philly CSV w próbie nie zwróciły `Last-Modified` ani `ETag`;
   przyszły importer musi bazować na treści/miesiącu/hashu, nie wyłącznie nagłówkach.
5. Nie odtworzono kompletnej historii wersji. Roczne rewizje oraz zmienne
   dokumenty wymagają oddzielenia bieżącej historii od wyników znanych wtedy.
6. Nie uzyskano indywidualnych uprawnień Philadelphia, TCB ani S&P;
   NY Fed ma wyraźną warunkową podstawę, ale wymagania prezentacji/eksportu
   pozostają pracą do wykonania. Nie deklarujemy publicznej gotowości MacroLens.
7. BLS pozostaje zablokowany dla sprawdzonego bezpośredniego klienta.
   Dostęp narzędzia WWW nie jest działającym importerem produkcyjnym.
8. Nie badano stabilności endpointów przez wiele dni ani kosztu hostingu;
   estymacja złożoności opisuje zakres prac, nie obietnicę czasu realizacji.
9. Bez konsensusu nie ma miary surprise. Nie prowadzono badania reakcji rynku.

Kontrola techniczna obejmowała po jednym oficjalnym CSV SA/NSA Empire,
jeden CSV Philly i jeden arkusz FT900 oraz ograniczone strony raportów,
harmonogramów i warunków. Nie pobierano masowo raportów historycznych ani
zestawów subskrypcyjnych. Jeden helper parsowania HTML nie miał biblioteki
`bs4`; zastąpiono go standardowym `html.parser`, bez instalacji pakietów.
Odpowiedzi pozostały w pamięci. Diagnostykę XLSX wykonano ok.
**2026-10-29T09:49:27 UTC**, bez deklaracji, że był to czas publikacji danych.

Nie uruchamiano pełnych testów ani buildu, ponieważ jedyną zmianą jest
dokument audytu. Ich wyniki z poprzedniego zamknięcia pozostają historyczne;
nie przypisuje się temu audytowi nowych 883/556 testów lub nowego CI.

## 9. Końcowy Git

`main` / `0147d6e1fc64d3c5e317f724e8f264fb119760b8`, bez zmiany HEAD.
Po zapisaniu raportu oczekiwany i kontrolowany zakres:

```text
 M README.md
 M frontend/src/brief/SourceCheckStatus.test.tsx
 M frontend/src/brief/SourceCheckStatus.tsx
 M frontend/src/styles.css
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
```

Cztery wcześniejsze pliki zachowane byte-identycznie. Brak stagingu,
commita i pusha; brak pozostałych nowych plików. Nie rozpoczęto wdrożenia.
