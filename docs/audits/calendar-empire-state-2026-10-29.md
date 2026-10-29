# MacroLens — etap 3C: Empire State Manufacturing Survey

Weryfikacja: **29.10.2026**, Europe/Warsaw, `C:\Projects\macrolens`.
Gałąź `main`, HEAD `0147d6e1fc64d3c5e317f724e8f264fb119760b8`.
Wdrożono kalendarz i bezpośredni Actual NY Fed wyłącznie dla **Current
General Business Conditions, SA (`GACDISA`)**. Bez stagingu, commita i pusha.
Nie rozpoczęto kolejnego etapu. Pięć zastanych plików zachowano byte-identycznie;
porównano ich SHA-256 przed pracą i przy zamknięciu.

## 1. Źródła, zakres i tożsamość

Źródłem jest [Empire State Manufacturing Survey](https://www.newyorkfed.org/survey/empire/empiresurvey_overview)
Federal Reserve Bank of New York. Parser czyta jawnie oznaczoną tabelę roczną,
jej konkretne daty oraz rzeczywiście podlinkowane własne raporty PDF.
Nie konstruuje nazw PDF i nie generuje terminów z częstotliwości miesięcznej.
Zegar 08:30 lub krótko po nim pochodzi ze strony badania; strefę Eastern Time
potwierdza [kalendarz NY Fed](https://www.newyorkfed.org/research/calendars/nationalecon_cal).

Zapisano **12 dat 2026**, w tym wymagane 15.09, 15.10, 16.11 i 15.12.
Miesiąc badania pochodzi z odpowiedniej kolumny tabeli, nie z odejmowania miesiąca.
Identyfikator `empire-state:YYYY-MM:monthly` pozostaje stabilny po przesunięciu
terminu. Zmiany terminu, zegara i dokumentu zachowują poprzedni stan w historii.
Krótsza lista lub błąd źródła nie kasuje potwierdzonych wcześniejszych terminów.
Przesunięcie bez nowego dokumentu unieważnia stare przypisanie dokumentu.

Nie znaleziono potwierdzonego rocznika 2027 w użytych źródłach. API zwraca
`not_published_in_checked_sources` i nie tworzy wydarzeń 2027. Nie jest to
twierdzenie o nieistnieniu innych dokumentów poza sprawdzonym zakresem.

## 2. Miara i parser CSV

[Oficjalny CSV SA](https://www.newyorkfed.org/medialibrary/media/survey/empire/data/esms_seasonallyadjusted_diffusion.csv)
jest bezpośrednim źródłem poziomów. [Dokumentacja kodów NY Fed](https://www.newyorkfed.org/medialibrary/media/survey/empire/data/all_data_idx.pdf)
rozróżnia `GACDISA` — Current SA, `GAFDISA` — Future SA oraz `GACDINA` — Current NSA.
Do obserwacji trafia tylko `GACDISA`; inne kolumny pełnego źródłowego RAW
nie stają się miarami MacroLens. Nie dodano subindeksów, NSA ani Future.

Indeks dyfuzyjny oznacza odsetek odpowiedzi o poprawie minus odsetek odpowiedzi
o pogorszeniu. Poziom i różnice są w **punktach indeksu**, bez procentów i m/m.
Próg neutralny wynosi zero; nie zastosowano progu 50 ani reguł ISM/PMI.
Indeks regionalny nie jest ogólnokrajową produkcją przemysłową.

Parser wymaga jednoznacznych kolumn `surveyDate` i `GACDISA`, poprawnego CSV
i daty ISO. Kolejność kolumn może się zmienić. Miesiąc normalizuje do pierwszego
dnia: `2026-10-31` jest okresem X, nie datą publikacji 31.10.
Zduplikowane miesiące, uszkodzone wiersze, brak wymaganej kolumny i poziomy poza
−100…100 powodują odrzucenie pliku. `ND`, puste pole i wartości niefinitywne
pozostają brakami; zero i ujemne indeksy są poprawnymi wynikami.
Nie zastępuje się brakującego Current kolumną Future lub NSA.

## 3. Dokument a dostępność Actual

Data w harmonogramie, dostępność własnego raportu i świeży CSV to osobne fakty.
Actual wymaga właściwego miesiąca, skończonego `GACDISA`, potwierdzonego
dokumentu danego wydarzenia oraz publikacji niebędącej w przyszłości.
Pierwsze przyjęcie wyniku wymaga zgodności poziomu CSV z własną tabelą Current
w PDF. Sam nowy hash, timestamp, upływ godziny albo PDF bez CSV nie tworzy Actual.
Brak/stary CSV daje jawny brak wyniku; po poprawnej aktualizacji może on zostać
uzupełniony zwykłym sprawdzeniem. Nie ma liczbowego fallbacku z PDF.

Przejrzano i sparsowano rzeczywiste raporty
[IX](https://www.newyorkfed.org/medialibrary/media/survey/empire/empire2026/2026_09-empire-state-manufacturing-survey.pdf)
oraz [X](https://www.newyorkfed.org/medialibrary/media/survey/empire/empire2026/2026_10_empire-state-manufacturing-survey.pdf).
Parser wymaga własnego miesiąca i roku, oznaczenia Seasonally Adjusted oraz
sekcji **Current Indicators / Change from Preceding Month**. To istotne,
ponieważ tabela Future ma podobny nagłówek kolumn. Nie użyto starego miesiąca
pozostawionego w elementach szablonu wykresu jako miesiąca raportu.
Poziomy Current/Previous obu dokumentów zgadzają się z CSV w tej próbie.

Dla wcześniej potwierdzonego miesiąca późniejsza zmiana bieżącego CSV może
zostać przyjęta jako rewizja current-vintage, z historią i informacją o różnicy
względem archiwalnego PDF. Nie dopasowuje się liczby do starego dokumentu.
Znany starszy hash CSV/raportu nie zastępuje nowszej przyjętej wersji.
Nie ma uniwersalnego dowodu kolejności dla każdej nieznanej wcześniej,
nieoznaczonej wersji wydawcy; konserwatywne odrzucenie wymaga wtedy przeglądu.

## 4. Dane i rzeczywiste odczyty

Kontrolowane pierwsze sprawdzenie rozpoczęto **2026-10-29T10:22:00.398080+00:00**.
Wykonano cztery żądania HTTP 200: strona harmonogramu, własne PDF IX/X i CSV.
Zapisano tylko **trzy poziomy**: VIII **20,6**, IX **7,6**, X **25,5**.
Sierpień jest kontekstem Previous, potwierdzonym również tabelą raportu IX.
Bez własnego raportu VIII nie otrzymuje przez to historycznego Actual.
Nie wykonywano szerszego backfillu.

| Wydarzenie / okres | NY → PL | Actual | Previous | Różnica | Forecast |
| --- | --- | ---: | ---: | ---: | --- |
| 15.09.2026 / IX | 08:30 → 14:30 | 7,6 | 20,6 | −13,0 pkt | — |
| 15.10.2026 / X | 08:30 → 14:30 | 25,5 | 7,6 | +17,9 pkt | — |
| 16.11.2026 / XI | 08:30 → 14:30 | — | 25,5 | — | — |
| 15.12.2026 / XII | 08:30 → 14:30 | — | — | — | — |

Tabela pochodzi z rzeczywistej projekcji i odpowiedzi lokalnego API, bez fixture'ów.
Previous to dokładnie poprzedni miesiąc, a nie ostatni dowolny dostępny odczyt.
Dla przyszłych Actual powód to `not_yet_published`; konsensus `not_integrated`.
Nie ma zaskoczenia wobec rynku ani kopiowania Previous do Forecast.
Wartości nie są wpisane na sztywno do kodu aplikacji.

Konwersja korzysta z IANA `America/New_York` → `Europe/Warsaw`.
Daty IX/X mają UTC 12:30, XI/XII UTC 13:30; PL pozostaje 14:30.
Testy obejmują także rozbieżne tygodnie DST. Przykłady syntetyczne nie tworzą
dodatkowych rzeczywistych terminów.

## 5. Wersje, provenance i minimalna zmiana schematu

Wyniki są zapisywane w istniejących `series` i `observation_vintages`, ze źródłem
`nyfed_empire_state`, lokalnym ID `NYFED_EMPIRE_GACDISA` i własną dzienną wersją.
Nie oznacza się ich jako `fred_snapshot`; FRED/ALFRED nie uczestniczą w imporcie.
Nie zmieniono `config/series.yaml`, tabel FRED ani kluczy istniejących obserwacji.

Przejrzano istniejący magazyn: tabele ISM mają ograniczenie wartości 0…100,
więc nie nadają się do ujemnego Empire. Z kolei dzienny klucz obserwacji nie
opisuje osobno wielu dokumentów i rewizji intraday. Dodano wyłącznie tabelę
metadanych `publisher_documents` i dwa nullable FK w `observation_vintages`:
`source_document_id` oraz `publication_document_id`. To zmiana addytywna,
bez resetu, zmiany dotychczasowej unikalności lub przebudowy danych.
Nie utworzono równoległego magazynu własnych liczbowych obserwacji.

Receipts zawierają URL, rzeczywisty czas pobrania, HTTP, SHA-256 i ścieżkę RAW,
rozpoznany zakres dokumentu oraz informacje o zmianach wartości. RAW jest
niezmiennym plikiem adresowanym hashem. Powiązanie obserwacji z CSV i własnym
raportem pozwala sprawdzić pochodzenie. API pokazuje okresy, wersje, historię
dokumentów, walidację i niezależne statusy harmonogramu, dokumentu i CSV.

Historia przechwyconych wersji zaczyna się od wdrożenia. Bieżący historyczny CSV
nie tworzy dawnych first printów. Rewizje sezonowe mogą zmieniać starsze poziomy.
W ramach jednego dnia aktualizuje się bieżący wiersz obserwacji; poprzednią
zawartość zachowują immutable RAW i metadane rewizji, nie osobny wiersz
`observation_vintages` dla każdej zmiany intraday. Nie jest to kompletna historia
wszystkich zmian wydawcy pomiędzy sprawdzeniami.
Planowany czas, czas pobrania i nieznany czas pierwszej dostępności są rozdzielone.

## 6. Koordynator, błędy i ponowne sprawdzenie

Nowy adapter korzysta z istniejącego koordynatora, wspólnego advisory lock,
budżetu żądań, wolnego interwału — domyślnie **6 godzin** — transakcji,
source_check_runs i atomowej publikacji Overview. Nie dodano usługi ani pollingu.
Normalny przebieg ma trzy żądania: strona badania, najnowszy należny własny PDF
i CSV. Dodatkowy historyczny PDF IX pobrano tylko w kontrolowanym uruchomieniu.
Nie powstaje automatyczny crawler archiwum.

Zapis schedule/PDF/CSV/obserwacji i końcowego statusu sukcesu łączy jedna transakcja.
Zapis początkowej próby i błędu pozostaje możliwy niezależnie. HTTP 403/404/503,
błąd parsera lub rollback nie kasuje ostatnich poprawnych wyników i nie udaje
udanego odczytu. Dostępność zapisanej liczby nie przemianowuje błędu źródła
na sukces. Czas 08:30 nie jest SLA CSV; interwał 6 godzin nie daje gwarancji
Actual w sekundę ani minutę publikacji.

Ponowne, zwykłe sprawdzenie rozpoczęto **2026-10-29T10:38:57.122863+00:00**.
Trzy odpowiedzi HTTP 200 pobrano odpowiednio o **10:38:57.745707**,
**10:38:58.032329** i **10:38:58.666600 UTC**. Ponowny import: **3 → 3 obserwacje**,
zero duplikatów, brak zmian ich `ingested_at`. Hash pełnych pozostałych obserwacji
przed/po był identyczny. Nie odświeżano innych dostawców.
Końcowa generacja Overview z zapisanych danych:
`dacc3dd1-76b1-4c3a-a4bc-48dc2992848c`.

SHA-256 zachowanych rzeczywistych materiałów:

- PDF IX: `d6cc192509ff3f4bf30439fbe0a00bd4a67f51e7d34613a6eab233257c81171c`.
- PDF X: `80645241eac173fb87d1c2a6b253fafd5571c6704117c2ccbfad3c4008578cc5`.
- CSV: `33c525e5bd0a5179fa8cd232fc7135e20597684ab21b0abbe88b74777a4fa45e`.

RAW pozostają w ignorowanym `data/raw/nyfed_empire_state/`; kontrolne payloady,
logi i artefakty przeglądarki w ignorowanym `data/raw/empire-state-2026-10-29/`.
Nie dodano RAW ani danych bazy do plików repozytorium.

## 7. Warunki NY Fed i prezentacja praw

Sprawdzono [Terms of Use NY Fed](https://www.newyorkfed.org/privacy/termsofuse).
Opisują warunkową możliwość pobierania, przechowywania, kopiowania, dystrybucji
i modyfikacji, z wyłączeniami i obowiązkami. Nie potraktowano samego HTTP 200
jako licencji. Dla nowej integracji zachowano oryginalny tytuł, oznaczenie
Federal Reserve Bank of New York, wymagany copyright, odnośnik do oryginalnego
CSV i pełnych warunków oraz informację o własnej normalizacji dat i różnicach.
Modyfikacje MacroLens nie są przypisywane NY Fed; brak sugerowania endorsement.
Warunki dalszej dystrybucji i brak nakładania dodatkowych ograniczeń na treści
NY Fed są przekazywane w obiekcie praw API i eksportowanym tekście Overview.
Nie wykorzystano logo ani oznaczeń sugerujących afiliację.

Te informacje występują w szczegółach Calendar, pozycji Overview, odpowiednim
kontrakcie API i eksporcie, nie wyłącznie w stopce. Lokalny identyfikator nie
wchodzi do ogólnego katalogu FRED/wykresów; nie dodano bocznego eksportu historii
bez tych metadanych. Nie potwierdza to zgodności całej aplikacji ani gotowości
publicznego demo. Dotychczasowe nierozstrzygnięte warunki FRED/PostgreSQL/RAW/cache
oraz ograniczenia Michigan, ADP i ISM pozostają bez zmian.

## 8. Calendar i Overview

Jeden wiersz i jedna miara na miesięczne wydarzenie. Istniejąca kategoria
Growth and consumer, redakcyjne **★★**, stabilny ID, chronologia i countdown.
Filtr ★★★ ukrywa Empire; kategoria growth je zachowuje, labor wyklucza.
EN/PL pokazuje punkty indeksu i neutralne różnice, bez nowych kolorów,
kolumn lub CSS. Oryginalna nazwa NY Fed pozostaje przy tłumaczeniu.
Szczegóły pokazują terminy, dokument, źródło, wersje i prawa; Escape przywraca fokus.
Overview ma nadal sześć kart i najwyżej cztery nadchodzące wydarzenia.
Nie zmieniono kolejności dotychczasowych publikacji ani składu MCI/PIT.

## 9. Walidacja

- Pełny backend: **926 passed**. Przyrost względem 883: **43 przypadki Empire**.
  Końcowy pełny przebieg po dodatkowej kontroli sekcji Current: 37,67 s.
- Pełny frontend: **563 passed**, 22 pliki, z blokadą sieci zgodną z CI.
  W pełnych przebiegach tego etapu nie wystąpił znany sporadyczny błąd MCI.
- Production build: **passed**. Jawne ostrzeżenie Vite: główny pakiet
  **524,26 kB**, ponad 500 kB; progu nie zmieniono.
- `git diff --check`: poprawny. Nic nie jest staged.
- Offline testy obejmują CSV, rozróżnienie SA/NSA/Future, ND/zero/ujemne,
  brak kolumn i miesięcy, duplikaty, daty, własny PDF i sekcję Current,
  spóźniony CSV, dokument bez liczby, rewizje, starszy plik, idempotencję,
  rollback, błędy HTTP, niezależne statusy, provenance, prawa, API,
  przyszły Actual, Previous, brak 2027, DST i cooldown.
- Nowy adapter izolowano w starszych testach niezwiązanych źródeł.
  Nie osłabiono globalnych blokad sieci/DB. Nie pomijano testów,
  nie zwiększano timeoutów i nie zmieniano MCI.
- Rzeczywisty HTTP API: cztery daty tabeli oraz brak wydarzeń 2027,
  właściwe wartości i okresy, jeden wiersz/miara, niezależne statusy, puste prognozy.
- Prawdziwy Chrome i API, bez fixture'ów odpowiedzi: **24 scenariusze**,
  EN/PL, **1366/390 px**, **56 odpowiedzi API HTTP 200**, zero wyjątków
  JavaScript i poziomego overflow. Daty IX–XII, filtry kategorii/★★★,
  źródła i prawa, jednostki, szczegóły, Escape/fokus, sześć kart i limit czterech.
  Obejrzano końcowe zrzuty, w tym mobilny PL. Bieżące okno Overview nie zawiera
  jeszcze 16.11; przyszłą pozycję Empire i prawa sprawdzają testy EN/PL.
- Podczas kontroli prawdziwego UI utrzymywano wspólną blokadę odświeżania.
  Nie podstawiano odpowiedzi koordynatora i nie uruchamiano pozostałych importerów.
  Po zakończeniu kontroli blokadę zwolniono.

Pierwsze nowe testy i kontrola parsera wykryły problemy fixture'ów oraz możliwość
odczytu tabeli Future po zmianie układu PDF. Poprawiono rzeczywistą walidację,
sprawdzono oba zachowane oficjalne PDF i ponownie cały backend.
Próby helpera Chrome wymagały poprawienia inicjalizacji języka/localStorage;
końcowy pełny przebieg opisany powyżej nie ma tych wyjątków. Nie instalowano
dodatkowych pakietów i nie zmieniano progów weryfikacji.

## 10. Ograniczenia i kontrola ręczna

Brak potwierdzonego 2027, konsensusu, pełnej historii first printów, pomiaru
latencji nowej publikacji i gwarancji aktualizacji w chwili planowanego zegara.
Zapisano tylko VIII–X; wcześniejsze potrzebne poziomy pozostają puste.
Obsługa innego przyszłego formatu PDF/CSV może wymagać przeglądu zamiast zgadywania.
Nie potwierdzono wszystkich przyszłych wyjątków rocznych ani kompletności
zmian intraday. Zachowano BLS 403 i pozostałe ograniczenia wcześniejszych etapów.
Nie wykonano ingestion FRED/ALFRED, resetu bazy lub backfillu innych serii.

Ręcznie: Calendar → Date range → 15.09, 15.10, 16.11 i 15.12.2026.
Sprawdź tabelę odczytów, 14:30, brak procentów, szczegóły i prawa NY Fed.
Włącz ★★★ — Empire znika; wybierz Growth and consumer — pozostaje.
Przełącz EN/PL, otwórz szczegóły na telefonie i zamknij Escape.
Dla stycznia 2027 nie powinno powstać wydarzenie Empire.

## 11. Końcowy Git — pełna lista

HEAD i gałąź bez zmian. **22 modified, 5 untracked**, nic staged.
Bez commita, pusha, resetu, clean i zmian historii. Nie uruchamiano nowego CI.

Zastane, zachowane SHA-256 i poza zakresem zmian etapu:

- `README.md` — modified.
- `frontend/src/brief/SourceCheckStatus.tsx` — modified.
- `frontend/src/brief/SourceCheckStatus.test.tsx` — modified.
- `frontend/src/styles.css` — modified.
- `docs/audits/calendar-next-releases-priority-2026-10-29.md` — untracked.

Zmodyfikowane w etapie 3C:

- `app/analytics/calendar_agenda.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/release_calendar.py`
- `app/analytics/source_checks.py`
- `app/database/schema.sql`
- `app/source_checks.py`
- `frontend/src/api/macrolens.ts`
- `frontend/src/brief/EconomyBrief.tsx`
- `frontend/src/brief/EconomyBrief.test.tsx`
- `frontend/src/brief/briefModel.ts`
- `frontend/src/brief/upcomingEvents.ts`
- `frontend/src/brief/upcomingEvents.test.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/i18n/pl.json`
- `tests/conftest.py`
- `tests/test_source_checks.py`

Nowe pliki etapu:

- `app/analytics/empire_state.py`
- `app/ingestion/sync_empire_state.py`
- `tests/test_empire_state.py`
- `docs/audits/calendar-empire-state-2026-10-29.md` — ten raport.

Nie dodano sekretów, `.env`, kluczy API, lokalnych danych PostgreSQL, RAW,
cache, logów, profili i zrzutów przeglądarki. Nie rozpoczęto kolejnej integracji.

## 12. Kontrola zamknięcia etapu — 29.10.2026

Ponownie przejrzano pełny diff, nowe moduły, testy, kontrakt API i źródłowe
[warunki NY Fed](https://www.newyorkfed.org/privacy/termsofuse). Nie zmieniano
metodologii. W transakcji tylko do odczytu (`transaction_read_only=on`)
potwierdzono ponownie tabelę IX–XII z sekcji 4 oraz hashe pięciu zapisanych
receipts/RAW. Nie wykonywano nowych żądań do wydawców ani ingestion.
Poprzednie kontrole Chrome pozostają wynikami wdrożenia, nie nowym przebiegiem
przeglądarkowym zamknięcia. Nie zmieniono MCI/PIT lub pozostałych publikacji.

### Rzeczywisty PostgreSQL: instalacja i aktualizacja

Docker Compose uruchamia PostgreSQL i zachowuje wolumen; nie montuje
`schema.sql` jako automatycznej inicjalizacji. Obsługiwana procedura projektu
to **`python -m app.database.init_db`** z aktywnego środowiska `.venv`.
Należy wykonać ją zarówno po utworzeniu pustej bazy, jak i przy aktualizacji
istniejącej instalacji, przed uruchomieniem nowego kodu. Procedura wczytuje
cały `schema.sql`, zatwierdza go transakcyjnie i wycofuje po błędzie.
Nie trzeba ręcznie wykonywać fragmentów DDL. Sam `docker compose up` nie
zastępuje tej komendy; nie dodano migracji podczas odczytu API.

Dodano trzy idempotentne indeksy: dokumentów po `(source, retrieved_at, id)`
oraz częściowe indeksy obu nowych FK obserwacji. Sprawdzono plan odczytu
dokumentów z wyłączonym seqscan — indeks potrafi obsłużyć filtr i kolejność;
nie przedstawia się tej próby na małej bazie jako benchmarku dużej historii.
FK mają domyślne NO ACTION: usunięcie lub zmiana ID używanego dokumentu
jest odrzucana, bez kaskadowego usuwania obserwacji. Dawne dane mogą mieć NULL.

Nowy, jawnie uruchamiany skrypt **`tests/postgres_empire_validation.py`**
tworzy dwie losowo nazwane bazy `macrolens_empire_test_<uuid>` i usuwa tylko
te utworzone przez siebie bazy po zamknięciu połączeń. Wymaga uprawnienia
CREATE DATABASE; nie inicjalizuje skonfigurowanej bazy użytkownika.
Przykład: `python tests/postgres_empire_validation.py --baseline 0147d6e`.
Odpowiedzi wydawcy są syntetyczne przez MockTransport, SQL jest rzeczywisty.
Skrypt jest osobną walidacją integracyjną, poza domyślnym offline pytest.

Oba scenariusze przeszły na working tree i następnie na dokładnym stagingu:

- **Nowa instalacja:** cały schemat, ponowna inicjalizacja bez duplicate errors,
  wymagane kolumny, nullable, FK i indeksy; rzeczywisty importer i powiązania.
- **Aktualizacja:** schemat z `0147d6e`, syntetyczne wcześniejsze obserwacje
  `fred_snapshot` i `alfred`, następnie dwukrotne uruchomienie istniejącego
  inicjalizatora z nowym SQL. Wszystkie wcześniejsze pola i wartości pozostają
  identyczne, dwa nowe FK są NULL. Nie zmieniono ich identyfikatorów/wersji.
- **Importer:** pierwsze przyjęcie, identyczny import bez zmiany `ingested_at`,
  nowy hash bez zmiany wartości, dwie rewizje tego samego dnia 7,6 → 7,8 → 7,9,
  odzyskanie wartości i przejść z RAW/receipts, odrzucenie znanej starej kopii,
  osobne błędy PDF i CSV, zachowanie ostatnich wyników oraz ochrona referencji.
- **Rollback:** trigger PostgreSQL wywołał błąd podczas zapisu obserwacji.
  Wszystkie nowe receipts i zmiany obserwacji w tej transakcji zostały cofnięte,
  próba otrzymała status error; nie powstały referencje bez dokumentu.
  RAW nieudanego importu mogą pozostać diagnostyką; nie oznaczają udanego zapisu.

Nie resetowano bazy użytkownika. W zamknięciu nie aplikowano na niej DDL ani
nie zmieniano obserwacji. Indeksy i aktualizację instalacji wdraża powyższa
normalna procedura projektu. Pierwsze próby helpera testowego wykryły brak
przekazania hasła w parametrach połączenia oraz parametryzację znaku `%`
w zapytaniu diagnostycznym; poprawiono helper, po czym oba pełne scenariusze
przeszły dwukrotnie. Nie ujawniono hasła i nie zmieniano ustawień serwera.

### Pełna walidacja i dokładny staging

Working tree: **926 passed backend**, **563 passed frontend / 22 pliki**,
production build poprawny, główny pakiet **524,26 kB**. Dokładna kopia stagingu
z pozostałymi śledzonymi zależnościami, bez pięciu wcześniejszych plików:
**926 passed backend**, **563 passed frontend**, poprawny build **526,31 kB**
oraz ponownie oba scenariusze PostgreSQL. Kopia zawiera wersje README,
SourceCheckStatus i styles z HEAD, a nie wcześniejsze zmiany użytkownika.
Stąd różnica rozmiaru pakietu. Nie pomijano testów, nie zwiększano timeoutów,
nie zmieniano MCI. Sporadyczny błąd MCI nie wystąpił w tych przebiegach.
Ostrzeżenie Vite ponad 500 kB pozostaje jawne, próg niezmieniony.

`git diff --check` i `git diff --cached --check` przeszły. Porównano zawartość
stagingu z wybranymi plikami, przejrzano pełny staged diff i sprawdzono wzorce
sekretów oraz brak danych lokalnych/artefaktów. Sandbox wymagał ponowienia
części komend z dostępem do logów i plików tymczasowych Vite; nie był to błąd
testów aplikacji. Ostrzeżenia LF→CRLF nie są błędami whitespace.

### Zatwierdzany zakres i informacje po commicie

Jeden commit: **`Add Empire State calendar and official NY Fed readings`**.
Zakres obejmuje dokładnie **23 pliki** — 22 pliki wdrożenia plus osobny skrypt
rzeczywistej walidacji PostgreSQL:

- `app/analytics/calendar_agenda.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/empire_state.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/release_calendar.py`
- `app/analytics/source_checks.py`
- `app/database/schema.sql`
- `app/ingestion/sync_empire_state.py`
- `app/source_checks.py`
- `frontend/src/api/macrolens.ts`
- `frontend/src/brief/EconomyBrief.tsx`
- `frontend/src/brief/EconomyBrief.test.tsx`
- `frontend/src/brief/briefModel.ts`
- `frontend/src/brief/upcomingEvents.ts`
- `frontend/src/brief/upcomingEvents.test.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/i18n/pl.json`
- `tests/conftest.py`
- `tests/test_source_checks.py`
- `tests/test_empire_state.py`
- `tests/postgres_empire_validation.py`
- `docs/audits/calendar-empire-state-2026-10-29.md`

Poza stagingiem, z identycznymi SHA-256, pozostają:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`
- `docs/audits/calendar-next-releases-priority-2026-10-29.md`

Sekcję zapisano przed ostatecznym commitem. Hash nowego commita, wynik zwykłego
pusha, rzeczywisty link i wyniki GitHub Actions oraz końcowy status Git zostaną
podane w zewnętrznym raporcie Codexa po ich uzyskaniu. Przed commitem zdalny
`origin/main` nadal wskazywał `0147d6e`. Nie deklaruje się tutaj przyszłego sukcesu.
Obecny MacroLens CI uruchamia offline backend i frontend/build **bez serwisu
PostgreSQL**; jego sukces nie zastąpi opisanej osobnej walidacji migracji.

Pozostają ograniczenia current-vintage, niepełnej historii first printów,
przechwyconych zamiast wszystkich wersji intraday, interwału 6 godzin,
niepotwierdzonego 2027, braku konsensusu i nierozstrzygniętej zgodności innych
źródeł/FRED. Nie deklaruje się publicznej gotowości całej aplikacji.
