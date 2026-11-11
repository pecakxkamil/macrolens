# MacroLens — czytelne karty wydarzeń makro

06.11.2026, Europe/Warsaw, `C:\Projects\macrolens`, main.

**Wdrożono bezpośrednio do działającego frontendu** pod
http://127.0.0.1:5173/#/calendar. Wszystko i Dane korzystają z tego samego
komponentu karty. Nie zmieniono backendu, bazy, F1/F2, monitora ani tabeli Wyniki.
Bez stagingu, commita lub pusha.

## Panel po kliknięciu

Nagłówek zawiera nazwę klikniętej miary, USA, okres referencyjny i osobno
datę/godzinę publikacji w Polsce. Pokazuje też MoM/YoY lub annualizację
i znaną podstawę SA/NSA. Nie wyprowadza rodziny z fragmentu nazwy.

Przy dostępnym Actual trzy kompaktowe pola pokazują Aktualny / Zmianę /
Poprzednio. Wartości i porównywalność pochodzą z tych samych
calendarReadingValue i calendarComparison co w tabeli. Aktualny/Poprzednio
są białe; delta dodatnia zielona, ujemna czerwona, zero i brak porównania
neutralne. To kierunek liczbowy, nie ocena ekonomiczna.

Dalej są krótka definicja i deterministyczna interpretacja rzeczywistego
odczytu, opcjonalny mały wykres oraz źródło. Nie używa się AI API,
prognozy zamiast Actual, wymyślonej przyczyny zmiany lub prognozy giełdy.
Nieporównywalne Previous daje neutralny komunikat. GDP uwzględnia różnicę
między poprzednim kwartałem a poprzednim szacunkiem tego samego kwartału.

JOLTS z normalnego API: **7523 / 7190 tys., delta +333 tys.**; widok PL
pokazuje **7,52 mln / +333 tys. / 7,19 mln**. Panel odróżnia wakaty od
zmiany zatrudnienia. ISM Manufacturing pokazuje 55,5 pkt, Services 54,5 pkt
i właściwy kontekst granicy 50 pkt. Każdy wiersz wielomiarowej publikacji
zachowuje własne series_id/metrykę/okres, także CPI MoM/YoY i core.

Oczekujące wydarzenie pokazuje „Oczekiwanie na publikację”, bez dużego
pustego bloku KPI. ADP/Michigan nie otrzymują wymyślonych liczb. Gdy dokument
jest potwierdzony, karta mówi „Dane dostępne w raporcie źródłowym” i linkuje
raport. Jeśli dokument nie jest potwierdzony, informuje tylko o braku
integracji liczbowej i kieruje do raportów wydawcy. Wydarzenia nieliczbowe
nie są prezentowane jako odczyty.

Przy głównej wartości widoczne pozostają ograniczenia jakości: niepotwierdzony
okres/mapowanie, konflikt źródeł lub harmonogramu, mieszane źródła Actual/
Previous oraz możliwość późniejszych rewizji. Nie przeniesiono ich wyłącznie
do technicznego rozwinięcia.

## Słownik i interpretacje

Słownik obejmuje **17 odmian**: JOLTS, NFP, stopę bezrobocia, CPI i Core CPI,
PCE i Core PCE, oba ISM PMI, Initial/Continuing Claims, realny GDP annualizowany,
trzy zakresy Retail Sales (całość, ex autos, control), ADP i decyzję FOMC.
Rozpoznanie sprawdza stabilne identyfikatory, metrykę, częstotliwość i jednostkę.
Nieznana lub niezgodna miara nie otrzymuje zgadywanego opisu.

Liczbowe odmiany mają szablony interpretacji; ADP pozostaje opisem raportu
bez zintegrowanego odczytu. Szablony obsługują wzrost, spadek, zero, wartości
ujemne, poprawne okresy i jednostki oraz próg ISM. Nie oceniają, czy zmiana
jest dobra lub zła. Nieznane porównywalne miary mogą korzystać z istniejącego
neutralnego opisu zmiany, bez nowej interpretacji ekonomicznej.

Definicje zweryfikowano w źródłach pierwotnych:
[BLS JOLTS](https://www.bls.gov/jlt/jltfaq.htm),
[BLS CES](https://www.bls.gov/ces/),
[BLS CPS](https://www.bls.gov/cps/definitions.htm),
[BLS CPI](https://www.bls.gov/cpi/questions-and-answers.htm),
[BEA core PCE](https://www.bea.gov/data/personal-consumption-expenditures-price-index-excluding-food-and-energy),
[BEA GDP](https://www.bea.gov/data/gdp/gross-domestic-product),
[ISM metodologia](https://www.ismworld.org/globalassets/pub/research-and-surveys/rob/pmi/f3dz202604pmi.pdf),
[DOL Claims](https://oui.doleta.gov/unemploy/claims.asp/wkclaims/report.asp),
[Census Retail](https://www.census.gov/retail/marts/www/timeseries.html),
[ADP](https://adpemploymentreport.com/) i
[Fed](https://www.federalreserve.gov/economy-at-a-glance-policy-rate.htm).
Nie importowano nowych wartości z tych stron.

## Prawdziwa historia i jej granice

Obecne API ma read-only GET historii serii i cech. Nie było potrzebne
nowe API, DDL ani zmiana chronionego backendu. Wykres pobiera dane wyłącznie
dla otwartej miary, korzystając z istniejących fetchSeriesHistory/
fetchFeatureHistory. Zamknięcie/zmiana wyboru anuluje stare żądanie;
spóźniona odpowiedź nie może zostać pokazana przy innym okresie. Zmiana
Actual/vintage podczas pollingu odświeża wykres; identyczny odczyt nie
powtarza pobrania tylko dlatego, że powstał nowy obiekt odpowiedzi.

Audyt normalnego API w zakresie **01.11–31.12.2026** objął **116 wydarzeń /
275 miar**, z których osiem ma potwierdzone Actual. **4 wydarzenia / 5 miar**
mogą teraz pokazać prawdziwy wykres po 12 punktów:

| Publikacja | Miara | Punkty |
|---|---|---:|
| 02.11, ISM Manufacturing | ISM_MANUFACTURING_PMI / raw | 12 |
| 03.11, JOLTS | JTSJOL / raw | 12 |
| 04.11, ISM Services | ISM_SERVICES_PMI / raw | 12 |
| 05.11, Weekly Claims | ICSA / raw | 12 |
| 05.11, Weekly Claims | CCSA / raw | 12 |

Liczby oznaczają rzeczywiste dane API, nie fixture testowe i nie pokrycie
wszystkich możliwych dat. Komponent ma także ścisłe mapowania dla NFP,
bezrobocia, CPI/Core, PCE/Core i GDP, ale nie deklaruje rzeczywistego wykresu
ich przyszłych niepotwierdzonych odczytów.

Wykres wymaga potwierdzonego Actual i okresu oraz co najmniej trzech różnych
poprawnych punktów. Dla oczekujących 267 miar tej odpowiedzi jest celowo
pomijany. Dla trzech opublikowanych miar DGORDER/mom, NFCI/raw i
CENSUS_FT900_TOTAL/raw nie dodano przejrzanego mapowania historii; nie
przeskalowano innej serii i nie rozbudowano backendu, aby wymusić wykres.
To ograniczenie tej wersji adaptera, nie twierdzenie o nieistnieniu ich
historii u źródła.

Walidacja wiąże series_id, raw/feature_name, wersję metodologii v1,
częstotliwość, jednostkę wejściową i właściwą jednostkę miary. Nie liczy
nowych transformacji w React. Nie miesza SA/NSA, poziomów z dynamiką ani
current-vintage z first print. Historia current-vintage jest tak podpisana
i może zawierać rewizje. Nie dokleja się do niej punktu z innej wersji Actual.
ISM jest dodatkowo ograniczone do jednego raw_hash dokumentu potwierdzającego
wybrany odczyt; starsze dokumenty nie uzupełniają luk tego raportu.

Maksymalnie 12 punktów jest sortowane według okresu; luki nie dostają
sztucznych obserwacji ani łączącego odcinka. Skala obsługuje liczby ujemne.
Każdy punkt ma okres i wartość z jednostką w title, a pełna lista tekstowa
jest dostępna dla czytnika ekranu. Zbyt mało punktów, niezgodne metadane,
sprzeczne duplikaty lub błąd GET oznaczają brak sekcji, bez pustego wykresu.

## Źródła i interakcje

Cały dotychczasowy markup EventDetails zachowano w pojedynczym natywnym
details „Źródła, rewizje i szczegóły techniczne”, domyślnie zamkniętym.
Porównanie z pełną kopią sprzed zmiany potwierdziło brak usunięć starej
treści po odwróceniu samego wrappera. Zachowano linki, rewizje, dane dostawcy,
identyfikatory, okresy, dowody i informacje aktualizacji — bez nowego JSON UI.

Ten sam komponent działa w Wszystko i Dane, z colSpan odpowiednio 6/8.
Nie jest modalem. Enter/Space otwierają, Escape zamyka i oddaje focus,
aria-expanded/aria-controls pozostają poprawne. Polling nie zamyka panelu,
nie powiela go i nie resetuje domeny; zmiana zakresu zamyka wybór.
Kliknięcie Earnings nadal przełącza do niezmienionej tabeli Wyniki.

## Wyniki końcowe

| Kontrola | Wynik |
|---|---|
| Pełny frontend Vitest | **858 passed / 42 pliki**, 58,16 s |
| Nowe przypadki tej funkcji | **34 passed** w powyższym zestawie |
| TypeScript noEmit | passed |
| Production build | passed, 4,03 s, największy chunk 407,04 kB |
| Backend odczytu API/historii/kalendarza/ISM/Fed | **142 passed**, 7,47 s |
| Normalny Chrome PL/EN, 1366/390 px | **1752 kontrole / 73 API GET HTTP 200** |
| Normalne pełne 16 tabel Earnings/F1 i katalogi/referencje | identyczne przed/po |
| Wszystkie 34 datowane obiekty API Earnings | identyczne przed/po |
| F1 V2 | **155 artefaktów zgodne**, activated=true/cooldown |

Chrome używał prawdziwego Vite 5173, API 8000 i normalnego SQL, bez fixture.
Sprawdził JOLTS, NFP, bezrobocie, CPI MoM/YoY, Core CPI, PCE/Core PCE, oba
ISM, obie miary Claims, GDP i ADP. Obejmował rzeczywiste źródła i punkty,
porównanie KPI z wierszem, złożone publikacje, brak Actual, dokument bez
liczb, jawne rozwinięcie dowodów, Enter/Space/Escape/focus, polling ponad
60 sekund, zmianę domeny i daty oraz brak podwójnego panelu. Zachowane
sześć/osiem/siedem kolumn, Earnings/Previous, 14 nowcastów, guidance NVIDIA,
Market Cap i wcześniejsze kolory. Brak JS/console.error, HTTP 503 i żądań
przeglądarki do wydawców. Obejrzano desktop EN/PL i mobile PL, także
powiększony zrzut liczb. Bez overflow strony. Nie jest to pełny audyt WCAG.

Pierwsze próby nie były zaliczone: Windows ujawnił konflikt nazw MacroTrend
i macroTrend, więc czysty moduł otrzymał nazwę macroTrendData. Doprecyzowano
asercje NBSP/źródłowego tekstu i dodatkowego read-only GET historii.
Helper Chrome wymagał pełnego zdarzenia klawiatury, checkVisibility dla
natywnie zamkniętego details, boolean zamiast obiektu DOM w protokole oraz
jawnego UTF-8 w oczekiwaniu PL. Poprawiono narzędzia bez osłabiania asercji
i powtórzono pełny końcowy przebieg. Nie podmieniano odpowiedzi API.

## Pliki, ochrona i zakończenie

Zmieniono tylko dwa zastane pliki:

- frontend/src/calendar/CalendarPage.tsx — import i wrapper wspólnej karty;
- frontend/src/calendar/CalendarPage.test.tsx — kontrola dodatkowego GET historii zamiast dawnego limitu jednego zapytania.

Nowe pliki:

- frontend/src/calendar/macroInsightFamilies.ts;
- frontend/src/calendar/macroInsight.ts;
- frontend/src/calendar/macroTrendData.ts;
- frontend/src/calendar/MacroTrend.tsx;
- frontend/src/calendar/MacroEventCard.tsx;
- frontend/src/calendar/macroEventCard.css;
- frontend/src/calendar/macroInsights.test.ts;
- frontend/src/calendar/MacroEventCard.test.tsx;
- docs/audits/macrolens-calendar-event-insights-2026-11-06.md.

Zapisano manifest 475 plików, pełny diff i kopię CalendarPage. **473 zastane
pliki pozostały byte-identyczne**. W dwóch koniecznych edycjach zachowano
wcześniejsze hunki i chronione prace. Nie zmieniono backendu/config, F2,
globalnego CSS, zależności, lockfile lub CI. Diagnostyka SQL była read-only.
F1/monitor i normalne PostgreSQL/API/Vite pozostają aktywne. Cache Market Cap
zachował SHA 94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799.
Nie blokowano zwykłej pracy makro ani nie deklaruje się niezmienności jego
autonomicznych zapisów. Nie wykonano DDL, importu, APPLY lub rewizji policy.

Własny Chrome/CDP 9323 zakończono po kontroli PID/argumentów. Nie tworzono
kontenerów ani klonów bazy. Logi, audyt historii, snapshoty, zrzuty i manifesty
są ignorowane w data/raw/calendar-event-insights-2026-11-06. Końcowo
**20 modified / 61 untracked**, indeks pusty, main/HEAD
c42cf6c411c85a64927fe5c6b3cf98f9e906c871 bez zmian. Bez stagingu,
commita, pusha, reset, clean, amend, force lub globalnego formatowania.
