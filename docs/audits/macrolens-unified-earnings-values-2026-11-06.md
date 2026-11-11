# MacroLens — prawdziwe wartości Earnings w kalendarzu Wszystko

06.11.2026, Europe/Warsaw, `C:\Projects\macrolens`.

**Wdrożono bezpośrednio w lokalnym frontendzie** pod
http://127.0.0.1:5173/#/calendar. Wszystko nadal ma jedną tabelę i sześć
kolumn. Zmieniono wyłącznie prezentację istniejących danych Earnings.
Bez DDL, importu, APPLY, zmiany autoryzacji, stagingu, commita lub pusha.

## Przyczyna i zmiana

CalendarPage pobiera Earnings przez useEarningsCalendar; unifiedCalendar
przekazuje ten sam obiekt API do wspólnej chronologii. Szczegółowy
EarningsCalendar otrzymuje tę samą instancję stanu. Problemem były trzy
wpisane na stałe kreski w UnifiedEarningsRow, a nie brak danych w bazie.

Aktualny i Poprzednio mają teraz dwie zwarte linie: EPS oraz Przych. / Rev.
W kolumnie vs poprzedni są różnice obu metryk. Nie przywrócono prognoz
lub porównań z konsensusem, nie dodano kolumn, paneli ani drugiej tabeli.
Różnice są neutralnymi zmianami kwartalnymi, bez beat/miss lub oceny spółki.

Wspólny selektor earningsActual zachowuje dotychczasowe reguły szczegółowej
tabeli: jawny null nie uruchamia fallbacku; starsze pola obsługiwane są tylko
przy braku nowego pola. EarningsCalendar korzysta z tego selektora, bez zmiany
układu i wynikowego zachowania. Oba widoki używają istniejącego financialValue;
jego dotychczasowe funkcje formatowania pozostały bez zmian.

Odejmowanie odbywa się na dziesiętnych stringach API przez BigInt i wspólną
skalę, przed formatowaniem. Unika odejmowania zaokrąglonych tekstów i błędów
zmiennoprzecinkowych. Dopiero wynik trafia do istniejącego formattera waluty
i jednostki. Kontrolowane są bezpośredni FY/Q poprzednika, waluta,
metodologia, jednostki, standard i podstawa akcji, gdy występują.
E2E podaje już kanoniczną kwotę actual, mimo braku etykiety unit w historii;
nie skaluje się jej ponownie z source_value. Legacy gaap_diluted normalizuje
się tak samo jak w istniejącym czytniku, bez normalizowania Intel attributable.

Brak Current lub porównywalnego Previous daje — tylko dla odpowiedniej
metryki. Zero i ujemne EPS są liczbami. Nie używa się guidance, prognozy,
adjusted EPS lub poprzedniego roku. CRWD i INTC zachowały właściwe null EPS.

## Rzeczywiste przykłady API i widoku

Poniżej format PL z komórek. Revenue mniejsze niż miliard formatter pokazuje
w milionach. Wartości źródłowe i dokładne różnice odczytano z API, nie z instrukcji.

| Raport | EPS Aktualny / Poprzednio / różnica USD | Revenue Aktualny / Poprzednio / różnica |
|---|---|---|
| AAPL Q4 FY2026 | 2,10 / 2,02 / +0,08 | 114,48 mld / 109,42 mld / +5,06 mld USD |
| AMD Q3 2026 | 1,46 / 1,38 / +0,08 | 13,38 mld / 11,54 mld / +1,84 mld USD |
| ARM Q2 FY2027 | 0,12 / 0,25 / −0,13 | 1,44 mld / 1,29 mld / +154 mln USD |
| QCOM Q4 FY2026 | 1,17 / 1,87 / −0,70 | 10,32 mld / 9,95 mld / +375 mln USD |
| PLTR Q3 2026 | 0,44 / 0,41 / +0,03 | 2,31 mld / 1,94 mld / +377,95 mln USD |

Przykładowo AMD Revenue to dokładnie 13377000000 − 11536000000 =
1841000000 USD. QCOM: 10322000000 − 9947000000 = 375000000 USD.
PLTR: 2313411000 − 1935464000 = 377947000 USD.
Komórki Current/Previous Wszystko porównano bezpośrednio z komórkami Wyniki.
NVIDIA, PANW i SNOW w tym zakresie mają brakujące Current i różnice —,
przy dostępnych Previous; prognoza NVIDIA nie zastępuje Actual.

## Walidacja

| Kontrola | Wynik |
|---|---|
| Pełny frontend Vitest | **809 passed / 39 plików**, 68,51 s |
| Nowe przypadki selektora/różnic/renderowania | **15 passed** w powyższym zestawie |
| TypeScript noEmit | passed |
| Production build | passed, Vite 5,79 s, największy chunk 407,04 kB |
| Chrome na normalnym Vite/API/SQL | **423 kontrole / 17 API GET HTTP 200** |
| Pełne dane i katalogi Earnings/F1, 16 tabel | identyczne przed/po |
| Całe rzeczywiste API Earnings, 34 datowane wydarzenia | wszystkie obiekty identyczne przed/po |
| Manifest F1 V2 | wszystkie **155 artefaktów zgodne** |
| Zachowanie wcześniejszych plików i diff --check | passed |

Chrome: normalne API 8000, Vite 5173, własny CDP 9315; PL/EN i 1366/390 px.
Nie podstawiano odpowiedzi. Dla wszystkich ośmiu wydarzeń Earnings w zakresie
listopad–grudzień sprawdzono sześć komórek EPS/Revenue Current/Previous/delta
z wartościami API, a Current/Previous także ze szczegółową tabelą Wyniki.
Sprawdzono sześć fizycznych kolumn, brak Forecast, jedną tabelę i nagłówek dnia,
chronologię, godziny, gwiazdki, nazwy, przejście do Wyniki oraz brak overflow.
Szczegółowy mobile zachowuje wewnętrzny scroll, wspólny widok zachowuje swój
dotychczasowy układ mobilny. Obejrzano desktop EN i telefon PL z nowymi liczbami.

Po rzeczywistym oczekiwaniu ponad 60 sekund potwierdzono nowy GET Earnings,
pozostanie w Wszystko, niezmienną liczbę wierszy i unikalne identyfikatory.
W Dane nadal jest osiem kolumn i 14 nowcastów, w Wyniki siedem kolumn,
Actual/Prognoza, guidance NVIDIA i Market Cap. Wspólne komórki makro są
identyczne w obu widokach. Przy porównaniu treści uwzględniono dotychczasową
różną kolejność wydarzeń o identycznej godzinie; kolejność czasową testowano
osobno. Bez JS/console.error, HTTP 503 i zewnętrznych żądań przeglądarki.
Nie deklaruje się pełnego audytu WCAG.

Pierwsze uruchomienia narzędzi nie były sukcesami: sandbox zablokował plik
tymczasowy Vite; Vitest wymagał zgodnych min/max workers. Pierwszy własny
Chrome zakończył się przed otwarciem CDP; wznowiono go z diagnostyką.
Helper makro początkowo porównywał także kolumny Forecast i kolejność remisów
czasowych; poprawiono go na pełne porównanie wspólnych komórek z zachowaniem
krotności wierszy i osobnej kontroli chronologii. Powtórzono pełny Chrome,
w tym polling. Nie osłabiono asercji wartości, guarda sieci lub aplikacji.

## Ochrona i pliki

F1 V2 pozostaje activated=true/cooldown. Monitor Earnings pozostaje aktywny.
Frontend nie jest częścią manifestu workera V2; nie było potrzebne nowe
zatwierdzenie SQL lub token. Sprawdzono istniejący token, policy, katalogi
i referencje read-only. Nie zmieniono F2, backendu, konfiguracji, danych,
źródeł, harmonogramów, autoryzacji ani monitora. Market Cap pozostaje
korzystającym z dotychczasowego źródła polem szczegółowej tabeli.
Zwykłe procesy makro pozostały uruchomione. Porównanie pełnego SQL z wcześniejszym
snapshotem zakończonego importu wykazało dopisywanie observations/features,
publisher_documents i source checks oraz zmiany stanu Overview. Nie deklaruje
się byte-identyczności całej bazy makro. Pełne 16 tabel Earnings/F1, ich katalogi
i referencje są identyczne z odczytem na początku tej poprawki.

Zmieniono pięć zastanych plików:

- frontend/src/calendar/CalendarPage.tsx — import komponentu i trzy komórki Earnings;
- frontend/src/calendar/EarningsCalendar.tsx — ten sam odczyt Actual przez wspólny selektor;
- frontend/src/calendar/earningsFinancialPresentation.ts — wydzielony selektor, bez zmiany formatterów;
- frontend/src/calendar/unifiedCalendar.css — trzy reguły zwartych linii Earnings;
- frontend/src/calendar/UnifiedCalendar.test.tsx — sześć brakujących metryk zamiast trzech pustych komórek.

Nowe pliki:

- frontend/src/calendar/earningsComparison.ts;
- frontend/src/calendar/UnifiedEarningsValues.tsx;
- frontend/src/calendar/UnifiedEarningsValues.test.tsx;
- docs/audits/macrolens-unified-earnings-values-2026-11-06.md.

Manifest wejścia obejmuje 468 zastanych plików. **463 pozostały byte-identyczne**.
W pięciu koniecznych zmianach zachowano wcześniejsze hunki, także CalendarPage;
pozostałe chronione prace i cały F2 są bez zmian. Globalny CSS, zależności,
lockfile i CI pozostają nietknięte. Manifesty, pełny wejściowy diff, odczyty
SQL/API, logi i zrzuty są ignorowane w data/raw/unified-earnings-values-2026-11-06.

Nie uruchamiano migracji, importu finansowego lub aktywacji. Wszystkie
diagnostyczne połączenia SQL miały wymuszone read-only; nie dodano wywołań
odświeżania do frontendu ani nie zmieniono istniejącego lifecycle makro.
Własny Chrome po kontroli PID/argumentów zakończono przez CDP. Normalny
PostgreSQL, API 8000 i Vite 5173 pozostają uruchomione, poprawka jest dostępna.
Końcowo **18 modified / 49 untracked**, indeks pusty; main/HEAD
c42cf6c411c85a64927fe5c6b3cf98f9e906c871 bez zmian. Bez stagingu,
commita, pusha, reset, clean, amend, force i globalnego formatowania.
