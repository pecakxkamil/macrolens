# MacroLens — R3: Release-Aware Refresh BEA

Weryfikacja **30.10.2026**, Europe/Warsaw, `C:\Projects\macrolens`,
`main`, HEAD `93bca08a8b3cfd64243697609276d888e7af47d1`.
Wdrożono ograniczone kontrole należnych GDP/PIO w istniejącym koordynatorze.
**Bez stagingu, commita i pusha.** Sześć wcześniejszych plików zachowano
byte-identycznie; porównano ich SHA-256 przed i po pracy.

## Zakres i terminy

Przejrzano R1/R2, koordynator i jego PostgreSQL store, R2 importer/wiązanie,
kalendarz, stan kontroli źródeł, hook React i testy. Stan wejściowy:
4 modified, 2 untracked, pusty staging, zgodny HEAD.
Nie dodano wydarzeń, wskaźników, kolumn, kart, CSS ani definicji miar.
Nie zmieniono MCI/PIT, Forecast, konsensusu lub innych wydawców.

Z zachowanych rzeczywistych dowodów [harmonogramu BEA](https://www.bea.gov/news/schedule/full)
odczytano read-only sześć odrębnych tożsamości:

| Publikacja | Release ID / okres / etap | NY | UTC | PL |
| --- | --- | --- | --- | --- |
| 29.10.2026 GDP | 53 / 2026-07-01 / advance | 08:30 EDT | 12:30 | 13:30 |
| 29.10.2026 PIO | 54 / 2026-09-01 / monthly | 08:30 EDT | 12:30 | 13:30 |
| 25.11.2026 GDP | 53 / 2026-07-01 / second | 08:30 EST | 13:30 | 14:30 |
| 25.11.2026 PIO | 54 / 2026-10-01 / monthly | 08:30 EST | 13:30 | 14:30 |
| 23.12.2026 GDP | 53 / 2026-07-01 / third | 08:30 EST | 13:30 | 14:30 |
| 23.12.2026 PIO | 54 / 2026-11-01 / monthly | 08:30 EST | 13:30 | 14:30 |

Użyto `America/New_York` i `Europe/Warsaw` przez IANA. Nie pobierano nowych
materiałów wydawcy w celu tej kontroli; nie deklaruje ona świeżej weryfikacji
strony internetowej. Godziny przyszłych wierszy odczytano z ich własnych
komórek harmonogramu, także gdy brak jeszcze linku do raportu.
Nie konstruuje się przyszłego URL-u. Rozbieżne daty/zegary dla tej samej
rodziny, okresu i etapu nie tworzą okna. Nowsza poprawnie odczytana tabela
BEA steruje planem; poprzednia data nie jest regułą zastępczą.

## Polityka krótkiego okna

Zachowano zaproponowane punkty: **T, T+2, T+5, T+10, T+20 minut**.
Maksymalnie pięć zarezerwowanych kontroli na tożsamość, bez rozpoczynania
nowych krótkich kontroli od **T+30 minut**. To najwcześniejsze punkty,
nie zegar gwarantujący wykonanie. Powrót o T+7 rezerwuje jedną bieżącą
kontrolę, pomija dawne punkty i przewiduje kolejny dopiero od T+10.
Niewykorzystane punkty nie są nadrabiane serią żądań. Otwarcie późno może
więc wykorzystać mniej niż pięć prób.

GDP i PIO tego samego terminu współdzielą job i odczyt harmonogramu, ale
mają osobne liczniki i statusy. Tożsamość ma postać
`bea:<release_id>:<period>:<stage/monthly>:<date>:<scheduled_UTC>`.
Advance, Second, Third i Updated pozostają rozdzielone, podobnie miesiące PIO.

Okno wymaga zapisanego zweryfikowanego terminu, okresu, etapu i zegara.
Na nowej instalacji, bez takich dowodów, zwykły job nadal może wykonać
pierwsze odkrycie BEA; brak lokalnego harmonogramu nie blokuje bootstrapu R2.
Nie generuje się terminów z częstotliwości ani stałego offsetu czasu.

## Dwa tryby, jedna blokada i jeden cache

`RefreshCoordinator.request` decyduje na backendzie o trybie:

- **standard:** dotychczasowy pełny przebieg, domyślnie minimum **900 s**
  między pełnymi jobami, z dotychczasową kolejnością i budżetami;
- **bea_release_aware:** tylko należne BEA, dopuszczalne podczas cooldown
  pełnego joba. Nie wywołuje `refresh_sources`, FRED, Empire, FT900 ani innych
  adapterów i nie wykonuje backfillu.

Gdy oba tryby są należne, najpierw wykonuje się wąski BEA. Dzięki temu
przyjęty BEA nie czeka na ukończenie całego batcha FRED. Należny pełny job
pozostaje należny i może ruszyć potem. Nie przesunięto go o kolejne 900 s
od zakończenia wąskiego joba. Podczas krótkiego okna pełny job respektuje
te same rezerwacje/backoff i nie dodaje kolejnego pobrania potwierdzonego
lub chwilowo nienależnego BEA. Po oknie zwykłe kontrole nadal wykrywają rewizje.

Pozostaje wspólny advisory lock **726530019**, ten sam mechanizm launch,
`overview_refresh_state`, `overview_publications` i atomowej publikacji.
Nie dodano usługi, demona, drugiego koordynatora ani równoległego cache.
Globalne **900 s**, retry i wolne źródła **21600 s** nie zostały skrócone.
Budżet wąskiego joba nie przekracza istniejącego budżetu i jest ograniczony
także końcem okna. Rozpoczęte żądanie może zakończyć się później; nie jest
to gwarancja zakończenia pobrania w konkretnej sekundzie.

Jeśli termin jest już należny przy odpowiedzi terminalnej, backend przekazuje
krótki przyszły termin UI (+5 s), aby zabezpieczenie R1 przed przeszłym
deadline nie odłożyło próby o 15 minut. Przy zajętej blokadzie i terminalnym
stanie zwraca +30 s, bez kontaktu z wydawcą i bez rezerwowania próby.
Trwający job pozostaje obserwowany przez dotychczasowy polling statusu.

## Trwałe próby i backoff

Stan w `source_versions.bea_release_aware` zachowuje osobny termin pełnego
joba, tryb, rekordy tożsamości, liczbę rezerwacji, ostatni wykorzystany punkt
i czas rezerwacji. Rezerwacja jest zatwierdzana **pod wspólną blokadą przed
HTTP i launch**. Restart lub drugi worker odczytuje te same dane.
Nie zmieniono schematu i nie utworzono tabeli liczników.

Rezerwacja zużywa możliwość także wtedy, gdy worker ulegnie awarii przed
samym HTTP lub wspólna kontrola zostanie przerwana backoff przed drugim
dokumentem. To konserwatywny limit; UI opisuje **zarezerwowane próby**,
nie udaje liczby zakończonych pobrań. Awaria nie zeruje licznika.
Scope `source_check_runs` identyfikuje tryb i zamierzone wydarzenia.

HTTP 429 respektuje Retry-After w sekundach lub jako datę HTTP; brak
poprawnego nagłówka oznacza ostrożne 900 s dla BEA. HTTP 503 respektuje
podany Retry-After. Termin liczy się od otrzymania odpowiedzi, nie od startu
joba. Backoff nie uruchamia FRED ani nie przyspiesza pozostałych źródeł.
Jeżeli wykracza poza okno, krótkie kontrole kończą się.

Transportowy backoff zapisuje się także jako niezakończony postęp istniejącej
kontroli źródła, niezależnie od końcowej transakcji danych. Nadal ma status
running, bez deklaracji sukcesu Actual. Plan odczytuje ten dowód po restarcie,
również gdy końcowa transakcja joba została wycofana i lokalna aktualizacja
source_versions z backoff nie przetrwała. Brak możliwości zapisu przy pełnej
awarii PostgreSQL nie daje gwarancji utrwalenia nowej informacji; nie ma
niezależnego pollera obchodzącego niedostępność magazynu/blokady.

## Dokumenty, miary i publikacja

Ponownie wykorzystano parser i zapis `sync_bea_reports.py` z R2. Standardowo
wąski job pobiera harmonogram oraz co najwyżej jeden należny dokument GDP
i jeden PIO; gdy należne jest tylko PIO, GDP nie jest pobierany. Brak linku
powoduje brak raportu w tej próbie, nie pobranie starszego jako nowego.
Zmiana oficjalnej daty/godziny aktualizuje plan, bez przyjęcia starego dowodu.

R3 nie zmienia definicji siedmiu miar, pełnego embargo R1, weryfikacji
wydawcy, pól, okresu/etapu, SQL i obu FK, RAW/SHA-256, precision, pierwszeństwa
BEA oraz jawnego FRED fallback z R2. Przed T nie ma nowego Actual. HTTP 200,
ETag, Last-Modified lub sam nowy hash nie są potwierdzeniem właściwego wyniku.

GDP kończy krótkie kontrole po potwierdzeniu własnego etapu. PIO wymaga
wszystkich sześciu miar; pięć potwierdzonych pozostawia partial i pozostałe
dozwolone punkty. Po wyczerpaniu punktów/limitu albo upływie okna brakujące
wyniki pozostają niepotwierdzone i wracają do zwykłego rytmu.

Jedna transakcja obejmuje dokumenty, obserwacje i ewentualną nową generację.
Wąski job porównuje potwierdzone odczyty, Previous i precyzję przed/po.
Nowy poprawny wynik, uzupełnienie PIO lub zmiana wartości wymagają publikacji.
Brak zmiany nie tworzy kolejnej generacji. Kosmetycznie nowy hash może
zachować receipt/historię bez nowej generacji tych samych odczytów.
Nie jest to nowa historia first printów ani pełny zapis zmian intraday.

Pole `publication_created_at` pochodzi z istniejącej publikacji SQL.
Ostatni zakończony wąski job bez nowej generacji nie udaje jej czasu publikacji.
Zachowano ostatnie dobre dane po błędzie, idempotencję i zabezpieczenia R2.

## Frontend

Hook R1 nie otrzymał drugiego timera lub osobnego pollera. Używa wcześniejszego
backendowego `next_check_at`, więc widoczna karta może obudzić się na BEA
przed pełnym jobem. Hidden, focus, abort, ograniczanie polling running,
reload wyłącznie nowej generacji i ochrona starego zakresu pozostają zachowane.

W istniejących szczegółach Calendar dodano EN/PL: limit/rezerwacje, liczbę
potwierdzonych miar, status okna i kolejny dozwolony termin. Dopasowanie
dotyczy własnej daty, okresu i etapu wiersza. Chronionego SourceCheckStatus
ani CSS nie zmieniano. Pozostają istniejące układy, sześć kart i limit
czterech wydarzeń Overview. Forecast i konsensus nie zostały dodane.

## Walidacja

- Pełny backend: **1113 passed** — wcześniejsze 1066 zachowane i **47 nowych
  przypadków R3**. Zegar IANA, fazy, granice okna, brak prób przed T,
  pięć punktów i limit, pojedynczy późny start, brak zaległej serii,
  częściowe PIO, bootstrap, kolizje harmonogramu, niepotwierdzone zegary,
  zachowanie standardowego deadline, pierwszeństwo wąskiego joba, restart,
  współbieżność, backoff, publikacja wyłącznie po zmianie i późniejsze rewizje.
- Pełny frontend: **605 passed / 25 plików**, z blokadą sieci CI.
  Nowe fake timers sprawdzają wcześniejszy deadline i pojedynczy powrót po
  uśpieniu; EN/PL sprawdza szczegóły, a regresja generacji jej faktyczny czas.
- Osobny TypeScript typecheck oraz production build: **passed**.
  Główny pakiet **543,90 kB**, gzip **158,02 kB**. Ostrzeżenie ponad 500 kB
  pozostaje jawne; bez optymalizacji Vite i zmiany progu.
- `tests/postgres_bea_release_validation.py`: **passed** na własnej bazie
  `macrolens_bea_release_test_<uuid>`, rzeczywisty SQL, syntetyczny HTTP/zegar.
  Dwie instancje koordynatora na niezależnych połączeniach modelują workery;
  trzy żądania przy zajętym lease rezerwują jeden wspólny zestaw prób.
  Sprawdzono trwałość stanu, osobne GDP/PIO, częściowe PIO, zatrzymanie GDP,
  generacje, błąd triggera SQL oraz przetrwanie backoff po błędzie końcowego
  zapisu joba. FRED/ALFRED i poprzednia generacja pozostają zachowane.
  Usunięto wyłącznie własną bazę; schematu bazy użytkownika nie inicjalizowano.
- Zachowany `tests/postgres_bea_validation.py` R2: **passed** ponownie,
  również na własnej usuwanej bazie. To kontrole lokalne, nie PostgreSQL w CI.
- Zapisane prawdziwe terminy i tożsamości tabeli wyżej potwierdzono przez
  read-only PostgreSQL i hashowane RAW, bez HTTP wydawcy i bez ingestion.
- Końcowy Chrome: **40 scenariuszy**, EN/PL, **1366/390 px**, prawdziwe API,
  **24 odpowiedzi HTTP 200**, bez wyjątków JS i poziomego overflow.
  Odczyty R2, nowa sekcja R3, przyszłe puste Actual, ★★★, szczegóły,
  Escape/fokus, nawigacja, tooltip BEA, sześć kart i limit wydarzeń.
  Obejrzano zrzuty desktop/mobile. API nie było podstawiane.
- Chrome działał pod wspólną blokadą przez read-only połączenie. Liczba
  i max timestamp kontroli oraz stan/generacja koordynatora przed/po były
  identyczne. Normalne POST aplikacji nie uruchomiły importerów. Lock zwolniono.
- `git diff --check`: poprawny. Nie pomijano testów ani nie zwiększano
  timeoutów; sporadyczny błąd MCI nie wystąpił w pełnych przebiegach.

Testy/przegląd wykryły i poprawiły zegary przyszłych wierszy bez linków,
niejednoznaczne zegary takich wierszy, bootstrap bez lokalnego harmonogramu,
powrót przeszłego deadline do zabezpieczenia R1 oraz backoff tracony przy
rollback końcowego zapisu. Helper PG początkowo odczytywał stan przed
symulowaną chwilą zakończenia capture; poprawiono jego zegar. Fixture PL
używał angielskiego selektora GDP, a typ CalendarEvent nie deklarował już
zwracanego pola estimate_stage; uzupełniono selektor i typ. Jedna próba
helpera Chrome nie znalazła otwartego tooltipa przy Escape. Nie osłabiono
asercji; pełny przebieg na ustabilizowanym kodzie przeszedł ponownie.
Usunięto powieloną deklarację helpera postępu; końcowy backend sprawdzono
ponownie w całości. Nie instalowano pakietów i nie wykonywano nowego CI.

## Ograniczenia

Nie obserwowano nowej publikacji na żywo. Nie zmierzono poprawy latencji
w minutach i nie gwarantuje się Actual dokładnie o 08:30 ET. To plan prób
uruchamianych przez istniejące żądania aplikacji: backend i widoczna karta
muszą działać. Uśpienie/throttling, sieć, backoff i zajęta wspólna blokada
mogą opóźnić lub pominąć punkty. Trwający pełny job nie jest przerywany.
Po restarcie zarezerwowane, lecz niedokończone próby nadal zużywają limit.

Niepotwierdzony przyszły harmonogram nie tworzy okna. Zmiana formatu BEA
może wymagać przeglądu. Pozostają current-vintage FRED, captured snapshot BEA,
niepełne first print/intraday, brak konsensusu i nierozstrzygnięte warunki
FRED oraz ograniczenia innych integracji. Nie rozpoczęto kolejnego etapu.

## Pliki i końcowy Git

16 plików R3:

- `app/analytics/bea_release_refresh.py` — nowy.
- `app/analytics/overview_refresh.py`
- `app/analytics/overview_refresh_store.py`
- `app/ingestion/sync_bea_reports.py`
- `app/source_checks.py`
- `frontend/src/api/macrolens.ts`
- `frontend/src/brief/useOverviewRefresh.test.tsx`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/ReadingAvailability.tsx`
- `frontend/src/calendar/ReadingAvailability.test.tsx`
- `frontend/src/i18n/pl.json`
- `tests/conftest.py`
- `tests/test_bea_release_refresh.py` — nowy.
- `tests/postgres_bea_release_validation.py` — nowy.
- `docs/audits/calendar-bea-release-aware-refresh-2026-10-30.md` — ten raport.

Poza zakresem, SHA-256 identyczne względem początku R3:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`
- `docs/audits/calendar-next-releases-priority-2026-10-29.md`
- `docs/audits/calendar-release-day-latency-2026-10-29.md`

`main`, HEAD bez zmian. **16 modified, 6 untracked**, pusty staging.
Bez commita, pusha, resetu, clean, amend i zmian historii.
RAW/logi, helpery, profile i zrzuty pozostają w ignorowanym
`data/raw/bea-r3-2026-10-30/`; nie dodano sekretów ani lokalnej bazy.

## Kontrola zamknięcia R3 — 30.10.2026

Potwierdzono początkowy `main`, HEAD `93bca08a8b3cfd64243697609276d888e7af47d1`,
16 modified / 6 untracked i pusty staging. Przejrzano pełny diff, wszystkie
16 plików R3, wcześniejsze audyty R1/R2/opóźnienia, testy koordynatora,
magazyn dokumentów i skrypty PostgreSQL. Sześć chronionych plików zachowano
byte-identycznie. Nie zmieniono schematu, miar R2, MCI/PIT, CSS ani innych
integracji. Nie wykonywano ingestion, nowych pobrań wydawcy lub POST refresh.

### Ustalenia i poprawki końcowego przeglądu

Zapisane oficjalne dowody ponownie odczytano z PostgreSQL w transakcji
`transaction_read_only=on`. Potwierdzono sześć odrębnych tożsamości z tabeli
na początku raportu, własne okresy i etapy, IANA i konwersje: 29.10 o 13:30 PL,
25.11 oraz 23.12 o 14:30 PL. W przyszłych wierszach brak URL raportu pozostaje
brakiem; nie skonstruowano adresów. Nie zastąpiono harmonogramu datami fixture.

Potwierdzono punkty T/+2/+5/+10/+20, limit pięciu rezerwacji i zamknięcie
od T+30. Brak próby przed T, pojedynczy późny start bez nadrabiania, osobne
GDP/PIO, zakończenie potwierdzonego GDP i sześciu miar PIO pozostają zachowane.
Wąski job ma pierwszeństwo przed jednocześnie należnym pełnym jobem i nie
przesuwa jego deadline. Standardowe 900 s i wolne 21600 s pozostają bez zmian.
Wspólny lock i zatwierdzenie rezerwacji przed launch/HTTP zachowują limit
po restarcie. Transakcja dokumentów/obserwacji/generacji pozostaje atomowa.
Brak zmiany liczb nie tworzy nowej generacji; jej czas pochodzi z publikacji SQL.

Przegląd wykrył dwa przypadki wymagające poprawy wyłącznie w zakresie R3:

- Po awarii końcowej transakcji niezależny transportowy receipt mógł pozostać
  `running`, mimo zakończenia koordynatora jako error. Odzyskiwanie pod wspólną
  blokadą zamyka teraz osierocone wpisy BEA z trybem R3 jako
  `error / refresh_interrupted`, zachowując ich scope i backoff. Nie zmienia
  innych zasobów i nie zeruje rezerwacji. Przypadek sprawdza rzeczywisty PG.
- Ujemna i zbyt duża liczba Retry-After nie są poprawnym czasem oczekiwania.
  Parser odrzuca je do ostrożnego fallbacku 900 s dla 429, zamiast skracać
  oczekiwanie do zera lub tracić backoff przez OverflowError. Zachowano
  obsługę liczby sekund, daty HTTP, 503 i brak nagłówka.

Dodano sześć przypadków offline ponad wcześniejsze 1113: deterministyczną
sekwencję listopadową oraz HTTP 500 i cztery niepoprawne nagłówki/backoff.
25.11: 14:20 i 14:29 bez próby, 14:30 bez nowego dokumentu, 14:32 poprawny
GDP Second przy nadal oczekiwanym PIO, 14:35 pobranie wyłącznie PIO i sześć
potwierdzonych miar. Advance pozostaje odrębny, Third pusty, Forecast null,
bez pełnego/FRED ingestion i bez zmiany terminu zwykłego joba.
Wszystkie wartości i zegary tego scenariusza są syntetyczne i offline.

### Nowe przebiegi walidacji

| Kontrola | Working tree | Dokładna kopia indeksu |
| --- | --- | --- |
| Pełny backend | **1119 passed**, 61,03 s | **1119 passed**, 60,88 s |
| Pełny frontend, blokada sieci CI | **605 passed / 25 plików** | **605 passed / 25 plików** |
| Osobny TypeScript typecheck | passed | passed |
| Production build | passed | passed |
| PostgreSQL BEA R2 | passed | passed |
| PostgreSQL BEA R3 | passed | passed |

Główny pakiet working tree: **543,90 kB**, gzip **158,02 kB**.
Kopia indeksu: **545,95 kB**, gzip **158,48 kB**. Kopia używa wersji
README/SourceCheckStatus/CSS z HEAD i nie zawiera dwóch wcześniejszych
nieśledzonych audytów; różnica pakietów nie jest optymalizacją R3.
Ostrzeżenie Vite ponad 500 kB pozostaje jawne. W tych lokalnych przebiegach
backendu nie wystąpiło ostrzeżenie Starlette/httpx. Ewentualny wynik CI
będzie raportowany odrębnie. Nie pomijano testów, nie zwiększano timeoutów
i nie zmieniano MCI/PIT; sporadyczny błąd MCI nie wystąpił.

Oba skrypty PostgreSQL ponowiono po poprawkach także na kopii indeksu.
Tworzą i usuwają wyłącznie własne losowe bazy. R3 sprawdził prawdziwy
advisory lock, dwa koordynatory i trzy nakładające się żądania, trwałe
rezerwacje, częściowe PIO, zatrzymanie GDP, generacje i rollback SQL.
Backoff pozostał skuteczny po błędzie końcowej transakcji i odczycie przez
następny worker, a osierocony transport nie był już running. R2 ponownie
sprawdził idempotencję, rewizje jednego dnia, RAW, oba FK i rollback.
Zachowano wcześniejsze FRED/ALFRED. Nie inicjalizowano i nie modyfikowano
bazy użytkownika. Standardowy GitHub CI nie wykonuje tych testów PG.

Pierwsza próba frontendu w sandboxie zakończyła się EPERM przy tworzeniu
tymczasowej konfiguracji Vite. Ponowienie z odpowiednim dostępem przeszło;
nie był to błąd testów aplikacji. Pierwsze porównanie bajtów eksportu indeksu
ujawniło normalizację LF/CRLF. Porównanie identyfikatorów Git z właściwym
filtrem ścieżki potwierdziło identyczną zawartość. Nie osłabiono asercji.
Wcześniejsze 40 scenariuszy Chrome pozostaje wynikiem wdrożenia R3,
nie nowym przebiegiem Chrome w zamknięciu.

### Staging, ochrona plików i dalszy wynik

Indeks zawiera dokładnie 16 plików wymienionych powyżej, z poprawkami
zamknięcia. Przejrzano cały staged diff i sprawdzono obie kontrole whitespace,
wzorce sekretów oraz wykluczenie RAW/cache/logów/profili, lokalnych danych
i helperów. Cały indeks wyeksportowano do izolowanej kopii z pozostałymi
śledzonymi zależnościami. Kod w niej odpowiada zatwierdzanemu indeksowi;
po końcowej walidacji uzupełniono tylko ten raport i jego kopię.

SHA-256 przed zamknięciem i po walidacji są identyczne; te pliki są poza stagingiem:

| Plik | SHA-256 przed = po |
| --- | --- |
| README.md | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` |
| SourceCheckStatus.tsx | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` |
| SourceCheckStatus.test.tsx | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` |
| styles.css | `7696bd5cac8c8bb3792f86d23e588c97f1fd87a5aef407a9f141ceb07b9b20e0` |
| calendar-next-releases-priority-2026-10-29.md | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` |
| calendar-release-day-latency-2026-10-29.md | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` |

Planowany jeden commit: **`Add release-aware BEA publication refresh`**.
Zdalny `origin/main` przed zatwierdzeniem nadal wskazywał `93bca08`.
Pełny hash, wynik zwykłego pusha i zakończony wynik rzeczywistego MacroLens CI
zostaną podane w zewnętrznej odpowiedzi po ich uzyskaniu. Nie deklaruje się
przyszłego sukcesu CI i nie powstanie drugi commit tylko dla tych informacji.

Pozostają wymagania działającego backendu i widocznej karty. Zamknięta karta
nie uruchamia autonomicznego monitoringu. Zajęty lock, throttling, sen i sieć
mogą pominąć punkty, a rezerwacja przerwana przed HTTP zużywa limit.
Nie zmierzono latencji rzeczywistej nowej publikacji i nie gwarantuje się
Actual o 08:30 ET. Nie rozpoczęto kolejnego etapu.
