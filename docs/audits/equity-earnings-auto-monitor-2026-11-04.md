# MacroLens — automatyczne sprawdzanie Earnings: implementacja i gotowość

Wykonano 04.11.2026, Europe/Warsaw, C:\Projects\macrolens, main,
HEAD 5b31cdb1ea042cd10483f701c262b85a958efc08. Bez stagingu, commita i pusha.

**Automatyczny import działał w pełnym izolowanym klonie PG17. W normalnej
aplikacji działa pętla wybudzania, ale import jest NIEAKTYWNY:
awaiting_activation. ARM/QCOM Current nadal pozostają tam null.**
Nowy zapis wymaga osobnej zgody zgodnie z sekcją 6 zlecenia użytkownika.
Poprzednia zgoda na historię E2E nie obejmuje automatycznych Current.

## Mechanizm i granice

API lifespan wybudza kontrolę co 30 sekund i używa istniejącego launchera
zadań overview_refresh.coordinator.launch. Dotychczasowy koordynator był
wyzwalany żądaniami; dodano wybudzanie w jego cyklu życia, bez niezależnego
procesu schedulera. Nie zmieniono harmonogramu makro. Brak tokenu oznacza
wyłącznie kontrolę pliku, bez połączenia z bazą lub HTTP wydawców.
GET Calendar pozostaje czytnikiem. GET /api/v1/earnings/monitor/status
pokazuje stan procesu, ostatni tick i wynik; nie uruchamia importu.

Dla after_close harmonogram zaczyna się od rzeczywistego zamknięcia sesji,
co 15 minut przez 6 godzin. Dla 04.11.2026 to 22:00, 22:15, 22:30 itd. PL.
Konferencja nie wyznacza początku. Before_open ma analogiczne sześciogodzinne
okno przed otwarciem. Nieznana godzina korzysta ze zweryfikowanego dnia,
co 2 godziny. Po szybkim oknie sprawdzanie wraca następnego dnia co 2 godziny,
nie dłużej niż 48 godzin od początku; potem review_required, bez HTTP.
Zaległe sloty są scalane do ostatniego, bez serii nadrabianych żądań.
Kompletny Published zatrzymuje sprawdzanie. Daty sesji uwzględniają DST,
święta i wcześniejsze zamknięcia z przejrzanego kalendarza 2026; lata poza
nim wymagają kontroli. Nie deklaruje się pokrycia kalendarza 2027.

Automatyczne adaptery obejmują WYŁĄCZNIE dwa zweryfikowane okresy pilotów.
Pozostałe firmy/okresy bez adaptera przechodzą do kontroli, bez zgadywania.
Nie jest to uniwersalny parser wszystkich 53 emitentów ani przyszłych PDF.
Registry wiąże CIK, FY/Q, koniec okresu, dzień release, podstawę akcji,
standard, walutę i dozwolone oficjalne URL. Nie zawiera oczekiwanych kwot.
Parser sprawdza bieżącą kwartalną kolumnę, konsolidację, reported diluted,
GAAP oraz jednostki. Odrzuca adjusted/basic/YTD i niejednoznaczny układ.

HTTP ma timeout 25 s, limit PDF 8 MiB, ograniczone przekierowania wyłącznie
na przejrzane URL, request budget i odstęp między wydawcami. 404 zachowuje
brak raportu, 429/5xx mają trwały backoff i Retry-After, 403/challenge lub
nieznane przekierowanie wymagają kontroli. Brak obchodzenia blokad.
Rzeczywiste PDF, SHA i receipts z HTTP pozostają ignorowane w data/raw.
Nie deklaruje się pełnego receipt w szczegółach każdej nieudanej walidacji.

Trwały append-only dziennik started/result i unikalny event/slot/phase
zapobiegają powtórzeniom po restarcie. Osierocona próba po 5 minutach dostaje
wynik interrupted; kolejny slot może wznowić pracę. Lease 726530022
serializuje procesy. Import i wynik imported zatwierdzają się atomowo przez
istniejący writer E2D i lock 726530020. HTTP odbywa się poza transakcją.
Nie pobiera się makro lease 726530019. Zmiana już wydanego dokumentu wymaga
kontroli zamiast automatycznego nadpisania. Stare wersje pozostają.

Calendar odczytuje API co 60 sekund bez przeładowania dokumentu, wstrzymuje
polling ukrytej karty, wznawia po jej pokazaniu i nie nakłada żądań.
Błąd tła zachowuje poprzednie wartości. Bez nowych kolumn/paneli.

## Rzeczywisty pilot i godziny prób

Oficjalne dokumenty pobrano rzeczywistym HTTP; próba automatyczna w klonie
nie podstawiała odpowiedzi. ARM: HTTP 200. QCOM: oficjalne 302 do przejrzanego
konta q4cdn, następnie 200. Walidacja kwartalnych GAAP danych:

| Emitent | Revenue | Reported diluted EPS | Źródło |
|---|---:|---:|---|
| ARM Q2 FY2027 | 1443 mln USD | 0,12 USD | [shareholder letter](https://investors.arm.com/static-files/0b5baa2e-fc47-4d05-b724-e49de7bd4356) |
| QCOM Q4 FY2026 | 10322 mln USD | 1,17 USD | [earnings release](https://investor.qualcomm.com/files/content_files/FY2026-4th-Quarter-Earnings-Release.pdf) |

ARM: US GAAP, USD, ordinary share; podstawę dodatkowo sprawdzono w
[oficjalnym 20-F](https://investors.arm.com/static-files/0b97f8e1-ac58-4b25-84d8-9df66807ab19).
Nie wykonano przeliczenia ADR/FX. QCOM: US GAAP, USD, common share.

Planowany slot próby to 23:00 PL, faktyczny start ARM **23:06:37,608 PL**,
wynik imported **23:06:39,543**. QCOM start **23:06:39,616**, imported
**23:06:41,582**. Są to czasy tej późniejszej próby w izolacji, nie dowód
sprawdzania o 22:00/22:15/22:30 ani first print emitenta. W normalnej bazie
nie było automatycznych prób HTTP/importu, gdyż nie włączono tokenu.

Pełny klon zaczął z pustymi Actual pilotów. Po kontrolowanej aktywacji
WYŁĄCZNIE klonu lifecycle sam uruchomił worker, pobrał PDF i dopisał 2 nowe
wersje / 4 obserwacje: E2D 27/46 → 29/50. Otwarte Chrome samo pokazało
0,12 / 1,44 mld USD i 1,17 / 10,32 mld USD. Dwa odczyty API, zero
przeładowań dokumentu, zero błędów JS. Kolejne ticki nie pobierały już
kompletnych raportów. Previous 23/45 i wszystkie dane makro klonu identyczne.

## Walidacja

| Kontrola | Wynik |
|---|---|
| Pełny backend offline | 1506 passed, 68,80 s |
| Pełny frontend offline | 715 passed / 35 plików, 30,28 s |
| TypeScript noEmit | passed |
| Production build | passed, największy chunk 407,04 kB |
| PostgreSQL 17 | 19/19 passed, wszystkie 18 wcześniejszych i nowy monitor |
| Chrome normalny Vite/API | 1133 kontrole, 28 API 200, dodatkowo 37 GET 200 |
| Chrome rzeczywisty automatyczny klon | passed, Actual pojawiają się przez polling, zero reload/JS errors |

Nowa walidacja SQL obejmuje prawdziwy backup/restore aktywacji, rollback DDL
po SQL 1/0, restart/404, trwały backoff/429, drugi OS process pod lease,
import przy zajętym makro lease, atomowy rollback dopisania finansów,
append-only oraz przerwaną próbę i wznowienie. Testy parserów sprawdzają
błędny kwartał, GAAP vs non-GAAP, skalowanie i brak raportu. Nie osłabiono
istniejących guardów importerów ręcznych lub testów HTTP.
Obejrzano zrzuty automatycznej izolacji, normalnego desktop EN i mobile PL.
To nie jest pełny audyt WCAG. Logi i dokładne wyniki są w ignorowanym
data/raw/earnings-auto-monitor-2026-11-04 i logach monitor-final-* w
 data/raw/earnings-ui-alignment-2026-11-04.

## Normalna baza i przygotowany plan

Odczyty diagnostyczne były read-only. Target localhost:5432/macrolens,
rola macrolens, OID 16384, klaster 7682090371041935398, PG17.
Przed/po wszystkie 11 tabel Earnings są byte-identyczne, oba katalogi
schematu identyczne. 24 tabele: 3 086 205 → 3 086 206 rekordów.
Zmieniły się tylko source_check_runs i overview_refresh_state w zwykłej
pracy makro. Nie deklaruje się ich byte-identyczności. E2D nadal 27/46,
historia 23/45; ARM/QCOM Current null. Brak dwóch tabel monitora.
Market Cap pozostaje 49/53; danych/cache nie importowano.

Świeży pełny pg_dump custom: 32 098 275 B, SHA-256
`4031f01efae8de6d59249e13a11958f1677efe72d9397276408801caa406f28a`.
TOC i pełny restore na własnym PG17 passed: 24 tabele / 3 086 206 rekordów,
pełne dane i katalogi zgodne z eksportowanym snapshotem. Z tego archiwum
wykonano demonstrację; tożsamości klonu nie podstawiano pod normalny target.

Gotowy plan normalnej aktywacji ma pełny kanoniczny SHA-256:

`d66741f4ff719a4d4443b95d4467526a9aeca822ce907e5486f255cc40d03c11`

Plik: data/raw/earnings-auto-monitor-2026-11-04/normal-monitor-plan.json.
Wiąże 16 artefaktów, wersje bibliotek, dokładny target, pełne dane 11 tabel
Earnings i referencję katalogu przed/po. Zmiany makro nie podmieniają planu.
Zakres: nowe earnings_monitor_policy i earnings_report_checks z ochroną
append-only oraz rozszerzenie istniejącego CHECK verification_method
z manual_official_report_review o automated_official_report_validation.
Pozostałe zabezpieczenia E2D pozostają. Następnie jawne enable-runtime
wiąże lokalny token z tym planem i zezwala na automatyczne Current pilotów.
Nie dodaje firm, events, periods, forecast ani zmian Previous/Market Cap.

Runner wymaga osobnej zgody na ten pełny hash i target, backup/restore,
zgodności artefaktów i snapshotów po lockach 022/020 oraz SHARE 11 tabel.
DDL i policy zatwierdzają się razem po kontroli katalogu i pustego dziennika.
Zmiana danych/artefaktów zatrzymuje apply. Token nie jest tworzony podczas
startup/GET. Nie wykonano normalnego apply/enable-runtime ani rollbacku.
Przed ewentualnym apply należy ponownie sprawdzić zgodność backupu/planu.

## Pliki, ochrona i sprzątanie

Zmiany: app/api/main.py, app/api/earnings.py, app/earnings_reports.py,
frontend/src/calendar/EarningsCalendar.tsx. Nowe moduły: earnings_monitor,
earnings_monitor_policy, earnings_monitor_sources, earnings_monitor_runtime,
SQL i runner activate_earnings_monitor, config źródeł, test jednostkowy,
walidacja PG, test polling oraz ten raport. Zależności/lockfile/CI bez edycji.

Z 28 zastanych dirty/untracked plików zmieniono tylko uzgodniony Calendar
(polling). Pozostałe 27 są byte-identyczne, w tym chronione prace i audyty.
Własne API 8043, preview 4213 i Chrome CDP 9283 zakończono; klony usunięto.
Po kontroli pełnego ID, etykiety, baz i klientów usunięto tylko własny
kontener 6d1aedf0ee3ddd30351616ae893dbe25f1993cb14993093506ee3ba38ee8b24b
z anonimowym wolumenem. Normalny PG/API8000/Vite5173 pozostawiono działające.
Plan, backup, receipts, PDF i screenshoty pozostają ignorowane w data/raw.
Końcowo 19 modified / 23 untracked, indeks pusty, HEAD/main bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend lub formatowania globalnego.
