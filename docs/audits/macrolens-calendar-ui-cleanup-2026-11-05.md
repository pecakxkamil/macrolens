# MacroLens — Calendar UI cleanup

Przygotowano 05.11.2026, Europe/Warsaw, C:\Projects\macrolens, main,
HEAD `c42cf6c411c85a64927fe5c6b3cf98f9e906c871`.

**Poprawka gotowa i sprawdzona w izolowanej kopii. Normalne UI pozostaje
bez zmian.** Aktywna autoryzacja F1 zamraża także modyfikowane pliki frontendu;
bez jej kontrolowanej migracji wdrożenie zatrzymałoby F1. Na osobne zlecenie
przygotowano [plan autoryzacji F1](macrolens-forecast-f1-ui-authorization-plan-2026-11-05.md),
ready_for_apply=false. Nie wykonano normalnego zapisu ani zmiany policy.

## Poprawka

Przejrzano wszystkie 53 nazwy; słownik prezentacji według CIK zmienia 37.
AMD pokazuje „Advanced Micro Devices, Inc.”, ARM „Arm Holdings plc”,
Qualcomm „Qualcomm Incorporated”. Zachowano marki IBM, NVIDIA i TSMC.
Nie zastosowano automatycznego titlecase; nieznany CIK zwraca oryginalną
nazwę. Aliasy GOOG/GOOGL korzystają z tego samego CIK i nazwy Alphabet.
Sprawdzono m.in. oficjalne strony
[Arm](https://investors.arm.com/governance/overview-documentation),
[ASML](https://investor.asml.com/investor-resources/capital-return-and-financing)
i [ExxonMobil](https://corporate.exxonmobil.com/news/news-releases).
Pełne zestawienie source/display dla 53 emitentów jest w ignorowanym
`data/raw/calendar-ui-cleanup-2026-11-05/name-review.json`.
Identyfikatory, tickery, aliasy, dane SQL i linki raportów pozostają oryginalne.

Nowe zwykłe otwarcie Calendar wybiera Wszystko / All. Kolejność i etykiety:
**Wszystko | Dane | Wyniki**, **All | Data | Earnings**. Świadomy wybór
pozostaje podczas rerender i odpytywania danych. Ponowne wejście/reset mount
wraca do All. Nie znaleziono istniejących linków z filtrem domeny; zachowano
dotychczasowy routing. Nie zmieniono grupowania dat, sortowania, zakresów,
stref, fetchera ani interwałów. Domyślne All wykonuje też potrzebny GET Earnings.

[Patch](../patches/macrolens-calendar-ui-cleanup-2026-11-05.patch) jest różnicą
względem zastanego working tree, zachowując wcześniejsze hunki użytkownika.
SHA-256: `aeee918881db29a3228cfdeef5882f276eed8deffbdc87bf2c406ee5e42f3338`.
`git apply --check` przeszedł; patcha nie zastosowano w normalnych źródłach.

Zakres patcha: CalendarPage.tsx, EarningsCalendar.tsx, nowe
earningsCompanyNames.ts i earningsCompanyNames.test.ts, EarningsDomains.test.tsx,
CalendarPage.test.tsx, CalendarRefresh.test.tsx, EarningsFinancials.test.tsx,
brief/marketImpact.test.tsx i navigation/lazyLoading.test.tsx.
Testy samego makro izolują fetch Earnings. Fikcyjna czwarta spółka ma teraz
własny CIK zamiast CIK Intel; test lazy loading uwzględnia potrzebny GET.
Nie zmieniono CSS, zależności, backendu, F2 lub danych finansowych.

## Previous: prawdziwe SQL i API

Porównano 34 wydarzenia SQL/API, wartości i poprzednie kwartały fiskalne.
Sprawdzono źródłowe jednostki, USD, US GAAP, reported diluted EPS i przychody
skonsolidowane dla poniższych przykładów:

| Bieżący / Previous | EPS Previous | Revenue Previous |
|---|---:|---:|
| AAPL Q4 / Q3 FY2026 | 2.02 USD | 109417000000 USD |
| AMD Q3 / Q2 2026 | 1.38 USD | 11536000000 USD |
| PLTR Q3 / Q2 2026 | 0.41 USD | 1935464000 USD |

CRWD Previous EPS pozostaje null, przychody dostępne. ARM/QCOM Previous
pozostają null. Nie wpisano liczb do frontendu. AMD nadal prowadzi do
oryginalnego oficjalnego release. GOOG/GOOGL nie dublują wydarzeń.

## Walidacja kandydackiego UI

| Kontrola | Wynik |
|---|---|
| Pełny backend offline | 1577 passed |
| Pełny frontend | 775 passed / 37 plików |
| TypeScript noEmit / production build | passed; największy chunk 407.04 kB |
| PostgreSQL history i history activation V2 | 2/2 passed, własny PG17 |
| Chrome PL/EN, 1366/390 px | 328 kontroli, 13 GET API 200 |
| Normalne Earnings/F1 i schemat | 16 pełnych snapshotów identyczne |
| Zastane pliki / autoryzacja F1 | 28 plików i 260 artefaktów identyczne |

Chrome używał production preview 4229 i prawdziwego normalnego API 8000,
bez podstawiania odpowiedzi finansowych. Lokalny proxy preview przekazywał
wyłącznie GET; inne metody odrzucał przed przekazaniem. Konfiguracja proxy
jest wyłącznie ignorowanym narzędziem kontroli, poza patchem aplikacji.
Brak błędów JS/console.error i żądań przeglądarki do wydawców. Sprawdzono
nazwy, kolejność/default domen, Previous, 14 nowcastów i guidance NVIDIA,
siedem kolumn Earnings, osiem makro, mobile scroll i brak overflow strony.
W pierwszym EN desktop odczekano rzeczywisty cykl 61 s: wybrana domena
pozostała; obie lokalizacje mają też testy zegara. Obejrzano desktop EN i
przewiniętą tabelę mobile PL. Nie jest to pełny audyt WCAG.

Pierwsze próby testów wykazały błędny wspólny CIK syntetycznej spółki oraz
stary licznik GET w lazy loading; poprawiono oczekiwania zgodnie z nowym
default All. Pierwsza próba preview miała błędny adres API/CORS; poprawiono
wyłącznie transport własnego preview i powtórzono Chrome. Pomocnicza asercja
metodologii Revenue miała niewłaściwą nazwę; sprawdzono rzeczywiste
consolidated_revenue. Nieudanych prób nie zaliczono jako sukcesów.

## Ochrona normalnego środowiska

Wymuszone read-only: localhost:5432/macrolens, PG17, rola macrolens,
OID 16384, klaster 7682090371041935398. Wszystkie 13 tabel Earnings i trzy
F1 zachowały pełne ordered binary COPY hash/count, także timestampy.
Oba katalogi schematu identyczne. F1: 20 vintages / 6 null freezes / 2 checks,
activated=true, cooldown. Earnings monitor: activated=true, loop_running=true,
completed. Nie wymagano byte-identyczności pracującego równolegle makro.
Market Cap cache identyczny, 49/53; F2 i wszystkie 13 chronionych prac
użytkownika zachowane byte-identycznie. Wszystkie 28 zastanych zmienionych/
nieśledzonych plików zachowano. Nie wykonano DDL/importu, zapisu policy,
podmiany tokenu, restartu zwykłego API/Vite ani stagingu/commita/pusha.

Manifesty, logi, zrzuty i kopia do testów pozostają w ignorowanym
data/raw/calendar-ui-cleanup-2026-11-05. Dostarczono patch i dwa raporty;
źródła normalnej aplikacji pozostają zgodne z aktywnym F1.

Własne preview 4229 i headless Chrome 9301 zakończono po sprawdzeniu PID
i pełnych argumentów. Własny PG17 55523 usunięto z wolumenem po potwierdzeniu
pełnego ID `3dd03221903114647c7bf7a33786b18029b53aa4deb752490a50388e454e9b4a`,
etykiety zadania, braku innych klientów oraz baz poza control/postgres/template.
Normalnego PostgreSQL 5432, API 8000 i Vite 5173 nie zatrzymywano.
Końcowo 9 modified / 22 untracked pliki (wcześniejsze 19 i trzy dostarczone),
indeks pusty. Bez reset/clean/amend lub globalnego formatowania.
