# MacroLens — E2A Activation: diagnoza, plan i zatwierdzona aktywacja

Diagnostyka rozpoczęta **02.11.2026**, przygotowanie zamknięte
**03.11.2026, Europe/Warsaw**. `C:\Projects\macrolens`, `main`, HEAD
`14e4829d79f3f4f0916629a560cfc0cf2a122836`.

**Status: aktywowano 03.11.2026 w normalnej bazie localhost:5432/macrolens.**
Po przygotowaniu zatrzymano się przed pierwszym zapisem. „Kontynuuj”
nie zostało potraktowane jako zgoda na DDL. Dopiero późniejsze wyraźne
zatwierdzenie przez użytkownika pełnego hasha planu pozwoliło wykonać
aktywację. Przed nią dodatkowo odtworzono pełną kopię do oddzielnej bazy
i sprawdzono jej dane. Wyniki wykonania oraz normalnej aplikacji są w sekcji 9.

## 1. Faktyczna przyczyna błędu

To **brak schematu i danych Earnings w normalnej bazie**, a nie pusty
tydzień, stary endpoint lub pomylenie dat konferencji. Poprzedni E2A
celowo inicjalizował jedynie bazy efemeryczne; normalna aplikacja miała
już nowy frontend i API, lecz nie miała tabel potrzebnych czytnikowi.

Dowody z działającej aplikacji z 02.11:

| Kontrola | Rzeczywisty wynik |
| --- | --- |
| Backend | Proces Uvicorn `app.api.main:app --reload`, katalog `C:\Projects\macrolens`; sprawdzono też rzeczywisty worker |
| `/health` | HTTP 200 |
| `/api/v1/earnings/companies` | HTTP 200, trzy oficjalne CIK i tickery; endpoint jest statyczny i nie dowodzi obecności danych w SQL |
| `/api/v1/calendar/events?domains=earnings`, 02–08.11 | HTTP 503 |
| Ten sam endpoint, 17.11 | HTTP 503 |
| Ten sam endpoint, 29.10 | HTTP 503 |
| Treść błędu | `Calendar domain unavailable; earnings requires the opt-in E2A schema.` |
| To samo żądanie z Origin frontendu | HTTP 503 i prawidłowy `Access-Control-Allow-Origin: http://localhost:5173` |
| Działający Vite | Moduły Earnings HTTP 200 przez `localhost:5173`; brak override API, używany fallback `http://127.0.0.1:8000` |
| Bezpośredni czytnik SQL w read-only | `UndefinedTable`, SQLSTATE **42P01**, `relation "earnings_events" does not exist` |
| `earnings_*` | Brak tabel i funkcji; rekordów nie można odczytać, bo nie istnieją tabele — to nie poprawna pusta lista wydarzeń |

Konfigurację celu potwierdzono w workerze aplikacji, odczytując wyłącznie
niesekretne DB_HOST/DB_PORT/DB_NAME/DB_USER. Nie wypisywano sekretów ani
zawartości `.env`. Odczyt PostgreSQL miał `transaction_read_only=on`.
Nie uruchamiano przeglądarkowej aplikacji, której stary hook mógłby wykonać
POST refresh; odpowiedź dla frontendu sprawdzono bezpośrednim GET z Origin.

Po wznowieniu 03.11 API na porcie 8000 i frontend na 5173 **nie były
uruchomione** — próby połączeń zakończyły się URLError. Nie przypisuje się
im obecnie HTTP 503. PostgreSQL ponownie stał się dostępny i nowy preflight
03.11 potwierdził ten sam klaster/bazę oraz nadal brak obiektów Earnings.
Usług aplikacji nie uruchamiano automatycznie podczas oczekiwania na zgodę.

## 2. Jednoznaczny zatwierdzony cel

| Pole | Wartość |
| --- | --- |
| Endpoint klienta | **localhost:5432** |
| Baza | **macrolens** |
| Rola | **macrolens** |
| Kontener istniejącej usługi | **macrolens_postgres**, PostgreSQL 17.11 |
| OID bazy | **16384** |
| Identyfikator klastra | **7682090371041935398** |
| Uprawnienie CREATE w public | Potwierdzone |
| Obiekty Earnings / kolizje nazw | Brak |

Procedura porównuje także identyfikator klastra, OID i rolę, a nie wyłącznie
napis „macrolens”. Zmiana celu lub schematu makro po preflight zatrzymuje
aktywację. Nie wybiera innej bazy ani nie tworzy bazy o podobnej nazwie.

## 3. Osobna procedura aktywacyjna

Dodano `app/database/activate_earnings.py`. Istniejący
`init_earnings_db.py` pozostaje byte-identyczny i nadal odrzuca zwykłą bazę
macrolens. Ani API, ani start aplikacji nie wykonują nowej procedury.

`prepare` wykonuje wyłącznie preflight read-only i zapisuje lokalny plan.
`apply` jest osobną, jawną ścieżką: wymaga dokładnego celu i hasha
zatwierdzonego planu, zgodnych hashy SQL/importera/manualnych danych oraz
zweryfikowanej lokalnej kopii wskazanej dla tego samego klastra/bazy.

Plan z 03.11 jest zapisany w ignorowanym pliku:

`data/raw/earnings-activation-2026-11-02/activation-plan-2026-11-03.json`

Jego identyfikator SHA-256, liczony z kanonicznego JSON:

`1359b113b2171e751328d03d343b40b7864f9f73107de66364f5d94bfa1abdb5`

Pełny zakres DDL to istniejący, zamrożony hashem
`app/database/earnings_schema.sql`:

1. `public.earnings_companies`
2. `public.earnings_company_aliases`
3. `public.earnings_periods`
4. `public.earnings_events`
5. `public.earnings_source_evidence`
6. `public.earnings_date_confirmations`

Dochodzą wyłącznie ich PK/UNIQUE/FK/CHECK, indeksy, dwie funkcje
`earnings_confirmation_transition()` i `earnings_immutable()` oraz trzy
triggery tych tabel. Nie powstają nowe obiekty makro, schematy, schedulery,
widoki FRED ani tabele EPS/revenue. Przy pierwszej aktywacji wszystkie
nazwy Earnings muszą być wolne. Przy kompletnym, identycznym schemacie
powtórzenie pomija DDL; częściowy lub obcy schemat jest odrzucany.
Klauzule CREATE OR REPLACE / DROP TRIGGER w źródłowym SQL dotyczą jedynie
Earnings; procedura nie wykonuje ich na zastanym innym schemacie.

Zapis odbywa się w jednej transakcji SERIALIZABLE, z limitami oczekiwania
na lock i czasu polecenia. Używa dotychczasowego wspólnego lease
726530019 oraz locka importera 726530020, bez zmiany polityki R3. Kontroluje
sygnaturę schematu makro przed/po i zgodność nowego schematu ze wzorcem
rzeczywiście przetestowanym w PostgreSQL. Błąd DDL, walidacji lub importu
wycofuje **zarówno nowe obiekty, jak i dane**. Nic nie jest commitowane
między utworzeniem tabel a seedem.

## 4. Dokładny seed i semantyka dat

Importer czyta tylko zatwierdzony lokalny `config/earnings_manual.json`.
Nie pobiera SEC/IR ani nowych źródeł. Po pierwszym poprawnym zapisie
oczekiwane liczby rekordów to:

| Tabela | Rekordy |
| --- | ---: |
| earnings_companies | 3 |
| earnings_company_aliases | 3 |
| earnings_periods | 6 |
| earnings_events | 6 |
| earnings_source_evidence | 5 |
| earnings_date_confirmations | 12 |

Widoczne datowane wydarzenia: NVDA Q3 FY2027 **17.11**, release orientacyjny
**22:20 PL**, call **23:00**; INTC Q3 **29.10**, **21:00+ PL** jako granica
AMC, call **22:00**; AMZN Q3 **29.10**, call **22:00**, bez ustalonej godziny
release. Pozostałe trzy eventy Q4 mają unknown i nie dostają daty.
Nie nadaje się im statusu published ani Actual.

Zakres **02–08.11** poprawnie nie obejmuje datowanego wydarzenia pilota.
Po aktywacji powinien zwrócić HTTP 200 z pustą listą datowaną i sekcją
unknown. Dla NVDA trzeba sprawdzić zakres obejmujący 17.11; dla AMZN/INTC
zakres obejmujący 29.10. Zmiana zakresu nie zastępuje brakującego schematu.

## 5. Kopia i sprawdzalny plan odtworzenia

03.11 wykonano pełny odczyt `pg_dump --format=custom --no-owner --no-acl`
istniejącej bazy. Kopia jest lokalna i ignorowana przez Git:

`data/raw/earnings-activation-2026-11-02/macrolens-before-earnings-2026-11-03.dump`

- Rozmiar: **29 750 504 B**.
- SHA-256: `76dd69fe538b5de761ee9e83c983f7d5539d5e1a66e29d2e5d6b7104cdfe0873`.
- `pg_restore --list`: poprawny kod 0, **13 wpisów TABLE DATA**, w tym
  observation_vintages i series.
- Manifest wiąże kopię z konkretnym klastrem, OID i bazą; procedura
  ponownie weryfikuje format, rozmiar i SHA przed dopuszczeniem apply.

Na etapie przygotowania sprawdzono wyłącznie TOC. Po wyraźnym zatwierdzeniu
wykonano także pełne odtworzenie rzeczywistych danych do oddzielnej bazy,
opisane w sekcji 9. Przy awarii w trakcie aktywacji
wystarcza rollback transakcji. Po udanym COMMIT ewentualne cofnięcie
samej aktywacji ma osobny, **nieuruchomiony na bazie użytkownika** plan
`app/database/earnings_activation_rollback.sql`: usuwa tylko sześć tabel
Earnings i dwie funkcje, bez CASCADE. Niespodziewane zależności mają
zatrzymać cofnięcie. Plan ten sprawdzono po COMMIT na bazie testowej;
obiekty i dane makro pozostały identyczne.

Pełna kopia jest dodatkowym zabezpieczeniem, a nie instrukcją automatycznego
nadpisania istniejącej bazy. Awaryjne pełne odtworzenie należy najpierw
wykonać do nowej bazy przez pg_restore z --exit-on-error, --single-transaction,
--no-owner i --no-acl, następnie sprawdzić dane i osobno uzgodnić dalsze
działanie. Nie wolno automatycznie usuwać ani nadpisywać macrolens; mogłoby
to utracić późniejsze, poprawne zapisy niezwiązane z Earnings.

## 6. Rzeczywiste testy i sprzątanie

- **1207 backend passed, 50,66 s**, pełny przebieg 02.11, w tym 8 nowych
  regresji bramek aktywacji. 03.11 powtórzono sam nowy zestaw: **8 passed**.
- `tests/postgres_earnings_activation_validation.py`: **passed** na własnym
  PostgreSQL 17, w losowej bazie `macrolens_activation_test_<uuid>`.
- Sprawdzono read-only prepare, błędny cel/token, rzeczywisty błąd SQL
  po utworzeniu DDL i imporcie, całkowity rollback, poprawne utworzenie,
  ponowienie bez duplikatów i zmian capture, istniejącą blokadę izolowanego
  inicjalizatora, złożone FK/CHECK w sygnaturze oraz jawne cofnięcie po COMMIT.
- Syntetyczne FRED/ALFRED i schemat makro porównano przed/po. Nie kopiowano
  danych użytkownika do testu. Syntetyczny plik w testach bramki backupu nie
  jest kopią produkcyjnych danych; rzeczywisty pg_dump opisano oddzielnie.
- Sieć wydawców blokował dotychczasowy guard. Nie uruchamiano scraperów,
  BEA refresh, E2B, CI ani nowego Chrome normalnej aplikacji przed zgodą.
- Frontend, K2, Overview, R1–R3, schema.sql i izolowany initializer nie
  zostały zmienione. Wyniki 656 frontend i 47 Chrome z E2A są wynikami
  poprzedniego etapu, nie nowym testem aktywacji.

Losową bazę testową usunął finally skryptu. Sprzątanie kontenera zostało
początkowo przerwane technicznym limitem automatycznego przeglądu zgód;
nie było to stwierdzenie niebezpieczeństwa operacji. Po wznowieniu 03.11
sprawdzono pełny ID, własną etykietę i brak pozostawionych baz testowych,
a następnie usunięto wyłącznie kontener próby
`macrolens_earnings_activation_20261102` i jego anonimowy wolumen.
Nie usuwano ani nie resetowano macrolens_postgres.

## 7. Pliki i Git

Zachowano byte-identycznie **wszystkie 28 zastanych modified/untracked
plików**. Hash manifestu i zastany diff są w ignorowanym katalogu diagnostyki.
Nie zmieniano dotychczasowych raportów E1/E2A.

Nowe pliki przygotowania aktywacji:

- `app/database/activate_earnings.py`
- `app/database/earnings_activation_rollback.sql`
- `tests/test_earnings_activation.py`
- `tests/postgres_earnings_activation_validation.py`
- `docs/audits/equity-earnings-activation-2026-11-03.md`

`main`, HEAD bez zmian; **10 modified / 23 untracked**, indeks pusty.
Backup, manifesty i plany znajdują się pod ignorowanym data/raw i nie
wchodzą do zakresu repozytorium. Bez stagingu, commita, pusha, resetu,
clean, amend i globalnego formatowania. Przed zgodą nie wykonywano zapisów
lub DDL w istniejącej bazie. Po zgodzie wykonano wyłącznie zatwierdzone
utworzenie Earnings i import manualnych metadanych.

## 8. Wyraźna zgoda użytkownika

Użytkownik wyraźnie zatwierdził **aktywację planu 1359b113…fa1abdb5 na
localhost:5432/macrolens**, rolą macrolens, w klastrze i bazie z sekcji 2:
utworzenie wyłącznie nowych obiektów Earnings i import wymienionego seeda
w jednej transakcji. Ochrona izolowanego inicjalizatora pozostaje nienaruszona.

Zgoda obejmowała ponowny preflight, pełne odtworzenie kopii do osobnej
bazy przed apply, jedną transakcję aktywacji, idempotencję i kontrolę normalnej
aplikacji. Wymagała zatrzymania przy niezgodności celu, DDL lub planu.
Wszystkie te kontrole przeszły bez zmiany zatwierdzonych artefaktów.

## 9. Wykonanie po zatwierdzeniu — 03.11.2026

### Preflight i pełne odtworzenie

Ponownie zweryfikowano pełny hash planu
`1359b113b2171e751328d03d343b40b7864f9f73107de66364f5d94bfa1abdb5`,
wszystkie pięć zamrożonych artefaktów, rozmiar/SHA kopii, rolę, endpoint,
klaster **7682090371041935398**, OID **16384**, brak kolizji Earnings
i niezmienioną sygnaturę schematu makro. Preflight miał read_only=on.
Nie zmieniono ani nie wygenerowano innego planu do wykonania.

Utworzono osobny kontener PostgreSQL 17
`macrolens_earnings_restore_20261103`, własny wolumen i port loopback 55443.
Do losowej bazy `macrolens_restore_check_f0d6d0be8fe84f02a9dd93934872e364`
odtworzono **cały zatwierdzony archive**, przez pg_restore z
--exit-on-error, --single-transaction, --no-owner i --no-acl.
Nie odtwarzano niczego do macrolens.

Odtworzenie zakończyło się **kodem 0**. Sprawdzono 13 tabel, zgodną
sygnaturę schematu i zero niezwalidowanych constraints, w tym:

| Odtworzona tabela | Rekordy |
| --- | ---: |
| observation_vintages | 1 798 271 |
| computed_features | 971 540 |
| source_check_runs | 1 618 |
| series | 58 |
| publisher_documents | 21 |
| overview_publications | 8 |

Losową bazę usunięto po kontroli. Po zakończeniu testów usunięto także
wyłącznie własny kontener odtworzeniowy i jego wolumen, po sprawdzeniu
pełnego ID i etykiety. Oryginalny macrolens_postgres pozostawiono.

### Zatwierdzony apply i idempotencja

Uruchomiono osobną ścieżkę apply z dokładnym celem i zatwierdzonym hashem.
Wynik: **created**, kod 0. Transakcja utworzyła wyłącznie obiekty Earnings
i zapisała zatwierdzony seed. Końcowe liczby:

| Tabela | Rekordy po aktywacji |
| --- | ---: |
| earnings_companies | 3 |
| earnings_company_aliases | 3 |
| earnings_periods | 6 |
| earnings_events | 6 |
| earnings_source_evidence | 5 |
| earnings_date_confirmations | 12 |

Powtórzenie tego samego zatwierdzonego planu zwróciło
**already_initialized**. Nie wykonywało ponownego DDL. Liczby rekordów
i hash pełnej projekcji Earnings z historią pozostały identyczne.
Nie uruchomiono rollbacku na bazie użytkownika.

### Ochrona istniejących danych makro

Przed apply, po apply i po końcowym UI wykonano pełny odczyt wszystkich
**13 istniejących tabel public poza Earnings**, w REPEATABLE READ READ ONLY.
Dla każdej zapisano liczbę rekordów i SHA-256 strumienia COPY binary,
uporządkowanego po PK. Porównanie obejmuje wartości i timestampy, nie
tylko count lub statystyki przybliżone.

**Wszystkie 13 tabel, łącznie 2 772 659 rekordów, pozostało identycznych.**
Wspólny hash zestawu porównań:

`24b8672e70d5d1c389ab6a6a29f9df45183fc59e91a659f82bbcfa89c2a784dd`

Obejmuje to FRED/ALFRED, computed_features, source_check_runs,
overview_refresh_state/publications i dokumenty. Schemat makro również
pozostał zgodny z zatwierdzonym preflight. Nie zmieniano K2, Overview,
R1–R3, interwałów, Forecast, przychodów lub EPS.

### Normalne API i Calendar

Uruchomiono zwykły Uvicorn na **127.0.0.1:8000** oraz Vite na
**localhost:5173**, korzystające z normalnej bazy macrolens. Nie używano
izolowanego API 8013, fixture odpowiedzi lub wrappera zmieniającego trasy.

Rzeczywiste GET dały:

| Żądanie Earnings | HTTP | Datowane eventy | Unknown |
| --- | ---: | ---: | ---: |
| 02–08.11, wszystkie tickery | 200 | 0 | 3 |
| 17.11, NVDA | 200 | 1 | 1 |
| 29.10, wszystkie tickery | 200 | 2 | 3 |

Stare API makro dla 02–08.11 zwróciło **HTTP 200 / 16 wydarzeń**.
Brak wydarzenia pilota w bieżącym tygodniu jest teraz poprawnym pustym
wynikiem, a nie błędem braku schematu.

Końcowy Chrome na **normalnym Vite i API**: **63 kontrole**, EN/PL,
1366/390 px, **20 zakończonych odpowiedzi API HTTP 200**, zero wyjątków JS,
console.error i poziomego overflow. Potwierdzono:

- NVDA 17.11: **ok. 22:20 — wyniki**, konferencja **23:00**.
- INTC 29.10: **21:00+ — po sesji USA**, konferencja **22:00**.
- AMZN 29.10: konferencja **22:00**, bez podstawienia jej do czasu release.
- Trzy przyszłe terminy unknown bez wygenerowanych dat.
- Makro/Earnings/Wszystkie, ticker NVDA, zakres historyczny i przyszły,
  oficjalne linki, szczegóły, Escape i powrót fokusu.
- Brak komunikatu błędu wczytywania Earnings oraz załadowane wiersze makro
  w widoku Wszystkie. Obejrzano zrzuty desktop EN i mobile PL.

Pierwszy przebieg potwierdzał Earnings, lecz helper wykonywał zrzut zanim
zakończył się GET makro. Doprecyzowano wyłącznie ignorowany helper, aby
czekał na załadowane wiersze, i wykonano cały przebieg ponownie.
Końcowe liczby 63/20 dotyczą tego kompletnego przebiegu.

Kontrola odbywała się pod tymczasowym lease 726530019 trzymanym osobnym
połączeniem read-only. Zapobiegło to uruchomieniu importerów przez zwykły
hook aplikacji. Nie wykonano żadnych żądań SEC/IR z aplikacji ani E2B.
Żądania filtrów pozostawały odczytami; makro nadal korzystało z własnego
API. Po zamknięciu diagnostycznego Chrome zwolniono lease. Zwykły mechanizm
odświeżania aplikacji pozostaje bez zmian, bez pozostawionej blokady.

**API i frontend pozostawiono uruchomione do codziennego korzystania.**
Adres: `http://localhost:5173/#/calendar`. Aby zobaczyć NVDA, wybierz
Wyniki spółek i zakres obejmujący 17.11; dla AMZN/INTC — 29.10.
Nie powstał automatyczny feed: kolejne zapowiedzi nadal wymagają ręcznych,
zweryfikowanych metadanych.

### Końcowy stan repozytorium

Nie zmieniono żadnego zamrożonego artefaktu zatwierdzonego planu. Z 33 plików
zastanych przy tym wykonaniu zaktualizowano wyłącznie ten raport wyników;
pozostałe 32 zachowano byte-identycznie. Wcześniejszy manifest 28 plików
z początku przygotowania również pozostaje zgodny.

`main`, HEAD nadal `14e4829d79f3f4f0916629a560cfc0cf2a122836`;
**10 modified / 23 untracked**, indeks pusty. Bez stagingu, commita i pusha.
Kopia, plany, porównania, logi, helpery i zrzuty pozostają ignorowane pod
data/raw. Nie dodano ich ani sekretów do zakresu Git.

## 10. Zamknięcie repozytorium E2A + Activation — 03.11.2026

Ponownie przejrzano granice aktywacji: osobny initializer pozostaje
ograniczony do baz izolowanych; prepare jest read-only; apply wymaga celu,
pełnego hasha planu, zamrożonych artefaktów i kopii. Transakcja SERIALIZABLE
obejmuje DDL i seed, błędy wycofują całość. Obcy/częściowy schemat jest
odrzucany; powtórzenie nie tworzy duplikatów. GET, API startup i frontend
nie wywołują aktywacji. Rollback nie używa CASCADE i pozostaje oddzielnym
narzędziem wymagającym świadomego zatwierdzenia. Nie znaleziono nowej usterki
w produkcyjnej procedurze wymagającej zmiany zatwierdzonego zakresu.

W normalnej macrolens **nie uruchomiono ponownie apply ani rollbacku**.
Jedynie read-only sprawdzono stan: 3 companies, 6 events, 12 confirmations;
NVDA Q3 FY2027 zachowuje approximate release i call 22:00 UTC / 23:00 PL,
INTC AMC i call 21:00 UTC / 22:00 PL, AMZN call i unknown release,
a trzy Q4 pozostają unknown. Nie zatrzymano aplikacji użytkownika.

Nowy zakres CI to dwa dodatkowe nazwane kroki w istniejącym PostgreSQL
integration, przy zachowaniu czterech wcześniejszych. Jedyną zmianą
walidacji Activation jest dopuszczenie nazwy efemerycznej bazy kontrolnej
CI obok dotychczasowej lokalnej. Oba skrypty tworzą własne losowe bazy,
używają syntetycznych rekordów oraz dotychczasowego guarda HTTP. Normalna
baza macrolens nadal jest odrzucana jako baza kontrolna tych walidacji.

Pełne **working tree: 1207 backend / 656 frontend**; pełne **staging-only:
1207 backend / 654 frontend**, Node **22.23.4**, osobny typecheck i oba
production buildy poprawne. Największy chunk obu buildów około 407,04 kB,
bez zmiany progu. Wszystkie **sześć** skryptów PostgreSQL przeszło osobno
dla working tree i indeksu, w tym fresh/upgrade Earnings oraz Activation
z SQL failure, idempotencją i odzyskaniem stanu. Szczegółowe czasy i
ograniczenia przebiegów zawiera sekcja 9 raportu E2A.

Pierwszy sandboxowy backend indeksu nie zakończył procesu po 100% i nie
został zaliczony jako sukces; identyczne ponowienie z szerszym dostępem
dało kod 0 i 1207 passed. Nie zmieniano timeoutów i nie pomijano testów.
Nie przeprowadzano ponownego Chrome; wcześniejszy wynik 63/20 nie jest
nowym wynikiem zamknięcia. Nie ukrywano ostrzeżeń zależności.

Staging ma dokładnie **22 pliki** z dozwolonego zakresu. CalendarPage
został dodany selektywnym patchem: **Previous week pozostało poza indeksem**,
a jego pełne bajty working tree są zachowane. Pozostałe wcześniejsze prace
użytkownika i E1 są wyłączone. Kopia indeksu używa ich wersji z HEAD,
nie lokalnych zmian. Porównano wszystkie blob IDs kopii, cały staged diff,
obydwa whitespace checks i wzorce sekretów. Raporty nie zawierają haseł,
tokenów, sekretnej zawartości .env lub danych kopii; identyfikatory lokalnej
bazy i SHA są diagnostyką. data/raw i pełne backupy pozostają ignorowane.

Potwierdzono zachowanie SHA-256 wszystkich 12 wyłączonych plików oraz
working tree CalendarPage względem wejścia zamknięcia. Zestaw obejmuje:
README, EconomyBrief i test, SourceCheckStatus i test, CalendarPage.test,
calendarAgenda, styles, trzy wcześniejsze audyty makro i E1. Wykaz hashy
jest utrzymany w lokalnym manifeście kontroli; nie dołączono go do commita
jako artefaktu diagnostycznego. Po testach zmieniono tylko oba raporty.

Zatwierdzany jeden commit: **Add earnings calendar pilot and safe activation**.
Pełny SHA, wynik zwykłego pusha na origin/main i URL oraz rzeczywiste,
zakończone wyniki wszystkich trzech jobów Actions będą w końcowym raporcie
Codexa po ich uzyskaniu. Nie przypisuje się im wyników lokalnych i nie
tworzy drugiego commita wyłącznie dla metadanych po pushu. Bez force push,
amend, resetu, clean i rebase. Nie rozpoczęto E2B; daty nadal są aktualizowane
ręcznie, bez automatycznego SEC/IR, EPS, revenue lub guidance.
