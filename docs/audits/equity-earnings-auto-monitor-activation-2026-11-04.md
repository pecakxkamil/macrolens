# MacroLens — automatyczny monitor Earnings: aktywacja zakończona

Wykonano 04.11.2026, Europe/Warsaw, C:\Projects\macrolens, main,
HEAD 5b31cdb1ea042cd10483f701c262b85a958efc08.

**Normalny monitor aktywny. Rzeczywisty automatyczny import ARM/QCOM
zakończony. Calendar sam pokazał Actual bez przeładowania strony.**
Adaptery obejmują dwa zatwierdzone okresy pilotów; nie deklaruje się
automatycznego pokrycia wszystkich spółek lub przyszłych raportów.

## Zgoda i kontrolowana aktywacja

Użytkownik odpowiedział „tak zatwierdzam” na konkretny plan normalnego
localhost:5432/macrolens i jego pełny kanoniczny SHA-256:

`d66741f4ff719a4d4443b95d4467526a9aeca822ce907e5486f255cc40d03c11`

Przed zapisem ponownie wykonano read-only prepare. Plan był identyczny:
target PG17, macrolens, OID 16384, klaster 7682090371041935398, pełne snapshoty
11 tabel Earnings, schemat, 16 artefaktów i wersje bibliotek. Również
załadowane artefakty działającego API odpowiadały zatwierdzonym. Token
normalnego monitora nie istniał. Indeks Git był pusty.

Ponownie sprawdzono SHA aktualnego archiwum i dowód pełnego restore z etapu
przygotowania: pg_dump custom 32 098 275 B, SHA-256
`4031f01efae8de6d59249e13a11958f1677efe72d9397276408801caa406f28a`.
Pełny restore PG17 potwierdził 24 tabele / 3 086 206 rekordów i katalogi.
Nie wykonywano restore normalnej bazy ani nowego backupu w tej aktywacji;
użyto sprawdzonego archiwum wykonanego podczas bezpośredniego przygotowania.
Chronione dane i schemat nadal mu odpowiadały.

CLI apply otrzymał jawnie dokładny target i pełny hash. W jednej transakcji
READ COMMITTED, pod advisory 726530022/726530020 i SHARE 11 tabel Earnings,
z limitami lock 5 s / statement 120 s, ponownie zweryfikowano dane i schemat.
DDL i policy zakończyły się COMMIT-em, kod 0, receipt outcome=created.
Powstały tylko earnings_monitor_policy i earnings_report_checks z ochroną
append-only oraz zatwierdzone rozszerzenie CHECK verification_method.
Nie osłabiono pozostałych guardów E2D. Nie blokowano makro lease 726530019.

Niezależny odczyt po COMMIT, jeszcze przed uruchomieniem importu, potwierdził
zgodny pełny katalog, wszystkie 11 tabel Earnings identyczne i pusty audit.
Dopiero potem CLI enable-runtime zweryfikował policy/target/artefakty i
utworzył ignorowany data/raw/earnings-monitor/activation.json. Nie zmieniano
kodu, .env ani sposobu uruchamiania API; bez restartu API/Vite.

## Normalny automatyczny import

Działający lifecycle backendu sam uruchomił worker po następnym wybudzeniu.
Nie wywoływano importu ręcznie ani przez Calendar GET. Faktyczne czasy PL:

| Raport | Slot harmonogramu | Start HTTP/check | Imported |
|---|---|---|---|
| ARM Q2 FY2027 | 23:15 | 23:19:24,355 | 23:19:26,307 |
| QCOM Q4 FY2026 | 23:15 | 23:19:26,359 | 23:19:28,443 |

To pierwsze próby po tej aktywacji; nie deklaruje się wcześniejszych prób
o 22:00/22:15/22:30. Start regularnego okna tego dnia wynosił 22:00 PL,
nie godzinę konferencji. Zaległe sloty scalono do ostatniego dostępnego.

| Emitent | Zweryfikowane reported diluted EPS | Revenue kwartalne |
|---|---:|---:|
| ARM Q2 FY2027 | 0,12 USD | 1 443 000 000 USD |
| QCOM Q4 FY2026 | 1,17 USD | 10 322 000 000 USD |

[Oficjalny ARM shareholder letter](https://investors.arm.com/static-files/0b5baa2e-fc47-4d05-b724-e49de7bd4356):
HTTP 200, PDF 3 217 032 B, SHA-256
`88fe0960810dd97a04bb459572f2684010eb8473452d834dc57533087f1279ad`.
USD, US GAAP, ordinary share. Nie przeliczano ADR ani FX.

[Oficjalny QCOM earnings release](https://investor.qualcomm.com/files/content_files/FY2026-4th-Quarter-Earnings-Release.pdf):
HTTP 302 do przejrzanego konta s204.q4cdn.com/645488518, następnie 200,
PDF 160 530 B, SHA-256
`6aa674a7f42a75aae351ccce55ae33ac2da34774827fdec43297f9ae6e12c4c6`.
USD, US GAAP, common share. Sprawdzono kwartalną kolumnę GAAP, nie non-GAAP.

Obie metryki każdego raportu zapisano atomowo przez append-only writer E2D,
z nową metodą automated_official_report_validation i rzeczywistymi receipts.
Nie zastąpiono historycznych zapowiedzi ani ich timestampów. Kolejne ticki
zwracają activated=true, status=completed, checked=0: raporty kompletne
zatrzymały sprawdzanie. Nie ma importów duplikatów lub kolejnych wersji.
Monitor pozostaje częścią działającego lokalnego backendu. Dla innych
okresów bez przejrzanego adaptera wymagana jest kontrola; nie zgaduje Actual.

## API, Chrome i integralność

Chrome CDP 9285 otwarto przed włączeniem tokenu na normalnym Vite 5173 /
API 8000. Najpierw oba Actual były null. Po automatycznym imporcie otwarta
strona sama pokazała ARM 0,12 USD / 1,44 mld USD i QCOM 1,17 USD /
10,32 mld USD dzięki natywnemu pollingowi co 60 s. Trzy odczyty Earnings API,
zero przeładowań dokumentu, zero błędów JS i zero żądań przeglądarki do
wydawców. Zachowano siedem kolumn, prognozy i Previous null pilotów oraz
Market Cap. Obejrzano rzeczywisty zrzut normal-auto-live-pl.png.

Pełne ordered binary COPY przed/po: 24 tabele / 3 086 206 → 26 tabel /
3 086 217 rekordów. Z istniejących tabel zmieniły się tylko dopisane E2D:
27 → 29 dokumentów, 46 → 50 obserwacji. Po wyłączeniu dokładnie dwóch nowych
dokumentów i ich czterech obserwacji odtworzono pierwotne SHA binary COPY:
wszystkie stare 27 dokumentów i 46 obserwacji są byte-identyczne.
Pozostałe dziewięć tabel Earnings identyczne w całości, w tym historia
Previous 23 raporty / 45 metryk. Companies 53, aliases 55, events/periods 37,
evidence 40, confirmations 66, E2B 6/12 zachowane.

Nowe tabele zawierają jedną policy i cztery wiersze audit (started/result
dla dwóch raportów). Wszystkie tabele i katalog makro identyczne w tym oknie.
Nie wykonano importu Market Cap, zmiany harmonogramu makro, restore/rollbacku
normalnej bazy ani dodatkowego DDL poza zatwierdzonym planem.
Pierwszy pomocniczy SELECT kontrolny użył błędnej nazwy canonical_value;
poprawiono wyłącznie read-only zapytanie na istniejące actual. Ponowna pełna
kontrola przeszła; nie zmieniano danych lub kodu aplikacji.

Pełne testy przygotowania pozostają aktualne: 1506 backendowych,
715 frontendowych / 35 plików, TypeScript/build passed, 19/19 PostgreSQL.
W tej aktywacji nie zmieniano przetestowanego kodu; dodatkowo wykonano
rzeczywisty normalny apply, read-only kontrole SQL/API i Chrome z żywym
importem oraz weryfikację kolejnych ticków bez nowych zapisów.

## Zakończenie

Wszystkie 42 zastane zmienione/nieśledzone pliki zachowano byte-identycznie.
Jedyny nowy plik Git tego etapu to ten raport. Własny Chrome zakończono
przez Browser.close na własnym CDP 9285. Nie uruchamiano nowego kontenera
lub osobnego API/preview. Normalne PG5432/API8000/Vite5173 działają dalej,
a zatwierdzony token monitora pozostaje aktywny. Backup, plan, receipts,
pełne snapshoty, actual attempts i screenshot są ignorowane w
 data/raw/earnings-auto-monitor-2026-11-04; PDF/token w data/raw/earnings-monitor.

Końcowo 19 modified / 24 untracked, indeks pusty, HEAD/main bez zmian:
5b31cdb1ea042cd10483f701c262b85a958efc08. Bez stagingu, commita, pusha,
resetu, clean, amend lub globalnego formatowania. Raport przygotowania
opisuje wcześniejszy stan awaiting_activation; niniejszy raport dokumentuje
późniejszą zatwierdzoną i wykonaną aktywację.
