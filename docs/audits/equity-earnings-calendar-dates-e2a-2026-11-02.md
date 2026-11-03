# MacroLens — E2A: oficjalne terminy wyników spółek

Implementacja i weryfikacja **02.11.2026, Europe/Warsaw**,
`C:\Projects\macrolens`, `main`, HEAD
`14e4829d79f3f4f0916629a560cfc0cf2a122836`.
Podstawa: [audyt E1](equity-earnings-calendar-source-audit-2026-11-02.md),
zlecenie E2A i późniejsze uzupełnienie hierarchii czasu. Późniejsze
uzupełnienie zastępuje błędną polską godzinę NVDA z pierwszego zlecenia:
**17.11 około 22:20 PL — wyniki; 23:00 PL — konferencja**.

**Wdrożono lokalny pilot dat, bez automatycznego feedu.** Schemat i dane
uruchamiano wyłącznie na własnym efemerycznym PostgreSQL 17. Istniejącej
bazy użytkownika nie odczytywano ani nie migrowano. W zwykłej bazie bez
opt-in schematu część Earnings zwróci kontrolowany błąd dostępności;
nie uruchamia migracji przez GET. Dotychczasowe makro pozostaje dostępne.
Nie rozpoczęto E2B. Bez stagingu, commita i pusha.

## 1. Stan wejściowy i zakres

Potwierdzono `main`, powyższy HEAD, **9 modified / 4 untracked**, pusty
indeks. Przeczytano E1, bieżący Calendar, typy, API, inicjalizator SQL,
R1–R3 i dotychczasowe walidacje PostgreSQL. Zapisano bajty i SHA-256
13 chronionych plików, łącznie z E1, oraz cały zastany tracked diff.
Nic nie cofano ani nie formatowano globalnie.

E2A dodaje osobne dane spółek/kwartałów/terminów, lokalny importer manualny,
odczytowe API i świadomie wybieraną domenę Earnings. Nie ma revenue, EPS,
guidance, konsensusu, surprise, tabel obserwacji finansowych, importera
wyników, schedulera lub drugiego timera React. Nie modyfikowano schematu
makro, inicjalizatora makro, zależności, K2, rankingu Overview i R1–R3.

## 2. Model i historia SQL

Osobny `app/database/earnings_schema.sql` tworzy:

| Tabela | Klucze i odpowiedzialność |
| --- | --- |
| earnings_companies | UUID emitenta, CIK CHAR(10) UNIQUE z zerami, nazwa i aktualny ticker |
| earnings_company_aliases | Klucz (company_id,ticker); alias nie tworzy nowego emitenta |
| earnings_periods | UUID i UNIQUE(company_id,fiscal_year,fiscal_quarter,period_kind), label emitenta, nullable period_end |
| earnings_events | Jeden UUID na period_id; złożony FK okres/emitent; publication_status=unconfirmed |
| earnings_source_evidence | Manualny URL, rodzaj, metoda, verified_on, minimalne potwierdzone fakty i fingerprint rekordu |
| earnings_date_confirmations | Osobne release/call, sequence, status, precision, lokalny czas/strefa, osobne exact/approximate UTC, dowód i supersedes |

UUID są deterministyczne: emitent od CIK, okres od CIK/FY/quarter, event
od period_id. Ticker nie jest częścią trwałego event_id. Aliasów nie kasuje
się przy dopisaniu nowego; obecna allowlista symboli pilotów wymaga jawnej
aktualizacji przy zmianie tickera. Nie jest to automatyczny katalog wszystkich
papierów SEC ani kompletna historyczna baza aliasów.

CIK, zakres kwartału, unikalność okresu/eventu i dokładność czasu chronią
CHECK/UNIQUE. Złożone FK łączą event, period, company i evidence tej samej
spółki. Nie ma ON DELETE CASCADE. UPDATE/DELETE dowodów i potwierdzeń
blokują triggery append-only. Trigger nowego potwierdzenia blokuje event,
wymaga następnej sequence i poprzednika własnego komponentu; po znanym
terminie dopuszcza tylko jawne changed/cancelled. Sprawdza też zgodność
exact/approximate UTC ze źródłową strefą. Aktywne potwierdzenie to ostatnia
sequence osobno dla release i call; nie przełącza się wskaźnika na stary rekord.

Importer `app/earnings.py` waliduje pełną partię przed zapisem, a następnie
zapisuje ją transakcyjnie pod osobnym xact lock **726530020**. To serializacja
ręcznego importu, nie nowy koordynator refresh; lock R3 726530019 pozostał
bez zmian. Identyczny rekord jest idempotentny. Znany stary rekord nie
reaktywuje się po późniejszej zmianie. Błąd SQL wycofuje całą partię i nowy
dowód, zachowując ostatni poprawny stan. Sprzeczna zmiana metadanych okresu
wymaga odrębnie przejrzanej korekty, zamiast cichej podmiany.

`init_earnings_db.initialize` odrzuca bazę spoza prefiksu
`macrolens_earnings_`. Nie jest wywoływany z API, z normalnego init_db lub
startu aplikacji. CLI `python -m app.earnings` czyta wyłącznie lokalny JSON
i również przechodzi przez tę bramkę. W E2A nie ma ścieżki wdrożenia DDL
do zwykłej bazy użytkownika; przyszła migracja wymaga osobnej decyzji.

## 3. Jawne źródła manualne

`config/earnings_manual.json` zawiera sześć eventów: trzy znane kwartały
i trzy następne kwartały **bez daty**. Sam label następnego okresu nie jest
prognozą daty ani period_end. Każdy dowód ma
`manually_verified_official_source`, oficjalny URL, source_kind,
`verified_on=2026-11-02`, CIK/FY/quarter i krótki opis faktów.

| Spółka | Okres | Data emitenta | Release time precision | Call time precision | Status | Oficjalny dowód |
| --- | --- | --- | --- | --- | --- | --- |
| NVDA / 0001045810 | Q3 FY2027, koniec 25.10 | 17.11.2026 | approximate: 13:20 PT → **ok. 22:20 PL** | exact: 14:00 PT → **23:00 PL** | confirmed; publikacja unconfirmed | [Zapowiedź NVIDIA z 28.10](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Sets-Conference-Call-for-Third-Quarter-Financial-Results/default.aspx) |
| AMZN / 0001018724 | Q3 2026, koniec 30.09 | 29.10.2026 — data konferencji | unknown | exact: 17:00 ET → **22:00 PL** | potwierdzony call, nie godzina release; publikacja unconfirmed | [Zapowiedź Amazon](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-to-Webcast-Third-Quarter-2026-Financial-Results-Conference-Call/) |
| INTC / 0000050863 | Q3 2026, koniec 26.09 | 29.10.2026 | after_close: granica sesji **21:00+ PL**, nie timestamp release | exact: 14:00 PDT → **22:00 PL** | confirmed; publikacja unconfirmed | [Datowana zapowiedź Intel](https://www.intel.com/content/www/us/en/newsroom/news/corporate/intel-reports-third-quarter-2026-financial-results.html) |
| NVDA | Q4 FY2027 | — | unknown | unknown | Termin nieogłoszony | Brak nowego dowodu; bez URL udającego potwierdzenie |
| AMZN | Q4 2026 | — | unknown | unknown | Termin nieogłoszony | Jak wyżej |
| INTC | Q4 2026 | — | unknown | unknown | Termin nieogłoszony | Jak wyżej |

Nową zapowiedź NVDA odczytano ręcznie przez narzędzie WWW w E2A;
potwierdza okres, release około 13:20 PT i call 14:00 PT. Dane AMZN/INTC
oparto na manualnych dowodach E1. Konflikt widgetu Intel „PST” kontra
datowana zapowiedź „PDT” zachowano w opisie dowodu i szczegółach UI;
do konwersji konferencji użyto prawidłowego PDT dla tej daty.
Nie oznaczono wyników historycznych jako published tylko na podstawie
daty konferencji. E2A nie importuje dowodów finansowej publikacji.

Nie tworzono HTTP receipts, HTTP 200 wydawców, fetched_at, first_seen,
accession ani RAW. `content_fingerprint` to SHA-256 kanonicznego **rekordu
metadanych**, nie hasz pobranego dokumentu. Nie użyto publisher_documents,
który wymagałby rzeczywistych RAW/hash/path. Verified_on oznacza dzień
weryfikacji manualnej, nie chwilę pierwszej dostępności wyników.

Importer nie zawiera klienta HTTP. Wymaga allowlisty trzech CIK, zgodnego
tickera i evidence CIK/okresu, HTTPS oraz konkretnego hosta oficjalnego.
Odrzuca błędną precyzję, strefę i sprzeczny skrót EST/EDT/PST/PDT względem
IANA, a także nieistniejącą/niejednoznaczną lokalną godzinę DST. Nie pobiera
strony w celu walidacji URL i nie uznaje linku za zgodę na archiwizację.
Pozostają bramki praw/dostępu z E1: brak aktywnego SEC/IR API, brak obejścia
403 i brak licencji pełnych archiwów lub redystrybucji komunikatów.

## 4. Hierarchia czasu i brak fikcyjnej precyzji

API zachowuje precision: exact, approximate, after_close, before_open,
date_only, unknown; source_local_date/time, kanoniczną strefę IANA,
timezone_label_raw i URL dowodu. Wiersz preferuje **release**, nie call.

| Oficjalny dowód | Prezentacja PL | Zapis |
| --- | --- | --- |
| Dokładny czas release | `22:20 — wyniki` | scheduled_at_utc tylko dla exact |
| Orientacyjny czas release | `ok. 22:20 — wyniki` | expected_time_utc, scheduled_at_utc=null |
| Tylko AMC + zweryfikowana sesja | `22:00+ — po sesji USA`, 29.10 `21:00+` | session_boundary_utc i osobny link reguły; oba pola czasu release=null |
| Tylko AMC bez zweryfikowanej sesji | `Po sesji USA` | Bez wyliczonej granicy |
| Tylko BMO | `Przed otwarciem USA`, opcjonalnie `przed HH:mm PL` | Granica oddzielona od timestampu release |
| Data bez godziny | `Godzina nieogłoszona` | scheduled/expected UTC=null |
| Brak daty release i call | `Termin nieogłoszony` | Poza osią, bez daty i bez północy |

NVDA: 13:20 America/Los_Angeles (PST) = 21:20 UTC = **22:20 Warszawa**.
Występujące w technicznych fixture `21:20Z` oznacza UTC, nigdy godzinę PL.
Konferencja jest osobno: 14:00 PST = 22:00 UTC = **23:00 PL**.
Żadna z tych wartości nie jest dowodem pierwszej rzeczywistej dostępności.

Sesja korzysta z małej, jawnej, ręcznie zweryfikowanej listy dat w kodzie,
na podstawie [oficjalnych godzin i wyjątków NYSE](https://www.nyse.com/trade/hours-calendars).
To referencja granicy regularnej sesji USA, nie nowy pobierany feed.
Lista jest ograniczona do sześciu dni kontrolnych/pilota; nie jest
wiecznym algorytmem „każdy weekday zamyka się o 16”. Poza listą nie
wyświetla się liczbowej granicy. 27.11 i 24.12 uwzględniają 13:00 ET;
święta, weekendy i niezweryfikowane przyszłe daty nie dostają standardowego
zamknięcia. Zmiana lub nadzwyczajna sesja wymaga aktualizacji manualnej.

Testy IANA: 16:00 NY→22:00 PL w zwykłym tygodniu, 16:00 NY→21:00 PL
29.10 i 16.03, BMO 09:30 NY→14:30 PL dnia 29.10, early close 13:00
NY→19:00 PL dnia 27.11, NVDA i syntetyczne 19:30 NY→01:30 PL następnego
dnia. Zakres czasu jest informacyjny; **nie gwarantuje rzeczywistej
godziny publikacji** i nie steruje żadnym szybkim monitoringiem E2A.

Date-only i AMC nie ustalają dokładnego polskiego dnia. Calendar pokazuje
grupę „Data emitenta; dzień i godzina publikacji w PL nieustalone”, zamiast
tworzyć midnight lub duplikować event. Przy filtrze zakresu dla takiego
wpisu stosuje jawną datę źródłową; dla exact/approximate — przeliczony
dzień Warszawy. AMZN call-only jest opisany jako data konferencji,
a główny tekst mówi, że godzina wyników jest nieogłoszona.

## 5. API i Calendar

Dodano:

- `GET /api/v1/calendar/events` — domains=macro/earnings lub oba, daty,
  tickers z allowlisty, walidacja maksymalnie 366 dni.
- `GET /api/v1/earnings/companies` — trzy jawne tożsamości pilota.
- `GET /api/v1/earnings/events/{event_id}` — metadane i historia, bez Actual.

Nowa unia `CalendarItem = MacroItem | EarningsItem` ma discriminator
domain. MacroItem owija istniejący event; EarningsItem nie ma fikcyjnego
release_id, series, importance lub period_before. Stare `/api/v1/calendar`
i `/api/v1/releases/{release_id}` zachowały swoje implementacje. Nowe GET
nie uruchamiają HTTP, importu lub refresh; earnings SQL ma REPEATABLE READ
READ ONLY. Revision makro i earnings są oddzielone, jest assembled_at i
`independent_domain_snapshots`: brak deklaracji jednej atomowej generacji.
Revision earnings obejmuje także historię i stan unknown; nie jest
publication_id Overview.

Calendar domyślnie pozostaje Makro. Radio Makro / Wyniki spółek / Wszystkie
jest odrębne od K2. W Earnings dostępne są NVDA/AMZN/INTC; brak zaznaczenia
oznacza wszystkie. Date presets i zakres pozostają wspólne. Wszystkie
pokazuje oba bloki domen z własnymi grupami dat, bez mieszania finansów
w makro tabelę Forecast/Actual/Previous. Nie wdrożono jednego globalnego
sortowania wierszy obu domen. Ten prosty podział chroni zastany renderer.

Widok earnings ma jeden zwarty wiersz na okres, a szczegóły: release/call,
źródło, verified_on, precision, strefę, status i historię. Conference call
nie dostaje osobnego wiersza. Escape zamyka szczegóły i oddaje focus.
Unknown jest osobną sekcją, bez wymyślonej daty. Nie ma pustych tabel EPS
lub revenue. EN/PL korzysta z aktualnego stanu języka aplikacji; nowe style
są wydzielone w earnings.css, bez zmiany chronionego styles.css.

Stan filtrów gwiazdek/kategorii makro jest zachowany przy przełączeniach.
Nie przemontowuje się istniejącego hooka. W teście zmiana domen nie dodaje
makro GET/POST; filtr tickerów wykonuje tylko GET earnings. Dotychczasowy
timer makro może nadal wykonać swoją już należną kontrolę; filtr earnings
nie tworzy drugiego timera ani nowego uprawnienia do ingestion.
Gwiazdki `2026-11-k2-v1`, rozkład 17/11/1 i ranking 17/max4 pozostają bez
zmian. Earnings nie wchodzi do Overview. Interwały 900/21600, punkty R3,
backoff, source checks, publication cache i next_check_at nie były edytowane.

## 6. Walidacja i izolacja

| Kontrola | Wynik |
| --- | --- |
| Pełny backend offline | **1199 passed**, w tym 36 przypadków E2A |
| Pełny frontend z no-network.cjs | **656 passed / 29 plików**, w tym 10 nowych przypadków Earnings |
| Osobny TypeScript typecheck | passed |
| Production build | passed; największy chunk około **407,04 kB**, bez podnoszenia progu Vite |
| PostgreSQL E2A | passed, osobno fresh i upgrade, dwie własne bazy |
| Cztery dotychczasowe skrypty PostgreSQL | Empire fresh/historyczny upgrade, FT900, BEA Direct, R3: wszystkie passed |
| Chrome production preview | **47 kontroli**, EN/PL, 1366/390 px; **12 odpowiedzi API 200**, zero JS/console errors/overflow |
| git diff --check | passed |

Backend testuje CIK/tickery/FY, unknown, approximate/exact, sesje, DST,
następny polski dzień, URL/CIK/okres, konflikt skrótu strefy i API union,
zakresy/domeny, brak HTTP. Nowy skrypt PostgreSQL sprawdza rzeczywiste
FK/UNIQUE/CHECK, append-only, changed/cancelled, starszy znany rekord,
rollback po triggerze, nullable date i zachowanie syntetycznych
FRED/ALFRED. Każda baza ma losowy prefiks i cleanup tylko własnej nazwy.
Nie zmieniano asercji czterech wcześniejszych skryptów ani globalnych
guardów. Nie dodano skryptu E2A do CI w tym zakresie; workflow pozostał
identyczny. Wyniki SQL są lokalne, nie deklaracją nowego zielonego GitHub CI.

Frontend obejmuje hierarchię czasu, early close, konferencję, unknown,
źródła, EN/PL, Escape/focus, API error/Retry oraz zachowanie filtrów makro
i liczby żądań po zmianie domen. Wszystkie wcześniejsze testy zachowano;
nie zwiększano timeoutów i nie pomijano testów. Znany sporadyczny błąd MCI
nie wystąpił. Pierwszy frontend w sandboxie nie otworzył tymczasowego pliku
konfiguracji Vite; poprawne ponowienie z dostępem do pliku przeszło.

Utworzono osobny kontener `macrolens_earnings_e2a_20261102`, oficjalny
PostgreSQL 17, dynamiczne bazy wewnątrz i loopback **55439**. Nie użyto
`macrolens_postgres`, jego bazy lub wolumenu. Trust dotyczył wyłącznie
efemerycznego serwisu; klient miał jawne, testowe dane. Kontrole SQL miały
guard blokujący publisher HTTP. Nie kopiowano produkcyjnych danych.

Chrome używał rzeczywistego API na 8013 i Vite production preview 4185,
z osobną bazą zawierającą wyłącznie podstawowy schemat i jawne metadata
E2A. Odpowiedzi API nie były podstawiane. Makro czytało swoje istniejące
lokalne dowody harmonogramów; nie deklaruje to walidacji produkcyjnych
Actual makro. API miało wymuszone read-only, a oddzielne połączenie trzymało
lock 726530019. Normalne POST starego hooka otrzymały stan zajętej blokady,
nie uruchomiły importerów. Guard HTTP stanowił dodatkowe zabezpieczenie.
Count/max source_check_runs, cały stan koordynatora oraz liczba confirmations
przed/po były identyczne. Nie wykonano żadnego żądania SEC/IR z aplikacji.

Smoke obejmował trzy historyczne/przyszłe wpisy, trzy unknown, NVDA
22:20/23:00, Intel 21:00+, AMZN call-only, oficjalne linki, filtry domen
i tickerów, Escape/fokus oraz powrót do makro. Obejrzano zrzuty desktop EN
i mobile PL. Pierwszy helper nie przeładował języka przy tym samym URL;
po poprawieniu nawigacji wykonano pełny przebieg ponownie. Krótszy nagłówek
filtra tickerów poprawił czytelność telefonu. Nie osłabiono kontroli.

## 7. Granice gotowości i E2B

To działający pilot **w izolacji**, nie produkcyjny automatyczny feed.
Zwykła baza użytkownika nadal nie ma schematu E2A. Nie wykonano na niej
DDL, seedów, ingestion, backfillu lub inicjalizacji. Nie ma cyklicznej
aktualizacji terminów: nowe zapowiedzi i zmiany wymagają jawnego manualnego
rekordu i przeglądu źródła. Szczególnie lista granic sesji jest ograniczona;
brak granicy jest bezpiecznym fallbackiem, nie powodem zgadywania 16:00.

Do E2B pozostają prawa pozyskania/minimalnego przechowywanego dowodu,
dostęp backendu SEC po 403, parsery revenue/GAAP EPS, własne finansowe
tabele wersji, porównania, reconciliation i testy. Nie wdrożono żadnego
z tych elementów. Brak gwarancji wyniku dokładnie o planowanej godzinie,
konsensusu, pełnego first print lub wszystkich korekt intraday. Manualne
metadane i linki nie są licencją pełnych komunikatów. E1 pozostaje
niezmienionym raportem z wcześniejszego badania, a nowy dowód NVDA i korektę
godziny opisuje ten raport.

## 8. Pliki E2A i ochrona wcześniejszej pracy

**16 plików E2A:**

- app/api/main.py — tylko dołączenie nowego routera.
- app/api/earnings.py — nowy router odczytowy.
- app/database/earnings_schema.sql — wydzielony opt-in SQL.
- app/database/init_earnings_db.py — bramka izolowanej inicjalizacji.
- app/earnings.py — lokalne metadane, walidacja, importer i czytnik.
- config/earnings_manual.json — jawne ręcznie zweryfikowane rekordy.
- frontend/src/calendar/CalendarPage.tsx — wąskie hunki domen i wrappera.
- frontend/src/calendar/EarningsCalendar.tsx — wydzielony renderer.
- frontend/src/calendar/earningsTypes.ts — unia i GET.
- frontend/src/calendar/earningsPresentation.ts — hierarchia czasu EN/PL.
- frontend/src/calendar/earnings.css — wyłącznie nowe style.
- frontend/src/calendar/EarningsCalendar.test.tsx — regresje komponentu/czasu.
- frontend/src/calendar/EarningsDomains.test.tsx — domeny/filtry/żądania.
- tests/test_earnings_dates.py — testy offline.
- tests/postgres_earnings_validation.py — rzeczywisty SQL w izolacji.
- docs/audits/equity-earnings-calendar-dates-e2a-2026-11-02.md — ten raport.

Z 13 chronionych plików **12 pozostało byte-identycznych**. Jedyny wyjątek
to jawnie dozwolone w zleceniu wąskie zmiany CalendarPage.tsx. Nie zmieniano
zastanych presetów poprzedniego tygodnia, renderowania makro lub testów
użytkownika. Oddzielne nowe testy zapobiegają potrzebie edycji chronionych
testów. Zapisano baseline, before.diff oraz `calendar-e2a.patch` i wersję
bez kontekstu w ignorowanym `data/raw/earnings-e2a-2026-11-02/` do późniejszego
przejrzenia i selektywnego stagingu. Nie zastosowano ich do indeksu.
Patche wymagają sprawdzenia kontekstu przy przyszłym stagingu.

Poniżej końcowe SHA-256 i status Git, po kontroli cleanup.

| Plik chroniony | SHA-256 przed | SHA-256 po |
| --- | --- | --- |
| `README.md` | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` | identyczny |
| `frontend/src/brief/EconomyBrief.tsx` | `017f87c9f580a10c7125e14cb0415f1556c2fcaa2724295f943eef26b82dfcc1` | identyczny |
| `frontend/src/brief/EconomyBrief.test.tsx` | `bb5c2f6adac6d3c182e893e0d58fa32ff711aee9d7722feaad0d67ad7c598ed5` | identyczny |
| `frontend/src/brief/SourceCheckStatus.tsx` | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` | identyczny |
| `frontend/src/brief/SourceCheckStatus.test.tsx` | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` | identyczny |
| `frontend/src/calendar/CalendarPage.tsx` | `92fe810add14ec6ba952be5fc12a8e1c2ddea7417891a98454af0a49d3d3d5c9` | `04d02ac84aac9d12ee78c604ab929ac47a5e189f43b2ec6f89cfae7659ef883c` |
| `frontend/src/calendar/CalendarPage.test.tsx` | `4e62ca7c6345190a79048dfaa09dd6178e76e141f3e6695607c4eba5edf637d9` | identyczny |
| `frontend/src/calendar/calendarAgenda.ts` | `57c84376346095d0beb65b3535105cf21dea2221c8705c85d0e004a0d1ece5f0` | identyczny |
| `frontend/src/styles.css` | `40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c` | identyczny |
| `docs/audits/calendar-event-impact-audit-2026-10-30.md` | `35e876926cea3c82e3b2df837876d6fb3cabd82ba55db67a4de7ad06159f6f1d` | identyczny |
| `docs/audits/calendar-next-releases-priority-2026-10-29.md` | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` | identyczny |
| `docs/audits/calendar-release-day-latency-2026-10-29.md` | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` | identyczny |
| `docs/audits/equity-earnings-calendar-source-audit-2026-11-02.md` | `a6db1f1a877aacb9bc1980608d20a1d1f1609023d64e1a11ef8699ec659b1434` | identyczny |

Końcowy backend: **1199 passed, 43,20 s**; frontend: **656 passed / 29 plików,
22,26 s**. Po ostatnim skróceniu nagłówka mobilnego ponowiono pełny frontend,
produkcję i wszystkie 47 kontroli Chrome. Następnie odtworzono zwykły build
z domyślnym adresem API projektu; testowy port nie pozostał w konfiguracji.

Po kontrolach zwolniono lock, zatrzymano własny backend/preview/Chrome,
usunięto własne losowe bazy i kontener wraz z jego anonimowym wolumenem.
Przed usunięciem sprawdzono stały ID utworzonego kontenera i własną etykietę;
na serwerze pozostały wyłącznie control/postgres/template. Pierwsze zakończenie
helpera przez konsolę przerwało jego finally; porównanie read-only i cleanup
wykonano wtedy jawnie według zapisanego własnego markera. Ostatni przebieg
zamknął się kodem 0 i wykonał cleanup samodzielnie. Nie usuwano innych zasobów.

Końcowo **10 modified / 18 untracked**, indeks pusty, HEAD i main bez zmian.
Wcześniejsze 4 nieśledzone audyty, w tym E1, pozostają poza zakresem E2A:

```text
 M README.md
 M app/api/main.py
 M frontend/src/brief/EconomyBrief.test.tsx
 M frontend/src/brief/EconomyBrief.tsx
 M frontend/src/brief/SourceCheckStatus.test.tsx
 M frontend/src/brief/SourceCheckStatus.tsx
 M frontend/src/calendar/CalendarPage.test.tsx
 M frontend/src/calendar/CalendarPage.tsx
 M frontend/src/calendar/calendarAgenda.ts
 M frontend/src/styles.css
?? app/api/earnings.py
?? app/database/earnings_schema.sql
?? app/database/init_earnings_db.py
?? app/earnings.py
?? config/earnings_manual.json
?? docs/audits/calendar-event-impact-audit-2026-10-30.md
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
?? docs/audits/calendar-release-day-latency-2026-10-29.md
?? docs/audits/equity-earnings-calendar-dates-e2a-2026-11-02.md
?? docs/audits/equity-earnings-calendar-source-audit-2026-11-02.md
?? frontend/src/calendar/EarningsCalendar.test.tsx
?? frontend/src/calendar/EarningsCalendar.tsx
?? frontend/src/calendar/EarningsDomains.test.tsx
?? frontend/src/calendar/earnings.css
?? frontend/src/calendar/earningsPresentation.ts
?? frontend/src/calendar/earningsTypes.ts
?? tests/postgres_earnings_validation.py
?? tests/test_earnings_dates.py
```

Pełny zakres obejmuje wyłącznie 16 wymienionych plików E2A; pozostałe pozycje
to zachowany stan użytkownika. Diagnostyka, patche, profile, zrzuty i marker
własnej bazy są ignorowane w data/raw, nie są nowymi plikami repozytorium.
Nie dodano sekretów, .env, pełnych komunikatów, bazy lub cache do zakresu Git.
Bez stagingu, commita, pusha, resetu, clean, amend i zmiany historii.

## 9. Zamknięcie E2A + Activation — 03.11.2026

Powyższe wyniki i statusy opisują wykonanie poprzednich etapów. W zamknięciu
potwierdzono main i bazowy HEAD 14e4829d79f3f4f0916629a560cfc0cf2a122836,
10 modified / 23 untracked oraz początkowo pusty indeks. Przejrzano E1,
E2A, Activation, kod, manualne dane, SQL i granice odświeżania. Nie wdrożono
E2B, nowych źródeł, schedulera lub automatycznego SEC/IR.

Staging obejmuje **22 pliki**: 16 E2A, 5 Activation i wyłącznie cztery
addytywne linie istniejącego workflow. Nowe dwa nazwane kroki PostgreSQL
uruchamiają walidacje terminów Earnings i aktywacji/odtworzenia. Cztery
wcześniejsze walidacje pozostają. Joby backend/frontend, triggery,
uprawnienia, concurrency i timeouty nie zmieniły się. Skrypt Activation
dopuszcza teraz także jawną efemeryczną nazwę kontrolną macrolens_ci_control;
nie dopuszcza zwykłej macrolens. Nie zmieniono produkcyjnego kodu aktywacji
ani izolowanego init_earnings_db podczas zamknięcia.

CalendarPage dodano przez **git apply --cached** z patchem zbudowanym
względem HEAD. Wyłączono wcześniejszy preset Previous week. Pozostałe
wcześniejsze zmiany użytkownika w całości pozostają poza indeksem:
README, EconomyBrief i test, SourceCheckStatus i test, CalendarPage.test,
calendarAgenda, styles, trzy audyty makro oraz E1. Ich SHA-256 są zachowane;
pełny working tree CalendarPage również nie został zmieniony. Indeks nie
potrzebuje rozszerzonego typu DatePreset z niezacommitowanego calendarAgenda.

| Nowa kontrola zamknięcia | Working tree | Dokładny indeks |
| --- | --- | --- |
| Backend offline | **1207 passed**, 61,07 s | **1207 passed**, 45,77 s |
| Frontend offline, Node 22.23.4 / no-network.cjs | **656 passed / 29 plików**, 45,76 s | **654 passed / 29 plików**, 30,28 s |
| Osobny TypeScript typecheck | passed | passed |
| Production build, Node 22 | passed | passed |
| Największy chunk | **407,04 kB** | **407,04 kB** |
| Empire fresh / historyczny upgrade | passed | passed |
| FT900 PostgreSQL | passed | passed |
| BEA Direct PostgreSQL | passed | passed |
| BEA Release-Aware PostgreSQL | passed | passed |
| Earnings dates PostgreSQL | passed, fresh i upgrade | passed, fresh i upgrade |
| Earnings Activation PostgreSQL | passed | passed |
| actionlint / whitespace | passed | passed |

Indeks wyeksportowano z pozostałymi śledzonymi zależnościami do osobnej
kopii. Każdy plik porównano z blobem indeksu z uwzględnieniem normalizacji
LF/CRLF. Nie ma w niej wcześniejszych zmian README/Overview/CSS, poprzedniego
tygodnia lub czterech nieśledzonych audytów. Różnica dwóch testów pochodzi
z chronionego CalendarPage.test, nie z usunięcia lub pominięcia przypadków.
Przeszły istniejące regresje K2, Overview oraz R1–R3; żadnych timeoutów lub
progów Vite nie zmieniano. Nie wystąpiło ostrzeżenie ponad 500 kB.

Pierwszy backend kopii w sandboxie dotarł do 100%, lecz nie zakończył
procesu i nie podał podsumowania. Nie policzono go jako sukcesu. Przerwano
tylko tę próbę i ponowiono identyczne polecenie z szerszym dostępem do plików;
kod 0 i 1207 passed pochodzą z zakończonego ponowienia. Nie ustalono dokładnej
przyczyny zawieszenia i nie zmieniano aplikacji/testów, aby je obejść.
Pierwszy --check selektywnego patcha odrzucił CRLF; przygotowano LF i ponowiono
kontrolę bez zmiany working tree. Ostrzeżenia Git LF/CRLF nie są błędami
whitespace. Nie zmieniano ani nie wyciszano zależności Starlette/httpx.

Oba komplety sześciu skryptów SQL korzystały wyłącznie z własnego
PostgreSQL 17 na loopback 55445 i losowych baz. HTTP wydawców blokuje guard.
Walidacje sprawdzają także rzeczywisty rollback i świadome usunięcie własnych
obiektów wyłącznie w testowej bazie. **Nie wykonywano apply, DDL, seedów,
rollbacku lub inicjalizacji w bazie użytkownika.** Read-only potwierdziło
w niej nadal 3 spółki / 6 eventów / 12 confirmations oraz poprawne czasy.
Normalnej aplikacji nie zatrzymywano. Nowego Chrome w zamknięciu nie było;
63 kontrole z raportu Activation pozostają wynikiem aktywacji.

Przejrzano cały staged diff, allowlistę 22 nazw i wzorce sekretów. Nie ma
.env, data/raw, backupów, manifestów, helperów, logów, buildów lub profili.
Po walidacji uzupełniono wyłącznie oba raporty i ich staging/eksport.

Jeden zatwierdzany commit: **Add earnings calendar pilot and safe activation**.
Przed zatwierdzeniem origin/main nadal wskazywał 14e4829. Pełny commit SHA,
wynik zwykłego pusha, rzeczywisty URL Actions i zakończone wyniki trzech
jobów zostaną podane w końcowej odpowiedzi po ich uzyskaniu. Ten zapis nie
ogłasza przyszłego sukcesu CI i nie wymaga drugiego commita tylko dla
metadanych, których nie ma przed pierwszym pushem. Ręczne aktualizacje dat,
brak EPS/revenue, konsensusu i automatycznego feedu pozostają aktualne.
