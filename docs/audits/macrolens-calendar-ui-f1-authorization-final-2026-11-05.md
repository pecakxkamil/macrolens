# MacroLens — Calendar UI i autoryzacja F1 V2: finalna gotowość

05.11.2026, Europe/Warsaw, C:\Projects\macrolens, main,
HEAD `c42cf6c411c85a64927fe5c6b3cf98f9e906c871`.

**Kod i pełne przejście sprawdzone na klonie. STOP przed normalnym APPLY.**
Normalny Calendar nadal używa poprzedniego kodu. Nie zmieniono normalnych
plików aplikacji, policy, tokenu ani danych. Nie wykonano commita/pusha/CI.

## Finalny plan wykonawczy

Pełny kanoniczny SHA-256:

`8e70cec78af59999f5e6e75c5e9b67c97f7be69f23ac071f9e56c93896b654c3`

Plan: `data/raw/calendar-ui-f1-final-2026-11-05/normal-executable-plan.json`.
To plan wykonawczy `version=2`, `revision=1`, `ready_for_apply=true` zgodny
z zaimplementowanym runnerem. Dwa niezależne prepare oraz ponowne rzeczywiste
CLI plan zwróciły identyczny dokument/hash. Próba klonu różni się wyłącznie
rzeczywistym targetem/target_label; nie podszywano się pod tożsamość normalnej bazy.

Target: **localhost:5432/macrolens, PG17, rola macrolens, OID 16384,
system_identifier 7682090371041935398**. Pierwotna policy ma check_id
`6ce8b8cb-8b4f-5c5d-a697-7a64b8daf97a` i plan
`33fb364f3f518a193d7d451c9dfad6f1d5e005eec2a67c8a01ab626c6c531289`.
Pierwotny kompletny plan i manifest 260 artefaktów pozostają w nowym planie
oraz niezmienionej starej policy. Historyczny hash jest ponownie obliczany.
Hash wcześniejszej propozycji d57df0… nie jest używany do APPLY.

Zakres zatwierdzenia: **jeden INSERT do forecast_refresh_checks** ze źródłem
`activation-ui-revision`, outcome=success, deterministycznym UUID,
retry_at=2099-01-01 i detail zawierającym cały plan oraz jego hash.
Bez DDL, UPDATE/DELETE, importu prognoz, zmiany freezes lub źródeł.
Następnie kontrolowane zainstalowanie 14 dokładnych plików UI/autoryzacji
z plan.delivery oraz nowego tokenu V2 po niezależnym verify, w uzgodnionym
krótkim oknie zatrzymania API/Vite. Testy dostarczono dodatkowo w patchu.

## Kod, manifest i ciągłość

Kod przygotowano w ignorowanej kopii
`data/raw/calendar-ui-f1-final-2026-11-05/review`, poza działającym runtime.
[Kompletny patch](../patches/macrolens-calendar-ui-f1-authorization-v2-2026-11-05.patch)
ma SHA-256 `63f0e0b34ed8d6d96a75ccad47aa5e0a69a1c29f6fa3224a796db33402d1eb9d`.
Obejmuje 15 ścieżek. `git apply --check` przeszedł na aktualnym working tree.
Oryginalny patch UI aeee91… wykorzystano bez odtwarzania rozwiązania od zera.

Nowe pliki: `app/database/forecast_f1_authorization_v2.py`,
`config/forecast_f1_runtime_manifest_v2.json`,
`tests/test_forecast_f1_authorization_v2.py` oraz dwa istniejące nowe pliki
słownika nazw z patcha UI. Minimalne zmiany backendu dotyczą wyłącznie
delegacji tokenu V2 w activate_forecast_f1.py i porównania załadowanego
manifestu backendu w forecast_f1_runtime.py. DDL F1 i kod monitora pozostają
identyczne.

Jawny manifest V2 obejmuje **152 ścieżki + trzy wersje bibliotek = 155
artefaktów**. Zachowawczo obejmuje całe aktualne app/config, wszystkie SQL,
requirements oraz wersje httpx/psycopg/pypdf. Ścieżki są zapisane w jawnej
posortowanej liście; brak pliku, nowy nieprzejrzany plik backendu/config,
usunięcie krytycznej pozycji lub zmiana hasha zatrzymują autoryzację.
Zmiana samej specyfikacji też zmienia kontrolowany hash.

Przeanalizowano importy AST, także względne i wewnątrz funkcji. Plan zawiera
krawędzie lokalnych importów oraz miejsca dynamicznych importów, SQL i
odczytów plików. AST nie jest deklarowane jako pełny dowód dynamicznej
zależności: obejmowanie całego app/config zabezpiecza konserwatywną granicę.
Łańcuch obejmuje połączenie, źródła i prawa, parser, importer, dispatch,
bindings, freeze, reader/API oraz lifecycle/coordinator. Zmienny lokalny
calendar_periods_v1.json jest używany przez istniejący kalendarz; krytyczna
projekcja okresów/czasów/serii jest nadal porównywana z historyczną policy.
Nie zamrożono całego zmiennego pliku dowodów jako stałych danych makro.

React nie jest importowany/wykonywany przez workera. Calendar GET odczytuje
dane; UI nie otrzymuje uprawnienia importu Forecast. Dotychczasowy POST
odświeżania makro nie jest autoryzacją F1. Dlatego teksty, nazwy, CSS, układ,
lokalizacje i testy React są poza manifestem **workera**, zachowując zwykłe
testy/TypeScript/build. Przyszła poprawka wyłącznie wizualna nie wymaga rewizji
SQL. Zmiana backendu/config/istotnej biblioteki, referencji lub metodologii
nadal wymaga właściwego przeglądu i autoryzacji; runner nie zatwierdza jej sam.

Odczyt V2 wymaga dokładnie jednej kompletnej rewizji pierwszego przejścia,
odpowiedniego UUID, hasha planu, pierwotnej policy, historycznego planu,
zgodnego manifestu, dispatch, schematu/zależności i referencji. Token wiąże
version=2, plan, target i manifest. Stary/obcy token lub częściowa/konfliktowa
rewizja są odrzucane. Kolejny backendowy upgrade wymaga osobnego protokołu;
nie dodano dowolnego automatycznego łańcucha zatwierdzającego nowy kod.

## Świeży backup i próba klonu

pg_dump custom: **32 716 514 B**, SHA-256:

`76c0ac04e25bd0d436d59c8337dfdca665a7836562c4386d9e072ab4db028280`

Normalny eksport miał wymuszone READ ONLY, jeden REPEATABLE READ i
pg_export_snapshot. Dump używał tego samego snapshotu. TOC i pełny restore
na własnym PG17, loopback 55527, kod 0: **29 tabel / 3 152 133 rekordy**,
pełne ordered binary COPY hash/count i oba katalogi zgodne, zero
niezwalidowanych constraints. Walidacyjna baza restore została usunięta.
Osobny pełny klon zachował własną prawdziwą tożsamość i przeszedł również
własny backup/restore przed migracją. Archiwa/manifesty/proofs są ignorowane.

Na pełnym klonie przeszły:

- zgodność historycznego planu i niezmiennej activation-policy;
- błędny hash/target, obca baza, brak artefaktów, obcy schemat;
- częściowa i konfliktowa rewizja, append-only SQL;
- rzeczywisty SQL 1/0 po INSERT: pełny rollback, wszystkie 29 tabel identyczne;
- równoległy aktywator oraz ograniczony lock timeout 5 s;
- prawidłowy zapis jednej rewizji, pozostałe 28 tabel byte-identyczne;
- ponowienie already_initialized bez nowych wierszy lub timestampów;
- zmiana CSS bez utraty autoryzacji, zmiana importera z poprawnym STOP;
- osobny proces workera pod rzeczywistym lease: busy, bez HTTP;
- prawdziwy autoryzowany worker: cooldown, added=0, frozen=0;
- restart rzeczywistego API 8057: ponownie activated=true/cooldown;
- pełne 29 tabel identyczne po workerze, API, Chrome i restarcie;
- instalacja dokładnych plików i tokenu w osobnym katalogu, idempotentne wznowienie.

Początkowy przebieg zatrzymał brak lokalnego dowodu kalendarza w kopii;
skopiowano rzeczywisty plik, pozostawiając ścisłe porównanie referencji.
Powtórzenie backupu wymagało nowej nazwy katalogu, ponieważ archiwów nie
nadpisuje się. Końcowy patch wymagał poprawnego znacznika braku końcowego
newline w nowym JSON. Poprawiono narzędzia i powtórzono odpowiednie kontrole;
nie osłabiano guardów ani asercji i nie zaliczano prób nieudanych.

## Calendar i testy

W przygotowanym UI jest domyślne **Wszystko**, kolejność
**Wszystko | Dane | Wyniki**, EN **All | Data | Earnings**. Świadomy wybór
przetrwał rzeczywisty cykl odświeżania i testy zegara. Ponowne zwykłe
otwarcie wybiera All. Słownik dla 53 CIK poprawia 37 nazw, m.in. AMD
„Advanced Micro Devices, Inc.”. Nie zmieniono nazw w bazie, tickerów,
aliasów lub linków.

Previous pozostaje zgodne z prawdziwym SQL/API: AMD Q3→Q2 2026 EPS 1.38 USD,
Revenue 11536000000 USD; AAPL Q4→Q3 FY2026 2.02 / 109417000000 USD;
PLTR Q3→Q2 2026 0.41 / 1935464000 USD. CRWD EPS Previous oraz ARM/QCOM
Previous zachowują null. ARM/QCOM Current Actual pozostają dostępne.
Nie zmieniono backendu Previous ani żadnych wartości finansowych.

| Kontrola przygotowanego kodu | Wynik |
|---|---|
| Pełny backend offline | **1588 passed**, 82.09 s |
| Pełny frontend offline | **775 passed / 37 plików**, 32.10 s |
| Nowe testy granicy V2 | **11 passed** w powyższym backendzie |
| TypeScript noEmit / production build | passed, Vite 4.62 s, chunk 407.04 kB |
| Wszystkie dotychczasowe PostgreSQL | **22/22 passed**: 20 CI, monitor i F2 |
| Nowa rzeczywista próba V2 | passed, osobny pełny klon |
| Chrome PL/EN, 1366/390 px | **328 kontroli / 13 API GET 200** |
| Restart, osobny proces, idempotentna instalacja | passed |
| Patch check / whitespace / ochrona plików | passed |

Chrome korzystał z production preview 4233 i rzeczywistego API/SQL klonu
8057, bez fixture odpowiedzi. Proxy preview przepuszczał wyłącznie GET.
Potwierdzono 14 nowcastów, guidance Revenue NVIDIA, brak jego Forecast EPS,
Market Cap, oba Previous, siedem kolumn Earnings, osiem makro, źródła,
wewnętrzny scroll telefonu i brak overflow strony. Brak błędów JS/console.error,
HTTP 503 i żądań przeglądarki do wydawców. Obejrzano desktop EN i mobile PL
po przewinięciu do wartości. Nie jest to pełny audyt WCAG.
Regresja F2 używała wyłącznie swoich fixture na osobnej bazie; bez nowych
rzeczywistych prognoz, kluczy lub kontaktowania dostawców.

## Dokładna kolejność cutover po zgodzie

1. Przed zmianą normalnych plików sprawdzić ich hashe przed z plan.delivery,
   hash planu, kopię stagingu, stary runtime/token/policy oraz aktualny backup.
   Uruchomić ponownie read-only CLI plan. Zmiana referencji lub F1 danych
   chronionych powoduje STOP i nowy plan; nie podmieniać zatwierdzonego hasha.
   Nowszy zgodny pełny backup/restore może być osobnym dowodem tego samego planu.
2. Ustalić krótkie okno. Zidentyfikować procesy API 8000/autoreload i Vite 5173,
   zapisać ich faktyczne komendy, zakończyć tylko te procesy i potwierdzić brak
   pozostałego workera oraz wolny lease F1. PostgreSQL pozostaje uruchomiony.
   Nie podmieniać plików przy działającym starym workerze.
3. Z przygotowanej kopii uruchomić poniższe CLI APPLY z dokładnym targetem,
   hashem i nowym plikiem receipt. Runner w jednej READ COMMITTED transakcji
   pobiera advisory 726530032/726530031, SHARE na referencjach i dwóch tabelach
   prognoz oraz SHARE ROW EXCLUSIVE na checks, lock_timeout 5 s,
   statement_timeout 120 s. Sprawdza wszystko ponownie przed i po INSERT.
   Nie używa makro lease 726530019; nie blokuje observations/features/Overview.
4. Niezależne CLI verify, nowy output. Sprawdzić oryginalną policy, jeden nowy
   check, wszystkie vintages/freezes i wcześniejsze tabele Earnings.
5. Dopiero z receipt **verified** uruchomić przygotowany install_reviewed.py.
   Sprawdza przed/po hashe wszystkich 14 plików; obcy working tree daje STOP.
   Zachowuje stare bajty i token w osobnym archiwum; instaluje dokładne pliki
   oraz atomowo wymienia sam plik tokenu. Nie zakłada atomowości całej operacji.
6. Z normalnego kodu wykonać read-only verify, wznowić API/Vite zapisanymi
   komendami i sprawdzić rzeczywisty runtime F1, monitor Earnings oraz Calendar.
   Przeprowadzić końcowe API/Chrome i weryfikację danych.

Runner: `review/app/database/forecast_f1_authorization_v2.py` w katalogu etapu.
Przykład sekwencji CLI, **wyłącznie po zgodzie**, z working directory review
i po ustawieniu dokładnych normalnych DB_* z lokalnej konfiguracji:

```powershell
$stage = 'C:\Projects\macrolens\data\raw\calendar-ui-f1-final-2026-11-05'
$python = 'C:\Projects\macrolens\.venv\Scripts\python.exe'
$hash = '8e70cec78af59999f5e6e75c5e9b67c97f7be69f23ac071f9e56c93896b654c3'
& $python -m app.database.forecast_f1_authorization_v2 plan --plan "$stage\normal-executable-plan.json" --backup "$stage\normal-backup.json" --out "$stage\pre-cutover-recheck.json"
& $python -m app.database.forecast_f1_authorization_v2 apply --plan "$stage\normal-executable-plan.json" --backup "$stage\normal-backup.json" --confirm-target 'localhost:5432/macrolens' --confirm-plan $hash --out "$stage\normal-revision-receipt.json"
& $python -m app.database.forecast_f1_authorization_v2 verify --plan "$stage\normal-executable-plan.json" --out "$stage\normal-revision-verified.json"
& $python "$stage\install_reviewed.py" --root 'C:\Projects\macrolens' --source "$stage\review" --plan "$stage\normal-executable-plan.json" --receipt "$stage\normal-revision-verified.json" --archive "$stage\normal-cutover-archive" --confirm-plan $hash
```

Każdy krok wymaga exit code 0 przed następnym; nowe wyjścia nie są nadpisywane.
CLI enable-runtime również istnieje, ale odrzuca nadpisanie starego tokenu;
sprawdzony instalator obsługuje zachowanie starego i dokładną wymianę nowego.
Przed COMMIT błąd wycofuje zapis. Po COMMIT, przy przerwaniu instalacji,
pozostawić usługi zatrzymane, odczytać receipt i stan plików, zweryfikować bazę
i wznowić idempotentną instalację zatwierdzonego pakietu. Nie uruchamiać starego
workera z nowym tokenem. Nie wykonywać automatycznego restore lub kasowania
rewizji; decyzja o cofnięciu po COMMIT jest osobna.

## Stan normalny i Git

Końcowy read-only ponownie potwierdził wszystkie 16 pełnych snapshotów
Earnings/F1 i oba katalogi bez zmian. F1 nadal ma 20 vintages, sześć null
freezes i dwa checks; aktywny stary token/260 artefaktów są zgodne.
F1 activated=true/cooldown; Earnings activated=true, loop_running=true,
completed. Market Cap cache nadal 49/53 i SHA 94ac71…799. Normalne makro
pracuje niezależnie; nie wymagano globalnej byte-identyczności jego zapisów.

Zapisano manifest wszystkich 445 zastanych plików i pełny dirty diff.
Wszystkie ich bajty zachowano, w tym 13 chronionych prac, cały nieaktywny F2,
wcześniejsze audyty i oryginalny patch/propozycję. Normalne źródła bez zmian.
Do repo doszły tylko ten raport i nowy patch; brak stagingu/commita/pusha,
reset/clean/amend/force/globalnego formatowania. Dokładny przyszły indeks/SHA
i wymagane CI należy zamknąć po zatwierdzeniu planu i bez dołączania cudzych
hunków. Lokalnych wyników nie przedstawia się jako Actions.

**Do zatwierdzenia pozostaje powyższy pełny hash, pojedynczy INSERT rewizji
i opisane kontrolowane okno instalacji plików/tokenu oraz restartu.**
Normalny UI nie wyświetla jeszcze poprawki; wdrożenie nie jest deklarowane.

Własne API 8057, preview 4233 i Chrome 9303 zakończono po weryfikacji PID/
argumentów. Klony usunięto, następnie własny kontener PG17 z wolumenem:
`3f2afa89c6116b732b26d99c635c561bc0f5ebb30dcddce37fefbb53424b5070`,
etykieta calendar-ui-f1-final-2026-11-05. Przed usunięciem potwierdzono brak
klientów i wyłącznie control/postgres/template. W trakcie regresji F2 nazwę
własnego kontenera dopasowano do istniejącej bramki, bez zmiany guarda.
Normalny PostgreSQL/API/Vite pozostawiono działające. Backupy, plany,
receipts, logi, zrzuty i finalna kopia kodu pozostają ignorowane w katalogu
etapu. Końcowo 9 modified / 24 untracked pliki, indeks pusty, HEAD bez zmian.
