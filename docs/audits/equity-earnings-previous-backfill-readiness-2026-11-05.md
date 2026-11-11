# MacroLens — uzupełnienie Previous: gotowość do osobnego zatwierdzenia

05.11.2026, Europe/Warsaw, `C:\Projects\macrolens`.

**STOP przed zapisem do normalnego PostgreSQL.** Siedem nowych raportów,
13 metryk sprawdzono na pełnym klonie PG17. Normalna historia nadal zawiera
23 raporty / 45 metryk. Nie wykonano normalnego APPLY, migracji, zmiany
autoryzacji F1, UI, stagingu, commita ani pusha.

## Pełny audyt datowanych wydarzeń

Rzeczywiste API, zakres 01.01–31.12.2026: **34 datowane wydarzenia, 68 pól
Previous**. Na wejściu 53 pola były dostępne, 15 brakowało w ośmiu wierszach.
Trzy niedatowane wydarzenia nie wymagają tworzenia fikcyjnych dat.
Sprawdzono dokładne poprzednie FY/Q, istniejące raporty oraz podstawę metryk.
Pełny wykaz wszystkich 34 i lista braków są w ignorowanym
`data/raw/earnings-previous-backfill-2026-11-05/audit.json`.

Pierwszy filtr oparty wyłącznie o potwierdzenia dat nie uwzględnił trzech
starszych pilotów datowanych przez `financial_release_date`. Porównanie
z pełnym API ujawniło ten błąd audytu. Końcowa partia obejmuje również
poprzedniki NVDA Q1 FY2027, INTC Q2 2026 i AMZN Q2 2026. Wcześniejszy
czteroraportowy plan `db5c8952…` jest nieaktualną próbą, nie planem zatwierdzenia.

### Oficjalne dokumenty i brakujące okresy

Wszystkie poniższe źródła odczytano bezpośrednio narzędziem WWW 05.11.2026.
Kwoty Revenue są skonsolidowane, kwartalne, USD; EPS to raportowany US GAAP
diluted na akcję. Bez non-GAAP, guidance, YTD, TTM, FX i przeliczania ADR.

| Wydarzenie → poprzednik | Koniec poprzedniego okresu | Release | Revenue źródłowe | EPS USD | Oficjalny dokument |
|---|---|---|---:|---:|---|
| ARM Q2 FY2027 → Q1 FY2027 | 2026-06-30 | 2026-07-29 | 1289 mln | 0.25 | [ARM 6-K / wyniki](https://investors.arm.com/node/8356/html) |
| QCOM Q4 FY2026 → Q3 FY2026 | 2026-06-28 | 2026-07-29 | 9947 mln | 1.87 | [QCOM SEC EX99.1](https://www.sec.gov/Archives/edgar/data/804328/000080432826000085/qcom062826erex991.htm) |
| PANW Q1 FY2027 → Q4 FY2026 | 2026-07-31 | 2026-09-01 | 3410 mln | -0.35 | [PANW IR](https://investors.paloaltonetworks.com/news-releases/news-release-details/palo-alto-networks-reports-fiscal-fourth-quarter-and-fiscal-10) |
| SNOW Q3 FY2027 → Q2 FY2027 | 2026-07-31 | 2026-09-02 | 1546793 tys. | -0.55 | [SNOW SEC EX99.1](https://www.sec.gov/Archives/edgar/data/1640147/000164014726000033/fy2027q2earnings.htm) |
| NVDA Q1 FY2027 → Q4 FY2026 | 2026-01-25 | 2026-02-25 | 68127 mln | 1.76 | [NVIDIA newsroom](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2026) |
| AMZN Q2 2026 → Q1 2026 | 2026-03-31 | 2026-04-29 | 181519 mln | 2.78 | [Amazon IR](https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-First-Quarter-Results/) |
| INTC Q2 2026 → Q1 2026 | 2026-03-28 | 2026-04-23 | 13577 mln | — | [Intel SEC EX99.1](https://www.sec.gov/Archives/edgar/data/50863/000005086326000077/q126earningsrelease.htm) |

Żaden z tych siedmiu okresów nie był zapisany w istniejącej historii.
ARM: EPS na ordinary share, bez zmiany liczby akcji; pozostałe EPS na common
share. QCOM 1.87 to GAAP, nie 2.21 non-GAAP. SNOW używa total revenue,
nie product revenue; jednostka tysiące zostaje zachowana. PANW i SNOW mają
ujemne raportowane EPS. NVIDIA 1.76 dotyczy kwartału, nie rocznego 4.90
ani non-GAAP 1.62. Amazon 181519 to total net sales, nie segment AWS.

### Dwa uzasadnione braki EPS

**CRWD Q2 FY2027 → Q1 FY2027:** raport jest już zaimportowany, Revenue
1385629000 USD pozostaje bez zmian. [Pierwotny komunikat](https://www.sec.gov/Archives/edgar/data/1535527/000153552726000022/crwd-20260603xex991.htm)
podaje diluted EPS 0.11 sprzed splitu 4:1. [10-Q, subsequent event](https://www.sec.gov/Archives/edgar/data/1535527/000153552726000025/crwd-20260430.htm)
pokazuje 0.03 jako pro forma, unaudited, po uwzględnieniu splitu.
Nie jest to non-GAAP; nie wolno jednak bez jawnej obsługi podstawy splitu
zastąpić nim istniejącego snapshotu `reported_diluted_total_eps` ani wyliczać
0.11/4 i zgadywać zaokrąglenia. Obecny raport nie jest aktualizowany.

**INTC Q2 2026 → Q1 2026:** oficjalny GAAP diluted EPS attributable to Intel
wynosi -0.73 USD. Źródło istnieje i nie ma problemu ADR. Current ma metodologię
`gaap_diluted_attributable_to_intel`, natomiast istniejący SQL historii
wymaga `reported_diluted_total_eps`; czytnik nie normalizuje tej pierwszej
podstawy do drugiej. Partia dodaje wyłącznie poprawne Revenue. Nie zmienia
etykiety EPS w celu obejścia guarda, schematu, czytnika ani aktywnego F1.
Pełna obsługa tej podstawy wymagałaby osobnego przeglądu modelu/autoryzacji.

Po izolowanym imporcie: **66/68 pól**, wszystkie 34 Revenue i 32 EPS.
Wszystkie 34 wydarzenia mają co najmniej jedną metrykę Previous.

## Mechanizm i kontrolowany plan

Dodano osobny pakiet `integrations/earnings_history_backfill`, poza
manifestem aktywnego backendu. Korzysta z istniejącego walidatora E2E,
deterministycznych fingerprintów/UUID oraz zatwierdzonej ścieżki INSERT
`activate_earnings_history.import_seed`. Walidator ładowany jest do prywatnej
instancji modułu z dodatkowym przejrzanym ledgerem. Nie zmienia globalnego
`app.earnings_history.DATA`, pierwotnego ledgeru, guarda izolacji lub runtime.

**Finalny kanoniczny SHA-256 planu:**

`b576ccc0df847e1fc6367c10cdc3be23ef3e7668c32019e9fcbac28d5b0c8df6`

Plan: `data/raw/earnings-previous-backfill-2026-11-05/normal-plan-final.json`.
Rzeczywiste read-only CLI prepare i ponowne plan zwróciły identyczny dokument
i hash. Plan klonu różni się wyłącznie prawdziwym targetem i target_label.

Target: **localhost:5432/macrolens, PostgreSQL 17, macrolens, OID 16384,
system_identifier 7682090371041935398**.

Zakres nowej zgody: **siedem INSERT do istniejącej
earnings_historical_reports, sześć par EPS/Revenue i jeden Revenue,
łącznie 13 metryk JSONB**. Historia 23/45 → 30/58. Bez nowej tabeli,
DDL, UPDATE/DELETE, wersjonowania istniejących dokumentów, emitentów,
eventów, okresów, zmian Current, poprzednich prawidłowych Previous,
Forecast lub Market Cap. Brak automatycznego workera/importu przy GET.

Plan wiąże cały ledger, operacyjny kod/JSON, 155 aktywnych artefaktów F1 V2,
pełne snapshoty 13 istniejących tabel Earnings oraz trzech Forecast,
publiczny schemat i krytyczne referencje F1. Przy zmianie — STOP, bez
automatycznego zastępowania zatwierdzonego dokumentu.

APPLY wymaga nowej jawnej zgody na pełny hash i target oraz zgodnego dowodu
backup/restore. Jedna READ COMMITTED transakcja, advisory 726530020,
SHARE na wszystkich istniejących tabelach Earnings w stałej kolejności,
lock_timeout 5 s i statement_timeout 120 s. Bez makro lease 726530019,
locków tabel makro lub zapisu policy/tokenów F1. Ponowna kontrola danych,
katalogów i artefaktów przed COMMIT. Błąd SQL wycofuje całą partię.
Zgodne ponowienie zwraca already_initialized bez nowych wierszy/timestampów.

## Backup, pełny restore i test importu

Świeży pełny `pg_dump custom`: **32827054 B**, SHA-256:

`939a7ffc8a11007c6cd6f6acad87c9db2dbbb55a6f9d3ddb8faff7d7904f0f43`

Jeden normalny REPEATABLE READ READ ONLY, pg_export_snapshot i dump tego
samego snapshotu z wymuszonym default_transaction_read_only. TOC i pełny
restore na własnym PG17: kod 0, **29 tabel / 3152366 rekordów**, pełne
ordered binary COPY hash/count i oba katalogi zgodne, zero niezwalidowanych
constraints. Baza weryfikująca restore została usunięta. Dowód wiąże target,
rozmiar/SHA archiwum i odtworzone dane. Backupy są ignorowane w RAW.

Z tego archiwum utworzono osobny świeży pełny klon finalnej partii siedmiu
raportów. Przed próbą wykonano także rzeczywisty backup/restore tego klonu.
**318 kontroli SQL/API** potwierdziło m.in. błędną zgodę/target, konkurencyjny
writer, rzeczywisty rollback po SQL 1/0 w środku partii, pięciosekundowy
lock timeout, obcy indeks, append-only oraz import i idempotencję.
Wszystkie 28 pozostałych pełnych tabel są byte-identyczne. Oryginalne
23 rekordy historii, także timestampy, pozostały byte-identyczne.

Rzeczywisty TestClient/SQL i osobne API klonu potwierdziły 34 datowane
wydarzenia, wszystkie siedem nowych poprzedników i dokładne FY/Q.
**692 porównania API** zachowania Current, istniejących Previous, okresów,
Forecast, dokumentów, czasu i Market Cap przeszły. Dwa pozostałe null
to wyłącznie opisane CRWD i INTC EPS.

## Testy i Chrome

| Kontrola | Wynik |
|---|---|
| Pełny backend offline, finalny kod | **1598 passed**, 80.67 s |
| W tym nowe testy operacji | **10 passed** |
| Pełny frontend, niezmieniony kod | **794 passed / 38 plików**, 76.26 s |
| TypeScript noEmit | passed |
| Production build | passed, 3.96 s, największy chunk 407.04 kB |
| Dotychczasowe PostgreSQL | **22/22 passed**: 20 nazwanych CI, monitor, F2 |
| Nowy pełny test backfill PG17 | **318 kontroli**, passed |
| Chrome PL/EN, 1366/390 px | **208 kontroli / 12 API GET 200**, passed |
| Pełne dane klonu przed/po końcowym UI | wszystkie **29 tabel identyczne** |

Chrome korzystał z własnego production preview 4241 i prawdziwego API 8061
na pełnym klonie PG17 55531. API miało wymuszone read-only; proxy dopuszczało
wyłącznie GET. Nie podstawiano odpowiedzi. Sprawdzono ARM 0.25/1289000000,
QCOM 1.87/9947000000, PANW i SNOW w API i komórkach Previous, oba języki,
desktop i wewnętrzny scroll mobile. Sześć kolumn Wszystko, osiem Dane,
siedem Wyniki, wspólna chronologia, 22:00+, ważność ≥200 mld USD,
kliknięcie do Wyniki, nazwy i linki zachowane. Nadal 14 nowcastów makro
i guidance NVIDIA. Brak JS/console errors, 503 i żądań do wydawców w tym
końcowym zestawie. Obejrzano zrzuty desktop i przewiniętej tabeli telefonu.
Nie deklaruje się pełnego audytu WCAG. Trzy starsze piloty zweryfikowano
przez pełne rzeczywiste SQL/API; końcowy zestaw widoku obejmuje listopad/grudzień.

Osobna próba makro obejmująca maj–grudzień ujawniła zastany błąd 503:
`forecast_f1.enrich_macro` próbuje użyć brakującego `event_id` starszego
wydarzenia. Kod aplikacji jest identyczny z wejściem; nie naprawiano go
w ramach importu historii ani nie zaliczono tej próby do sukcesów.
Pełne API Earnings dla tego zakresu działa. Końcowe testy Chrome używają
listopada/grudnia, a nie deklaracji poprawności całego historycznego makro.
Pomocniczy odczyt SHA początkowo wskazał ledger zamiast cache Market Cap;
poprawiono ignorowany helper i powtórzono pełną kontrolę integralności.

## Normalna aplikacja, ochrona i dalszy krok

Normalne 13 pełnych tabel Earnings oraz trzy Forecast, schemat i referencje
są zgodne z wejściem/backupem. F1 V2: **activated=true, cooldown**, 20 vintages,
sześć freezes, trzy checks i wszystkie 155 artefaktów zgodne. Earnings monitor:
**activated=true, loop_running=true, completed**. Normalne procesy nie były
zatrzymywane. F2 pozostaje nieaktywne; jego regresja używała swoich fixture
na osobnej bazie, bez nowych realnych danych lub kluczy.

Market Cap: cache 49/53, SHA
`94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799`
bez zmian/importu. Zwykłe procesy makro mogły pracować niezależnie; nie
przypisuje się ich zapisów tej operacji ani nie blokuje ich dla testów.

Zachowano bajty wszystkich **459 zastanych plików**, także 13 chronionych
prac i F2; manifest i pełny wejściowy diff są w ignorowanym RAW.
Dodano tylko pięć plików pakietu integracji, dwa testy i ten raport.
Nie zmieniono żadnego istniejącego pliku app/config/frontend, zależności,
lockfile, workflow ani wcześniejszego audytu. Indeks pozostaje pusty.

Po osobnej zgodzie należy ponownie sprawdzić read-only CLI plan, aktualność
pełnego backup/restore oraz targetu. Zmiana chronionego stanu wymaga STOP
i nowego planu do osobnego zatwierdzenia. Następnie APPLY dokładnego hasha,
niezależne verify, porównanie starych rekordów i API/Chrome normalnej
aplikacji. Po COMMIT nie wykonuje się automatycznego restore/rollbacku.
Nie używa się wcześniejszych zgód F1/E2E. **W tym etapie normalny import
nie został wykonany i brakujące Previous nie są jeszcze widoczne lokalnie.**

Własne API 8061, preview 4241 i Chrome/CDP 9311 zakończono po sprawdzeniu
PID/argumentów; Chrome zamknięto przez CDP. Usunięto dwa własne klony
oraz bazę regresji F2, następnie własny kontener i anonimowy wolumen po
kontroli pełnego ID
`ef4d57ae9d0efb8625f4821153653d2063b89a12c0a0604766af177f25f09f37`,
nazwy, etykiety `earnings-previous-backfill-2026-11-05`, braku klientów
i pozostawionych baz poza control/postgres/template. Normalny PostgreSQL,
API 8000 i Vite 5173 pozostawiono działające. Brak diagnostycznych lease.

Końcowy Git: **17 modified / 44 untracked**, indeks pusty,
HEAD `c42cf6c411c85a64927fe5c6b3cf98f9e906c871` bez zmian.
Osiem nowych plików zadania nie obejmuje wcześniejszych nieśledzonych prac.
Wszystkie 459 początkowych SHA zachowano; diff --check passed.
Bez reset, clean, git add, amend, force lub globalnego formatowania.
Plany, dump, dowody restore, receipts, pełne snapshoty, logi i screenshoty
pozostają ignorowane w RAW. Git nie zawiera pełnych dokumentów lub sekretów.
