# MacroLens — wspólny Calendar Wszystko

05.11.2026, Europe/Warsaw, C:\Projects\macrolens, main,
HEAD c42cf6c411c85a64927fe5c6b3cf98f9e906c871.

**Normalny widok Wszystko na 5173/8000 ma jedną wspólną tabelę makro i
Earnings.** Domyślne Wszystko oraz kolejność Wszystko | Dane | Wyniki
pozostają. EN: All | Data | Earnings. Nie ma osobnej sekcji ani pełnej
tabeli Earnings nad makro w tym widoku.

## Wspólna prezentacja

Typowany model `macro | earnings` łączy wyniki istniejących API tylko na
froncie. Zachowano osiem kolumn makro. Wyniki mają nazwę np.
„Wyniki AMD · Q3 2026”; pięć komórek liczbowych zawiera neutralne —.
Nie podstawia się EPS, przychodów, Forecast, zera ani fikcyjnego porównania.
Kliknięcie nazwy przełącza na pełne Wyniki z tym samym zakresem dat.
Oficjalne linki w pełnej tabeli pozostają niezmienione.

Na prawdziwych danych potwierdzono m.in.:

- 02.11: ISM Manufacturing 16:00, następnie AAPL/PLTR z nieznaną godziną;
- 03.11: JOLTS i zamówienia dóbr trwałych 16:00, AMD 22:00+;
- 04.11: ADP 14:15, bilans handlowy/NFCI 14:30, ISM Services 16:00,
  ARM i QCOM 22:00+;
- 17.11: NVIDIA Q3 FY2027 w swoim dniu, z oknem 22:00+.

Jeden dzień ma jeden nagłówek. Kolejność to lokalny dzień Europe/Warsaw,
potwierdzona chwila lub znana granica okna i stabilny klucz domena/event_id.
Nieznane godziny są na końcu dnia, bez timestampu północy. Klucze domen
nie kolidują, powtórne rekordy tego samego wydarzenia nie dublują wierszy.
Wiersze poszczególnych miar makro nadal należą do jednego raportu, jak wcześniej.

## Ważność dużych spółek

Zgodnie z dodatkową instrukcją użytkownika **wyniki spółki o zweryfikowanej
kapitalizacji co najmniej 200 000 000 000 USD mają ★★★**. Próg jest włącznie
z 200 mld. Porównanie wykorzystuje dokładny tekst USD/BigInt, przed
zaokrągleniem wartości prezentowanej w miliardach; nie ma FX.

Warunek wymaga istniejącego `verified_snapshot` i prawidłowej wartości/daty.
Stale, brak, niepoprawna lub niższa kapitalizacja daje — w kolumnie ważności;
nie przypisano automatycznie oceny 1/2. Testy obejmują także 199999999999.99
oraz 200000000000.01. W normalnym widoku AMD i NVIDIA mają ★★★,
QCOM poniżej progu i ARM bez kapitalizacji mają —. AAPL/PLTR również
spełniają próg. Dostępny opis podaje podstawę 200 mld USD.

Domyślny widok zachowuje wszystkie datowane Earnings, także te bez oceny.
Jawny filtr „Tylko ★★★” ogranicza je do spółek spełniających próg.
Filtry i klasyfikacja makro zachowują dotychczasowe działanie.

## Czas sesji i zakres wiarygodności

Nie dodano kalendarza giełd ani stałej godziny 22:00 na froncie. Istniejące
API przekazuje `session_context` dla przejrzanych notowań NYSE/Nasdaq:
otwarcie/zamknięcie obliczone w America/New_York, uwzględniające święta
i skrócone sesje. Front konwertuje te konkretne chwile do Europe/Warsaw.
Nie zakłada, że każdy emitent jest notowany w USA lub na NYSE.

Oficjalna dokładna godzina release jest pokazywana jako rzeczywista godzina
PL. Zweryfikowane after_close i odpowiednie approximate wskazują granicę
zamknięcia z „+”. Before_open pokazuje np. „< 15:30”; sortowanie używa znanej
granicy otwarcia, bez wymyślania początku przedziału. Tooltip/dostępny opis
wyjaśnia orientacyjny charakter okna. Godzina konferencji nie jest używana
jako release ani jako dowód okna we wspólnej tabeli.

AAPL/PLTR mają tutaj —, jeśli źródłowe release jest date-only; sama godzina
call nie tworzy im godziny publikacji. Istniejąca prezentacja pełnych Wyników
pozostaje bez zmian. Nie zmieniono dat/historii dowodów.

Testy potwierdziły różnice DST w marcu i październiku, zwykłe listopadowe
22:00+, zamknięcie 27.11 i 24.12 o 19:00 PL oraz dokładny release 23:30 UTC
przechodzący na 00:30 następnego dnia PL. Backendowy odczyt kalendarza
potwierdził też brak sesji 26.11. Obecny przejrzany kontekst sesji obejmuje
2026; poza dostępnym kontekstem nie dopisuje się sesji/okna.

## Pobieranie i pozostałe zakładki

Wspólny hook wydziela dotychczasowe odpytywanie Earnings: 60 s, bez nakładania
żądań, pauza w ukrytej karcie, wznowienie po jej pokazaniu, AbortController
i kontrola aktywności po zmianie zakresu/unmount. All i pełne Wyniki korzystają
z tego samego wyniku; przejście do szczegółów nie wymusza dodatkowego GET.
Makro korzysta z dotychczasowego niezależnego API/hooka refresh.

Błąd jednej domeny nie usuwa danych drugiej. Loading/partial error są
komunikowane przy zachowaniu dostępnych wierszy. Po błędzie odświeżania
Earnings zachowuje ostatnie dane; dyskretny komunikat dotyczy All.
Dotychczasowe zachowanie błędów pełnego widoku Wyniki zachowano.
Spóźniona odpowiedź starego zakresu nie wraca do nowej tabeli; sprawdzono
także przypadek, gdy jej wiersz pasowałby datą do nowego zakresu.

**Dane** zachowują dotychczasowy kalendarz makro. **Wyniki** zachowują siedem
kolumn, wartości, mniejsze Previous, Market Cap, źródła i wygląd.
Nowe zawijanie długich liczb na telefonie dotyczy wyłącznie klasy tabeli All;
globalnego CSS nie zmieniono.

## Walidacja

| Kontrola | Końcowy wynik |
|---|---|
| Pełny frontend offline | **794 passed / 38 plików**, 38.19 s |
| Nowe przypadki wspólnego kalendarza | **19 passed**, w powyższym zestawie |
| TypeScript noEmit | passed |
| Production build po korekcie mobile | passed, 4.17 s, chunk 407.04 kB |
| Odpowiednie backendowe F1/Calendar | **82 passed**, 11.53 s |
| PostgreSQL 17: rzeczywiste read-only SQL | passed, 16 pełnych snapshotów + katalogi + autoryzacja |
| Normalny Chrome PL/EN, 1366/390 px | **145 kontroli / 17 GET API 200** |
| Wcześniejszy pełny Chrome z realnym pollingiem | **145 kontroli / 37 GET API 200** |
| Integralność F1 i chronionych plików | passed |

Oba przebiegi Chrome korzystały z prawdziwych normalnych 5173/8000/5432,
bez fixture odpowiedzi. Każdy obejmował rzeczywisty cykl 61 s pollingu,
jedną tabelę, brak duplikatów, poprawne dni/godziny i próg ważności,
przejście do pełnych Wyników, siedem/osiem kolumn, guidance i oficjalny
link AMD, powrót do All, brak overflow strony i żądań przeglądarki do wydawców.
Zero JS/console.error i HTTP 503. Obejrzano desktop EN i mobile PL, także
po poprawie zawijania kwot. Nie deklaruje się pełnego audytu WCAG.

Pierwsze testy ujawniły dodatkowe ograniczanie wyników API makro po stronie
prezentacji oraz zmianę komunikatu błędu tła w pełnych Wynikach. Przywrócono
dotychczasowy kontrakt makro i zachowanie pełnych Wyników. Test spóźnionej
odpowiedzi miał problem z oczekiwaniem async act; zastąpiono go jawnym
sprawdzeniem abort i zakończenia starej Promise, zachowując asercję ignorowania
wiersza. Nie zwiększano timeoutów ani nie pomijano testów. Jeden helper
przebudowy Chrome wymagał jawnego UTF-8; końcowy pełny przebieg powtórzono.
Nieudanych prób nie zaliczono jako sukcesów.

Nie uruchamiano niepowiązanych mutujących walidacji migracji PostgreSQL.
Zmiana jest wyłącznie frontendowa: odpowiednią kontrolą SQL były rzeczywiste
read-only odczyty targetu, danych, katalogów i autoryzacji przed/po UI.

## F1 V2, dane i ochrona prac

Normalny target sprawdzano z wymuszonym READ ONLY/REPEATABLE READ:
localhost:5432/macrolens, PG17, rola macrolens. Wszystkie **16 tabel
Earnings/Forecast**, pełne hashe/liczniki i timestampy oraz oba katalogi
schematu są identyczne przed i po końcowym Chrome. Manifest F1 V2 ma nadal
**155 zgodnych artefaktów**, ten sam token i rewizję. Nie wykonano SQL WRITE,
DDL, APPLY, nowej policy lub tokenu, importu prognoz lub aktywacji F2.

F1 status: activated=true, cooldown. Earnings monitor: activated=true,
loop_running=true, completed. Zostały 20 prognoz, sześć null freezes,
trzy checks; zachowano 14 nowcastów i guidance NVIDIA. Bez zmian danych
Actual/Previous: SQL/API ponownie potwierdziły AMD 1.38 / 11536000000 USD,
AAPL 2.02 / 109417000000 USD i PLTR 0.41 / 1935464000 USD dla poprawnych
poprzednich kwartałów. Market Cap nie importowano.

Istniejące zwykłe odświeżanie makro pozostało aktywne. Nie deklaruje się
globalnej niezmienności jego równoległych zapisów; nie zmieniono jego
backendu, konfiguracji, lease lub sposobu uruchamiania.

Zapisano manifest 453 zastanych plików i pełny dirty diff. **451 plików
pozostaje byte-identyczne**. Zmieniono tylko konieczne CalendarPage.tsx
i EarningsCalendar.tsx, zachowując wcześniejsze hunki. Pozostałe chronione
prace, globalny CSS, F2, backend i poprzednie audyty pozostały identyczne.

Zmiany etapu:

- frontend/src/calendar/CalendarPage.tsx
- frontend/src/calendar/EarningsCalendar.tsx — wydzielenie fetch/poll, bez zmiany tabeli
- frontend/src/calendar/useEarningsCalendar.ts — nowy
- frontend/src/calendar/unifiedCalendar.ts — nowy
- frontend/src/calendar/unifiedCalendar.css — nowy, tylko mobile All
- frontend/src/calendar/UnifiedCalendar.test.tsx — nowy
- docs/audits/macrolens-calendar-unified-all-2026-11-05.md — ten raport

Manifesty, odpowiedzi API, snapshoty, logi i screenshoty pozostają ignorowane
w data/raw/calendar-unified-all-2026-11-05. Własny Chrome testowy zakończono;
normalny PostgreSQL/API/Vite pozostawiono działające. Nie restartowano ich
ręcznie i nie tworzono kontenera/bazy testowej. Indeks pusty, main/HEAD
bez zmian, końcowo **17 modified / 35 untracked plików**. Bez stagingu,
commita, pusha, reset/clean/amend/force lub globalnego formatowania.
