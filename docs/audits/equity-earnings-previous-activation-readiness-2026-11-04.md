# MacroLens — Market Cap i gotowość E2E Activation

Wykonano **04.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`, main,
HEAD `94526c9cf0422dde041c69fd4fdec21549a8b39e`.

**Market Cap uproszczono lokalnie. E2E Activation przygotowano i sprawdzono
na klonie rzeczywistego backupu. Nie wykonano apply w normalnej bazie.**
Normalne Previous nadal pochodzi wyłącznie z istniejących E2B/E2D i dotyczy
czterech datowanych wydarzeń. Nowe 23 raporty / 45 metryk działają tylko
w izolacji. Nie wykonano stagingu, commita ani pusha.

## 1. Market Cap: wygląd i atrybucja

Siedem kolumn zachowano. Komórka kapitalizacji zawiera jedynie kwotę,
np. **4 937,5 mld USD**, albo `—`; jest wyśrodkowana, bez daty, nazwy
źródła, przycisku i panelu. Poprawiono grupowanie czterocyfrowych liczb
w polskim locale, używając niełamliwej spacji. Data, dostawca, źródłowy URL,
SHA odpowiedzi, czas pobrania i podstawa pomiaru pozostają w cache/API.

Bezpośrednio pod Market Cap jest jeden mały podpis z dwoma linkami:
DeltaScreener · TGMCharts. Nie ma powtórzeń w wierszach ani dużej stopki.
Ponownie odczytano [TGMCharts §19](https://tgmcharts.com/terms) oraz
[licencję DeltaScreener](https://deltascreener.com/data). Obie wymagają
widocznej nazwy i linku tam, gdzie wyświetlane są dane; nie wskazują
obowiązku powtarzania podpisu przy każdym pomiarze. Przyjęta forma jest
atrybucją bezpośrednio przy tej samej kolumnie danych, a nie w odległym
raporcie. Nie deklaruje się dodatkowych praw do samodzielnego feedu.

Aktualny cache zachowano: **49/53 emitentów**, 2 TGMCharts / 47 DeltaScreener,
wszystkie daty **2026-11-03**. TSM, ASML, ARM i SHOP nadal mają brak ze
względu na niepotwierdzony zakres ADR/klas. Nie pozyskano nowych kwot,
nie odnawiano dat pomiaru i nie użyto FMP. W zakresie 01.05–31.12 są
34 datowane wiersze, z czego 31 ma kapitalizację; SHOP nie ma tam eventu.

## 2. Polityka świeżości i odświeżania

Zmieniono limit wyłącznie zgodnie z tym zleceniem:

| Źródło lokalnego cache | Podstawa daty | Maksymalny wiek |
|---|---|---:|
| TGMCharts | Dzienny EOD / potwierdzony lastCloseDate | 7 dni kalendarzowych |
| DeltaScreener | Rzeczywista data miesięcznego pliku | 45 dni kalendarzowych |

Wiek liczony jest w UTC. Ponowne pobranie tego samego pliku nie zmienia
as_of. Niezmienione rekordy i lista braków nie powodują ponownego zapisu
cache, także po zmianie czasu pobrania. Brak nowszych danych nie usuwa
poprzednich wartości, jeżeli nadal są ważne według właściwej polityki.
Nie ma FX, nowych kapitalizacji lub migracji Market Cap w PostgreSQL.
Pierwszeństwo aktualnego zweryfikowanego snapshotu SQL przed cache zachowano.

Sprawdzono `app/api/main.py` i `app/analytics/overview_refresh.py`:
RefreshCoordinator uruchamia wątek na żądanie odświeżenia Overview,
koordynuje publikację makro, transakcje i istniejące lease. Nie jest
ogólnym lokalnym schedulerem. Podpięcie cen do tego mechanizmu wymagałoby
zmiany makro i jego zakresu odpowiedzialności. **Nie podpięto Market Cap
do Overview, Calendar GET ani nowego stale działającego procesu.**

Ręczne polecenie nadal działa:

```powershell
.venv/Scripts/python.exe -m app.earnings_market_cap_public refresh
```

Przygotowano formę dla ewentualnego przyszłego zewnętrznego harmonogramu:

```powershell
.venv/Scripts/python.exe -m app.earnings_market_cap_public refresh --if-due --event-date 2026-11-04
```

Wywołujący harmonogram musi przekazać zweryfikowany dzień wydarzeń Earnings.
Inny dzień niż dzisiejszy UTC daje no-op. Atomowe utworzenie dziennego pliku
próby blokuje kolejną próbę tego dnia, także po awarii. W tym trybie
miesięczny CSV jest sprawdzany dopiero przy wieku co najmniej 38 dni lub
braku ważnego snapshotu, najwyżej raz na trzy dni. Ręczny jawny refresh
pozostaje dostępny niezależnie od tej bramki. Nie zainstalowano zadania
systemowego i nie uruchomiono automatycznego odświeżenia w tym etapie.

Dotychczasowe ograniczenia requestów, odstęp, retry/backoff, cache godzinowy
odpowiedzi i brak sekretów zachowano. GET Calendar odczytuje tylko lokalny
plik i SQL read-only, bez HTTP do źródeł.

## 3. Przyczyna pustego Previous i dokładny zakres E2E

Normalna baza zawiera sześć wcześniejszych raportów E2B i 27 dokumentów E2D,
ale **nie ma `earnings_historical_reports`**. Sam frontend nie tworzy
historii. Dlatego cztery wydarzenia pilotów mogą użyć już istniejącego
poprzedniego eventu, a AAPL/PLTR/AMD nie mają skąd odczytać przygotowanych
historycznych snapshotów. Nie podstawiono ledgeru lub fixture do normalnego
API i nie dodano mapy wartości w frontendzie.

Ledger `config/earnings_previous_reviewed.json` zachowano byte-identycznie.
Zakres aktywacji to jedna tabela historii, jej constraints/indeksy, jedna
funkcja i trzy triggery, **23 snapshoty / 45 metryk: 23 Revenue i 22 EPS**.
CRWD ma wyłącznie Revenue; EPS pozostaje null ze względu na porównywalność
po splicie. Bez nowych earnings_events, earnings_periods, firm, prognoz
lub zmian E2A–E2D. Nie zmieniono wartości ani oficjalnych źródeł.

Czytnik nadal porównuje dokładny poprzedni kwartał, z rollover FY,
walutą/standardem/metodologią/share basis, bez nearest-report fallback,
FX i ADR. Nie miesza Current z Previous. ARM/QCOM pozostają bez Previous;
PANW/SNOW także nie zostały rozszerzone.

## 4. Runner prepare/apply i jego bramki

Nowy `app/database/activate_earnings_history.py` jest osobnym ręcznym
runnerem; nie importuje go startup/API. Wykorzystuje istniejący wzorzec
E2D Activation, pełne katalogi schematu, binary COPY po PK i walidację
backup/restore. Pierwotny importer historii nadal odrzuca normalną bazę;
nie osłabiono jego prefiksu. Specjalny zapis aktywatora ma dostęp dopiero
po zgodności pełnego planu, celu, artefaktów, backupu, dowodu restore,
manifestu, bieżącego schematu i wszystkich 23 tabel.

Prepare działa READ ONLY. Apply wymaga osobnej zgody i zatwierdzonego
okna bez innych klientów bazy; brak takiego okna jest błędem przed DDL.
DDL+seed wykonuje się razem w SERIALIZABLE, z lockami 726530019/726530020,
lock_timeout 5 s i statement_timeout 120 s. Import jest dokładnym snapshotem
23/45, bez poprawek lub nowych wersji. Niezgodność wycofuje całą transakcję.
Po COMMIT nie ma automatycznego rollbacku. Granice cofnięcia opisuje osobny
zamrożony dokument `equity-earnings-previous-activation-rollback-2026-11-04.md`.

## 5. Rzeczywisty backup i restore

Normalny cel potwierdzono read-only: **localhost:5432/macrolens**, rola
**macrolens**, OID **16384**, klaster **7682090371041935398**, PostgreSQL 17.
Nie zatrzymano normalnego makro. Z eksportowanego snapshotu REPEATABLE READ
READ ONLY wykonano prawdziwy pg_dump custom z wymuszonym read-only po stronie
pg_dump. Backup:

- plik lokalny: `data/raw/earnings-previous-readiness-2026-11-04/normal-e2e.dump`;
- rozmiar: **31 218 033 B**;
- SHA-256: `947e4ff0a8d092a0f72a8b204f5e892e871822dc9cd893dbb667c97e8ef104b5`;
- TOC zweryfikowane przez pg_restore --list;
- snapshot: **23 tabele / 2 963 496 rekordów**.

Pełny restore do własnej losowej bazy PG17 zakończył się kodem 0.
Porównano wszystkie rekordy/timestampy uporządkowanym binary COPY oraz
obie reprezentacje katalogów schematu: pełna zgodność, zero niezwalidowanych
constraints. Bazę testowego restore następnie usunięto, a dowód z hashem
zachowano w `normal-restore-proof.json`. Nie odtwarzano nic do normalnej bazy.

Następnie wykonano drugi restore normalnego backupu do własnego klonu.
Na tym klonie przeprowadzono osobny rzeczywisty backup/restore, prepare
własnego planu i próbę aktywacji. Token klonu jest odrębny od normalnego
planu. Normalny plan nigdy nie został przekazany do apply.

## 6. Wyniki próby i API/UI

Na klonie rzeczywistych danych: **created**, potem kontrolowane
**already_initialized**, bez dodatkowych rekordów, wersji lub timestampów.
Błąd SELECT 1/0 po pierwszym historycznym rekordzie wycofał razem cały DDL
oraz seed. Wszystkie pierwotne **23 tabele pozostały identyczne**.
Po aktywacji klon miał 24 tabele, z czego nowa historia ma 23 rekordy / 45 miar.
Testy dotychczasowej historii dodatkowo potwierdziły append-only, FK/CHECK,
rewizje, stale captures, constraints i brak dziedziczenia pominiętego EPS.

Izolowane API było read-only z lease tylko na własnej bazie; wrapper dodał
jedynie CORS preview. Nie podstawiano odpowiedzi. Previous sprawdzono
bezpośrednio przez prawdziwe API/SQL i Chrome, w tym:

| Bieżący / poprzedni okres | Previous EPS | Previous Revenue |
|---|---:|---:|
| AAPL Q4 / Q3 FY2026 | 2,02 USD | 109,417 mld USD |
| PLTR Q3 / Q2 2026 | 0,41 USD | 1,935464 mld USD |
| AMD Q3 / Q2 2026 | 1,38 USD | 11,536 mld USD |
| INTC Q3 / Q2 2026 | −2,16 USD | 16,128 mld USD |
| AMZN Q3 / Q2 2026 | 5,75 USD | 200,606 mld USD |
| NVDA Q2 / Q1 FY2027 | 2,39 USD | 81,615 mld USD |

Przyszła NVDA Q3 ma Current null i Previous Q2 2,46 USD / 96,221 mld USD.
Normalny Calendar nadal ma 4 eventy z Previous; klon z historią — 27.
ARM i QCOM pozostają null. EPS CRWD także null. Prognozy nie zostały dodane.
Normalnego Previous dla AAPL/PLTR/AMD nie deklaruje się jako aktywowanego.

## 7. Końcowy plan gotowy do osobnego zatwierdzenia

Plik: `data/raw/earnings-previous-readiness-2026-11-04/normal-plan.json`.
Kanoniczny pełny SHA-256:

`6d224e8299ba70a2c133e3c2cadc345a3ed16f60a41aefa7427892d112f073fb`

Status: `awaiting_explicit_approval_not_executed`, `ready_for_apply=true`.
Oznacza to gotowość artefaktu do zatwierdzenia, nie zgodę na zapis ani
obecne okno serwisowe. Po normalnym Chrome ponownie porównano plan,
wszystkie artefakty, backup i dowód restore oraz pełne 23 tabele: zgodne.
Hash ponownie obliczony z zapisanego JSON jest identyczny. Nie stosuje się
wcześniejszego tokenu E2D.

Do wykonania potrzebna jest osobna zgoda użytkownika obejmująca:

> Zatwierdzam E2E Activation wyłącznie planu SHA-256
> 6d224e8299ba70a2c133e3c2cadc345a3ed16f60a41aefa7427892d112f073fb
> dla localhost:5432/macrolens, roli macrolens, OID 16384, klastra
> 7682090371041935398, PostgreSQL 17. Zatwierdzam okno serwisowe i zatrzymanie
> zidentyfikowanego backendu oraz innych procesów zapisujących przed kontrolą
> integralności i apply. Zakres: jedna tabela historii z ochroną i 23 snapshoty /
> 45 miar, bez zmian E2A–E2D i Market Cap SQL. Po kontroli należy wznowić aplikację.

Przed zapisem trzeba ponownie sprawdzić target, brak innych klientów,
zgodność wszystkich 23 tabel, schematu, artefaktów, backupu i restore.
Każdy drift zatrzymuje apply przed zapisem. Nie podmienia się automatycznie
zatwierdzonego planu. Jeżeli dane/backup wymagają aktualizacji, potrzebne są
nowe przygotowanie, hash i osobna zgoda. Po COMMIT brak automatycznego cofnięcia.

## 8. Testy i ochrona normalnych danych

| Kontrola | Wynik |
|---|---|
| Pełny backend offline | **1461 passed**, pytest 88,66 s |
| Pełny frontend offline, Node 22.23.4 | **694 passed / 33 pliki**, 30,30 s |
| TypeScript noEmit | passed |
| Production build | passed, Vite 4,45 s; największy chunk 407,04 kB |
| Wszystkie poprzednie PostgreSQL | **16/16 passed** |
| Nowa walidacja E2E Activation | passed: backup/restore, bramki, rollback, idempotencja i API |
| Normalny Chrome | **841 kontroli / 28 API 200**, dodatkowo 37 GET 200 |
| Chrome klonu po aktywacji | **841 kontroli / 24 API 200**, dodatkowo 37 GET 200 |
| JS / console.error / HTTP 503 / publisher HTTP w GET/UI | zero |
| Normalne 23 tabele i oba katalogi przed/po | identyczne |
| Wszystkie 24 tabele klonu przed/po UI | identyczne |

Przeszły EN/PL, 1366/390 px, siedem kolumn, pojedyncza kwota Market Cap,
spacje tysięcy, atrybucja wyłącznie w nagłówku, brak daty/źródła w wierszach,
49/53 danych w cache, cztery braki, Current/Previous Actual/Prognoza,
źródła raportów, zakresy, domeny, wewnętrzny scroll telefonu i brak overflow
całej strony. Obejrzano desktop EN i mobile PL obu środowisk. To nie pełny WCAG.

Pierwsza referencja nowego testu próbowała powtórnie walidować już
znormalizowane rekordy przez pierwotny importer; poprawiono harness na
dokładny zapis aktywatora. Frontendowy test braku linku dotyczył wcześniej
całej tabeli; po dodaniu wymaganych linków w nagłówku zawężono go do wiersza,
który nadal nie może otrzymać fikcyjnego źródła raportu. Wszystkie pozostałe
asercje zachowano. Helper wydruku błędu testu wymagał UTF-8 na Windows.
Nieudanych prób nie zaliczono jako sukcesów, nie zwiększano timeoutów.

Normalne pełne snapshoty i katalogi przed/po są identyczne: 23 tabele /
2 963 496 rekordów. Zachowano **53 firmy, 55 aliasów, 37 okresów/eventów,
40 evidence, 66 confirmations, 6 dokumentów/12 miar E2B i 27/46 E2D**.
Nie ma historii E2E ani store Market Cap. Każde połączenie diagnostyczne
normalnej bazy i pg_dump miało read-only. Nie wykonano normalnego DDL,
importu Previous/Market Cap, UPDATE/DELETE, restore, rollbacku ani lease.
Nie zatrzymywano zwykłych procesów makro. API 8000 i Vite 5173 działają.
R1–R3, K2, Overview, ich źródła i interwały nie zostały zmienione.

## 9. Pliki, zachowanie prac i zakończenie

Zmieniono siedem zastanych plików:

- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/EarningsCalendar.test.tsx
- frontend/src/calendar/earningsMarketCap.ts
- frontend/src/calendar/EarningsMarketCap.test.tsx
- app/earnings_market_cap_cache.py
- app/earnings_market_cap_public.py
- tests/test_earnings_market_cap_public.py

Dodano pięć:

- app/database/activate_earnings_history.py
- tests/test_earnings_history_activation.py
- tests/postgres_earnings_history_activation_validation.py
- docs/audits/equity-earnings-previous-activation-rollback-2026-11-04.md
- ten raport.

Z 55 zastanych zmienionych/nieśledzonych plików **48 zachowano
byte-identycznie**, w tym wszystkie 13 chronionych plików użytkownika,
wcześniejsze audyty, ledger/kod E2E i aktywator E2D. Zależności, lockfile,
CI, globalny CSS i poprzednie dokumenty pozostały bez zmian tego etapu.

Końcowy Git: **21 modified / 39 untracked**, indeks pusty, main i HEAD bez
zmian. Bez stagingu, commita, pusha, resetu, clean, amend i globalnego formatowania.
Pełne manifesty/diffy, backupy, plany, wyniki, logi i zrzuty są ignorowane
w `data/raw/earnings-previous-readiness-2026-11-04/`.

Własne API/preview/Chrome zakończono, lease izolacji zwolniono i wszystkie
własne losowe bazy usunięto. Po potwierdzeniu pełnego ID
`f1b470513f392a9d33b396225ca5ea20499d0dc235a9227f6b63dd283bdd030e`,
etykiety i braku baz poza control/postgres/template usunięto wyłącznie
własny kontener PG17 i anonimowy wolumen. Normalny PostgreSQL i aplikacja
pozostają uruchomione. Backup, cache i plan zachowano lokalnie do dalszej
pracy; żadne pełne komunikaty, sekrety lub normalne dane nie trafiły do Git.
