# MacroLens — spójna prezentacja czasu wyników

Wykonano **04.11.2026, Europe/Warsaw**, C:\Projects\macrolens,
main, HEAD **5b31cdb1ea042cd10483f701c262b85a958efc08**.
Bez stagingu, commita i pusha. Zmiana działa na normalnym Vite/API.

## Etykiety i model prezentacyjny

Wspólne klucze w earningsTimeLabels.ts:

| Klucz | PL | EN |
|---|---|---|
| after_close | Po sesji USA | After US close |
| before_open | Przed sesją USA | Before US open |
| during_session | W trakcie sesji USA | During US session |
| unknown | Godzina niepotwierdzona | Time not confirmed |
| call + warsaw | Konferencja: 23:00 PL | Call: 23:00 Warsaw |

Pierwsza linia jest normalnym tekstem, druga mniejsza i tylko dla istniejącej,
zweryfikowanej dokładnej konferencji. Bez minuty publikacji, badge'ów,
tooltipów, przypisów i nowych kolumn. Zachowano wyśrodkowanie. Wcześniejsze
usunięcie podpisu dostawców pod Market Cap pozostaje zachowane.

Formatter zwraca window i odrębne basis: official, indicative, unknown.
Nie aktualizuje surowej precision, confidence, statusu ani dowodów. Oficjalne
before_open/after_close mają pierwszeństwo przed godziną calla. Dokładny
zweryfikowany czas publikacji jest klasyfikowany wobec sesji NY; tylko taki
czas potwierdza during_session. Orientacyjny czas publikacji może sugerować
przed/po, ale nie potwierdza publikacji podczas sesji.

Jeżeli okna brak, orientacyjne after_close wymaga sprawdzonego notowania USA,
zweryfikowanej dokładnej konferencji po rzeczywistym zamknięciu, tego samego
dnia NY oraz braku sprzecznego czasu/dat dokumentu. Anulowana lub niezweryfikowana
konferencja, brak sesji, inny dzień lub obcy listing nie wystarczają.
Nie wylicza się konkretnej minuty publikacji z konferencji. Superseded historia
nie zastępuje aktualnego snapshotu dowodów.

## Dane normalnego API i źródła

Wszystkie poniższe pozycje pokazują **Po sesji USA / After US close**:

| Spółka / okres | Konferencja PL | Podstawa okna |
|---|---|---|
| AAPL Q4 FY2026 | 23:00 | orientacyjna, harmonogram |
| PLTR Q3 2026 | 23:00 | orientacyjna, harmonogram |
| AMD Q3 2026 | 23:00 | oficjalne after_close |
| INTC Q3 2026 | 22:00 | oficjalne after_close |
| AMZN Q3 2026 | 22:00 | orientacyjna, harmonogram |
| ARM Q2 FY2027 | 23:00 | oficjalne after_close |
| QCOM Q4 FY2026 | 22:45 | oficjalne after_close |

To wynik rzeczywistego modelu w Chrome i normalnego API, nie mapowanie tickerów
w rendererze. Wyniki zapisano w ignorowanym timing-projection.json. ARM/QCOM
mają już oficjalną precision after_close; fallback harmonogramu nie był potrzebny.

Sprawdzono wskazane przez użytkownika oficjalne strony:
[Apple](https://www.apple.com/newsroom/2026/11/apple-reports-fourth-quarter-results/),
[Palantir](https://investors.palantir.com/news-details/2026/Palantir-Announces-Date-of-Third-Quarter-2026-Earnings-Release-and-Webcast/),
[AMD](https://ir.amd.com/news-events/press-releases/detail/1300/amd-to-report-fiscal-third-quarter-2026-financial-results),
[Intel](https://www.intel.com/content/www/us/en/newsroom/news/corporate/intel-reports-third-quarter-2026-financial-results.html),
[Amazon](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Third-Quarter-Results/default.aspx).

AMD i Intel jawnie potwierdzają publikację po zamknięciu. Datowane komunikaty
wynikowe Apple i Amazon oraz podane godziny konferencji nie zostały potraktowane
jako dowód dokładnego czasu publikacji. Odczyt Palantir IR pokazał szkielet strony,
bez treści komunikatu; nie deklaruje się dodatkowej weryfikacji jej okna.
AAPL/PLTR/AMZN zachowują w modelu podstawę indicative i swoje pierwotne dowody.

## Minimalne rozszerzenie read-only

Dotychczasowy kontrakt nie zawiera pełnego kontekstu sesji ani giełdy emitenta.
Dodano wyłącznie opcjonalne session_context: sprawdzony listing USA oraz
open/close UTC i daty sesji dla release/call. Stare pola eventów są identyczne.
To kontekst prezentacji, nie dowód nowego release.

app/earnings_session.py korzysta z lokalnego, już zweryfikowanego rejestru
53 emitentów (CIK/ticker/alias, reviewed_sec, Nasdaq/NYSE) i ograniczonego
kalendarza **2026**. Ten kalendarz sprawdzono w
[NYSE](https://www.nyse.com/trade/hours-calendars) i
[Nasdaq](https://nasdaqtrader.com/Trader.aspx?id=Calendar).
Obejmuje weekendy, dziesięć świąt i krótsze sesje 27.11 oraz 24.12.
Nie jest kalendarzem bezterminowym: poza sprawdzonym rokiem brak kontekstu
do szacowania, zamiast zgadywania.

Granice tworzy ZoneInfo America/New_York, a istniejący formatPolandTime
obsługuje Europe/Warsaw. Zachowano UTC wyliczone wcześniej z America/Los_Angeles.
Zamknięcie 29.10 to 20:00 UTC / 21:00 PL, 02.11 to 21:00 UTC / 22:00 PL,
a 27.11 to 18:00 UTC / 19:00 PL. Nie użyto stałej 22:00 PL.
Nie zmieniono starej temporal() ani dat/groupowania Calendar.

Brak dodatkowych zapytań SQL, DDL, importerów lub HTTP w GET.
Nowe pole powstaje w istniejącym odczycie, po dotychczasowych projekcjach.
API nadal używa REPEATABLE READ READ ONLY. Nie zmieniono Current/Previous,
23 raportów / 45 miar, prognoz, statusów, źródeł lub Market Cap.

## Walidacja

| Kontrola | Wynik |
|---|---|
| Pełny backend offline | **1481 passed**, 70,20 s |
| Finalne testy zależności czasu backendu | **49 passed**, 1,43 s |
| Pełny finalny frontend offline | **711 passed / 34 pliki**, 30,28 s |
| TypeScript noEmit | passed |
| Production build | passed, Vite 4,00 s; największy chunk 407,04 kB |
| Chrome, normalny Vite/API/SQL | **1133 kontroli / 28 odpowiedzi API 200** |
| Dodatkowe bezpośrednie GET helpera Chrome | **37 HTTP 200** |
| JS / console.error / HTTP 503 | zero |
| Chronione pliki / cache / diff --check | passed |

Pełny backend przeszedł przed końcowym usunięciem redundantnego, identycznego
wyliczenia dnia; po tej zmianie ponownie przeszło 49 testów zależności.
Finalny frontend obejmuje guard niepoprawnego timestampu konferencji.

Regresje obejmują siedem wymaganych spółek, oficjalne przed sesją i dokładne
during_session, brak podstaw, brak/niezweryfikowany/anulowany call, obcy listing,
inny dzień, sprzeczną datę raportu, oficjalne okno sprzeczne z godziną calla,
approximate vs exact, Published/Scheduled, PL/EN, UTC/DST i early close.
Poprzednie oczekiwania szczegółowej minuty publikacji zmieniono zgodnie z nowym
kontraktem; testy zachowania surowych danych i dat zachowano/dodano.

Chrome użył normalnego http://localhost:5173/#/calendar i API 8000, bez fixture.
Sprawdzono wszystkie 34 wiersze, cztery wartości i prognozy, siedem kolumn,
słownik pory wyników, odrębny call, siedem konkretnych przypadków, zakresy/domeny
i zachowany Market Cap. PL/EN, desktop 1366 i mobile 390 px. Obejrzano desktop EN,
mobile PL oraz przewiniętą komórkę czasu. Brak overflow strony, requestów
do wydawców i zbędnego refetch przy zmianie domen. To nie pełny audyt WCAG.

Porównano całe stare obiekty events/undated przed/po: poza nowym session_context
wszystkie dotychczasowe pola są identyczne, także precision, daty, source URL,
statusy, Current/Previous i źródła. Zmiana earnings_data_revision wynika z nowego
kontekstu; assembled_at zachowuje dotychczasową semantykę czasu odpowiedzi.

## Ochrona danych, pliki i Git

Normalna baza: ten sam target localhost:5432/macrolens, rola macrolens,
OID 16384, klaster 7682090371041935398. Diagnostyka wyłącznie read-only.
W badanym przedziale pełne COPY/hash/count wszystkich **24 tabel /
2 963 787 rekordów** i oba katalogi schematu są identyczne. W szczególności
wszystkie **11 tabel Earnings**, historia 23/45 i timestampy są identyczne.
Nie wykonano zapisu do normalnego PostgreSQL. Nie zatrzymano aplikacji,
odświeżeń makro lub PostgreSQL. Nie zakładano lease.

Manifest wszystkich 17 zastanych dirty plików i diff zapisano w ignorowanym
data/raw/earnings-session-presentation-2026-11-04. Spośród nich zmieniono
wyłącznie upoważniony EarningsCalendar.tsx; pozostałe 16 są byte-identyczne,
w tym wszystkie 13 chronionych plików i wcześniejsza zmiana testu Market Cap.
Cache nadal ma 49/53 firm, SHA
`94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799`.
Wcześniejszych raportów nie edytowano.

Sześć zmienionych istniejących plików tego etapu:

- app/earnings.py
- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/earningsPresentation.ts
- frontend/src/calendar/earningsTypes.ts
- frontend/src/calendar/EarningsCalendar.test.tsx
- frontend/src/calendar/EarningsCoverage.test.tsx

Sześć nowych plików:

- app/earnings_session.py
- tests/test_earnings_session.py
- frontend/src/calendar/earningsSessionPresentation.ts
- frontend/src/calendar/earningsTimeLabels.ts
- frontend/src/calendar/EarningsSessionPresentation.test.tsx
- docs/audits/equity-earnings-session-presentation-2026-11-04.md

Końcowo **16 modified / 12 untracked**, indeks pusty, main/HEAD bez zmian.
Bez stagingu, commita, pusha, reset, clean, amend i globalnego formatowania.
Zależności, lockfile, CI i CSS bez edycji tego etapu. Własny Chrome zakończono
przez odrębny CDP 9279. Nie tworzono baz lub kontenerów testowych.
Normalne API/Vite/PostgreSQL pozostają działające; helpery/logi/zrzuty są
ignorowane w data/raw.
