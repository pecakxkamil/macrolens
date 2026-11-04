# MacroLens — Earnings UI: Market Cap zamiast Szczegółów

Wykonano **04.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`, `main`,
HEAD `94526c9cf0422dde041c69fd4fdec21549a8b39e`.

**Stan po sekcji 11: normalny Calendar pokazuje rzeczywiste Market Cap
z lokalnego cache dla 49/53 emitentów, bez klucza, konta i płatności.
TSM, ASML, ARM i SHOP pozostają bez wyceny z powodu niepotwierdzonego
zakresu ADR/klas. Nie wykonano DDL ani importu do normalnego PostgreSQL.**
Sekcje 1–10 dokumentują wcześniejszy cleanup i etap FMP, w którym było
0/53 wartości. Adapter FMP pozostaje nieaktywny. Bez stagingu, commita i pusha.

## 1. Widok i źródła finansowe

Dokładnie siedem kolumn: Spółka, Czas wyników · Polska, EPS aktualny,
EPS poprzednio, Przychody aktualne, Przychody poprzednio, Market Cap.
Usunięto nagłówek i przyciski Szczegóły, panel, jego stan/Escape/aria-controls
oraz CSS przeznaczony wyłącznie dla niego. Status nadal istnieje w API.
Nie dodano kolumny źródeł, badge'y, ikon, nowych opisów lub stopki.

Ticker/nazwa prowadzi do rzeczywistego zweryfikowanego raportu finansowego,
jeśli taki istnieje. Link ma etykietę z tickerem, okresem i informacją
„Oficjalny raport finansowy”, działa z klawiatury i ma widoczny focus.
Zapowiedź daty lub call bez raportu nie tworzy linku do fikcyjnego dokumentu.
Źródła Previous, dat, call, statusy i pełna historia pozostają w API/SQL.

Current/Previous i cztery linie prognoz zachowano. Previous nadal ma mniejszą
typografię. Spółka jest wyrównana do lewej, sześć pozostałych kolumn do środka.
Szerokość tabeli i wewnętrzny scroll zachowano, bez overflow całej strony.

## 2. Format kapitalizacji

Weryfikowany snapshot USD jest formatowany dopiero w UI do miliardów:
PL `850,4 mld USD`, EN `850.4 bn USD`, maksymalnie dwa miejsca po przecinku.
Mniejsza druga linia to `Stan na 03.11.2026` / `As of 11/03/2026`.
To **przykład użyty tylko w syntetycznych testach**, nie wycena żadnej firmy.

API zachowuje pełną precyzję w tekście Decimal. Formatter wykorzystuje
BigInt do zaokrąglenia, bez konwersji dokładnej kwoty do float. Bardzo mała
dodatnia kapitalizacja jest pokazywana jako `< 0,01 mld USD`, nie zero.
Brak wartości, statusu weryfikacji lub prawidłowej daty daje samo `—`.
Nie ma oznaczenia live i nie ma wymyślonej daty pomiaru.

## 3. Ocena dostępnych źródeł i braki

Przegląd app/config/frontend nie wykazał istniejącego feedu, adaptera lub
snapshotów Market Cap. Dotychczasowe dane finansowe E2B/E2D/E2E nie są
źródłem kapitalizacji. Nie łączono EPS/revenue z domniemaną ceną lub liczbą
akcji. Nie odczytywano i nie wypisywano sekretów.

Przejrzano oficjalną dokumentację potencjalnych źródeł 04.11.2026:

| Rodzaj | Ocena i granice |
|---|---|
| Dane emitenta / SEC | [EDGAR API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) udostępnia filings i fakty XBRL. Dane o akcjach wymagają właściwego okresu i klas; same nie dostarczają zsynchronizowanej ceny giełdowej. Nie użyto public float ani diluted weighted-average shares zamiast shares outstanding. |
| Notowania | Potrzebny jest zweryfikowany pomiar ceny z datą/czasem oraz właściwa liczba akcji i komplet klas z zgodnego okresu. W projekcie nie ustalono takiego połączenia danych i uprawnień. Nie obliczano kapitalizacji z ceny bieżącej i odległego historycznie share count. |
| Gotowy Market Cap — Alpha Vantage | [Dokumentacja](https://www.alphavantage.co/documentation/) opisuje dane fundamentalne, a [warunki](https://www.alphavantage.co/terms_of_service/) rozróżniają prywatny niekomercyjny dostęp od szerszego wykorzystania. Nie potwierdzono tu konta/planu, prawa do wymaganego przechowywania i prezentacji, daty konkretnego pomiaru i pokrycia wszystkich klas/ADR dla 53 firm. Nie wykonano requestów danych. |
| Gotowy Market Cap — FMP | Dostawca opisuje [dostęp do historycznej kapitalizacji](https://site.financialmodelingprep.com/faqs?code=data). [Warunki](https://site.financialmodelingprep.com/terms-of-service) wiążą dostęp i użycie z planem/umową i ograniczają szerszą prezentację/redystrybucję. Nie potwierdzono odpowiedniej umowy i metodologii whole issuer. Nie pobrano wycen. |

To ocena możliwości, nie twierdzenie, że każdy prywatny użytek jest zakazany.
Nie przyjęto jednak, że darmowa strona lub endpoint stanowi zgodę na wszystkie
potrzebne działania. Nie zakładano konta/subskrypcji i nie kontaktowano
dostawców w imieniu użytkownika. Nie używano Investing.com, nie obchodzono
API/antybota i nie scrapowano stron z notowaniami.

**Brak zatwierdzonego źródła i pomiarów dotyczy wszystkich 53 emitentów.**
Pusty `config/earnings_market_cap_reviewed.json` jest celowy. Nie ma dat
ostatnich rzeczywistych pomiarów do podania. Priorytet NVDA/MSFT/AAPL/AMZN/
GOOGL/META/AVGO/AMD/TSLA/NFLX nie został wypełniony liczbami zastępczymi.

| Emitent | CIK | Market Cap / data |
|---|---|---|
| NVDA | 0001045810 | brak / brak pomiaru |
| AMZN | 0001018724 | brak / brak pomiaru |
| INTC | 0000050863 | brak / brak pomiaru |
| AAPL | 0000320193 | brak / brak pomiaru |
| MSFT | 0000789019 | brak / brak pomiaru |
| GOOGL | 0001652044 | brak / brak pomiaru |
| META | 0001326801 | brak / brak pomiaru |
| TSLA | 0001318605 | brak / brak pomiaru |
| AVGO | 0001730168 | brak / brak pomiaru |
| AMD | 0000002488 | brak / brak pomiaru |
| ORCL | 0001341439 | brak / brak pomiaru |
| NFLX | 0001065280 | brak / brak pomiaru |
| MU | 0000723125 | brak / brak pomiaru |
| QCOM | 0000804328 | brak / brak pomiaru |
| TSM | 0001046179 | brak / brak pomiaru |
| ASML | 0000937966 | brak / brak pomiaru |
| ARM | 0001973239 | brak / brak pomiaru |
| AMAT | 0000006951 | brak / brak pomiaru |
| LRCX | 0000707549 | brak / brak pomiaru |
| KLAC | 0000319201 | brak / brak pomiaru |
| TXN | 0000097476 | brak / brak pomiaru |
| ADBE | 0000796343 | brak / brak pomiaru |
| CRM | 0001108524 | brak / brak pomiaru |
| NOW | 0001373715 | brak / brak pomiaru |
| PLTR | 0001321655 | brak / brak pomiaru |
| CRWD | 0001535527 | brak / brak pomiaru |
| PANW | 0001327567 | brak / brak pomiaru |
| SNOW | 0001640147 | brak / brak pomiaru |
| IBM | 0000051143 | brak / brak pomiaru |
| CSCO | 0000858877 | brak / brak pomiaru |
| UBER | 0001543151 | brak / brak pomiaru |
| ABNB | 0001559720 | brak / brak pomiaru |
| SHOP | 0001594805 | brak / brak pomiaru |
| BKNG | 0001075531 | brak / brak pomiaru |
| PYPL | 0001633917 | brak / brak pomiaru |
| COIN | 0001679788 | brak / brak pomiaru |
| JPM | 0000019617 | brak / brak pomiaru |
| BAC | 0000070858 | brak / brak pomiaru |
| GS | 0000886982 | brak / brak pomiaru |
| V | 0001403161 | brak / brak pomiaru |
| MA | 0001141391 | brak / brak pomiaru |
| WMT | 0000104169 | brak / brak pomiaru |
| COST | 0000909832 | brak / brak pomiaru |
| HD | 0000354950 | brak / brak pomiaru |
| LLY | 0000059478 | brak / brak pomiaru |
| UNH | 0000731766 | brak / brak pomiaru |
| JNJ | 0000200406 | brak / brak pomiaru |
| XOM | 0002115436 | brak / brak pomiaru |
| CVX | 0000093410 | brak / brak pomiaru |
| CAT | 0000018230 | brak / brak pomiaru |
| BA | 0000012927 | brak / brak pomiaru |
| DIS | 0001744489 | brak / brak pomiaru |
| BRK-B | 0001067983 | brak / brak pomiaru |

## 4. Emitent, klasy akcji i ADR

Snapshot jest przypisany do istniejącego company_id/CIK, nie tickera lub
eventu. Jeden zbiorczy odczyt wybiera tę samą kapitalizację dla wszystkich
wydarzeń emitenta, niezależnie od historycznej daty raportu Earnings.
GOOG/GOOGL i BRK.B/BRK-B zachowują jednego emitenta. Nie dodano nowych aliasów
(np. BRK.A) do rejestru; potencjalne dane Berkshire muszą obejmować wszystkie
klasy całej spółki, bez sumowania dwóch kompletnych kapitalizacji.

Model wymaga jawnego `whole_issuer_all_classes` i dowodu podstawy pomiaru.
Odrzuca class-only, ADR-only, public float i enterprise value. TSM, ASML,
ARM i inni zagraniczni emitenci nie otrzymali wartości tylko na podstawie
amerykańskiego tickera. Akceptowana ścieżka to bezpośrednio zweryfikowany
Market Cap całego emitenta w USD; nie wykonuje się własnego FX, przeliczenia
ADR ani sumowania klas. Ścieżka obliczeniowa cena×akcje nie jest na tym etapie
akceptowana — wymaga osobno zweryfikowanego modelu, wejść i źródeł.

## 5. Osobny store i API

Minimalny model to `earnings_market_cap_snapshots`, oddzielny od finansów
Earnings, historii E2E i makro. Ma NUMERIC USD, identyfikator/CIK emitenta,
datę as_of, opcjonalny measured_at z timezone, source URL/ID/version,
metodę, zakres whole issuer, basis/access evidence, verified_on,
fingerprint i lokalny captured_at. FK wskazuje istniejącą spółkę.

SQL kontroluje dodatnią skończoną kwotę, USD, daty, tożsamość i zakres.
Triggery blokują UPDATE/DELETE/TRUNCATE. Unikalność obejmuje emitenta,
źródło, dzień pomiaru i wersję źródła; ponowienie identycznego fingerprintu
niczego nie zmienia. Korekta musi być osobnym snapshotem z nową wersją
źródła; stary pozostaje w bazie. Importer waliduje całą partię względem
dokładnego reviewed ledgeru i używa istniejącego advisory locka.

Inicjalizator/importer dopuszcza wyłącznie własny prefiks izolacji
`macrolens_earnings_e2b_e2c_e2d_e2e_cap_`, a zastany schemat wymaga zgodnej
pełnej sygnatury. Nie ma importu/startupu/DDL ani transportu HTTP w GET.
Rzeczywisty produkcyjny ledger jest pusty; syntetyczne wpisy testowe używają
osobnego tymczasowego ledgeru i nie są danymi rynkowymi.

Do istniejącej odpowiedzi Earnings dodano `market_cap_usd`,
`market_cap_as_of`, `market_cap_source`, `market_cap_status` i pełny
`market_cap_snapshot`. Stare pola i provenance pozostały dostępne.
Nieaktywny store daje null i `not_activated`; aktywny pusty — `unavailable`.
Częściowy store jest odrzucany. Odczyt odbywa się w dotychczasowej transakcji
REPEATABLE READ READ ONLY. SELECT DISTINCT ON pobiera najnowsze snapshoty
zbiorczo dla emitentów, bez N+1. Pierwszeństwo ma data/czas pomiaru, a nie
późniejszy capture starej wartości; date-only jest konserwatywnie przed
pomiarami z czasem tego samego dnia. Czas nieznany pozostaje null.

## 6. Walidacja

| Kontrola | Nowy wynik |
|---|---|
| Pełny backend offline | **1383 passed**, pytest 47,74 s |
| Pełny frontend offline | **691 passed / 33 pliki**, 27,26 s |
| TypeScript noEmit | passed |
| Production build | passed, 3,18 s; największy chunk 407,04 kB |
| Dotychczasowe PostgreSQL 17 | **13/13 passed**, w tym historia E2E |
| Nowy PostgreSQL Market Cap | passed: 53 syntetyczne snapshoty |
| Chrome izolowany | **709 kontroli / 26 odpowiedzi API 200**, dodatkowo 37 GET 200 |
| Chrome normalny | **709 kontroli / 28 odpowiedzi API 200**, dodatkowo 37 GET 200 |
| JS / console.error / HTTP 503 / publisher requests | zero |
| Normalne 23 tabele i katalogi przed/po | identyczne |
| Chronione pliki, indeks, whitespace | passed |

Nowe przypadki obejmują pełną precyzję kwot, zero/null/brak daty,
niepoprawny pomiar, USD/skale, brak uprawnień lub dowodu podstawy,
class-only/ADR-only/EV, najnowszy as_of zamiast capture, wszystkie 53 firmy,
aliasy, idempotencję bez timestamp drift, append-only, prawdziwy rollback
DDL+seeda, zły schemat i realne HTTP listy/szczegółów nad SQL. Wszystkie
24 wcześniejsze tabele izolacji pozostały identyczne po nowym imporcie.

Regresje: Empire, FT900, BEA Direct, BEA release/R3, E2A/Activation,
E2B/Activation, E2C/Activation, E2D/Activation i nowa historia E2E.
Wykonano je na własnym PG17, loopback 55475, bez połączeń do normalnej bazy
i z guardem publisher HTTP. Nie zmieniono guardów, timeoutów lub CI.

Chrome: EN/PL, 1366/390 px. Normalny Vite/API 5173/8000 oraz osobny
production preview/API 4201/8031. Izolacja zawierała 53 **syntetyczne**
kapitalizacje z etykietą źródła testowego, nie pozyskane wyceny. Nie
podstawiano odpowiedzi API. Wrapper dodawał tylko CORS, a API izolacji
miało read-only i lease wyłącznie na izolacji. Pełne 25 tabel przed/po UI
jest identyczne. Obejrzano desktop EN i mobile PL; nie jest to audyt WCAG.

Potwierdzono dokładnie siedem kolumn, brak przycisków/panelu Szczegóły,
wyśrodkowanie, format i datę Market Cap, brak fikcyjnego linku, fokus
raportu, wewnętrzny scroll i brak overflow strony, wszystkie domeny,
zakresy i jeden nagłówek dnia. Wszystkie cztery kolumny finansowe porównano
z rzeczywistym API i ledgerami. Poprzednie testy panelu zastąpiono testami
linków i nowego kontraktu; regresje liczb i semantyki zachowano.

## 7. Ochrona E2A–E2E i normalnego PostgreSQL

Odczyty diagnostyczne wymuszały read-only. Potwierdzono
localhost:5432/macrolens, macrolens, OID **16384**, klaster
**7682090371041935398**. Pełne uporządkowane binary COPY wszystkich
**23 tabel / 2 963 374 rekordów** i obie reprezentacje katalogów schematu
są identyczne przed/po. Brak tabeli kapitalizacji i historii E2E.

Zachowane: 53 spółki, 55 aliasów, 37 okresów/eventów, 40 evidence,
66 confirmations, 6 dokumentów/12 miar E2B, 27 dokumentów/46 miar E2D.
INTC Q3/Q2: 0,60/−2,16 i 16,513/16,128 mld USD; AMZN: 1,89/5,75
i 201,944/200,606 mld; NVDA Q2/Q1: 2,46/2,39 i 96,221/81,615 mld.
Przyszła NVDA Q3 ma nadal Current null z poprzednim Q2. Forecast null.
Normalne Previous ma nadal cztery datowane wydarzenia, izolacja z E2E — 27.
23 historyczne raporty / 45 miar i null EPS CRWD po splitach zachowano
byte-identycznie; nadal nie aktywowano ich w codziennym PostgreSQL.

Nie wykonano normalnego DDL/importu/UPDATE/DELETE/rollbacku/restore,
nie zakładano normalnego lease. Nie zmieniono R1–R3, K2, Overview, makro,
źródeł lub harmonogramów. Normalny backend i Vite pozostają uruchomione.

## 8. Późniejsza aktywacja — niewykonana

Najpierw trzeba zatwierdzić konkretny dostęp do danych, zakres uprawnień,
metodologię whole issuer, daty pomiarów oraz rzeczywisty ledger. Dopiero
wtedy osobny runner/plan, stabilne snapshoty, uzgodnione okno, świeży
backup i pełny restore/test na PG17 oraz osobna zgoda na pełny hash.
Zakres techniczny: jedna nowa tabela, indeksy/constraints, funkcja i trzy
triggery, następnie wyłącznie zatwierdzone snapshoty. Bez aktywacji historii
E2E, feedu cenowego i zmian innych tabel. Propozycja lokalna ma
`ready_for_apply=false` i zero zatwierdzonych produkcyjnych snapshotów.

## 9. Pliki i Git

Zmodyfikowano osiem zastanych plików:

- app/earnings.py
- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/earningsTypes.ts
- frontend/src/calendar/earnings.css
- frontend/src/calendar/EarningsCalendar.test.tsx
- frontend/src/calendar/EarningsCoverage.test.tsx
- frontend/src/calendar/EarningsFinancials.test.tsx
- frontend/src/calendar/EarningsReports.test.tsx

Dodano osiem:

- app/earnings_market_cap.py
- app/database/earnings_market_cap_schema.sql
- config/earnings_market_cap_reviewed.json
- frontend/src/calendar/earningsMarketCap.ts
- frontend/src/calendar/EarningsMarketCap.test.tsx
- tests/test_earnings_market_cap.py
- tests/postgres_earnings_market_cap_validation.py
- docs/audits/equity-earnings-market-cap-2026-11-04.md

Manifest wejścia 34 zastanych plików i pełny diff zapisano w ignorowanym
data/raw/earnings-market-cap-2026-11-04. Pozostałe **26 zastanych plików
są byte-identyczne**, w tym 13 chronionych plików użytkownika, E2D Activation,
kod/ledger historii E2E oraz wcześniejsze audyty. Zależności, lockfile,
globalny CSS i CI nie były edytowane.

Końcowo **18 modified / 24 untracked**, indeks pusty, main i HEAD bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend i globalnego formatowania.
Własne API/preview/Chrome zakończono, izolowany lease zwolniono w finally,
losowe bazy usunięto. Własny kontener
`c6c1795b14930e926afffbc17f6a88811faa1badc7a86d20460ec4223833b5df`
i anonimowy wolumen usunięto po kontroli ID, nazwy, etykiety oraz braku baz
poza control/postgres/template. Normalnego kontenera i usług nie zatrzymywano.
Helpery, syntetyczne ledgery, logi, manifesty i screenshoty pozostają
ignorowane w data/raw. Nie dodano sekretów lub pełnych dokumentów do Git.


## 10. FMP — adapter i weryfikacja dostępu, 04.11.2026

Ten etap uzupełnia wcześniejszy cleanup UI. HEAD nadal
`94526c9cf0422dde041c69fd4fdec21549a8b39e`, main. Wejście:
18 modified / 24 untracked, pusty indeks. Manifest 42 zastanych plików
oraz pełny diff zapisano w ignorowanym
`data/raw/earnings-fmp-pilot-2026-11-04/`.

**Rzeczywisty pilot jest zablokowany: brak skonfigurowanego FMP_API_KEY
oraz potwierdzenia dostępu/przechowywania/wyświetlania dla tego konta.
Wykonano zero żądań do API danych FMP, zaimportowano zero rzeczywistych
snapshotów. Pokrycie rzeczywistymi kapitalizacjami nadal wynosi 0/53.**
Odczyt dokumentacji WWW nie jest testem dostępu do danych. Nie użyto
wartości demo ani dokumentacyjnych jako aktualnych kapitalizacji.

### Dostawca i warunki

Wybrano **FMP jako warunkowego pierwszego kandydata**, ze względu na
bezpośrednią datowaną kapitalizację, batch i osobny profil do kontroli
emitenta. Nie jest to potwierdzenie dostępności 53 symboli lub uprawnień
konkretnego konta. Adapter korzysta z Stable:

- `profile?symbol=...` — CIK, waluta notowań, ADR i dane identyfikacyjne;
- `market-capitalization?symbol=...` — datowana kapitalizacja;
- `market-capitalization-batch?symbols=...` — jawnie wybrany wariant batch.

Endpoint Market Cap potwierdza [oficjalna dokumentacja](https://site.financialmodelingprep.com/developer/docs/stable/market-cap),
profile/batch oraz uwierzytelnianie nagłówkiem `apikey` —
[katalog Stable](https://site.financialmodelingprep.com/developer/docs).
Brak daty w samym profilu nie jest zastępowany datą pobrania.

[Cennik FMP](https://site.financialmodelingprep.com/developer/docs/pricing)
podaje Basic 0 USD / 250 wywołań dziennie. Przy rozliczeniu rocznym
Starter/Premium/Ultimate pokazują odpowiednio 19/49/99 USD miesięcznie
oraz 300/750/3000 wywołań na minutę. Zakresy opisano jako US, UK/Canada
oraz global; Ultimate wymienia batch. Darmowy plan ma 500 MB na 30 dni.
Nie ustalono na tej podstawie, że wszystkie potrzebne endpointy i symbole
są dostępne za darmo. Wymagany plan i koszt dla konkretnego konta pozostają
do potwierdzenia; nie zalecono zakupu przed takim potwierdzeniem.

[Warunki FMP](https://site.financialmodelingprep.com/terms-of-service)
§2.2.1 ograniczają personal use do osoby i własnego użytku niekomercyjnego;
kopiowanie/pobieranie wymaga uprzedniej pisemnej zgody. §2.2.2 wymaga
odrębnej umowy dla wyświetlania wielu osobom. §2.8 dotyczy zabezpieczeń
miejsc przechowywania i zgłoszenia IP/domen. Nie znaleziono ogólnego
pozwolenia na bezterminową retencję; licencja zależy od subskrypcji.
Także cennik wymienia osobną Data Display and Licensing Agreement.
Nie potwierdzono prawa tego konta do lokalnego magazynu i prywatnego UI;
publiczna publikacja nie jest objęta przygotowanym adapterem.

Porównano jedną alternatywę: [Twelve Data Market Cap](https://twelvedata.com/docs/fundamentals/market-cap).
Bezpośredni `/market_cap` zawiera datę, wartość i walutę instrumentu;
dokumentacja podaje 5 kredytów na żądanie oraz Ultra dla osoby / Enterprise
dla biznesu lub wyżej. Nie daje to zweryfikowanej przewagi kosztowej
nad FMP dla tego zadania, ani dowodu pokrycia wszystkich 53 emitentów.
Pozostawiono jeden adapter FMP, bez dodatkowego dostawcy lub automatycznego
fallbacku. Wybór należy ponownie ocenić, jeśli rzeczywisty pilot FMP
wykaże braki CIK, daty, whole issuer lub nieodpowiednie uprawnienia.

### Wynik pilota i lista braków

Sprawdzono jedynie obecność właściwych zmiennych w środowisku i lokalnym
`.env`, bez wypisywania sekretów i bez odczytu innych projektów.
`check` zwrócił `key_configured=false`, a próba `collect` zakończyła się
`missing_fmp_api_key` przed HTTP. Nie utworzono pozornego klucza.

Pilot NVDA, AAPL, MSFT, AMZN, GOOGL, META, AMD, INTC, TSM, ASML:
**0/10 pozyskanych wartości**, brak rzeczywistych dat i walut pomiarów,
brak niezależnego porównania kwot. Powód wszystkich braków: nieuruchomiony
z powyższej przyczyny dostęp live, a nie potwierdzony brak pokrycia FMP.
Nie przystąpiono do pobierania pozostałych firm.

Pełna lista 53 braków: NVDA, AMZN, INTC, AAPL, MSFT, GOOGL, META, TSLA,
AVGO, AMD, ORCL, NFLX, MU, QCOM, TSM, ASML, ARM, AMAT, LRCX, KLAC, TXN,
ADBE, CRM, NOW, PLTR, CRWD, PANW, SNOW, IBM, CSCO, UBER, ABNB, SHOP, BKNG,
PYPL, COIN, JPM, BAC, GS, V, MA, WMT, COST, HD, LLY, UNH, JNJ, XOM, CVX,
CAT, BA, DIS, BRK-B.

Mapa 53 unikalnych CIK/symboli jest **kandydatem do sprawdzenia przez profil**.
GOOG/GOOGL korzystają z jednego emitenta i GOOGL; Berkshire z jednego
BRK-B. Profil musi potwierdzić CIK. Dla TSM/ASML i innych notowań
zagranicznych sam symbol, waluta lub `isAdr` nie dowodzą kapitalizacji
całego emitenta: wymagany jest jawny dowód wszystkich klas akcji.

### Adapter i granice importu

`app/earnings_market_cap_fmp.py` jest ręcznym CLI, poza Calendar/startupem.
Kwoty JSON są parsowane jako Decimal i przechowywane jako tekst dziesiętny.
Brak float, obliczeń cena×akcje, sumowania pełnych wycen klas, FX i ADR.
Kandydat zachowuje company_id/CIK, symbol, wartość/walutę, datę pomiaru,
czas pobrania, profil, metodę, źródło, status weryfikacji oraz receipt:
endpoint, symbole, status HTTP, SHA odpowiedzi i dostępny bezpieczny
x-request-id. SHA metadanych nie jest wersją dostawcy. Nie wymyślano
czasu pomiaru, kiedy API udostępnia jedynie datę.

Przed siecią wymagane są klucz i aktualne, jawne potwierdzenie dostępu,
lokalnego przechowywania oraz prywatnego wyświetlania. Szablon ma wszystkie
zgody false i puste referencje. Każdy emitent wymaga potwierdzenia whole
issuer, a kilka spółek — co najmniej trzy niezależne kontrole wartości,
daty i waluty. Różnica wymaga wyjaśnienia; adapter nie poprawia kwoty FMP.
Przegląd jest związany pełnym SHA kandydatów. Fixture nie przechodzi
produkcyjnego `prepare` ani importu.

Batch pilota wymaga 11 requestów, all53 — 54. Tryb pojedynczy wymaga
20/106, wybierany jest jawnie. Domyślny budżet wynosi 12, maksymalny 108;
tempo to co najmniej sekunda odstępu, timeout 20 s. 401/403/429/5xx,
redirect, zła odpowiedź i przekroczenie budżetu przerywają bez retry
lub zmiany endpointu. Klucz jest tylko w nagłówku, bez URL, logów i UI.

Wykorzystano istniejący store i walidatory, bez nowej tabeli lub DDL.
Cała partia jest walidowana przed zapisem, append-only i advisory lock
pozostają. Ten sam pomiar z nowym czasem pobrania nie tworzy kolejnego
rekordu ani timestampu; sprzeczna treść tej samej wersji jest odrzucana.
Receipt pierwszego zapisu pozostaje zachowany. Import działa wyłącznie
we własnej bazie prefiksu `macrolens_earnings_e2b_e2c_e2d_e2e_cap_`.

Obecny store/UI jest USD-only. Kandydaty TWD/EUR zachowują walutę w pliku,
ale nie trafiają do pola `market_cap_usd`: dostają jawny powód braku.
Nie podstawiono USD i nie dodano przeliczenia. To może ograniczyć
rzeczywiste pokrycie po pilocie; dziś nie wiadomo, których spółek dotyczy.

Polityka świeżości: maksymalnie **7 dni kalendarzowych** od `as_of` UTC.
Starszy/future snapshot nie daje bieżącej kwoty; API zwraca null, a tabela
`—`. Wygaśnięcie potwierdzonego dostępu FMP też ukrywa kwotę. Historia
pozostaje w store/provenance. Nie dodano sieci do GET ani schedulera.

### Jak uruchomić rzeczywisty pilot później

1. Uzyskać własny klucz przez [konto FMP](https://site.financialmodelingprep.com/developer/docs/pricing).
   W lokalnym serwerowym `.env` ustawić `FMP_API_KEY`, bez prefiksu VITE.
   Nie przesyłać klucza w rozmowie. Potwierdzić dostęp do profile i
   datowanego cap/batch oraz prawa lokalnego przechowywania i UI.
2. Skopiować `config/earnings_market_cap_fmp_review.example.json` do
   ignorowanego `data/raw/.../review.json`. Wypełnić rzeczywistą referencję
   uprawnień, zakres, verified_on i valid_until. Nie ustawiać true
   wyłącznie z racji posiadania klucza; brakujące zgody zatrzymują kolekcję.
3. Uruchomić z katalogu projektu (poniższe polecenia nie zostały wykonane
   z rzeczywistym kluczem):

```powershell
.venv/Scripts/python.exe -m app.earnings_market_cap_fmp check
.venv/Scripts/python.exe -m app.earnings_market_cap_fmp collect --scope pilot --mode batch --request-budget 12 --review data/raw/earnings-fmp-pilot-2026-11-04/review.json --output data/raw/earnings-fmp-pilot-2026-11-04/pilot.json
```

4. Sprawdzić faktyczne CIK, notowania/ADR, waluty, daty, wszystkie klasy,
   świeżość oraz niezależne źródła dla co najmniej trzech emitentów.
   W review zapisać dowody, datę przeglądu i `candidate_sha256`, obliczone
   funkcją `app.earnings_market_cap_fmp.digest` na odczytanym JSON pilota
   (kanoniczny hash metadanych, nie zwykły hash bajtów pliku).
   `independent_check` zawiera source_url, as_of, market_cap_value,
   currency oraz difference_explanation, jeżeli wartości się różnią.
5. `prepare --input .../pilot.json --review .../review.json --output .../reviewed.json`
   od tego samego modułu tworzy partię i listę braków. Po przygotowaniu
   własnej izolowanej bazy z istniejącym schematem cap, ustawieniu jej
   DB_* i wyłączeniu dotenv: `import-isolated --input .../reviewed.json`.
   Import nie inicjalizuje schematu i odrzuca normalną bazę.
6. Dopiero po rzeczywistym sukcesie pilota zbierać `--scope all` z
   `--mode batch --request-budget 54`, ponowić przegląd nowego SHA i import.
   Jeżeli batch nie jest dozwolony, nie ponawiać automatycznie: osobno
   wybrać dozwolony single i jego budżet 106.

Ręczne odświeżenie może być wykonywane raz dziennie po aktualizacji danych
przez dostawcę: collect → przegląd nowego pomiaru/ważności uprawnień →
prepare → import w izolacji. Ten sam pomiar jest idempotentny. Żaden krok
nie uruchamia automatycznej aktywacji w normalnej bazie. Nie trzeba ponownie
sprawdzać niezmienionych praw codziennie, ale ich termin musi nadal obowiązywać.

### Nowe wyniki testów

| Kontrola tego etapu | Wynik |
|---|---|
| Pełny backend offline | **1424 passed**, pytest 61,76 s |
| Pełny frontend offline, Node 22.23.4 | **691 passed / 33 pliki**, 32,46 s |
| TypeScript noEmit | passed |
| Production build | passed, Vite 4,08 s, największy chunk 407,04 kB |
| Dotychczasowe PostgreSQL 17 | **14/14 passed** |
| Nowa integracja FMP → SQL → API | passed, wyłącznie odpowiedzi syntetyczne |
| Normalny Chrome | **709 kontroli / 28 odpowiedzi API 200**, dodatkowo 37 GET 200 |
| Izolowany Chrome, pusty store cap | **709 kontroli / 26 odpowiedzi API 200**, dodatkowo 37 GET 200 |
| JS / console.error / HTTP 503 / publisher HTTP | zero |
| Rzeczywisty FMP pilot / import | **zablokowany / 0 snapshotów** |

Parser i integracja badają 401/403/429/5xx, redirect, timeout, błędny JSON,
limity, brak CIK, złą tożsamość, duplikaty/klasy, datę, Decimal i waluty,
brak dowodów, zmieniony hash, niezależne porównanie i różnice, stale oraz
wygaśnięcie dostępu. Własny PG17 na loopback 55477 potwierdził
11/54 mock-requestów i 10/53 **syntetyczne** rekordy, idempotencję przy
ponownym pobraniu, append-only, odrzucenie partii i rollback DDL+seeda.
Wszystkie 24 wcześniejsze tabele izolacji zachowano. To nie wynik live.

Chrome używał prawdziwych API/SQL: normalny Vite/API 5173/8000 oraz własny
production preview/API 4203/8033. W tym przebiegu nie prezentowano
syntetycznych wycen w UI; izolowany store cap był pusty. EN/PL,
1366/390 px, wszystkie cztery metryki porównane z API/ledgerami, zakresy,
domeny, oficjalne linki i fokus, siedem kolumn, scroll i brak overflow
przeszły. Obejrzano desktop EN i mobile PL. Kwoty/datę prawdziwego FMP
pozostawiono jako niewykonaną walidację zależną od dostępu; format kwot
sprawdzają testy offline. Nie deklaruje się pełnego audytu WCAG.

### Normalna baza, ochrona prac i zakończenie

Read-only potwierdziło ten sam target localhost:5432/macrolens, rolę
macrolens, OID 16384 i klaster 7682090371041935398. Przed/po porównano
pełne binary COPY wszystkich 23 tabel i obie reprezentacje katalogów.
**Wszystkie 10 tabel Earnings i katalogi są identyczne.** Zachowano
53/55 spółek/aliasów, 37/37 okresów/eventów, 40 evidence, 66 confirmations,
6/12 E2B i 27/46 E2D. Nie ma store cap ani historii E2E w normalnej bazie.
Previous nadal ma 4 datowane eventy, a w izolacji z historią — 27.

Przy działającej aplikacji normalna baza wzrosła z 2 963 449 do
2 963 450 rekordów. Zmieniły się wyłącznie overview_refresh_state i
source_check_runs; pozostałe 21 tabel są byte-identyczne. Nie przypisuje
się zwykłych odświeżeń makro aktywacji; żadnej aktywacji nie wykonano.
Nie było normalnego DDL/importu/UPDATE/DELETE/restore/rollbacku ani lease.
API 8000 i Vite 5173 pozostawiono działające.

Zmienione w tym etapie: `.env.example`, `app/earnings_market_cap.py`,
`frontend/src/calendar/earningsTypes.ts`,
`frontend/src/calendar/EarningsMarketCap.test.tsx`,
`tests/postgres_earnings_market_cap_validation.py` oraz ten raport.
Nowe: `app/earnings_market_cap_fmp.py`,
`config/earnings_market_cap_fmp_symbols.json`,
`config/earnings_market_cap_fmp_review.example.json`,
`tests/test_earnings_market_cap_fmp.py`,
`tests/postgres_earnings_market_cap_fmp_validation.py`.

Spośród 42 zastanych zmienionych/nieśledzonych plików zmieniono tylko pięć
właściwych powyższych; pozostałe **37 zachowano byte-identycznie**, w tym
wszystkie 13 chronionych plików użytkownika, wcześniejsze audyty,
aktywator E2D i kod/ledger historii E2E. Nie zmieniono zależności, lockfile,
CI, globalnego CSS, układu tabeli, Actual/Previous, K2/Overview/R1–R3.
Końcowy Git: **19 modified / 29 untracked**, pusty indeks, main i HEAD
bez zmian. Bez stagingu, commita i pusha.

Do normalnej aktywacji nadal potrzebne są rzeczywisty udany pilot,
zatwierdzone prawa i zweryfikowany ledger, następnie osobny runner,
świeży stabilny odczyt celu, backup z pełnym restore/testem na PG17,
kompletny plan i osobna zgoda na jego pełny hash. Ten etap nie tworzy
tokenu apply ani zgody na import Market Cap lub historii E2E.


Własne API zakończyło się poprawnie, zwolniło lease i usunęło losową bazę;
pełne 25 tabel izolacji przed/po Chrome są identyczne. Własne preview i
headless Chrome zakończono. Kontrola sprzątania najpierw zatrzymała się na
różnicy reprezentacji czasu procesu w JSON; po porównaniu ścieżki i
identycznego czasu Unix w milisekundach zakończono wyłącznie własne PID.
Nie pominięto sprawdzania tożsamości procesu.

Po kontroli pełnego ID
`81bfe2d4be11ebe557cef158f933b1f8951ef3fd7fb5c141ee4007baa3cd371c`,
etykiety `earnings-fmp-pilot-2026-11-04` i braku baz poza
control/postgres/template usunięto wyłącznie własny kontener PG17 i jego
anonimowy wolumen. Normalny PostgreSQL, backend i Vite pozostały poza
sprzątaniem. Logi, zrzuty, helpery i manifesty są ignorowane w data/raw.
Nie dodano sekretów, raw odpowiedzi dostawcy ani pełnych dokumentów do Git.


## 11. Darmowy lokalny cache: TGMCharts i DeltaScreener — 04.11.2026

Zlecenie wymagało 0 zł, bez rejestracji, kluczy i kontaktowania dostawców.
Te warunki zachowano. HEAD/main bez zmian. Wejście: **19 modified /
29 untracked**, indeks pusty. SHA wszystkich 48 zastanych plików i pełny
diff zapisano w ignorowanym `data/raw/earnings-public-cap-2026-11-04/`.

### Rzeczywisty odczyt, dostęp i pochodzenie dat

[TGMCharts Summary](https://tgmcharts.com/developers/docs/summary)
odczytano bez konta i nagłówków uwierzytelniających. Wszystkie **53 symbole
zwróciły HTTP 200** i rzeczywiste dodatnie kapitalizacje. Pilot AAPL, NVDA,
MSFT, AMZN, GOOGL, AMD, TSM, ASML także miał 8/8 HTTP 200. Nie użyto
przykładowych liczb. Przechowano lokalne odpowiedzi i czasy pobrania.

[API terms §19](https://tgmcharts.com/terms) dopuszczają użycie odpowiedzi
we własnej aplikacji z nazwą TGMCharts i linkiem. Zabraniają samodzielnego
feedu/redystrybucji hurtowej i obchodzenia ograniczeń.
[Dokumentacja limitów](https://tgmcharts.com/developers/docs/authentication-and-limits)
podaje darmowe 500 jednostek dziennie także bez klucza oraz cache odpowiedzi.
Użyto sekwencyjnego odczytu 53 symboli z odstępem co najmniej 1,1 s,
bez równoległego bombardowania i bez prób logowania lub zakładania kont.

Istotne ograniczenie odpowiedzi: `price.lastCloseDate=2026-11-03` datuje
oficjalne zamknięcie, ale obok jest inna `latestPrice` ze źródłem
`fmp-delayed`. Nie przypisano odmiennej wycenie automatycznie daty zamknięcia.
TGM przyjęto jako EOD tylko dla **ADBE i CSCO**, gdzie latestPrice i
lastClose są identyczne, na podstawie opisanej semantyki EOD summary.
Nie deklaruje się intraday/live ani dokładnego czasu pomiaru.
Pozostałe niejednoznaczne odpowiedzi nie zostały arbitralnie przeliczone
na kurs zamknięcia; ich odrzucenie ma jawny powód.

**DeltaScreener było potrzebne.** [Strona danych](https://deltascreener.com/data)
udostępnia datowany CSV za darmo, z atrybucją i linkiem, bez konta i klucza.
Rzeczywiście pobrano `us-stock-universe-latest.csv` i
`us-stock-universe-2026-11-03.csv`: 1 610 141 B, identyczne bajty,
4 894 wiersze. Wyboru dokonano z pliku datowanego, nie na podstawie daty
pobrania. Dokumentacja nazywa `mktCap` kapitalizacją spółki w USD i opisuje
cenę jako ostatnie zamknięcie przed datą pliku. **03.11 jest datą miesięcznego
snapshotu, a nie wymyślonym dokładnym czasem notowania.** Zachowuje to
`measurement_basis` w API/cache. W tabeli data jest widoczna przy kwocie.
Nie wprowadzono dłuższego limitu dla danych miesięcznych: po 7 dniach
snapshot znika z bieżącej prezentacji, nawet jeżeli kolejny miesięczny CSV
nie został jeszcze opublikowany.

### Tożsamość, klasy i wynik pokrycia

Nowy jawnie przejrzany plik `config/earnings_market_cap_public_identity.json`
wiąże dokładne nazwy dostawców, symbole i giełdę CSV z 53 istniejącymi CIK.
Dostawcy w tych odpowiedziach nie dostarczają CIK; nie twierdzi się inaczej.
To dopasowanie do dotychczasowego rejestru SEC, nie nowy rejestr emitentów.
Zmiana nazwy/symbolu/giełdy lub niejednoznaczna klasa wymaga ponownego
przeglądu i powoduje brak wartości. Nie dopasowuje się automatycznie fuzzy.

Alphabet: jeden CIK, wybrano GOOGL. CSV GOOG/GOOGL zawiera alternatywne
pełne wyceny tej samej spółki zależne od notowania; nie sumowano ich.
Berkshire: jeden CIK, kandydat TGM `BRK-B`, CSV `BRK.B`; wiersz BRK.A
pozostaje alternatywą, bez osobnego emitenta lub sumowania wycen.
Przyjęto bezpośrednią kapitalizację spółki opisaną przez dostawcę, bez
samodzielnej rekonstrukcji liczby wszystkich akcji z implied shares.

**49/53 dostępnych kapitalizacji**, w tym **2 TGMCharts + 47 DeltaScreener**.
Cztery braki:

- TSM i ASML: wartości USD istnieją, ale nie potwierdzono zakresu całego
  emitenta względem ADR / New York Registry Shares; pozostawiono `—`.
- ARM: TGM ma wartość i flagę ADR, zakres całego emitenta niepotwierdzony;
  dodatkowo brak w pobranym CSV.
- SHOP: CSV opisuje Class A Subordinate Voting Shares; zakres pozostałych
  klas niepotwierdzony, a TGM ma niejednoznaczną datę kapitalizacji.

Nie przeliczano TWD/EUR, nie mnożono ADR i nie tworzono zer. Wszystkie
przyjęte kwoty są źródłowymi USD i mają datę **2026-11-03**. Pełny wybór:

| Ticker | Market Cap, dokładne USD | Źródło | Data snapshotu / EOD |
|---|---:|---|---|
| NVDA | 4869646000000 | DeltaScreener | 2026-11-03 |
| AMZN | 2649438869000 | DeltaScreener | 2026-11-03 |
| INTC | 317008016700 | DeltaScreener | 2026-11-03 |
| AAPL | 4937502977600 | DeltaScreener | 2026-11-03 |
| MSFT | 3765969472800 | DeltaScreener | 2026-11-03 |
| GOOGL | 3401168208750 | DeltaScreener | 2026-11-03 |
| META | 1343585383100 | DeltaScreener | 2026-11-03 |
| TSLA | 1596191490384 | DeltaScreener | 2026-11-03 |
| AVGO | 1538206751399 | DeltaScreener | 2026-11-03 |
| AMD | 762104648607 | DeltaScreener | 2026-11-03 |
| ORCL | 360127434000 | DeltaScreener | 2026-11-03 |
| NFLX | 259579999402 | DeltaScreener | 2026-11-03 |
| MU | 943140397800 | DeltaScreener | 2026-11-03 |
| QCOM | 173075427295 | DeltaScreener | 2026-11-03 |
| TSM | — | niepotwierdzony zakres / brak | — |
| ASML | — | niepotwierdzony zakres / brak | — |
| ARM | — | niepotwierdzony zakres / brak | — |
| AMAT | 297226050327 | DeltaScreener | 2026-11-03 |
| LRCX | 284774127817 | DeltaScreener | 2026-11-03 |
| KLAC | 199496578423 | DeltaScreener | 2026-11-03 |
| TXN | 275976815400 | DeltaScreener | 2026-11-03 |
| ADBE | 95797688000 | TGMCharts | 2026-11-03 |
| CRM | 186146140000 | DeltaScreener | 2026-11-03 |
| NOW | 110029581170 | DeltaScreener | 2026-11-03 |
| PLTR | 410308621400 | DeltaScreener | 2026-11-03 |
| CRWD | 247597684144 | DeltaScreener | 2026-11-03 |
| PANW | 287862811353 | DeltaScreener | 2026-11-03 |
| SNOW | 102551904000 | DeltaScreener | 2026-11-03 |
| IBM | 238652454471 | DeltaScreener | 2026-11-03 |
| CSCO | 405968170313 | TGMCharts | 2026-11-03 |
| UBER | 136259177600 | DeltaScreener | 2026-11-03 |
| ABNB | 102458220271 | DeltaScreener | 2026-11-03 |
| SHOP | — | niepotwierdzony zakres / brak | — |
| BKNG | 115524828750 | DeltaScreener | 2026-11-03 |
| PYPL | 48826094756 | DeltaScreener | 2026-11-03 |
| COIN | 36492342868 | DeltaScreener | 2026-11-03 |
| JPM | 905326350200 | DeltaScreener | 2026-11-03 |
| BAC | 343158239000 | DeltaScreener | 2026-11-03 |
| GS | 261681567798 | DeltaScreener | 2026-11-03 |
| V | 795280716678 | DeltaScreener | 2026-11-03 |
| MA | 576801040004 | DeltaScreener | 2026-11-03 |
| WMT | 1016167127302 | DeltaScreener | 2026-11-03 |
| COST | 461098244102 | DeltaScreener | 2026-11-03 |
| HD | 340361815910 | DeltaScreener | 2026-11-03 |
| LLY | 1327720485388 | DeltaScreener | 2026-11-03 |
| UNH | 359432941800 | DeltaScreener | 2026-11-03 |
| JNJ | 651321865569 | DeltaScreener | 2026-11-03 |
| XOM | 738787248624 | DeltaScreener | 2026-11-03 |
| CVX | 450021132900 | DeltaScreener | 2026-11-03 |
| CAT | 282065773500 | DeltaScreener | 2026-11-03 |
| BA | 138995719476 | DeltaScreener | 2026-11-03 |
| DIS | 195305905900 | DeltaScreener | 2026-11-03 |
| BRK-B | 1041113327811.9 | DeltaScreener | 2026-11-03 |

### Cache i działający normalny Calendar

`app/earnings_market_cap_cache.py` rozszerza istniejący czytnik o opcjonalny
fallback. **Aktualny zweryfikowany SQL snapshot ma pierwszeństwo**, nawet
jeśli cache jest nowszy. Dopiero brak aktualnego snapshotu pozwala wybrać
jedną wartość z cache. Nie ma dwóch sprzecznych kwot. Możliwość późniejszej
aktywacji PostgreSQL pozostaje; nie powstał drugi magazyn SQL.

Ręczny skrypt `app/earnings_market_cap_public.py` działa bez połączenia do
bazy. Odczytuje wyłącznie zatwierdzone publiczne ścieżki HTTPS, parsuje
Decimal, waliduje całą partię i atomowo zastępuje lokalny JSON. Cache
`data/raw/earnings-market-cap-cache/current.json` jest ignorowany przez Git.
Zawiera tylko wybrane wartości monitorowanych emitentów, metadane źródła,
CIK/company_id, symbol/nazwę/giełdę, USD, datę, czas pobrania, podstawę
pomiaru i SHA rzeczywiście pobranych bajtów. Pełny publiczny CSV i odpowiedzi
są wyłącznie lokalnymi artefaktami. Nie uruchomiono usługi całego zbioru.

Czytnik GET nie importuje klienta HTTP, nie pobiera danych i nie zapisuje
pliku lub SQL. Brak, niepoprawny/ucięty/za duży cache, duplikaty, błędne
identity, daty lub stare wartości dają brak danych, bez HTTP 503. Zegar UTC
i 7 dni są wspólne z istniejącą polityką. Brak nowego schedulera, feedu,
kluczy lub sekretów. FMP i jego konfigurację zachowano bez zmian i bez użycia.

Ręczne odświeżenie z katalogu repozytorium:

```powershell
.venv/Scripts/python.exe -m app.earnings_market_cap_public refresh
```

Polecenie odświeża all53, używa TGM w pierwszej kolejności i datowanego CSV
dla braków. Odpowiedzi są cache'owane na co najmniej godzinę. Budżet to
maksymalnie 120 requestów, 1,1 s między requestami. Dla 429/5xx maksymalnie
dwie ponowne próby z backoff i respektowaniem Retry-After; długie oczekiwanie
powoduje zakończenie próby zamiast obchodzenia limitu. 401/403, nieznany
symbol, redirect i niezatwierdzony endpoint nie mają retry/obejścia.
Brak zweryfikowanych danych nie nadpisuje istniejącego cache pustą partią.
`--scope pilot` służy do ograniczonego odczytu ośmiu firm i tworzy cache
tego zakresu; do zwykłego pełnego cache używa się domyślnego all.

Uruchomiono rzeczywiste CLI: **49 wartości / 4 braki**. Dzięki reuse
zapisanych odpowiedzi wymagało jednego nowego GET strony danych, bez
ponownego pobierania 53 endpointów w ciągu godziny. Nie zapisano danych
produkcyjnych do konfiguracji Git.

Normalny backend wymagał przeładowania: jego zidentyfikowany worker nie
udostępniał jeszcze nowego fallbacku. Potwierdzono port/PID, polecenie i
rodzica, zakończono wyłącznie normalny reloader/worker, następnie uruchomiono
API z aktualnego projektu, na tym samym 127.0.0.1:8000, z logiem w data/raw.
Vite 5173 pozostał w jednej istniejącej instancji. Oba działają.

**Kwoty są widoczne w normalnym `http://localhost:5173/#/calendar`.**
Siedem kolumn pozostaje; Market Cap pokazuje kwotę w mld USD, małą datę
oraz dyskretny link TGMCharts/DeltaScreener. Bez nowej stopki, panelu lub
checkboxów. Dla 34 datowanych wierszy szerokiego zakresu 31 ma wycenę,
a trzy nie: TSM, ASML i ARM. SHOP nie ma datowanego wydarzenia w tym zakresie.
49/53 oznacza pokrycie rejestru, nie liczbę wierszy kalendarza. Current /
Previous / Forecast, źródła raportów, zakresy i filtry nie zmieniają semantyki.

### Walidacja i ochrona bazy

| Kontrola nowego etapu | Wynik |
|---|---|
| Pełny backend offline, ostatni przebieg | **1452 passed**, pytest 58,13 s |
| Pełny frontend offline | **693 passed / 33 pliki**, 31,88 s |
| TypeScript noEmit | passed |
| Production build | passed, Vite 4,11 s; największy chunk 407,04 kB |
| Dotychczasowe PostgreSQL | **15/15 passed**, w tym FMP i Market Cap |
| Nowy SQL/API lokalnego cache | passed; wszystkie 24 stare tabele izolacji identyczne |
| Normalny Chrome EN/PL, 1366/390 px | **957 kontroli / 28 API 200**, dodatkowo 37 GET 200 |
| JS / console.error / HTTP 503 / publisher HTTP w Calendar | zero |
| Normalne 23 tabele i obie reprezentacje katalogów | **identyczne przed/po** |

Testy obejmują precyzję, daty pomiaru vs retrieval, USD, ADR/klasy,
GOOG/GOOGL i Berkshire, duplikaty również stale, świeżość, atomową publikację,
uszkodzony lub brakujący cache, priorytet SQL, błędy 401/403/429/5xx,
backoff, budżet i brak sieci w GET. Jednostkowe i SQL przykłady są jawnie
syntetyczne, odseparowane od lokalnego cache użytkownika. Do conftest i
istniejącego guarda SQL dodano wyłącznie izolację lokalnego pliku cache;
nie osłabiono żadnej blokady HTTP/DB. Nowy test SQL sprawdza realne API bez
nowej tabeli cap; all24 pozostaje identyczne. Regresje używały własnego
PG17, loopback 55479, bez połączenia do normalnej bazy.

Pierwsza próba nowego SQL zatrzymała się na ścieżce importu, druga na
niepoprawnej nazwie punktu podmiany połączenia. Poprawiono harness, bez
osłabienia asercji, i wykonano test ponownie z kodem 0. Dodatkowy test
cache godzinowego ujawnił różne zegary testu i klienta po przekroczeniu
pełnej godziny; ujednolicono zegar, a cały backend wykonano ponownie.
Nieudanych prób nie zaliczono jako sukcesów.

Chrome używał normalnego Vite/API i prawdziwego cache pobranego ze źródeł,
bez podstawiania odpowiedzi i syntetycznych wycen w UI. Wszystkie kwoty
API sprawdzono z cache, a cztery kolumny finansowe z API i ledgerem E2D.
Przeszły źródło/data przy rzeczywistych kwotach, brak wartości, aliasy,
oficjalne linki raportów i fokus, domeny i zakresy, jeden nagłówek dnia,
wewnętrzny scroll mobile i brak overflow strony. Obejrzano desktop EN i
mobile PL. Brak pełnej deklaracji WCAG. Brak dla ADR jest zamierzony,
nie stanowi potwierdzenia danych całego emitenta.

Normalny target sprawdzono read-only: localhost:5432/macrolens, rola
macrolens, OID **16384**, klaster **7682090371041935398**, PG17.
Pełne uporządkowane binary COPY: **23 tabele / 2 963 450 rekordów**,
wszystkie hashe/liczniki i obie reprezentacje katalogów są identyczne.
Zachowano 53 companies, 55 aliases, 37 periods i events, 40 evidence,
66 confirmations, sześć dokumentów/12 miar E2B oraz 27 dokumentów/46 miar
E2D. Nie ma tabeli cap i historii E2E. Nie wykonano DDL, importu, UPDATE,
DELETE, restore, rollbacku ani normalnego lease. Odczyt cache działa
całkowicie poza zapisem normalnego PostgreSQL. R1–R3, K2 i Overview bez zmian.

### Pliki, Git i sprzątanie

Nowe pliki:

- app/earnings_market_cap_cache.py
- app/earnings_market_cap_public.py
- config/earnings_market_cap_public_identity.json
- tests/test_earnings_market_cap_public.py
- tests/postgres_earnings_public_cap_validation.py

Zmiany tego etapu:

- app/earnings_market_cap.py — fallback po istniejącym SQL readerze;
- frontend/src/calendar/earningsTypes.ts — opcjonalna nazwa źródła;
- frontend/src/calendar/earningsMarketCap.ts — bezpieczny link atrybucji;
- frontend/src/calendar/EarningsCalendar.tsx — link przy kwocie;
- frontend/src/calendar/EarningsMarketCap.test.tsx — atrybucja i 7 kolumn;
- tests/conftest.py i tests/postgres_http_guard.py — izolacja lokalnego cache;
- ten raport.

Spośród 48 zastanych zmienionych/nieśledzonych plików zmieniono tylko sześć
właściwych plików powyżej; **pozostałe 42 zachowano byte-identycznie**, w tym
13 chronionych plików użytkownika, wszystkie pliki FMP, .env.example,
aktywator E2D i kod/ledger historii E2E. Nie zmieniono zależności, lockfile,
CI, globalnego CSS, innych audytów lub modelu SQL.

Końcowo **21 modified / 34 untracked**, indeks pusty, main i HEAD bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend i globalnego formatowania.
Własny Chrome zakończono po kontroli ścieżki i czasu procesu. Po kontroli
pełnego ID `b7dd57ff2812ea3d3c53bba4d982bfe5fbe985a3d2862a6a868bd8153a82fe89`,
etykiety `earnings-public-cap-2026-11-04` i braku pozostawionych baz
usunięto wyłącznie własny kontener PG17 i jego anonimowy wolumen.
Normalny PostgreSQL, API 8000 i Vite 5173 pozostawiono działające.

Cache jest celowo pozostawiony jako lokalne źródło normalnej aplikacji.
Usunięcie pliku cache wyłącza fallback; nie wymaga rollbacku bazy.
Późniejsza aktywacja store PostgreSQL nadal wymaga osobnego planu i zgody;
ten etap jej nie rozpoczyna. Nie wykonano E2E Activation ani kolejnego feedu.
