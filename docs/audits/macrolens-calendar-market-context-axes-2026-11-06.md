# MacroLens — osie wykresów i kontekst gospodarki / USD

06.11.2026, Europe/Warsaw, `C:\Projects\macrolens`.

Zmianę wprowadzono bezpośrednio do lokalnego frontendu na
http://127.0.0.1:5173/#/calendar. Bez zapisu SQL, importu, zmiany autoryzacji,
stagingu, commita lub pusha.

## Wykresy

Istniejące wykresy mają oś wartości z jednostkami, delikatną siatkę i daty
okresów referencyjnych. Skala jest jawnie opisana jako dopasowana do danych;
nie wymusza zera dla wskaźników poziomu. Obsługuje wartości ujemne i stałe.
Daty zachowują rzeczywiste odstępy; brakujący okres nadal przerywa linię.
ResizeObserver dopasowuje współrzędne do rzeczywistej szerokości, zachowując
11-pikselowe podpisy na telefonie. Lista wartości dla czytnika pozostaje.

Nie rozszerzono źródeł historii ani reguł jej porównywalności. Brak odczytu
lub zgodnej historii nie powoduje utworzenia wykresu. Pięć istniejących
wykresów opublikowanych miar nadal korzysta z rzeczywistych 12 punktów:
JOLTS, ISM przemysł/usługi oraz nowe/kontynuowane wnioski o zasiłek.

## Objaśnienia

Przejrzany rejestr obejmuje wszystkie **45 kombinacji seria/transformacja**
znalezionych w rzeczywistym kalendarzu 01.11.2026–01.02.2027. Sprawdza też
częstotliwość i jednostkę; nie dopasowuje po fragmentach nazwy. Oddzielne
objaśnienia dotyczą ADP, wstępnego/końcowego Michigan, protokołu, konferencji
i projekcji Fed. Nieznana przyszła miara pozostaje bez kierunkowego sygnału.

Karta rozdziela gospodarkę od warunkowego mechanizmu USD/Fed. Kierunek
obserwowanej zmiany wykorzystuje istniejące calendarComparison i jego bramki.
Przy null, zerze, niezgodnych okresach, źródłach lub niepotwierdzonym mapowaniu
tekst jest instrukcją czytania, a nie deklaracją aktualnego sygnału.

Uwzględniono m.in. kurczenie PMI poniżej 50 mimo poprawy, próg zero dla
Empire State, CFNAI względem trendu, wzrost NFCI jako zacieśnienie, inflację
jako presję cenową zamiast dowodu zdrowia gospodarki, strukturę płac,
uczestnictwo w rynku pracy, nominalne/realne wydatki, SAAR budownictwa,
oszczędności, składniki salda handlowego i różnicę stopy efektywnej od decyzji
Fed. Dla niejednoznacznych kanałów nie przypisano prostego kierunku USD.

Teksty są opracowanym objaśnieniem mechanizmu, nie prognozą kursu lub
stwierdzeniem zaobserwowanej reakcji. Zmiana względem Previous nie dowodzi
zaskoczenia względem konsensusu. Znaczenie mają względne oczekiwania stóp,
pozostałe publikacje i nastroje wobec ryzyka.

Podstawy sprawdzone w źródłach pierwotnych:
[transmisja polityki Fed](https://www.federalreserve.gov/monetarypolicy/monetary-policy-what-are-its-goals-how-does-it-work.htm),
[oczekiwania stóp i USD](https://www.federalreserve.gov/econres/notes/ifdp-notes/the-sensitivity-of-the-us-dollar-exchange-rate-to-changes-in-monetary-policy-expectations-20170922.htm),
[reakcje na zaskoczenia makro](https://www.federalreserve.gov/econres/ifdp/the-high-frequency-response-of-exchange-rates-and-interest-rates-to-macroeconomic-announcements.htm),
[PPI](https://www.bls.gov/ppi/faqs/questions-and-answers.htm),
[stała struktura ECI](https://www.bls.gov/eci/factsheets/relative-importance-factsheet.htm),
[oszczędności BEA](https://www.bea.gov/data/income-saving/personal-saving-rate),
[CFNAI](https://www.chicagofed.org/research/data/cfnai/current-data),
[NFCI](https://www.chicagofed.org/research/data/nfci/current-data),
[Empire State](https://www.newyorkfed.org/survey/empire/empiresurvey_overview.html),
[produkcja przemysłowa](https://www.federalreserve.gov/releases/g17/about.htm),
[budownictwo i SAAR](https://www.census.gov/construction/soc/methodology.html).
Karty zawierają linki metodologiczne oraz wyjaśnienie mechanizmu Fed/USD.

## Walidacja i ochrona

- Pełny frontend: **933 passed / 43 pliki**, 65,29 s; 75 nowych przypadków.
- TypeScript noEmit: passed. Production build: passed, 3,50 s;
  największy chunk 407,04 kB.
- Chrome na rzeczywistym Vite/API/SQL: **5796 kontroli / 92 GET HTTP 200**,
  PL/EN, 1366/390 px, wszystkie 45 miar w Wszystko i Dane. Osie, jednostki,
  daty i teksty, brak overflow strony; obejrzano desktop EN i mobile PL.
  Zero błędów JS/console.error i żądań przeglądarki do wydawców.
  Przeszły też klawiatura/focus, zwijanie technicznych szczegółów,
  rzeczywisty polling po ponad 60 s, wartości Earnings i zachowane prognozy.
  To nie jest pełny audyt WCAG.
- Niezależny read-only SQL: wszystkie 16 pełnych tabel Earnings/F1,
  katalogi i referencje identyczne przed/po. Pełne 34 obiekty Earnings
  identyczne, w tym Current/Previous i Market Cap.
- F1 V2 activated=true/cooldown; wszystkie **155 artefaktów zgodne**.
  Monitor Earnings activated=true, loop_running=true/completed.
- Wartości, okresy i metody miar makro są identyczne. Zwykły worker makro
  odświeżył część provenance: czasy kontroli/pobrania i ścieżki/hashe
  dokumentów kalendarza. Nie deklaruje się niezmienności całego makro.

Pierwsze próby ujawniły błędną datę miesięczną w syntetycznym teście NFCI
oraz kolizję nazw modułów w resolverze Vite na Windows. Poprawiono datę
tygodniową i nadano komponentowi osobną nazwę. Helper Chrome rozszerzono
na pełny zakres z ECI, jawne wyłączenie filtrów i kontrolę pól technicznych
zamiast zakazu oficjalnych skrótów wskaźników. Po zatrzymaniu własnego
okna Chrome wykonano nowy przebieg headless z diagnostyką CDP. Nieudanych
prób nie zaliczono; nie podstawiano odpowiedzi API ani nie osłabiano
porównywalności danych.

Zmieniono cztery zastane pliki: MacroEventCard.tsx, MacroTrend.tsx,
macroTrendData.ts i macroEventCard.css. Dodano MacroEconomicContext.tsx,
macroMarketProfiles.ts, macroMarketProfiles.test.ts oraz ten raport.
Wszystkie wymienione źródła są w frontend/src/calendar.
**480 z 484 zastanych plików zachowano byte-identycznie**, w tym chronione
prace użytkownika i F2. Cztery konieczne zmiany zachowują wcześniejszy kod.
Backend, konfiguracja, globalny CSS, zależności, lockfile i CI bez zmian.
Manifesty, logi, odczyty i zrzuty są ignorowane w
data/raw/calendar-market-context-axes-2026-11-06.

Bez migracji, importu, zmiany Forecast, monitora lub kapitalizacji.
Normalne PostgreSQL, API 8000 i Vite 5173 pozostają uruchomione.
Własny Chrome zakończono po sprawdzeniu PID/argumentów profilu i portu 9327.
Końcowo **20 modified / 65 untracked plików**, indeks pusty,
main/HEAD c42cf6c411c85a64927fe5c6b3cf98f9e906c871 bez zmian.

## Późniejsza korekta układu i skrócenie opisów — 06.11.2026

Na kolejne zlecenie wykres przeniesiono na prawo od opisu przy szerokości
od 1000 px. Na telefonie pozostaje pod tekstem. Siatka dwóch kolumn powstaje
tylko przy rzeczywiście dostępnym wykresie; brak historii nie zostawia pustej
kolumny. Osie, jednostki, daty i dane wykresu zachowano.

Nagłówek zmieniono na „Jak to interpretować?” / „How to interpret it?”.
Usunięto widoczne ogólne zastrzeżenie, blok „Podstawy” z trzema linkami
i opis wersji historii nad wykresem. Pozostały zwykłe źródła oraz zwijane
szczegóły techniczne. Opisy USD skrócono do kierunku i przyczyny przez stopy
Fed, z krótkim odniesieniem do oczekiwań w samym zdaniu. JOLTS otrzymał
konkretny opis popytu na pracę i płac bez powtarzania definicji wakatów.
Niejednoznaczne miary mają własny opis kanału, zamiast ogólnego „wpływ mieszany”.

Końcowe sprawdzenie: **933 testy / 43 pliki, 67,41 s**, TypeScript i build
passed (4,45 s). Rzeczywisty Chrome/API: **1910 kontroli / 87 GET 200**,
PL/EN, 1366/390 px. Przeszły położenie wykresu, osie, krótsze teksty,
klawiatura, sześć kolumn Wszystko, osiem Dane, siedem Wyniki, wartości,
prognozy i brak overflow. Bez błędów JS/console.error i żądań przeglądarki
do wydawców. Obejrzano desktop PL i mobile PL oraz desktop EN.

Zmieniono siedem istniejących plików frontendowych: MacroEventCard.tsx,
MacroEventCard.test.tsx, MacroEconomicContext.tsx, MacroTrend.tsx,
macroEventCard.css, macroMarketProfiles.ts i macroMarketProfiles.test.ts,
oraz dopisano tę sekcję raportu. Manifest wejściowy i logi są w ignorowanym
data/raw/calendar-card-layout-2026-11-06. Pozostałe **480 z 488 zastanych
plików** zachowano byte-identycznie, w tym prace chronione i F2.
Wszystkie 155 artefaktów F1 zgodne; status F1 cooldown/activated,
monitor Earnings completed/activated. Nie wykonywano SQL, importu,
migracji lub zmian policy. Normalne API/Vite pozostają uruchomione.
Własny Chrome 9331 zakończono po kontroli PID i profilu.
Git nadal **20 modified / 65 untracked**, indeks pusty, bez commita/pusha.

## Skrócenie rozwinięcia źródeł — 06.11.2026

Na kolejne zlecenie usunięto z rozwinięcia blok pojedynczej miary
agenda-measure-detail: dostępność, generacje, wersje, obliczenia i powtórzone
odczyty. JOLTS zachowuje wskazaną nazwę i opis publikacji, dzień/godzinę,
oba źródła oraz listę statusów sprawdzenia. Karta, interpretacja, wykres
i wartości tabeli bez zmian. Szczególne informacje o samych publikacjach
i atrybucje pozostałych wydawców zachowano.

Zmieniono CalendarPage.tsx oraz odpowiednie asercje CalendarPage.test.tsx
i CalendarRefresh.test.tsx. Nowe dwa przypadki PL/EN sprawdzają dokładny
zakres krótkiego podsumowania. Pełny frontend: **935 passed / 43 pliki**,
62,86 s. TypeScript/build passed (5,62 s). Rzeczywisty Chrome: **1102 kontrole /
55 GET 200**, PL/EN desktop/mobile, bez błędów JS i overflow; obejrzano
rozwinięty JOLTS w PL. Logi i manifest w ignorowanym
data/raw/calendar-source-summary-2026-11-06. **484/488 zastanych plików**
byte-identyczne po doliczeniu tej aktualizacji raportu. Wszystkie 155
artefaktów F1 bez zmian. Bez SQL, backendu, importu, stagingu lub pusha;
normalne API/Vite działają. Własny Chrome 9333 zamknięty po kontroli PID/profilu.
Git: **20 modified / 65 untracked**, indeks pusty.

## Ujednolicenie kolorów Dane / Wyniki — 06.11.2026

Na kolejne zlecenie Dane używają kierunku liczbowego w porównaniach Previous
i konsensusu: dodatnia różnica zielona, ujemna czerwona, zero/brak neutralne.
Legenda jest zgodna z Wszystko. Wyniki zachowują siedem kolumn: kolor
aktualnego EPS i Revenue pokazuje kierunek względem porównywalnego Previous,
oddzielnie dla metryk. Natywny tooltip podaje dokładną różnicę. Previous,
prognozy i Market Cap zachowują wcześniejszy styl. Wykorzystano istniejące
earningsChange z dokładną arytmetyką i bramkami porównywalności; bez zmiany
wartości lub backendu. Wszystko pozostaje bez zmiany prezentacji.

Pełny frontend: **937 passed / 43 pliki**, 82,73 s; TypeScript i build
passed (5,66 s). Chrome na rzeczywistym API: **1294 kontrole / 56 GET 200**,
PL/EN, 1366/390 px, rzeczywiste computed colors, bez błędów JS, overflow
strony lub żądań przeglądarki do wydawców. Obejrzano desktop Wyniki.
Nowe testy sprawdzają niezależne kierunki EPS/Revenue, zero i brak Previous.

Zmieniono CalendarPage.tsx, EarningsCalendar.tsx, earnings.css,
unifiedCalendar.css oraz CalendarPage.test.tsx i EarningsFinancials.test.tsx;
dopisano tę sekcję raportu. **481/488 zastanych plików** byte-identyczne.
Wszystkie 155 artefaktów F1 bez zmian. Logi i manifest są w ignorowanym
data/raw/calendar-domain-colors-2026-11-06. Bez SQL, importu, stagingu,
commita i pusha. Normalne API/Vite działają; własny Chrome 9335 zamknięty
po kontroli PID/profilu. Git: **21 modified / 65 untracked**, indeks pusty.
