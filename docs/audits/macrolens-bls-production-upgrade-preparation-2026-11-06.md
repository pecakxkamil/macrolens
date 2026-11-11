# MacroLens — kandydat BLS i przygotowanie upgrade'u autoryzacji F1 V2

06.11.2026, Europe/Warsaw, `C:\Projects\macrolens`, main,
HEAD `c42cf6c411c85a64927fe5c6b3cf98f9e906c871`.

**Zaimplementowano i sprawdzono działający kod w izolacji PG17. STOP przed
normalnym APPLY. Normalny backend, token i policy pozostają bez zmian;
normalna baza nie otrzymała BLS. Przejściowe timeouty normalnego API ustąpiły
bez restartu; końcowe Calendar/F1/Earnings zwróciły HTTP 200.**

## Finalny wykonywalny plan

Kanoniczny SHA-256:

`374e93e3c7f21cf232db989e0532045c073328f71b2e4c3e5b3da3265499e2ad`

Plan `version=3`, `ready_for_apply=true`:
`data/raw/bls-production-upgrade-2026-11-06/normal-reviewed-final.json`.
Osobne rzeczywiste CLI `plan` potwierdziło identyczny dokument/hash.
Finalny plan klonu różni się **wyłącznie prawdziwym targetem**; nie podstawiano
normalnej tożsamości pod izolację.

Target: localhost:5432/macrolens, PostgreSQL 17, rola macrolens,
OID 16384, system_identifier 7682090371041935398.

Zakres transakcji to dokładnie **trzy INSERT-y, bez DDL**:

1. Jeden oryginalny, przejrzany dokument do `publisher_documents`,
   source=`bls:employment`, kind=`employment-batch`.
2. Jeden receipt w `source_check_runs`, resource=`bls:employment:seed`,
   phase=`reviewed_snapshot_import_not_new_http`. Czas tego INSERT-u jest nowy;
   oryginalny capture zapisano osobno. To nie deklaruje nowego HTTP.
3. Jedna append-only rewizja `activation-bls-revision` w
   `forecast_refresh_checks`, wiążąca cały plan i jego hash.

Następnie niezależne verify oraz instalacja **13 dokładnych plików i tokenu
version=3** w osobno zatwierdzonym oknie. Nie nadpisuje się pierwotnej policy
ani rewizji UI. Nie importuje się Forecast, observations, computed_features,
Earnings lub Market Cap. Nie dodaje się tabel, emitentów lub wydarzeń.

Bootstrap z zachowanego dokumentu jest konieczny: dwugodzinne okno tej
publikacji minęło o 16:30 PL. Sama instalacja workera po tym terminie nie
powinna obchodzić jego limitu czasu ani deklarować świeżego pobrania.

## Zaimplementowany adapter i worker

Kod jest w ignorowanej kopii bieżącego working tree:
`data/raw/bls-production-upgrade-2026-11-06/review`.
[Kompletny patch do przeglądu](../patches/macrolens-bls-production-upgrade-2026-11-06.patch)
obejmuje 17 ścieżek; `git apply --check` przeszedł na normalnym working tree.
Patch służy do przeglądu. Instalator dostarcza dokładne bajty z kopii review.

SHA patcha:
`b49861f3a730d581450b498f0db57d2aee404080b74646741f15a452fbc28ac4`.
Kanoniczny SHA pełnego manifestu kodu backendu:
`541d41bf1a7156f1f9d3e90d9f037428118e0c19790309c9309f60be38823fb8`.

Produkcyjny adapter `app/ingestion/bls_employment.py` wykonuje jeden POST
zbiorczy do oficjalnego Public API. Nie korzysta z HTML zwracającego 403,
nie śledzi przekierowań, nie rotuje tożsamości, nie zakłada konta i nie używa
klucza. Twardy kontrakt obejmuje sześć SA serii:

| Calendar | BLS | Podstawa wejściowa / wynik |
|---|---|---|
| PAYEMS | CES0000000001 | poziomy w tys. osób → różnica miesięczna w tys. miejsc pracy |
| UNRATE | LNS14000000 | U-3, procent |
| CES0500000003 | CES0500000003 | private/all employees, USD za godzinę → pochodna m/m |
| CIVPART | LNS11300000 | aktywność zawodowa, procent |
| U6RATE | LNS13327709 | U-6 SA, procent |
| AWHAETP | CES0500000002 | private/all employees, godziny tygodniowo |

Parser odrzuca obce/NSA i zduplikowane serie, brak wymaganych miesięcy,
duplikaty obserwacji, niepoprawne okresy, NaN/Infinity, błędne poziomy i
zerowy mianownik. Roczne M13 nie zastępuje miesiąca. Sprawdza jednostkę,
jeżeli odpowiedź ją podaje. Anonimowy podstawowy format nie dostarcza
katalogu jednostek: nie udaje się pobrania nieobecnej metadanej. Podstawą
jest zamrożony kontrakt dokładnych oficjalnych identyfikatorów i jednostek.
[Dokumentacja BLS](https://www.bls.gov/developers/api_signature_v2.htm),
[ograniczenia i formaty](https://www.bls.gov/developers/api_faqs.htm).

NFP i AHE liczone są przez Decimal z zależności **tej samej odpowiedzi**.
AHE m/m jest jawnie pochodne i zaokrąglone do jednego miejsca; zachowano
również niezaokrąglony wynik i poziomy wejściowe. Dokument zachowuje
oryginalne bajty, SHA, HTTP capture, request, identyfikatory, release,
proof harmonogramu, metody, historię i footnotes. Kopia RAW pozostaje
ignorowana, a oryginalny tekst JSON jest także w metadata dokumentu.
Czytnik ponownie sprawdza hash, kontrakt i wynik parsowania.

Worker wymaga niezależnej autoryzacji version=3 przed HTTP i zapisem.
Ma własny account lease 726530033, trwały claim **przed HTTP**, minimum
15 minut między próbami i maksymalnie osiem prób w rolling 24 h. Błędy oraz
przerwania też zużywają próbę. Retry-After jest liczony od odebrania odmowy;
także termin dłuższy niż doba pozostaje aktywny po przekroczeniu rolling day.
Timeout 25 s, limit odpowiedzi 2 MiB, brak natychmiastowych retry.

Adapter działa tylko dla potwierdzonego release 50 i zgodnego miesiąca,
po oficjalnym czasie, w oknie dwóch godzin. Kompletna odpowiedź kończy
specjalne próby. Ponowne sprawdzenie harmonogramu nie reaktywuje importu.
Dokumentacja podaje limit 25 zapytań dziennie bez rejestracji; adapter
przyjmuje niższy limit ośmiu. Nie obserwuje wywołań innych aplikacji z tego
samego IP, więc nie gwarantuje dostępności całej pozostałej kwoty.

`bls_employment_runtime` korzysta z istniejącego `coordinator.launch`,
listenera uruchomień `app.earnings_monitor_runtime` oraz jednej kontroli
przy starcie. **Nie ma nowego timera, pakietu schedulera ani procesu.**
Okresowe wybudzanie zakłada aktywny dotychczasowy lifecycle Earnings;
nie jest uzależnione od otwartej strony. Polityki i kodu monitora nie edytowano.

W istniejącym `refresh_fred()` dodano także ograniczone pobieranie brakującego
okresu po release 50 mimo niezmienionych metadanych, w normalnym jobie/budżecie.
Po uzyskaniu okresu lub kompletnego BLS dodatkowe pobieranie ustaje.
Nie usunięto globalnych bramek świeżości czytnika FRED: bezpośredni BLS ma
osobną, zweryfikowaną projekcję. Nie oznacza się BLS jako FRED/ALFRED.

## Prawdziwe dane i semantyka Previous

Kandydacki adapter wykonał prawdziwe zapytania HTTP 200 wyłącznie w izolacji.
Końcowy zachowany dokument pobrał **backendowy startup bez przeglądarki**,
o **16:23:32.459984 PL**. SHA oryginalnej odpowiedzi:

`e60010ae46d44e5aa5d7e8dd951e6e98b3b0c21a5b7998149c845d1ced8475dd`.

Finalny plan jawnie wiąże ten istniejący capture. Jego późniejszy import
nie zmienia go w nowy HTTP ani w udowodniony first print.

| Miara | Actual w API klonu | Previous z tej samej odpowiedzi | Zmiana w Calendar |
|---|---:|---:|---:|
| NFP | +165 tys. | +60 tys. | +105 tys. |
| U-3 | 4,1% | 4,2% | −0,1 pkt proc. |
| AHE m/m | +0,4% | +0,3% | +0,1 pkt proc. |
| Participation | 61,9% | 61,8% | +0,1 pkt proc. |
| U-6 | 7,9% | 7,6% | +0,3 pkt proc. |
| Weekly hours | 34,4 | 34,4 | 0 |

AHE Actual to 100×(38,00/37,86−1)=0,369783…%, zaokrąglone do 0,4%.
Wrześniowe AHE w tej samej odpowiedzi jest również wyliczone i zaokrąglone,
a nie mieszane ze starszym FRED 0,132415…%.

Wrześniowy zapis ALFRED 159044−159015=**29 tys.** pozostał identyczny.
Październikowe **165 tys.** i zrewidowany wrzesień **60 tys.** są osobnym
snapshotem BLS. Nie nadpisano historycznych obserwacji lub first print.
API zachowuje alternatywę FRED, a UI wyjaśnia Previous BLS oraz wcześniej
lokalnie zapisane 29 tys. Nie deklaruje się kompletnego archiwum first print.

Calendar korzysta z istniejących komponentów. Zmiana +105 jest zielona,
spadek U-3 czerwony, zero neutralne — według dotychczasowej reguły liczbowej.
Wykres bierze punkty z tej samej odpowiedzi BLS, bez dokładania aktualnego
punktu do starej historii FRED. NFP ma dziewięć porównywalnych miesięcznych
zmian w zweryfikowanej odpowiedzi. Interpretacja wykorzystuje 165/60,
a nie 165/29. Bez nowych kolumn lub przebudowy układu.

## Autoryzacja i zgodność F1

Manifest rozszerzono z 152 do **156 ścieżek**, nadal obejmujących wszystkie
app/config, SQL i requirements, oraz trzy wersje bibliotek: razem
**159 artefaktów**. Specyfikacja manifestu też jest chroniona. Nie usunięto
żadnej wcześniejszej krytycznej ścieżki; React pozostaje poza uprawnieniem
workera, natomiast konkretna dostawa plików jest związana planem.

Nowy protokół sprawdza dokładnie jedną kompletną rewizję UI V2, jej pełny
hash i historyczny plan, pierwotną immutable policy, schemat, referencje,
dispatch, seed Forecast i prawdziwy target. Zachowuje pierwotny plan
`33fb364f3f518a193d7d451c9dfad6f1d5e005eec2a67c8a01ab626c6c531289`
oraz rewizję UI
`8e70cec78af59999f5e6e75c5e9b67c97f7be69f23ac071f9e56c93896b654c3`.

Nie jest to dowolny automatyczny łańcuch zatwierdzania backendu. Stary lub
obcy token nie uprawnia do BLS; nowy token bez zgodnego wpisu SQL również
nie wystarcza. Istniejący F1 nadal ma tę samą politykę źródeł, cooldown,
metodologię, prognozy i freezes. Tokeny testowe mają rzeczywiste tożsamości
klonów. **Nie utworzono normalnego tokenu version=3.**

## Backup, pełny klon i walidacja

Końcowy świeży normalny pg_dump custom: **33 897 874 B**, SHA-256:
`0039b71375bcf346e62f22d351c6411c75a8b0674b67fc3c9c94926f8350c119`.

Eksport miał jeden REPEATABLE READ READ ONLY, pg_export_snapshot i wymuszone
default_transaction_read_only dla pg_dump. TOC i pełny restore na własnym
PG17, loopback 55539, passed. **29 tabel / 3 301 844 rekordy**, wszystkie
pełne ordered binary COPY hash/count i oba katalogi zgodne ze snapshotem;
zero niezwalidowanych constraints. Klon przeszedł również swój własny
backup i pełny restore z jego prawdziwą tożsamością.

Po naturalnym dopisaniu checks przez normalny F1 wcześniejszy backup
prawidłowo nie przeszedł prepare. Wykonano nowy eksport/restore, zamiast
pomijać różnicę. Finalna próba używa identycznego chronionego stanu.

| Kontrola | Wynik |
|---|---|
| Pełny finalny backend offline | **1633 passed**, 89,45 s; 24 nowe testy adaptera |
| Pełny frontend offline | **945 passed / 45 plików**, 67,35 s; cztery nowe przypadki |
| Końcowy TypeScript noEmit | passed |
| Production build | passed, 4,19 s, największy chunk 407,05 kB |
| Nowe rzeczywiste PostgreSQL | **11 kontroli workera passed** |
| Dokładny finalny APPLY w klonie | trzy INSERT-y; SQL 1/0 wycofało wszystkie razem |
| Ponowienie i niezależny verify | passed; bez nowych wierszy lub timestampów |
| Pełne recovery po COMMIT, wyłącznie klon | wszystkie 29 snapshotów odtworzone; tożsamość DB zachowana |
| Instalacja, częściowe wznowienie, trzecie ponowienie | 13 plików zgodnych; stary token zachowany |
| Verify z osobnego procesu zainstalowanego kodu | passed |
| Rzeczywisty restart API i GET/UI | wszystkie 29 pełnych snapshotów identyczne przed/po |
| Chrome, realne SQL/API/production preview | **87 kontroli / 16 API HTTP 200**, PL/EN, 1366/390 |
| Patch check / ochrona zastanych plików | passed |

Testy obejmują pełny batch, brakujące/zduplikowane serie i miesiące, NSA,
jednostki, NaN, niepełne odpowiedzi, transport, limit bajtów, idempotencję,
restart po claim przed HTTP, account lease, quota ośmiu prób i trzydniowy
Retry-After. Nowy test wywołuje rzeczywiste kandydackie `refresh_fred()`:
niezmienione metadane, brak okresu → HTTP/ingest; po pojawieniu się okresu
→ brak kolejnego wymuszonego pobrania. Testy zachowują guard sieci/SQL.

Negatywne wstrzyknięcia stanu i MockTransport są jawnie syntetyczne,
wyłącznie w klonie. Po nich przywrócono wszystkie 29 tabel byte-identycznie.
Nie zaliczono ich do prawdziwych danych BLS. Końcowy upgrade zmienia tylko
publisher_documents, source_check_runs i forecast_refresh_checks. Wszystkie
13 tabel Earnings oraz forecast_vintages/freezes pozostały identyczne.

Chrome: własne API 8059, preview 4239, CDP 9347. Sprawdzono osobno sześć
Actual i Previous, kierunki delt, dziewięć punktów NFP z BLS, źródło i
rozróżnienie 60/29, sześć/osiem kolumn Wszystko/Dane, 14 nowcastów F1,
osiem wydarzeń i siedem kolumn Wyniki, guidance NVIDIA i brak overflow.
Bez JS/console.error, HTTP 503 lub żądań przeglądarki do wydawców.
Obejrzano desktop PL i przewinięty telefon PL z wykresem. To nie pełny WCAG.

API klonu utrzymywało własny macro lease, aby GET/polling nie uruchamiały
niezwiązanych importerów. BLS miał oddzielny autoryzowany zapis do tego samego
rzeczywistego klonu. Bez podstawiania odpowiedzi API/SQL lub liczb w React.

Nieudanych prób nie zaliczono: pierwsza kopia nie zawierała starych dokumentów
wymaganych przez testy aktywatorów; uzupełniono je i powtórzono pełny backend.
Pierwszy Vitest odziedziczył port API preview; powtórzono z domyślnym env.
Pomocniczy parser tekstu Chrome mylił kropkę jednostki „godz.” z liczbą;
poprawiono wyłącznie helper. Dokończono także kontrolę wznowienia instalatora.
Guardów i asercji danych nie osłabiano. Nie deklaruje się GitHub Actions.

## Pliki kandydata

Dokładna dostawa 13 ścieżek:

- app/bls_employment_runtime.py — nowy listener;
- app/forecast_f1_runtime.py — wybudzanie BLS i token version=3;
- app/analytics/calendar_readings.py — źródłowa projekcja;
- app/analytics/overview_refresh.py — brakujący okres bez zmiany metadanych;
- app/database/activate_forecast_f1.py — delegacja jawnej autoryzacji;
- app/database/forecast_f1_authorization_bls.py — nowy prepare/apply/verify;
- app/database/install_bls_reviewed.py — instalacja i wznowienie po verify;
- app/ingestion/bls_employment.py — nowy adapter/parser/store/projection;
- config/forecast_f1_runtime_manifest_v2.json — pełny nowy manifest;
- frontend/src/api/macrolens.ts — typy provenance;
- frontend/src/calendar/macroInsight.ts — jasna informacja o Previous/revizji;
- frontend/src/calendar/MacroTrend.tsx — wykres jednej odpowiedzi BLS;
- frontend/src/calendar/macroTrendData.ts — punkty tego samego źródła.

Dodatkowo patch zawiera tests/conftest.py, tests/test_bls_employment.py,
tests/fixtures/bls_employment_response.json i
frontend/src/calendar/BlsProjection.test.tsx. Oryginalna fixture jest
oznaczona jako rzeczywisty capture do testu offline, nie feed produkcyjny.

## Przyszłe wykonanie — wymaga osobnej decyzji

1. Ponownie sprawdzić responsywność normalnego API po wcześniejszych timeoutach,
   stary token/policy/monitor oraz before-hashe wszystkich 13 plików.
   **STOP przy niesprawnym API, nieznanym procesie lub zmienionych referencjach.**
2. Ponowić read-only CLI plan i backup/restore checks. Nowy zgodny backup
   może być osobnym dowodem; zmiana planu oznacza STOP i nowy pełny hash.
3. Dopiero po osobnej zgodzie na powyższy hash, trzy INSERT-y i okno
   zidentyfikować dokładne procesy API/Vite oraz ich komendy i je zatrzymać.
   PostgreSQL pozostaje uruchomiony. Potwierdzić zakończenie writerów.
4. APPLY z kopii review: READ COMMITTED, advisory 726530032/031/033,
   lock_timeout 5 s, statement_timeout 120 s. Krótkie SHARE na referencjach
   Earnings/makro i danych Forecast oraz SHARE ROW EXCLUSIVE na checks.
   Bez macro lease 726530019, DDL i globalnych blokad observations/Overview.
5. Niezależne verify; sprawdzić starą policy i rewizję UI, jeden nowy wpis
   autoryzacji, dokładny dokument i seed receipt oraz stary stan chroniony.
6. Z receipt verified uruchomić instalator: zachowuje stare bajty i token,
   sprawdza before/after i dostarcza dokładne 13 plików; atomowo wymienia
   sam token. Nie uznaje plików, SQL i tokenu za jedną atomową operację.
7. Verify z zainstalowanego kodu, wznowienie zapisanymi komendami,
   kontrola F1/Earnings, wszystkich sześciu Actual/Previous w API i Chrome
   oraz kolejnego rzeczywistego wybudzenia bez przeglądarki.

CLI runnera, z cwd `review` i dokładnymi normalnymi DB_*; **nie wykonano APPLY**:

```powershell
$stage = 'C:\Projects\macrolens\data\raw\bls-production-upgrade-2026-11-06'
$python = 'C:\Projects\macrolens\.venv\Scripts\python.exe'
$hash = '374e93e3c7f21cf232db989e0532045c073328f71b2e4c3e5b3da3265499e2ad'
& $python -m app.database.forecast_f1_authorization_bls plan --plan "$stage\normal-reviewed-final.json" --backup "$stage\final-backup\normal-backup.json" --out "$stage\pre-cutover-plan.json"
& $python -m app.database.forecast_f1_authorization_bls apply --plan "$stage\normal-reviewed-final.json" --backup "$stage\final-backup\normal-backup.json" --confirm-target 'localhost:5432/macrolens' --confirm-plan $hash --out "$stage\normal-apply-receipt.json"
& $python -m app.database.forecast_f1_authorization_bls verify --plan "$stage\normal-reviewed-final.json" --out "$stage\normal-verified.json"
& $python "$stage\review\app\database\install_bls_reviewed.py" --root 'C:\Projects\macrolens' --source "$stage\review" --plan "$stage\normal-reviewed-final.json" --receipt "$stage\normal-verified.json" --archive "$stage\normal-install-archive" --confirm-plan $hash
```

Każdy krok wymaga exit code 0 przed kolejnym i nowego outputu. Zachować RAW
wskazany w planie oraz kopię review. Token jest wydawany wyłącznie po verify.
Przed COMMIT błąd wycofuje wszystkie trzy INSERT-y. Po COMMIT, przy przerwanej
instalacji pozostawić usługi zatrzymane, zweryfikować receipt/bazę/pliki
i wznowić instalację tego samego zatwierdzonego pakietu. Nie uruchamiać starego
kodu z nowym tokenem. Nie wykonywać automatycznego restore normalnej bazy
lub kasowania rewizji; cofnięcie po COMMIT wymaga osobnej decyzji.

## Normalne środowisko i zakończenie

Normalny PostgreSQL nadal ma 29 tabel, zero dokumentów `bls:employment`
i zero `activation-bls-revision`. Ostatnia kontrola SQL potwierdziła zgodność
normalnych tokenów/policy F1 i Earnings oraz wszystkich **16 pełnych
snapshotów Earnings/Forecast** z końcowym normalnym backupem. Pierwotne
155 artefaktów F1 są zgodne. Sześć serii nadal nie ma października w SQL.
Market Cap cache ma ten sam SHA 94ac71…799, 49/53; skopiowano tylko istniejący
cache do izolacji, bez importu. F2 i jego pliki pozostały bez zmian.

W pierwszych kontrolach HTTP Calendar przekroczył 40 s, a osobne F1/monitor
status przekroczyły 10 s. Vite i SQL odpowiadały. Po zakończeniu testów
i sprzątaniu izolacji **bez restartu normalnego API** końcowe próby zwróciły
HTTP 200: F1 activated=true/cooldown, Earnings activated=true,
loop_running=true/completed. Calendar nadal zwraca sześć Actual null oraz
Previous 29 tys., 4,2%, 0,132415…%, 61,8%, 7,6% i 34,4. Dokładne odpowiedzi
są w plikach normal-*-recovered.json i normal-final-status-retry.json.
Nie ustalono przyczyny przejściowego opóźnienia; nie przypisuje się jej bez
dowodu adapterowi, którego normalny backend nie zawiera. Nie wydawano poleceń
restartu normalnych usług. Ponowne timeouty przed cutover oznaczają STOP.

Zachowano byte-identycznie wszystkie **494 zastane pliki**, w tym prace
Calendar, 13 chronionych plików i F2. Do normalnego repo dodano wyłącznie
ten raport i patch. Kod kandydacki, plany, dumpy, proofs, receipts, logi
i screenshoty pozostają ignorowane w katalogu etapu.

Własne API 8059, preview 4239 i Chrome 9347 zakończono po sprawdzeniu
PID/argumentów. Własny PG17 i jego wolumen usunięto dopiero po kontroli
pełnego ID `21bf949938b05c24c54f46104e6db328b0eada3f623073951cf23dbfa4466d8d`,
etykiety bls-production-upgrade-2026-11-06, listy wyłącznie własnych baz
i braku innych klientów. Usunięto jedynie własny junction node_modules;
docelowe normalne zależności zachowano. Nie usuwano kopii review lub dowodów.

Końcowo **30 modified / 73 untracked**, indeks pusty, HEAD bez zmian.
Bez stagingu, commita, pusha, reset/clean/amend/force i globalnego formatowania.
**Normalny Calendar nie został naprawiony ani aktywowany tym etapem.**
