# MacroLens — E2C: pokrycie kalendarza wyników spółek

Weryfikacja **03.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`,
`main`, HEAD **4f4e12ce138be210bedbb13924cf0c4e52d65411**.

**Nowy widok działa lokalnie: nie pokazuje undated ani przyszłych Q4 bez
daty. Rozszerzone dane sprawdzono wyłącznie w izolacji: 53 emitentów,
27 nowych datowanych wydarzeń dla 27 nowych firm.** Normalna baza ma
nadal 3 firmy i działające E2B; nowych firm/terminów tam nie importowano.
Sekcje 1–12 opisują implementację bez stagingu, commita i pusha; osobne
zamknięcie na późniejsze zlecenie użytkownika opisuje sekcja 13.
Nie wdrożono feedu SEC/IR lub konsensusu.

## 1. Stan wejściowy i ochrona prac

Potwierdzono HEAD, main, pusty indeks, **9 modified / 9 untracked**.
Zastany zakres zawierał 13 wcześniejszych plików użytkownika oraz pięć
plików przygotowania E2B Activation. Przeczytano E1, E2A, E2B i raport
aktywacji. Pełny zastany diff i SHA-256 wszystkich **18 plików** zapisano
przed zmianami w ignorowanym `data/raw/earnings-e2c-2026-11-03/`.

Z 18 zastanych plików **17 pozostało byte-identycznych**. Wyjątek:
CalendarPage.tsx dostał wyłącznie `hidden={domain==='earnings'}` na stopce
źródeł makro, konieczne do wymaganego rozdzielenia atrybucji. Zastany
Previous week, renderer makro, hook, filtry i test CalendarPage zachowano.
Nie formatowano globalnie, nie resetowano ani nie usuwano pracy użytkownika.
Raporty E1/E2A/E2B/Activation i pozostałe cztery audyty są bez edycji.

## 2. Wyłącznie datowane wydarzenia i wspólny nagłówek

EarningsCalendar renderuje tylko datowane `events` należące do wybranego
zakresu. Dodatkowa kontrola daty w UI odrzuca także błędnie umieszczony
niedatowany/out-of-range wpis w events. `undated` nie jest renderowane:
brak osobnej tabeli, rozwijanej sekcji lub placeholderów na dole.
API zachowuje undated dla zgodności i audytu; żadne rekordy nie zostały
usunięte. Rejestr firmy nie generuje kolejnego kwartalnego eventu.

Pusty zakres: **„Brak publikacji wyników z potwierdzoną datą w wybranym
zakresie.”** W normalnej bazie 26.10–01.11 pokazuje dokładnie INTC i AMZN
z 29.10; 02–08.11 jest pusty, mimo trzech zachowanych unknown w SQL.
W izolacji poprzedni tydzień zawiera również cztery nowe firmy z 28.10.

Kluczem grupy jest wyświetlana data kalendarzowa, bez dwóch nagłówków
`pl:` i `source:` dla 29.10. Nie powstaje polska północ lub nowy timestamp.
Wiersz bez ustalonego polskiego dnia zachowuje oznaczenie **„Data emitenta;
dzień i godzina wyników w PL nieustalone”**. Taki sam napis daty w nagłówku
nie oznacza, że przeliczono date-only na Europe/Warsaw. Szczegóły zachowują
źródłową datę, strefę, precision i historię.

AMZN: **„Wyniki: godzina nieznana”**, osobno **„Konferencja: 22:00”**.
Call jest teraz także drugorzędną informacją w wierszu pozostałych firm.
NVDA zachowuje **ok. 22:20 / call 23:00**, INTC **21:00+ / call 22:00**.
Godzina call nie zastępuje release. Orientacyjne godziny/AMC/BMO nie
gwarantują rzeczywistej chwili pierwszej dostępności wyników.

Earnings ma własną atrybucję dowodów emitentów/IR w szczegółach. Stopka
FRED/ALFRED jest ukryta tylko w domenie Earnings; pozostaje źródłem makro
w Makro/Wszystkie. Nie sugeruje się, że FRED dostarczył EPS lub revenue.

## 3. Rejestr i tożsamość

`config/earnings_companies_reviewed.json` zawiera **53 emitentów / 55
aliasów** z całej listy użytkownika. Jest to ręczny rejestr obserwowanych
firm, nie deklaracja działającego monitoringu sieciowego. Osobny plik
`config/earnings_dates_reviewed.json` zawiera tylko **27 konkretnych
datowanych rekordów**. W SQL po izolowanym imporcie firmy bez dat nie mają
nowych periods/events. Odczyt firm nadal pochodzi z SQL, bez checkboxów
i bez ograniczenia czytnika do trzech CIK.

Tożsamości oparto na aktualnym oficjalnym
[pliku SEC ticker/CIK/exchange](https://www.sec.gov/files/company_tickers_exchange.json).
TSM odczytano również w jego dalszej części, nie zgadywano CIK.
COIN zweryfikowano przez
[własny 10-Q Coinbase](https://www.sec.gov/Archives/edgar/data/1679788/000167978826000122/coin-20260930.htm).
Nazwy są nazwami emitentów skonformowanymi przez SEC, nie osobną opinią
prawną o pełnej strukturze grup. Nie obchodzono niedostępnego submissions
API SEC ani ograniczeń dostępu. Nie tworzono HTTP receipts/fetched_at,
first_seen, accession lub RAW hash na podstawie linku.

GOOG i GOOGL mają **CIK 0001652044**, jeden company_id i jeden event na
okres; klasy akcji potwierdza
[10-Q Alphabet](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000048/goog-20260331.htm).
BRK-B i BRK.B są aliasami jednego emitenta **0001067983**, bez nowych
kwartalnych placeholderów. Identyfikatory UUID nadal pochodzą od CIK
i okresu, nie tickera. Odczyt API po GOOG/GOOGL zwraca jeden event.

Wykryto rzeczywistą niespójność referencji: plik SEC nadal przypisuje WMT
do NYSE, natomiast [aktualne IR Walmart](https://stock.walmart.com/) podaje
Nasdaq. W rejestrze zachowano źródło i opis konfliktu, przyjęto bieżące IR.
XOM ma w aktualnym pliku SEC CIK **0002115436** i nazwę ExxonMobil Holdings
Corp; [obecne IR](https://investor.exxonmobil.com/company-information/faq)
potwierdza Holdings. Nie połączono automatycznie wcześniejszego emitenta
na podstawie samego tickera; w E2C nie dodano raportów XOM.

**Granica weryfikacji profili:** wszystkie 53 mają źródło identyfikatora
SEC, ale nie ukończono pełnej weryfikacji roku fiskalnego i podstawy
sprawozdawczości dla wszystkich firm bez eventów. Rejestr jawnie zachowuje
pending/null zamiast zgadywać. Fiscal year/quarter i period_end nowych
27 eventów zweryfikowano osobno w dowodach ich okresów; brak potwierdzonego
period_end pozostaje null. Przed nowymi Actual konieczna jest osobna
weryfikacja jednostki, waluty, GAAP/IFRS i jednostki ADR.

IR PYPL zwróciło 403, UNH 406, JNJ timeout, CVX 403 — profile mają
`access_pending`; nie obchodzono tych ograniczeń. To nie oznacza, że firmy
nie ogłosiły dat, tylko że E2C nie ma ich zweryfikowanych wydarzeń.

## 4. Rzeczywiste daty i brak nowych Actual

Weryfikacja manualna przez narzędzie WWW: **03.11.2026**. Źródłami są
oficjalne strony komunikatów, datowane zapowiedzi, komunikaty IR i dokumenty
regulacyjne. Nie korzystano z Investing.com jako dowodu. Zapisano minimalne
fakty, nie pełne komunikaty. Wyszukiwanie pomogło znaleźć dokumenty;
bezpośrednie odczyty pozwoliły m.in. odróżnić datę Salesforce **26.08**
na IR od mylącego adresu innej strony zawierającego 03.09.

Każdy rekord ma CIK, FY/Q, label i nullable period_end, datę emitenta,
precision, oddzielny call, oficjalny URL, rodzaj dowodu, verified_on
i tekst potwierdzonych faktów. Bieżący status publikacji nie wynika
z upływu daty. Zapowiedzi nie są oznaczane published. Istniejące sześć
dokumentów i 12 obserwacji E2B są identyczne; **nowe 27 firm ma Actual null**.
Nie dodawano Forecast, guidance jako konsensusu, surprise lub beat/miss.

Nowe daty i odnośniki są zestawione w tabeli na końcu raportu. Firmy
z samą datą komunikatu nie mają wymyślonej godziny, a nieuwzględnione
godziny konferencji wymagają dalszego przeglądu — nie deklaruje się
pełnego pokrycia wszystkich call. Przyszłe terminy z dowodami obejmują
m.in. QCOM/ARM 04.11, NVDA 17.11, PANW 18.11 i SNOW 02.12.

## 5. Model, mała migracja stref i kontrolowany importer

Nie dodano nowych tabel. Oddzielny `earnings_coverage_schema.sql` rozszerza
**jeden CHECK source_timezone w earnings_date_confirmations**, wyłącznie
w izolacji. Stary CHECK przyjmował tylko NY/LA. Nowy pozwala zachować
IANA dla date-only TSM/ASML i dokładnego call Micron w Mountain Time:
NY, LA, Chicago, Denver, Toronto, Amsterdam, London, Taipei, Etc/UTC.
To nie migruje danych i nie dodaje timestampów do date-only.

Odrębny initializer wymaga własnej nazwy `macrolens_earnings_e2b_e2c_…`,
porównuje pełną oczekiwaną definicję starego/nowego CHECK i odrzuca obcą.
Ponowienie zgodnego schematu pomija DDL. Stare initializery i allowlisty
E2A/E2B pozostały bez zmian. **Na normalnej bazie ten CHECK jest nadal stary.**

`app/earnings_coverage.py` nie ma HTTP. Nowy importer waliduje odrębny
rejestr CIK i aliasów, hosty, zgodność dowodu z emitentem/okresem,
fiscal label/end z ręcznym ledgerem okresów, datę i IANA/DST, precision
oraz brak pól finansowych. Nie dopuszcza partii z powtórzonym okresem lub
dwoma unknown zamiast datowanego eventu. Sam rejestr nie generuje okresów.

Nie zmienia istniejących company/period/event, nie nadpisuje dat ani
historii. Dopisane confirmations są append-only z sequence/supersedes;
znany stary fingerprint nie reaktywuje starej daty. Nowa zmiana wymaga
changed/cancelled i nowego dowodu. Alias zajęty przez innego emitenta
powoduje odmowę. Idempotencja nie dodaje wersji lub timestampów.
CLI działa tylko na własnej bazie E2C, obejmuje migrację stref i import
w jednej transakcji; nie istnieje ścieżka CLI apply do normalnej macrolens.
Nie używa publisher_documents makro, nie dodaje schedulera i nie rozszerza
dotychczasowej allowlisty trzech firm w importerach pilota.

## 6. Pokrycie i obiektywny audyt luk

| Priorytet | Emitenci rejestru | Z datą w izolacji | Nowe firmy z datą |
|---|---:|---:|---:|
| A | 12 | 12 | 9 |
| B | 9 | 9 | 9 |
| C | 9 | 9 | 9 |
| D | 6 | 0 | 0 |
| E | 17 | 0 | 0 |
| Razem | **53** | **30** | **27** |

**23 firmy bez zweryfikowanej daty w tym zestawie:** UBER, ABNB, SHOP,
BKNG, PYPL, COIN, JPM, BAC, GS, V, MA, WMT, COST, HD, LLY, UNH, JNJ,
XOM, CVX, CAT, BA, DIS, BRK-B. Nie oznacza to braku zapowiedzi w internecie;
terminów tych firm nie importowano i nie zgadywano.

Sprawdzono aktualne strony [S&P DJI](https://www.spglobal.com/spdji/en/indices/equity/sp-500/)
i [Nasdaq](https://www.nasdaq.com/docs/2026/05/04/NDX.pdf). Strona S&P
nie dostarczyła pełnych aktualnych wag, a znaleziony PDF Nasdaq miał datę
majową, więc nie potraktowano go jako aktualnego listopadowego rankingu.
Strony Invesco QQQ zwracały dynamiczne placeholdery zamiast pełnej listy;
nie użyto ich do twierdzenia, że wykonano porównanie 30 pozycji.

Wykonano kontrolę **30 największych pozycji SPY i 30 największych pozycji
CNDX na 02.11.2026**, korzystając z oficjalnych publikowanych holdings:
[State Street SPY](https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx)
i [iShares Nasdaq-100](https://www.ishares.com/uk/individual/en/products/253741/ishares-nasdaq-100-ucits-etf/latest-holdings.csv).
**To jawne przybliżenie przez fundusze, nie dokładna licencjonowana lista
wag indeksów.** Wagi ETF i indeksu mogą się różnić. Wykonano tylko lokalny
jednorazowy odczyt referencji audytu; aplikacja nie pobiera tych plików.

Po deduplikacji GOOG/GOOGL każda trzydziestka ma 29 emitentów.
Rejestr obejmuje 24/29 emitentów referencji SPY i 23/29 referencji CNDX.
Luki SPY: **ABBV, PG, KO, MRK, GE**. Luki CNDX: **SPCX, AMGN, LIN, GILD,
ADI, PEP**. Razem **11 brakujących kandydatów**, nie dodano ich automatycznie
bez pełnego przeglądu tożsamości i źródeł. SPCX jest obserwacją z aktualnego
pliku funduszu, nie założeniem na podstawie dawnego składu Nasdaq.
Pełna kolejność kontrolnych 30+30 jest zachowana lokalnie w index-coverage-audit.json.

Rejestr obejmuje technologię, komunikację, handel/konsumpcję, finanse,
ochronę zdrowia, energię i przemysł. Brakuje reprezentatywnego pokrycia
utilities, real estate i materials; samo 53 firm nie oznacza pokrycia
wszystkich 11 sektorów lub wszystkich ważnych emitentów. D–E wymagają
następnego manualnego przeglądu terminów, a kandydaci powyżej dalszej
kwalifikacji. **Nie deklaruje się 100% pokrycia rynku.**

## 7. Walidacja

| Kontrola | Wynik E2C |
|---|---|
| Pełny backend offline | **1294 passed, 42,90 s** |
| Pełny frontend offline, Node 22.23.4 | **664 passed / 31 plików, 30,30 s** |
| TypeScript noEmit | passed |
| Production build | passed, największy chunk **407,04 kB**, próg bez zmian |
| Nowy PostgreSQL E2C | passed, prawdziwy PostgreSQL 17 |
| Dotychczasowe PostgreSQL | **8/8 passed**, w tym E2B Activation z realnym backup/restore |
| Chrome normalny Vite/API | **143 kontrole / 28 odpowiedzi API 200**, zero JS/console errors/503 |
| Chrome izolowany production preview/API | **143 kontrole / 24 odpowiedzi API 200**, zero JS/console errors/503 |
| Snapshoty normalnej bazy przed/po smoke | **21 tabel / 2 924 713 rekordów**, wszystkie hash/count identyczne |

Nowe regresje obejmują aliasy i jednego emitenta, CIK/host, ledger okresu,
unknown bez generowania eventów, daty historyczne/nadchodzące, oddzielny
release/call, DST i datę następnego polskiego dnia w zachowanych testach,
no-HTTP GET, idempotencję, stare rekordy po rewizji i całkowity rollback
migracji stref + 53 firm + dat po rzeczywistym błędzie SQL.
Porównano pierwotne wiersze E2A jako podzbiór rozszerzonych tabel,
całe sześć dokumentów/12 Actual E2B i wszystkie 13 tabel makro.

Chrome używał 1366/390 px, EN/PL, poprzedniego i bieżącego tygodnia,
własnego zakresu, dat NVDA/INTC/AMZN, nowych firm w izolacji, wartości
E2B, null nowych Actual, braku ticker checkboxów i zbędnego refetch przy
Wszystkie, jednego nagłówka 29.10, źródeł, Escape/focus i wewnętrznego
scrolla tabeli. Obejrzano desktop EN i mobile PL. Nie deklaruje to pełnego
audytu WCAG lub badania konkretnym czytnikiem ekranu.

Pierwszy frontend w sandboxie nie zapisał tymczasowego pliku Vite;
ponowienie z dostępem przeszło. Pierwsze testy UI miały stare etykiety
pustego zakresu i selektory trafiające w nową dodatkową konferencję/tekst
przycisku; poprawiono oczekiwania bez usuwania regresji. Jedna nowa mutacja
Q4 w teście była już poprawnym Q4 Apple, więc zastąpiono ją błędnym Q1.
Nie zwiększano timeoutów i nie pomijano testów. Nieudanych prób nie
zaliczono jako sukcesów. Nie uruchamiano nowego GitHub Actions.

## 8. Normalna baza i izolacja

Normalna `localhost:5432/macrolens`, rola macrolens, OID **16384**,
klaster **7682090371041935398**: wyłącznie odczyty diagnostyczne, bez DDL,
nowych spółek/eventów, importu lub rollbacku. Jej E2B nadal działa.
Nie zatrzymywano normalnego backendu i nie zmieniano jego konfiguracji.
UI ukrywające unknown jest już dostępne na zwykłym Vite; nowe 50 firm
i 27 dat z izolacji nie są jeszcze aktywne w codziennej bazie.

Smoke normalnego UI chronił tymczasowy lease na osobnym połączeniu
read-only, aby zwykły hook nie uruchomił importerów. Zwolniono go po
pełnym porównaniu wszystkich 21 tabel; nie pozostały diagnostyczne
transakcje. Nie zmieniono R1–R3, K2, Overview, BEA, FRED/ALFRED,
parametrów źródeł lub ich mechanizmu blokad. Brak żądań SEC/IR z aplikacji.

Izolacja: własny PostgreSQL 17 na loopback **55457**; rzeczywiste API
**8021**, osobny production preview **4191**, bez fixture odpowiedzi.
API smoke miało wymuszone read-only i własny lease. Wszystkie 21 tabel
izolacji przed/po UI identyczne. Testy używały syntetycznego makro i jawnego
manualnego seeda Earnings, bez kopiowania danych użytkownika.

Po testach zamknięto własne API/preview/diagnostyczny Chrome, usunięto
własne losowe bazy. Po sprawdzeniu pełnego ID
`7e2908205f12c1c887727c0bba82e75b8c4d3503802226eda58e3820086e8f51`
i etykiety usunięto tylko `macrolens_financial_e2c_20261103` i anonimowy
wolumen. Pozostawiono normalne macrolens_postgres, API 8000 i Vite 5173.

## 9. Późniejsza aktywacja — niewykonana, wymaga osobnej zgody

Lokalna propozycja: `data/raw/earnings-e2c-2026-11-03/activation-proposal.json`.
**ready_for_apply=false**. Hash kanonicznej propozycji:
`89eae4e3218e95f099f47a661f92d9c781ef5855fba7b0c869b07c681edcdb2f`.
To identyfikator propozycji zakresu, **nie gotowy token do apply**.

1. Osobno uzgodnić okno serwisowe i potwierdzić rzeczywisty target,
   klaster/OID/rolę, aktualne E2A/E2B, schematy i brak konfliktów aliasów.
2. Wstrzymać zidentyfikowany backend zapisujący przed snapshotem;
   PostgreSQL pozostawić uruchomiony. Wykonać dwa pełne stabilne odczyty.
3. Wykonać świeży pełny pg_dump, manifest celu/SHA/rozmiar i pełny restore
   do osobnej bazy. Stare kopie E2A/E2B nie są zabezpieczeniem tego etapu.
4. Przygotować osobną kontrolowaną ścieżkę apply oraz zamrożony plan:
   jedyny DDL to rozszerzenie wskazanego CHECK stref, dane to **50 nowych
   firm, 52 aliasy, 27 periods/events, 35 evidence, 54 confirmations**.
   Dotychczasowe wiersze i finanse pozostają bez UPDATE/DELETE.
5. Uzyskać osobną wyraźną zgodę na konkretny target i pełny hash planu
   po backup/restore. Nie używać dawnych zgód lub planów E2B.
6. Jedna SERIALIZABLE transaction, dotychczasowe locki, jawne limity
   oczekiwania; kontrola pełnych hashy przed/po. DDL i seed razem podlegają
   rollbackowi błędu. Obcy/partial schemat lub nowe dane mają zatrzymać
   operację, bez automatycznej naprawy lub zmiany zatwierdzanego hasha.
7. Po COMMIT oczekiwane: **53 firmy, 55 aliasów, 37 okresów i wydarzeń,
   40 evidence, 66 confirmations, nadal 6 dokumentów i 12 Actual E2B**.
   Idempotentna powtórka bez timestampów/wersji; przed restartem porównać
   wszystkie pierwotne wiersze E2A/E2B i 13 tabel makro.
8. Dopiero potem wznowić API z aktualnym kodem i sprawdzić normalny UI.
   Cofnięcie po COMMIT wymaga osobnej decyzji, manifestu dodanych ID
   i wykluczenia późniejszych zależności; bez CASCADE i bez przywracania
   starszej kopii ponad późniejsze poprawne dane.

## 10. Granice i wynik lokalny

Nowe dane są manualne. Brak parsera/schedulera, automatycznego SEC/IR,
obchodzenia 403, konsensusu, surprise i nowego revenue/EPS. Publiczny
odczyt faktu nie jest licencją do pełnego archiwum lub redystrybucji
komunikatów. Nie skopiowano interfejsu Investing.com.

Rejestr nie obejmuje wszystkich liderów sektorów, a lista D–E nie ma
w tym etapie zweryfikowanych wydarzeń. Dane fiskalne i zasady GAAP/IFRS,
waluty oraz ADR wymagają dalszej weryfikacji przed finansowym importem
nowych firm. Nie udaje się kompletnego first print, wszystkich korekt
intraday lub pełnej historii call. Event z oficjalną datą bez Actual
pozostaje finansowo niezweryfikowany, nawet jeśli data już minęła.

**Można już sprawdzić poprawiony widok pod http://localhost:5173/#/calendar.**
Ukrywa Q4 bez dat i poprawnie filtruje zakres. Rozszerzenie do 53 firm
w normalnym PostgreSQL wymaga osobnej aktywacji opisanej wyżej.

## 11. Zakres plików i Git

Zakres E2C: app/earnings.py (wyłącznie filtrowanie aliasów), nowy
app/earnings_coverage.py, nowy app/database/earnings_coverage_schema.sql,
dwa nowe config JSON, EarningsCalendar.tsx i test, earningsPresentation.ts,
EarningsDomains.test.tsx, nowy EarningsCoverage.test.tsx, pojedynczy
atrybut stopki w CalendarPage.tsx, dwa nowe testy backend/SQL i ten raport.
Nie zmieniano zależności, lockfile, CI, globalnego CSS i testów użytkownika.

Końcowo **14 modified / 17 untracked**, indeks pusty, HEAD/main bez zmian.
Zestaw obejmuje także zachowane wcześniejsze prace. Wszystkie snapshoty,
kopie referencyjne, logi, plany i zrzuty są ignorowane w data/raw.
Nie wykonano stagingu, commita, pusha, resetu, clean, amend, force push
lub globalnego formatowania.

## 12. Pełny wykaz emitentów i dowodów

Poniższe tabele są wygenerowane wyłącznie z przejrzanych lokalnych
metadanych i dotyczą **izolowanego** zakresu. `0` oznacza brak eventu
E2C, nie brak ogłoszenia przez firmę w rzeczywistości.

### Rejestr wszystkich 53 emitentów

Sektory są roboczą klasyfikacją rejestru, nie licencjonowanym eksportem GICS.
Country jest informacją profilu; podstawa sprawozdawczości/currency nie służy
w E2C do żadnego nowego importu finansowego. Dla firm bez eventów pełny
profil fiskalny pozostaje do przeglądu — nie wygenerowano na jego podstawie
kwartałów ani dat. Nazwy/IR pochodzą z oficjalnych profili emitentów, CIK
z referencji SEC opisanej wyżej.

| Priorytet | Ticker / aliasy | Emitent | CIK | Sektor | Kraj | Oficjalne IR | Datowane eventy w izolacji |
|---|---|---|---|---|---|---|---:|
| A | NVDA | NVIDIA CORP | 0001045810 | Technology | US | [IR](https://investor.nvidia.com) | 3 |
| A | AMZN | AMAZON COM INC | 0001018724 | Consumer discretionary | US | [IR](https://ir.aboutamazon.com) | 2 |
| A | INTC | INTEL CORP | 0000050863 | Technology | US | [IR](https://www.intc.com) | 2 |
| A | AAPL | Apple Inc. | 0000320193 | Technology | US | [IR](https://investor.apple.com) | 1 |
| A | MSFT | MICROSOFT CORP | 0000789019 | Technology | US | [IR](https://www.microsoft.com/en-us/Investor/) | 1 |
| A | GOOGL / GOOG | Alphabet Inc. | 0001652044 | Communication services | US | [IR](https://abc.xyz/investor/) | 1 |
| A | META | Meta Platforms, Inc. | 0001326801 | Communication services | US | [IR](https://investor.atmeta.com) | 1 |
| A | TSLA | Tesla, Inc. | 0001318605 | Consumer discretionary | US | [IR](https://ir.tesla.com) | 1 |
| A | AVGO | Broadcom Inc. | 0001730168 | Technology | US | [IR](https://investors.broadcom.com) | 1 |
| A | AMD | ADVANCED MICRO DEVICES INC | 0000002488 | Technology | US | [IR](https://ir.amd.com) | 1 |
| A | ORCL | ORACLE CORP | 0001341439 | Technology | US | [IR](https://investor.oracle.com) | 1 |
| A | NFLX | NETFLIX INC | 0001065280 | Communication services | US | [IR](https://ir.netflix.net) | 1 |
| B | MU | MICRON TECHNOLOGY INC | 0000723125 | Technology | US | [IR](https://investors.micron.com) | 1 |
| B | QCOM | QUALCOMM INC/DE | 0000804328 | Technology | US | [IR](https://investor.qualcomm.com) | 1 |
| B | TSM | TAIWAN SEMICONDUCTOR MANUFACTURING CO LTD | 0001046179 | Technology | TW | [IR](https://investor.tsmc.com) | 1 |
| B | ASML | ASML HOLDING NV | 0000937966 | Technology | NL | [IR](https://investor.asml.com) | 1 |
| B | ARM | ARM HOLDINGS PLC /UK | 0001973239 | Technology | GB | [IR](https://investors.arm.com) | 1 |
| B | AMAT | APPLIED MATERIALS INC /DE | 0000006951 | Technology | US | [IR](https://ir.appliedmaterials.com) | 1 |
| B | LRCX | LAM RESEARCH CORP | 0000707549 | Technology | US | [IR](https://investor.lamresearch.com) | 1 |
| B | KLAC | KLA CORP | 0000319201 | Technology | US | [IR](https://ir.kla.com) | 1 |
| B | TXN | TEXAS INSTRUMENTS INC | 0000097476 | Technology | US | [IR](https://investor.ti.com) | 1 |
| C | ADBE | ADOBE INC. | 0000796343 | Technology | US | [IR](https://www.adobe.com/investor-relations.html) | 1 |
| C | CRM | Salesforce, Inc. | 0001108524 | Technology | US | [IR](https://investor.salesforce.com) | 1 |
| C | NOW | ServiceNow, Inc. | 0001373715 | Technology | US | [IR](https://investor.servicenow.com) | 1 |
| C | PLTR | Palantir Technologies Inc. | 0001321655 | Technology | US | [IR](https://investors.palantir.com) | 1 |
| C | CRWD | CrowdStrike Holdings, Inc. | 0001535527 | Technology | US | [IR](https://ir.crowdstrike.com) | 1 |
| C | PANW | Palo Alto Networks Inc | 0001327567 | Technology | US | [IR](https://investors.paloaltonetworks.com) | 1 |
| C | SNOW | Snowflake Inc. | 0001640147 | Technology | US | [IR](https://investors.snowflake.com) | 1 |
| C | IBM | INTERNATIONAL BUSINESS MACHINES CORP | 0000051143 | Technology | US | [IR](https://www.ibm.com/investor) | 1 |
| C | CSCO | CISCO SYSTEMS, INC. | 0000858877 | Technology | US | [IR](https://investor.cisco.com) | 1 |
| D | UBER | Uber Technologies, Inc | 0001543151 | Consumer discretionary | US | [IR](https://investor.uber.com) | 0 |
| D | ABNB | Airbnb, Inc. | 0001559720 | Consumer discretionary | US | [IR](https://investors.airbnb.com) | 0 |
| D | SHOP | SHOPIFY INC. | 0001594805 | Technology | CA | [IR](https://www.shopify.com/investors) | 0 |
| D | BKNG | Booking Holdings Inc. | 0001075531 | Consumer discretionary | US | [IR](https://ir.bookingholdings.com) | 0 |
| D | PYPL | PayPal Holdings, Inc. | 0001633917 | Financials | US | [IR](https://investor.pypl.com) | 0 |
| D | COIN | Coinbase Global, Inc. | 0001679788 | Financials | US | [IR](https://investor.coinbase.com) | 0 |
| E | JPM | JPMORGAN CHASE & CO | 0000019617 | Financials | US | [IR](https://www.jpmorganchase.com/ir) | 0 |
| E | BAC | BANK OF AMERICA CORP /DE/ | 0000070858 | Financials | US | [IR](https://investor.bankofamerica.com) | 0 |
| E | GS | GOLDMAN SACHS GROUP INC | 0000886982 | Financials | US | [IR](https://www.goldmansachs.com/investor-relations) | 0 |
| E | V | VISA INC. | 0001403161 | Financials | US | [IR](https://investor.visa.com) | 0 |
| E | MA | Mastercard Inc | 0001141391 | Financials | US | [IR](https://investor.mastercard.com) | 0 |
| E | WMT | Walmart Inc. | 0000104169 | Consumer staples | US | [IR](https://stock.walmart.com) | 0 |
| E | COST | COSTCO WHOLESALE CORP /NEW | 0000909832 | Consumer staples | US | [IR](https://investor.costco.com) | 0 |
| E | HD | HOME DEPOT, INC. | 0000354950 | Consumer discretionary | US | [IR](https://ir.homedepot.com) | 0 |
| E | LLY | ELI LILLY & Co | 0000059478 | Health care | US | [IR](https://investor.lilly.com) | 0 |
| E | UNH | UNITEDHEALTH GROUP INC | 0000731766 | Health care | US | [IR](https://www.unitedhealthgroup.com/investors.html) | 0 |
| E | JNJ | JOHNSON & JOHNSON | 0000200406 | Health care | US | [IR](https://www.investor.jnj.com) | 0 |
| E | XOM | ExxonMobil Holdings Corp | 0002115436 | Energy | US | [IR](https://investor.exxonmobil.com) | 0 |
| E | CVX | CHEVRON CORP | 0000093410 | Energy | US | [IR](https://www.chevron.com/investors) | 0 |
| E | CAT | CATERPILLAR INC | 0000018230 | Industrials | US | [IR](https://investors.caterpillar.com) | 0 |
| E | BA | BOEING CO | 0000012927 | Industrials | US | [IR](https://investors.boeing.com) | 0 |
| E | DIS | Walt Disney Co | 0001744489 | Communication services | US | [IR](https://investors.thewaltdisneycompany.com) | 0 |
| E | BRK-B / BRK.B | BERKSHIRE HATHAWAY INC | 0001067983 | Financials | US | [IR](https://www.berkshirehathaway.com) | 0 |

### Każdy nowy zweryfikowany okres i termin

Daty odnoszą się do emitenta, jeżeli nie znamy polskiego dnia.
`date_only` nie zawiera timestampu. Poniższe okresy są konkretnymi
ręcznie zweryfikowanymi etykietami emitenta; nie wyznaczają automatycznie
kolejnych okresów. Każda pozycja oznacza dokładnie jeden nowy event.

| Firma | FY / kwartał emitenta | Period end | Data emitenta | Release precision | Call źródłowy | Oficjalny dowód |
|---|---|---|---|---|---|---|
| AAPL | Q4 FY2026 | 2026-09-26 | 2026-11-02 | date_only | 14:00 PT | [oficjalne źródło](https://www.apple.com/newsroom/2026/11/apple-reports-fourth-quarter-results/) |
| MSFT | Q1 FY2027 | 2026-09-30 | 2026-10-28 | after_close | 14:30 PT | [oficjalne źródło](https://news.microsoft.com/source/2026/10/07/microsoft-announces-quarterly-earnings-release-date-69) |
| GOOGL | Q3 2026 | 2026-09-30 | 2026-10-28 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://abc.xyz/investor/news/news-details/2026/Alphabet-Announces-Third-Quarter-2026-Results-2026-FCcqxfIfmh/default.aspx) |
| META | Q3 2026 | 2026-09-30 | 2026-10-21 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Third-Quarter-2026-Results/) |
| TSLA | Q3 2026 | 2026-09-30 | 2026-10-21 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://ir.tesla.com/press-release/tesla-releases-third-quarter-2026-financial-results) |
| AVGO | Q3 FY2026 | 2026-08-02 | 2026-09-02 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-third-quarter-fiscal-year-2026-financial) |
| AMD | Q3 2026 | — | 2026-11-03 | after_close | 17:00 ET | [oficjalne źródło](https://ir.amd.com/news-events/press-releases/detail/1300/amd-to-report-fiscal-third-quarter-2026-financial-results) |
| ORCL | Q1 FY2027 | — | 2026-09-10 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://investor.oracle.com/investor-news/news-details/2026/Oracle-Announces-Q1-Results-Driven-by-Triple-Digit-Growth-in-Cloud-Infrastructure-Revenues/default.aspx) |
| NFLX | Q3 2026 | 2026-09-30 | 2026-10-20 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://ir.netflix.net/files/doc_financials/2026/q3/FINAL-Q3-26-Shareholder-Letter.pdf) |
| MU | Q4 FY2026 | 2026-09-03 | 2026-09-30 | date_only | 14:30 MT | [oficjalne źródło](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/default.aspx) |
| QCOM | Q4 FY2026 | — | 2026-11-04 | after_close | 13:45 PT | [oficjalne źródło](https://investor.qualcomm.com/news-events/press-releases/news-details/2026/Qualcomm-Schedules-Fourth-Quarter-and-Fiscal-2026-Earnings-Release-and-Conference-Call/default.aspx) |
| TSM | Q3 2026 | 2026-09-30 | 2026-10-15 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://pr.tsmc.com/english/news/3346) |
| ASML | Q3 2026 | — | 2026-10-14 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://investor.asml.com/news-releases/news-release-details/asml-reports-eu11.7-billion-total-net-sales-and-eu5.0-billion-net-income-q3-2026) |
| ARM | Q2 FY2027 | — | 2026-11-04 | after_close | 14:00 PT | [oficjalne źródło](https://newsroom.arm.com/news/arm-announces-earnings-release-date-for-second-quarter-fiscal-year-ending-2027) |
| AMAT | Q3 FY2026 | 2026-07-26 | 2026-08-13 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-announces-third-quarter-2026-results) |
| LRCX | Q1 FY2027 | 2026-09-27 | 2026-10-21 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://investor.lamresearch.com/2026-10-21-Lam-Research-Corporation-Reports-Financial-Results-for-the-Quarter-Ended-September-27%2C-2026) |
| KLAC | Q1 FY2027 | 2026-09-30 | 2026-10-28 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://ir.kla.com/news-events/press-releases/detail/523/kla-corporation-reports-fiscal-2027-first-quarter-results) |
| TXN | Q3 2026 | 2026-09-30 | 2026-10-21 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://www.ti.com/about-ti/newsroom/news-releases/2026/2026-10-21-ti-reports-third-quarter-2026-financial-results-and-shareholder-returns.html) |
| ADBE | Q3 FY2026 | — | 2026-09-10 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://news.adobe.com/news/2026/09/adobe-q3fy26-financial-results) |
| CRM | Q2 FY2027 | 2026-07-31 | 2026-08-26 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx) |
| NOW | Q3 2026 | 2026-09-30 | 2026-10-28 | after_close | nie wprowadzono / do przeglądu | [oficjalne źródło](https://newsroom.servicenow.com/press-releases/details/2026/ServiceNow-to-Announce-Third-Quarter-2026-Financial-Results-on-October-28/default.aspx) |
| PLTR | Q3 2026 | 2026-09-30 | 2026-11-02 | date_only | 17:00 ET | [oficjalne źródło](https://www.sec.gov/Archives/edgar/data/1321655/000132165526000045/a2026q3ex991pressrelease.htm) |
| CRWD | Q2 FY2027 | 2026-07-31 | 2026-08-26 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://ir.crowdstrike.com/news-releases/news-release-details/crowdstrike-reports-second-quarter-fiscal-year-2027-financial) |
| PANW | Q1 FY2027 | 2026-10-31 | 2026-11-18 | after_close | nie wprowadzono / do przeglądu | [oficjalne źródło](https://investors.paloaltonetworks.com/node/20971/pdf) |
| SNOW | Q3 FY2027 | 2026-10-31 | 2026-12-02 | after_close | 14:00 PT | [oficjalne źródło](https://www.snowflake.com/en/news/press-releases/fy27-q3-earnings-date-announcement/) |
| IBM | Q3 2026 | 2026-09-30 | 2026-10-21 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://www.sec.gov/Archives/edgar/data/51143/000005114326000093/ibm-20261021xex991.htm) |
| CSCO | Q4 FY2026 | — | 2026-08-12 | date_only | nie wprowadzono / do przeglądu | [oficjalne źródło](https://investor.cisco.com/news/news-details/2026/CISCO-REPORTS-FOURTH-QUARTER-AND-FISCAL-YEAR-2026-EARNINGS/default.aspx) |

### Ostatni komunikat i następna zapowiedź

Dla starych pilotów: NVDA ostatni raport **26.08, Q2 FY2027**, następna
zweryfikowana data **17.11, Q3 FY2027**; AMZN i INTC ostatnie raporty
**29.10, Q3 2026**, bez nowego datowanego Q4. Dowody pozostają w E2A/E2B.
Dla każdego z 27 nowych emitentów powyższa tabela zawiera jedyny wprowadzony
okres. Jeśli dowód jest earnings_release, jego data jest ostatnim
zweryfikowanym komunikatem tego zestawu. Jeśli jest zapowiedzią, nie
przedstawia się jej jako rzeczywistej publikacji tylko dlatego, że minął dzień.
Nie deklaruje się, że istnieje kompletna historia lub że zweryfikowano
wszystkie późniejsze komunikaty danego emitenta.

Zapowiedzi z datą od 03.11: AMD **03.11**, QCOM i ARM **04.11**, NVDA
**17.11**, PANW **18.11**, SNOW **02.12**. Dla pozostałych nowych firm
najbliższa przyszła data w tym zestawie nie jest znana. Dla wszystkich
23 firm D–E ostatni raport i najbliższa zapowiedź są **niezweryfikowane
w E2C**; eventów 0, powód: brak przejrzanego dowodu w tym zakresie,
z dodatkowymi ograniczeniami IR dla PYPL/UNH/JNJ/CVX opisanymi wyżej.

## 13. Zamknięcie Git E2B Activation i E2C

Zgodnie z osobnym zleceniem zamknięto etapy w dwóch logicznych commitach.
Na wejściu ponownie potwierdzono HEAD 4f4e12ce138be210bedbb13924cf0c4e52d65411,
14 modified / 17 untracked i pusty indeks. Zapisano manifest **31 plików**,
pełny diff oraz chronione SHA. Nie wykonywano nowej aktywacji, DDL,
importu lub rollbacku w normalnej bazie.

Pierwszy commit: **565a0fa126a0e2a09f5b858ed61074feebe9dc96**,
**Add safe earnings financial activation**. Dokładnie sześć plików:
pięć jawnie wskazanych plików E2B Activation i minimalna zmiana ci.yml.
Ósmy krok PostgreSQL uruchamia rzeczywisty test aktywacji/backup/restore.
Test dopuszcza jawny service container GitHub Actions po pełnym ID,
wyłącznie z kontrolną bazą CI, rolą CI i hostem loopback; normalna
macrolens pozostaje odrzucana. Nie zmieniono produkcyjnego aktywatora.
Nową ścieżkę z ID kontenera dodatkowo wykonano lokalnie na własnym serwisie.

Pierwsza dokładna kopia indeksu: **327 blob IDs** zgodnych, bez E2C i
prac użytkownika; **1251 backend**, **658 frontend**, Node 22.23.4
typecheck/build, PostgreSQL **8/8** i actionlint przeszły.

Drugi commit: **Expand earnings calendar coverage and hide undated events**.
Zakres ma dokładnie **15 plików**: 14 plików E2C z sekcji 11 i ci.yml.
Workflow dodaje dziewiąty krok coverage and issuer aliases, zachowując
wszystkie osiem wcześniejszych. Nie zmieniono dependencies, lockfile,
uprawnień Actions, timeoutów, K2, Overview lub R1–R3.

CalendarPage wystawiono **wyłącznie patchem indeksu**: HEAD plus jeden
atrybut `hidden` stopki. Sprawdzono dokładne bajty staged blobu. Previous
week i pozostały diff użytkownika są poza indeksem. Cały working tree
CalendarPage pozostał byte-identyczny ze stanem wejściowym zamknięcia.
Pierwszy lokalny patch miał CRLF niezgodne z indeksem; został odrzucony.
Zapisano go jako LF i dopiero poprawny wąski patch zastosowano. Nie
wystawiano całego pliku ani nie cofano wcześniejszych zmian.

### Nowe wyniki zamknięcia

| Kontrola | Working tree | Dokładny indeks E2C |
|---|---|---|
| Pełny backend offline | **1294 passed, 63,79 s** | **1294 passed** |
| Pełny frontend offline | **664 passed / 31 plików** | **662 passed / 31 plików** |
| TypeScript noEmit / Node 22.23.4 build | passed | passed |
| Największy chunk | **407,04 kB** | **407,04 kB** |
| PostgreSQL | **9/9 passed** | **9/9 passed** |
| actionlint / diff checks | passed | passed |

Dwa dodatkowe testy working tree pochodzą z chronionego CalendarPage.test;
ich brak w HEAD nie jest utratą testów. Nie dołączono wcześniejszej pracy
tylko dla wyrównania liczników. Kopia E2C ma **335 zgodnych blob IDs**;
przejrzano cały staged diff, ścieżki i wzorce sekretów. Brak .env, RAW,
kopii SQL, referencji ETF, logów i helperów w stagingu. Po walidacji
zmieniono wyłącznie tę dokumentację i jej staging.

Nowy Chrome używał **wyłącznie kodu indeksu**: produkcyjny preview 4193,
API 8023 i własna baza PostgreSQL 17 na 55459, bez fixture odpowiedzi.
**143 kontrole / 35 zakończonych odpowiedzi API 200**, EN/PL, 1366/390 px,
zero JS/console errors i HTTP 503. Przeszły brak undated, puste zakresy,
6 eventów poprzedniego tygodnia w izolacji, nowe firmy, jeden nagłówek
29.10, czasy release/call, null nowych Actual/Forecast, stare wartości E2B,
brak checkboxów, źródła, szczegóły/Escape/focus, Makro i Wszystkie oraz
brak zbędnego refetch Earnings. Obejrzano mobile PL. Pierwszy helper
trafił na jeszcze nieotwarty port CDP; pełne ponowienie po starcie Chrome
przeszło. Nie zmieniano produkcyjnego kodu lub asercji w celu obejścia błędu.

Testy PostgreSQL miały rzeczywiste fresh/upgrade, błędne approval/target/
backup/hash, rollback SQL, append-only, rewizje, aliasy, 53 firmy i
27 nowych dat. Wszystkie używały własnych losowych baz i guarda HTTP.
Read-only API smoke i osobny lease na izolacji zachowały wszystkie 21
tabel identycznie przed/po. Nie było żądań SEC/IR z aplikacji.

### Ochrona normalnej bazy i prac użytkownika

Nowy odczyt normalnej localhost:5432/macrolens potwierdził OID 16384,
klaster 7682090371041935398, **3 firmy / 10 eventów / 6 dokumentów /
12 Actual**. Wszystkie **osiem tabel Earnings** ma pełne hash/count
identyczne z końcem implementacji E2C; CHECK stref nadal nie zawiera
Denver/Taipei. Nie uruchomiono na niej DDL, seeda, apply lub rollbacku.
Nie zatrzymywano ani nie zastępowano zwykłego API/Vite. Aktywność zwykłego
makro nie jest przedstawiana jako migracja tej sesji; testy makro wykonano
w izolacji. Nie zmieniono źródeł lub parametrów odświeżania.

Wszystkie **13 wcześniejszych plików użytkownika** zachowano byte-identycznie
względem wejścia zamknięcia. Obejmuje to README, EconomyBrief/test,
SourceCheckStatus/test, cały CalendarPage z Previous week, jego test,
calendarAgenda, styles i cztery nieśledzone audyty. Manifest SHA pozostaje
lokalnie, nie dodano go do commita. Użytkownik nie traci niezacommitowanych
zmian przez selektywny staging.

Po testach zamknięto własne API/preview/Chrome, zwolniono izolowany lease
i usunięto własne losowe bazy. Własny kontener sprzątany jest po kontroli
pełnego ID i etykiety; normalny macrolens_postgres pozostaje poza cleanup.

Pełny SHA drugiego commita, zwykły push obu commitów i URL oraz rzeczywiście
**zakończone** wyniki trzech jobów Actions zostaną podane w końcowym raporcie
Codexa. Nie tworzy się trzeciego commita wyłącznie dla metadanych po pushu.
Nie deklaruje się sukcesu CI na podstawie lokalnych testów. Końcowo poza
commitami pozostaje **9 modified / 4 untracked**, indeks pusty.

E2C nadal **nie jest aktywowane w normalnej bazie**. Rejestr 53 firm
i 27 nowych dat sprawdzono w izolacji; 23 firmy D–E pozostają bez
zweryfikowanych dat, a 11 kandydatów z referencji ETF wymaga dalszego
audytu. Propozycja 89eae4e3… ma ready_for_apply=false i nie jest zgodą.
Następny krok to osobne przygotowanie aktywacji E2C ze świeżym backupem,
pełnym restore, oknem serwisowym i nowym zatwierdzonym planem. Nie
rozpoczęto E2D, dodatkowego importu D–E lub automatycznego feedu.
