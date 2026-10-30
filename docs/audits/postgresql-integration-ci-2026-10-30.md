# MacroLens — H1: PostgreSQL integration w CI

Weryfikacja **30.10.2026**, Europe/Warsaw, `C:\Projects\macrolens`.
`main`, HEAD `66043ed4c8b2252e99525b8a5e4f1d11c60444b3` —
`Add release-aware BEA publication refresh`. Dodano trzeci job do istniejącego
MacroLens CI i blokadę niezamierzonego HTTP w czterech walidacjach SQL.
**Bez stagingu, commita i pusha.** Nie uruchomiono nowego workflow na GitHubie.

## Stan początkowy i granice

Potwierdzono HEAD, gałąź, 4 modified / 2 untracked oraz pusty indeks.
Przeczytano workflow, Compose, requirements, połączenia i inicjalizator SQL,
schemat, cztery skrypty i używane fixtures oraz audyty Empire/FT900/BEA/R3.
Dotychczasowe CI miało wyłącznie backend offline i frontend/build. Wyniki
1119/605 z zamknięcia R3 były punktem odniesienia, nie nową walidacją H1.

Offline pytest celowo blokuje prawdziwe HTTP i PostgreSQL. Nie potwierdza
semantyki PostgreSQL: DDL upgrade, FK, indeksów, advisory lock, UUID/datetime,
savepointów, transakcji i rollbacku. Nowy job uzupełnia tę lukę, zachowując
dotychczasową izolację. Backend i frontend oraz ich timeouty, blokady,
triggery push/PR do main i workflow_dispatch, uprawnienia `contents: read`
oraz concurrency pozostały identyczne względem HEAD.

Nie zmieniono kodu produkcyjnego, schematu/init_db, requirements/lockfile,
Compose, UI, miar, MCI/PIT, polityki R3 ani interwałów 900/21600 s.
Nie wykonywano ingestion, backfillu, nowych pobrań wydawców ani DDL na bazie
użytkownika. Instalacja pakietów do walidacji Linux dotyczyła wyłącznie
usuwanego kontenera, nie zależności projektu lub hosta.

## Nowy job i środowisko

`postgres-integration`, nazwa **PostgreSQL integration tests**, jest niezależny
od dwóch wcześniejszych jobów: Ubuntu 24.04, Python 3.12, timeout 15 minut,
instalacja istniejącego requirements.txt. Zachowano pełne SHA pinowanych
actions/checkout i actions/setup-python oraz `persist-credentials: false`.

Serwis `postgres:17` używa oficjalnego mechanizmu
[GitHub Actions services](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).
Job działa bez kontenera, więc hostem klienta jest **127.0.0.1**, nie nazwa
`postgres`. Port ma jawne mapowanie **127.0.0.1:5432:5432**.
Healthcheck: `pg_isready -U macrolens_ci -d macrolens_ci_control`, interwał
5 s, timeout 5 s i 10 prób. Brak wolumenu produkcyjnego i repository secrets.
Usługa jest usuwana przez runner po jobie.

| Zmienna | Wartość / pochodzenie |
| --- | --- |
| PYTHON_DOTENV_DISABLED | 1 |
| FRED_API_KEY | pusta |
| DB_HOST | 127.0.0.1 |
| DB_PORT | 5432 |
| DB_NAME / POSTGRES_DB | macrolens_ci_control |
| DB_USER / POSTGRES_USER | macrolens_ci |
| DB_PASSWORD | losowa wartość generowana w jobie, maskowana przed eksportem do GITHUB_ENV |

Wyłącznie efemeryczny serwis testowy używa `POSTGRES_HOST_AUTH_METHOD=trust`.
Nie ma hasła serwera do ujawnienia w logu startu usługi. Wymagany przez
kontrakt aplikacji niepusty DB_PASSWORD jest maskowaną wartością klienta;
trust nie używa go do uwierzytelnienia. Nie jest to test uwierzytelniania
hasłem ani konfiguracja zalecana dla produkcyjnego PostgreSQL. W tym jobie
nie ma produkcyjnych hostów, sekretów, bazy `macrolens` ani lokalnego `.env`.
Rola testowa może tworzyć bazy, co jest niezbędne dla istniejących skryptów.

## Historyczny baseline i cztery kroki

Zweryfikowano bezpośrednio obiekt przez git cat-file, treść przez git show,
historię schema.sql oraz git merge-base --is-ancestor. Baseline
**0147d6e1fc64d3c5e317f724e8f264fb119760b8** jest przodkiem HEAD i dokładnym
rodzicem `cae63e39f9de1a434b0c98df6525ee9f878eb360`, który dodał tabelę
publisher_documents i dwa FK. W starym schemacie tych obiektów nie ma.

Tylko nowy job ma `fetch-depth: 0`. Wcześniejsze checkouty nie pobierają
dodatkowej historii. Osobny krok sprawdza istnienie i przodka baseline,
odczytuje jego schema.sql i odrzuca baseline zawierający publisher_documents.
Nie zastąpiono historycznego upgrade porównaniem nowego schematu z samym sobą.

Każdy z poniższych skryptów ma odrębny, nazwany krok, bez continue-on-error,
warunkowego pomijania lub potoków ukrywających niezerowy kod:

| Komenda | Co rzeczywiście sprawdza |
| --- | --- |
| `python tests/postgres_empire_validation.py --baseline 0147d6e1fc64d3c5e317f724e8f264fb119760b8` | Fresh i historyczny upgrade, ponowna inicjalizacja, nullable FK/indeksy, FRED/ALFRED, idempotencja, rewizje, RAW/hash, błędy źródła i rollback |
| `python tests/postgres_ft900_validation.py` | UUID/datetime w receipts, idempotencja, zmiana projekcji BEA, rewizje i odzyskanie RAW, FRED/ALFRED i atomowy rollback |
| `python tests/postgres_bea_validation.py` | Syntetyczny dokument i rzeczywiste obserwacje/FK, selekcja BEA/FRED, idempotencja, rewizje intraday, RAW, HTTP/parser error i rollback |
| `python tests/postgres_bea_release_validation.py` | Wspólny lock, dwie instancje koordynatora, trwałe rezerwacje, GDP/PIO, częściowe PIO, zatrzymanie prób, nowy worker, backoff po rollbacku, generacje i FRED/ALFRED |

## Bezpieczeństwo i blokada HTTP

Przejrzano main() wszystkich skryptów. Empire tworzy dwie losowe bazy,
pozostałe po jednej. Nazwy mają własne prefiksy i UUID oraz są różne od bazy
kontrolnej. CREATE/DROP używa psycopg.sql.Identifier. Empire śledzi tylko
faktycznie utworzone nazwy; pozostałe wykonują DROP dopiero po udanym CREATE.
Cleanup jest w finally, po wyjściu z kontekstów połączeń. Nie znaleziono
wąskiego błędu cleanup wymagającego zmiany modelu lub utraty asercji.

Dodany `tests/postgres_http_guard.py` otacza wejście każdego skryptu.
Blokuje prawdziwe transporty httpx sync/async i urllib.urlopen, zachowując
MockTransport. Rejestruje próbę i odrzuca całą walidację także wtedy, gdy
importer przechwyci wyjątek i potraktuje go jak zwykły błąd źródła.
Nie zmienia socketów ani libpq, więc lokalny PostgreSQL pozostaje rzeczywisty.
Fixtures i klienty używane przez te cztery skrypty pozostają syntetyczne.
Nie jest to systemowy firewall dla dowolnej przyszłej biblioteki sieciowej.

Cztery nowe testy offline sprawdzają MockTransport, niezmienione funkcje
socketów i przechwycone błędy httpx/async/urllib. Istniejące globalne blokady
pytest i Node no-network.cjs nie zostały osłabione. Prawdziwa baza nie oznacza
prawdziwych wydawców; ten zestaw nie jest pełnym e2e publikacji makro.

## Rzeczywista walidacja lokalna

Utworzono osobny, losowo nazwany kontener **PostgreSQL 17.11** z własnym
anonimowym wolumenem, kontrolną bazą i dynamicznym portem loopback 32768.
Wszystkie pięć zmiennych DB wskazywało wyłącznie ten serwer; dotenv był
wyłączony. Nie użyto istniejącego macrolens_postgres ani postgres_data.

| Walidacja | Windows / lokalny Python | Linux / Python 3.12.16 |
| --- | --- | --- |
| Empire fresh i upgrade | passed | passed |
| FT900 | passed | passed |
| BEA Direct | passed | passed |
| BEA release-aware | passed | passed |
| Testy blokady HTTP | 4 passed | 4 passed |

Linux używał kontenera python:3.12-slim, kopii śledzonych plików HEAD z
nałożonymi zmianami H1, bez `.env` i RAW użytkownika. Oryginalne .git było
montowane read-only dla prawdziwego git show. Zależności z requirements
i git zainstalowano tylko w tym kontenerze. Klient Linux współdzielił
namespace sieciowy własnego PostgreSQL, więc używał 127.0.0.1:5432;
Windows korzystał z mapowanego portu. To nie jest uruchomienie runnera
Ubuntu 24.04 lub platformowego lifecycle usług GitHub Actions.

Wszystkie skrypty zakończyły się kodem 0. Sprawdzono następnie brak pozostałych
baz testowych; zostały tylko kontrolna, postgres i template. Niepoprawny
endpoint 127.0.0.1:1 zwrócił niezerowy kod, bez tworzenia bazy. Niezerowy
skrypt i niezdrowa usługa nie mają ścieżki do zielonego wyniku w workflow.
Po walidacji usunięto wyłącznie własne kontenery i anonimowy wolumen,
uprzednio sprawdzając ich losową nazwę/ID i własną etykietę. Istniejący
kontener użytkownika pozostawiono bez resetu lub usuwania.

| Pozostała kontrola H1 | Nowy wynik |
| --- | --- |
| Pełny backend offline | **1123 passed**, 57,06 s — 1119 wcześniejszych + 4 testy guard |
| Pełny frontend, blokada sieci CI | **605 passed / 25 plików**, 26,92 s |
| Osobny TypeScript typecheck | passed |
| Production build | passed, **543,90 kB**, gzip **158,02 kB** |
| actionlint oraz parser YAML | passed |
| git diff --check | passed |

Porównanie sparsowanego YAML z HEAD potwierdziło identyczne oba wcześniejsze
joby, triggery, permissions i concurrency. Nowy job nie ma needs, produkcyjnych
sekretów ani własnego kontenera joba; ma cztery jawne kroki SQL.
Healthcheck i mapowanie portu sprawdzono także lokalnie przez Docker.
Ostrzeżenie Vite ponad 500 kB zachowano. Linux/R3 wypisał istniejące
StarletteDeprecationWarning dotyczące httpx; niczego nie wyciszano i nie
zmieniano dependencies. Nie pomijano testów i nie zwiększano timeoutów.

Nie wykryto niezgodności skryptów między Windows i Linux. Ignorowany helper
lokalnej walidacji początkowo użył nowszego argumentu tarfile.extractall,
niedostępnego w lokalnym Pythonie. Zastąpiono go jawną kontrolą ścieżek
zaufanego archiwum Git; nie zmieniano testów produkcyjnych. Standardowa
ścieżka Docker Desktop była nieaktualna; uruchomiono znalezioną instalację
użytkownika w tle, bez resetowania kontenera lub wolumenu.

## Zakres i końcowy Git

Osiem plików H1:

- `.github/workflows/ci.yml`
- `tests/postgres_empire_validation.py`
- `tests/postgres_ft900_validation.py`
- `tests/postgres_bea_validation.py`
- `tests/postgres_bea_release_validation.py`
- `tests/postgres_http_guard.py` — nowy.
- `tests/test_postgres_http_guard.py` — nowy.
- `docs/audits/postgresql-integration-ci-2026-10-30.md` — ten raport.

Zmiany czterech dotychczasowych skryptów ograniczają się do opakowania main()
blokadą HTTP. Nie przepisano ich asercji ani cleanup. Diagnostyka, logi,
kopie i helper lokalnego Dockera pozostają ignorowane w
`data/raw/pg-ci-h1-2026-10-30/`, poza zakresem Git.

Sześć chronionych plików zachowano byte-identycznie, SHA-256 przed = po:

| Plik | SHA-256 |
| --- | --- |
| README.md | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` |
| frontend/src/brief/SourceCheckStatus.tsx | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` |
| frontend/src/brief/SourceCheckStatus.test.tsx | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` |
| frontend/src/styles.css | `7696bd5cac8c8bb3792f86d23e588c97f1fd87a5aef407a9f141ceb07b9b20e0` |
| docs/audits/calendar-next-releases-priority-2026-10-29.md | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` |
| docs/audits/calendar-release-day-latency-2026-10-29.md | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` |

`main`, HEAD bez zmian. **9 modified / 5 untracked**, staging pusty:

```text
 M .github/workflows/ci.yml
 M README.md
 M frontend/src/brief/SourceCheckStatus.test.tsx
 M frontend/src/brief/SourceCheckStatus.tsx
 M frontend/src/styles.css
 M tests/postgres_bea_release_validation.py
 M tests/postgres_bea_validation.py
 M tests/postgres_empire_validation.py
 M tests/postgres_ft900_validation.py
?? docs/audits/calendar-next-releases-priority-2026-10-29.md
?? docs/audits/calendar-release-day-latency-2026-10-29.md
?? docs/audits/postgresql-integration-ci-2026-10-30.md
?? tests/postgres_http_guard.py
?? tests/test_postgres_http_guard.py
```

Bez stagingu, commita, pusha, resetu, clean, amend lub zmiany historii.
Nowy job nie został jeszcze uruchomiony na GitHubie; nie ma jego wyniku ani
nowego URL workflow. Weryfikacja platformowa wymaga późniejszego commita/pusha.
Nie rozpoczęto H2, nowych integracji ani zmian produkcyjnego odświeżania.

## Kontrola zamknięcia H1 — 30.10.2026

Stan wejściowy zamknięcia ponownie potwierdzono: `main`, HEAD
`66043ed4c8b2252e99525b8a5e4f1d11c60444b3`, 9 modified / 5 untracked,
pusty indeks. Aktualne SHA-256 sześciu chronionych plików zgadzały się
z tabelą raportu. Przejrzano pełny diff i wszystkie osiem plików H1.
W czterech wcześniejszych skryptach część przed wejściem main() pozostaje
identyczna z HEAD: zachowano wszystkie asercje, transakcje i cleanup.
Nie znaleziono błędu wymagającego zmian kodu H1 podczas zamknięcia.

Sprawdzono ponownie, że dwa wcześniejsze joby, permissions, concurrency
i triggery są identyczne względem HEAD. Nowy job jest niezależny i ma
Ubuntu 24.04, Python 3.12, serwis postgres:17, healthcheck, cztery osobne
kroki, brak continue-on-error i jawny port 127.0.0.1:5432:5432.
Trust jest ograniczony do efemerycznego serwisu; maskowany losowy DB_PASSWORD
zapewnia tylko zgodność z kontraktem klienta. Nie ma produkcyjnych sekretów
ani testu produkcyjnego uwierzytelniania. Zapis portu przejrzano również
w publicznym kodzie runnera, ale nie zastępuje to uruchomienia na platformie.

Baseline 0147d6e1fc64d3c5e317f724e8f264fb119760b8 ponownie sprawdzono przez
cat-file, git show i relację przodka. Nie ma w nim publisher_documents ani
source_document_id/publication_document_id. Tylko nowy job pobiera pełną
historię. Rzeczywisty test Empire ponownie wykonał fresh oraz upgrade
własnych baz od starego schematu, bez zmniejszania zakresu.

### Nowe przebiegi working tree i dokładnego indeksu

| Kontrola | Working tree | Staging-only |
| --- | --- | --- |
| Pełny backend offline | **1123 passed**, 57,92 s | **1123 passed**, 66,02 s |
| Pełny frontend offline | **605 passed / 25 plików**, 26,46 s | **605 passed / 25 plików**, 27,94 s |
| Osobny TypeScript typecheck | passed | passed |
| Production build | passed | passed |
| actionlint i kontrola YAML | passed | passed |
| Empire fresh / historyczny upgrade | passed | passed |
| FT900 PostgreSQL | passed | passed |
| BEA Direct PostgreSQL | passed | passed |
| BEA release-aware PostgreSQL | passed | passed |
| Guard HTTP sync/async/urllib/MockTransport | **4 passed** | **4 passed** |

Oba zestawy SQL przeszły osobno z Windows oraz Linux/Python 3.12.16,
na dwóch odrębnych efemerycznych serwerach PostgreSQL 17.11. Każdy skrypt
zakończył się rzeczywistym kodem 0 po swoich asercjach. Sprawdzono brak
pozostałych baz testowych, a błędny endpoint ponownie dał niezerowy kod.
Własne kontenery i ich wolumeny usunięto po sprawdzeniu etykiet oraz ID.
Nie resetowano istniejącego kontenera/volumenu użytkownika i nie uruchamiano
na jego bazie DDL, inicjalizatora ani ingestion.

Kopia całego indeksu używa śledzonych zależności z HEAD, w tym wcześniejszych
wersji README/SourceCheckStatus/CSS, bez dwóch wcześniejszych nieśledzonych
audytów. Porównano identyfikatory Git wszystkich ośmiu plików z eksportem,
uwzględniając normalizację LF/CRLF. Nie zależy od chronionych zmian użytkownika.
Główny pakiet: working tree **543,90 kB**, gzip **158,02 kB**; indeks
**545,95 kB**, gzip **158,48 kB**. Ostrzeżenia Vite ponad 500 kB pozostają.
Linux/R3 ponownie wypisał StarletteDeprecationWarning dotyczące httpx;
nie wyciszano go i nie aktualizowano dependencies. Nie pomijano testów,
nie zwiększano timeoutów i nie zmieniano MCI/PIT.

Pierwsza próba ignorowanego helpera eksportu uruchomiona z podkatalogu kopii
nie uzyskała poprawnego archiwum Git i zakończyła się przed utworzeniem
serwera. Poprawiono wyłącznie helper: kopiuje wskazane przez indeks pliki
z izolowanej kopii. Pełne ponowienie przeszło. Nie zmieniano skryptów,
asercji lub workflow, aby obejść tę usterkę diagnostyki.

### Zatwierdzany zakres i wynik po pushu

Staging zawiera dokładnie osiem plików H1 wymienionych wyżej. Przejrzano
cały staged diff, sprawdzono obie kontrole whitespace, wzorce sekretów,
brak .env, RAW/cache/logów, helperów i artefaktów kontenerowych. Kod
produkcyjny, schema.sql, requirements/lockfile, Compose, UI i R3 pozostają
bez zmian. Wszystkie sześć chronionych SHA-256 nadal zgadza się z tabelą
przed/po, a pliki pozostają poza stagingiem. Po walidacji uzupełniono tylko
ten raport, jego staging i kopię.

Planowany jeden commit: **`Add PostgreSQL integration tests to CI`**.
Pełny hash, wynik zwykłego pusha oraz rzeczywisty URL i zakończone wyniki
trzech jobów zostaną podane w zewnętrznym raporcie Codexa po ich uzyskaniu.
Nie deklaruje się przyszłego sukcesu platformy na podstawie actionlint
lub lokalnego Dockera. Zamknięcie wymaga rzeczywistego zielonego trzeciego
joba; nie powstanie dodatkowy commit wyłącznie dla wpisania jego wyniku.
Ograniczenie guarda do transportów httpx/urllib pozostaje jawne: nie jest
to uniwersalny firewall. Nie rozpoczęto H2 ani kolejnego etapu.
