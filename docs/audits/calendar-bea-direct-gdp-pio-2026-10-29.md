# MacroLens — R2: bezpośredni Actual GDP i PIO z BEA

Weryfikacja **29.10.2026**, Europe/Warsaw, `C:\Projects\macrolens`, `main`,
HEAD `3111c81040e6c20ed30d020585af65c553398bf5`. Wdrożono bezpośrednie
opublikowane stopy BEA dla istniejących wydarzeń GDP / Personal Income and
Outlays. **Bez stagingu, commita i pusha.** Sześć wcześniejszych plików
zachowano byte-identycznie, porównując SHA-256 przed i po pracy.

## Źródła i faktycznie wybrany format

Przejrzano oficjalny [harmonogram](https://www.bea.gov/news/schedule/full),
strony [GDP](https://www.bea.gov/data/gdp/gross-domestic-product),
[Personal Income](https://www.bea.gov/data/income-saving/personal-income)
i [PCE prices](https://www.bea.gov/data/personal-consumption-expenditures-price-index/).
Zbadano pięć własnych dokumentów HTML:

- [GDP Q3 Advance, 29.10](https://www.bea.gov/news/2026/gdp-advance-estimate-3rd-quarter-2026).
- [GDP Q2 Second, 26.08](https://www.bea.gov/news/2026/gdp-second-estimate-and-corporate-profits-2nd-quarter-2026).
- [GDP Q2 Third, 30.09](https://www.bea.gov/news/2026/gdp-third-estimate-industries-corporate-profits-state-gdp-and-state-personal-income-2nd).
- [PIO September, 29.10](https://www.bea.gov/news/2026/personal-income-and-outlays-september-2026).
- [PIO August, 30.09](https://www.bea.gov/news/2026/personal-income-and-outlays-august-2026).

Nagłówek H1 identyfikuje raport, okres i etap. Własny nagłówek embargo
potwierdza datę, weekday, godzinę i EST/EDT. GDP ma tabelę Real GDP and
Related Measures z kolumnami etapów tego samego kwartału. PIO ma tabelę
Personal Income and Related Measures z miesięcznymi zmianami, natomiast
core r/r i saving rate występują w osobnych jednoznacznych akapitach.
Nagłówkowa kwota nominalnego PCE/DPI nie zastępuje realnych zmian.

Raporty zawierają rzeczywiste linki Full Release PDF, Historical Comparisons
XLSX, a GDP także Vintage History; odsyłają do archiwum wersji i interaktywnych
tabel. Dwa podlinkowane PDF bieżących GDP/PIO odczytano dodatkowo w pamięci
(425531 / 404608 bajtów); nie są źródłem importowanych obserwacji.
Produkcja tej wersji używa **HTML published rates**, bez importera PDF,
XLSX lub API NIPA. Po zmianie HTML zachowuje ostatni poprawny wynik i błąd,
zamiast szukać dowolnej liczby lub automatycznie zmieniać kanał.

## Mapowanie i definicje

Zachowano release 53/54 oraz siedem identyfikatorów miar istniejącego API.
Nie utworzono nowych wydarzeń. Rozpoznawane linie mają następujące znaczenie:

| Miara MacroLens | Konkretne pole komunikatu / odniesienie NIPA | Jednostka i metoda |
| --- | --- | --- |
| GDPC1 / qoq_annualized | Real GDP, własna kolumna Advance/Second/Third/Updated; tabela 1.1.1 Real GDP | Opublikowana kwartalna zmiana realna SAAR, procent |
| PCEPI / mom | PCE price index / Percent change from preceding month; tabela 2.8.7, linia PCE | Opublikowana miesięczna zmiana cen SA |
| PCEPILFE / mom | PCE price index excluding food and energy; 2.8.7, linia PCE excluding food and energy | Miesięczna zmiana cen SA |
| PCEPILFE / yoy | Osobny akapit core / from one year ago | Roczna zmiana cen; nie roczna zmiana realnej konsumpcji |
| PCEC96 / mom | Real PCE w miesięcznej tabeli; 2.8.1, linia real PCE | Miesięczna zmiana realna, bez dodatkowej annualizacji |
| DSPIC96 / mom | Real DPI w miesięcznej tabeli; real DPI w addendum 2.6 | Miesięczna zmiana realnego dochodu rozporządzalnego |
| PSAVERT / raw | Personal saving rate / percentage of DPI; odpowiednia linia 2.6 | Poziom procentowy, bez m/m |

Nazwy tabel zweryfikowano w Related Data Tables oraz oficjalnych
[metadanych opisowych PIO](https://www.bea.gov/news/pio-release-additional-information).
**2.8.6 zawiera poziomy realnego PCE, a 2.8.11 roczne zmiany realnego PCE;
2.8.11 nie jest źródłem core PCE inflation r/r.** 2.8.4 zawiera indeksy cen,
a 2.8.7 ich zmiany. Nie podstawiono tabeli poziomów za gotową stopę.
Mapowanie wdrożenia dotyczy jawnych nazw linii i jednostek HTML, nie
numerycznych LineCode API. Nie deklaruje się zweryfikowanego mapowania
TableName/LineCode/Frequency/TimePeriod ani działającego feedu API NIPA.
[API BEA](https://apps.bea.gov/api/signup/) wymaga odrębnej rejestracji/klucza;
nie rejestrowano konta i nie uzależniono wdrożenia od uzyskania klucza.

## Potwierdzanie raportu i wybór źródła

Wydzielono wspólny `parse_bea_clock` z parsera R1. Zachowuje jego ścisłe
reguły i stare metadane, lecz direct Actual wymaga pełnego potwierdzonego
zegara. Sprawdza oficjalny HTTPS `/news/`, tytuł, okres, etap, datę, weekday,
EST/EDT względem IANA i konflikty metadanych. Godzina pochodzi z właściwego
wiersza harmonogramu; nie zastępuje się np. jawnego 10:00 stałym 08:30.
GDP dodatkowo uzgadnia kwartał tabeli i pierwszego akapitu oraz wynik
tekstowy z własną kolumną tabeli. Previous jest poprzednim kwartałem
z akapitu, nie wcześniejszą estymacją tego samego kwartału.

PIO wymaga własnego miesiąca/roku, miesięcznej tabeli i poprawnych kolumn
poprzedniego/bieżącego miesiąca. Brak jednej linii nie pożycza nominalnej,
headline/core lub rocznej liczby; inne poprawne miary mogą zostać zapisane,
a kontrola jest partial. Nieprawidłowe liczby i konflikt tekst/tabela
odrzucają dokument. Zero zaokrąglone jest poprawną liczbą.

Preferencja jest deterministyczna: zgodny potwierdzony BEA + powiązana
obserwacja SQL → BEA Actual; brak zgodnego dowodu → dotychczasowy FRED
z jawną etykietą fallback. Dokument bez zgodnego wiersza SQL/FK nie tworzy
liczby. Niewłaściwy okres/etap/data oraz przyszły dokument nie mogą zostać
pożyczone. Bezpośredni własny raport potwierdza okres również wtedy, gdy
FRED nie ma jeszcze obserwacji lub metadanych okresu.

`fred_alternative` zachowuje odrębną wartość i provenance. Rozbieżność większa
niż 0,05 pkt proc. przy stopie ogłoszonej do jednego miejsca oznacza konflikt;
BEA pozostaje Actual, a konflikt jest jawny. Taki rozjazd może wynikać
z późniejszych rewizji current-vintage; nie oznacza automatycznie błędu BEA.
Nie miesza się wartości w średnią i nie zastępuje opublikowanego 3,4
wyliczeniem FRED 3,369619.

Previous pochodzi z tego samego dokumentu BEA, jeśli jest dostępny. Gdy
brakuje go w HTML, dopuszczony jest wyłącznie jawny FRED Previous dokładnie
poprzedniego okresu i tej samej miary. `mixed_sources` wyłącza różnicę.
Brak takiego dopasowania pozostawia Previous pusty. Nie kopiuje się wartości
z poprzedniego komunikatu jako rzekomo niezrewidowanego Previous nowego.

## Rzeczywiste wyniki Calendar

| Publikacja 29.10 | Actual BEA | Previous | Źródło Previous |
| --- | ---: | ---: | --- |
| GDP Q3 Advance | 3,4% | 2,2% | Ten sam BEA |
| Headline PCE m/m, IX | 0,5% | 0,3% | Ten sam BEA |
| Core PCE m/m, IX | 0,3% | 0,3% | Ten sam BEA |
| Core PCE r/r, IX | 3,1% | ok. 3,034442% | Odrębny FRED current-vintage; bez różnicy |
| Real PCE m/m, IX | 0,0% | 0,5% | Ten sam BEA |
| Real DPI m/m, IX | −0,3% | 0,0% | Ten sam BEA |
| Saving rate, IX | 3,8% | 4,0% | Odrębny FRED current-vintage; bez różnicy |

0,0% realnego PCE jest zaokrągleniem komunikatu, nie dowodem matematycznego
braku zmiany. API zachowuje precision=1 i metodę published_rate/published_level.
Wyniki aplikacji pochodzą z parsera i bazy; nie są stałymi w kodzie.
Zaimportowany GDP Second Q2 ma 1,5 / 2,1, a Third Q2 2,2 / 2,5.
Różne Previous tych etapów pozostają odrębnymi dowodami.
PIO August ma m.in. core m/m 0,2 oraz saving 4,1; późniejszy wrześniowy
dokument podaje zrewidowane sierpniowe core m/m 0,3. Nie nadpisano dawnego
komunikatu wrześniowym Previous.

Rzeczywiste GET potwierdziły puste Actual dla GDP Second **25.11**, GDP Third
**23.12** i PIO za X **25.11**. Wartości Q3 Advance nie przeniesiono do
przyszłych etapów. Forecast pozostaje null, konsensus not_integrated.
29.10 08:30 EDT = 12:30 UTC = **13:30 PL**; przyszłe 08:30 EST to 14:30 PL.
Konwersja korzysta z IANA, bez stałej różnicy sześciu godzin.

## Magazyn, import i koordynator

Źródło `bea_official`; istniejące `publisher_documents`, `series` oraz
`observation_vintages`. Wewnętrzne identyfikatory BEA rozdzielają miarę
i etap GDP; identyfikatory miar API pozostają oryginalne. Nie dodano ich
do katalogu FRED/wykresów ani `config/series.yaml`. Nie zmieniono schematu,
unikalności obserwacji lub inicjalizatora. DDL bazy użytkownika nie wykonywano.

Actual jest w SQL NUMERIC, powiązany FK z własnym dokumentem. Receipt
zachowuje rzeczywisty URL, HTTP, fetched_at, SHA-256, RAW, tytuł, okres,
etap, pole, opublikowany tekst liczby, jednostkę i precision. Parsed Previous
jest metadanymi pola własnego dokumentu. Odczyt Actual wymaga obserwacji SQL,
nie używa samej kopii wyniku w JSON jako równoległego magazynu liczb.

RAW jest niezmienny, adresowany hashem. Zmieniony dokument tworzy receipt
i przejście before/after; ponowne identyczne bajty są idempotentne. Znany
starszy hash jest odrzucany. Nie ma uniwersalnego dowodu kolejności dowolnej
nieznanej wcześniej, nieoznaczonej kopii wydawcy. Jedna dzienna obserwacja
może się zmienić intraday; przechwycone wcześniejsze wersje pozostają
w RAW/receipts. To captured snapshot od wdrożenia, **nie pełna historia
first printów ani wszystkich zmian intraday**. FRED zachowuje current-vintage.

Adapter jest wywoływany przed FRED w dotychczasowym jobie. Standardowo:
harmonogram + najnowszy należny GDP + najnowszy należny PIO = trzy żądania.
Nie ma crawlera archiwum, nowego schedulera lub szybkiego okna. Zachowano
lock 726530019, budżet, transakcje i **900 s** między jobami; wolne zasoby
pozostają na **21600 s**. Awaria/wyczerpanie budżetu FRED nie uniemożliwia
wcześniejszej próby BEA. Błąd parsera/HTTP zachowuje ostatni poprawny wynik;
błąd SQL wycofuje jednostkę zapisu dokumentów/obserwacji. Wspólna generacja
jest publikowana przez dotychczasowy koordynator.

Kontrolowany import rozpoczęto **2026-10-29T21:26:07.981488+00:00**.
Sześć HTTP 200: harmonogram i pięć wybranych dokumentów; **15 obserwacji**.
Ponowne przetworzenie zachowanych dokumentów bez HTTP: brak zmian obserwacji
i ich ingested_at. Porównano pełne pozostałe **1 649 695 obserwacji**:
SHA-256 przed/po identyczny:
`1c6609b43f80a14ef5b346aaa9dc2eeae2a1f2870adfb01b6b016f83229c6db6`.
Nie uruchamiano innych importerów ani FRED/ALFRED backfillu.

Pierwsza publikacja Overview: `4a887a99-a8a3-4703-82d0-589fafcd4c0d`.
Po doprecyzowaniu precyzji/źródła rocznego kontekstu przebudowano wyłącznie
cache z zapisanych danych: `aa1347af-17b9-4fab-93ee-3deaf86df160`.
Dokumenty/RAW produkcyjne są w ignorowanym `data/raw/bea_official/`,
diagnostyka w `data/raw/bea-direct-2026-10-29/`. Wstępne pięć pobrań HTML
służyło badaniu formatu; dodatkowe dwa PDF wyłącznie diagnostyce w pamięci.

Rzeczywiste SHA-256 zachowanych HTML:

- GDP Advance: `b51d2f8f5bb721a5b37d17426a7512dcbfce1949aeb1e33b3ff28c823fcaaa30`.
- GDP Second: `9df4091f2d06bae11761d7a41e996d574555ca7936e572373956fdf89a9a19c1`.
- GDP Third: `f7232e509576e8c9f5649c05c966bec16e9e0b834ba1876a97f771645d3a31da`.
- PIO September: `ecebe8c3ca45d0e8b73d1036edee38838e930b6d96b89f7098235d76ea6b1f07`.
- PIO August: `3abedebba9660e9322d9b0bee8aa98064b0a2ffd9c0904384a723bb962b732ce`.

Na końcowej wersji kodu ponownie odczytano pięć receipts oraz RAW w transakcji
read-only, potwierdzono hashe i identyczne wyniki parsera z zachowanego
harmonogramu i dokumentów. Nie wymagało to nowych żądań ani importu.

## API, UI, prawa i ograniczenia

Calendar i Overview zachowują układ, kolumny, filtry, sześć kart i limit
czterech wydarzeń. Bez nowego CSS. Actual/Previous BEA są prezentowane do
jednego miejsca, także 0,0. Różnice mieszanych źródeł są puste. Szczegóły
Calendar i istniejący tooltip Overview pokazują źródło, oryginalny tytuł,
etap, snapshot, hash, pobranie, zaokrąglenie i alternatywę FRED w EN/PL.
Tooltip korzysta z istniejącego ograniczonego, przewijanego wariantu.
Eksport Overview zachowuje prawa i provenance. Wcześniejszy roczny kontekst
FRED realnych miar pozostaje odrębnie oznaczony; core r/r używa BEA.
Nie oblicza się porównania z odległym FRED punktem historycznym jako
rzekomo jednorodnej historii BEA. MCI/PIT oraz jego inputy pozostają bez zmian.

[BEA FAQ 147](https://www.bea.gov/help/faq/147) dopuszcza użycie/reprodukcję
własnych materiałów public-domain, jeśli nie zastrzeżono inaczej, i prosi
o atrybucję. Użyte komunikaty nie wskazały odmiennej licencji dla tych stóp.
Zachowano pełną nazwę BEA, źródło, oryginalny tytuł, politykę, własne
normalizacje i brak endorsement, bez logo. Nie przenosi się tego ustalenia
na cudze materiały, całe MacroLens ani niezależne warunki FRED/RAW/cache.
Nie deklaruje się gotowości publicznego demo ani gwarancji prawnej całości.

Nie zmierzono nowej publikacji na żywo ani skrócenia latencji w minutach.
HTML może być opóźniony lub zmieniony; cykl 15 minut i atomowe zakończenie
mogą opóźnić dostępność. Nie ma gwarancji Actual dokładnie o 08:30 ET,
konsensusu, pełnej historii first printów lub wszystkich zmian intraday.
API NIPA/PDF fallback nie zostały wdrożone. Zachowano BLS 403 i ograniczenia
pozostałych rodzin. Nie rozpoczęto następnego etapu.

## Walidacja

- Backend: **1057 passed**, w tym **51 nowych przypadków BEA** ponad 1006.
  Zachowano wcześniejsze regresje GDP/PCE, Empire, FT900, ISM, ADP, Michigan.
- Frontend z blokadą sieci CI: **600 passed / 25 plików**. Sześć nowych
  testów sprawdza EN/PL, dokładność, zero, konflikt, mieszane Previous,
  FRED fallback oraz provenance eksportu.
- Osobny TypeScript typecheck i production build: poprawne. Główny pakiet
  **543,03 kB**, gzip **157,71 kB**; jawne ostrzeżenie ponad 500 kB,
  bez zmiany progu lub optymalizacji bundla.
- `tests/postgres_bea_validation.py`: rzeczywisty PostgreSQL, syntetyczne
  HTTP, wyłącznie własna baza `macrolens_bea_test_<uuid>`. Pierwszy import,
  identyczne bajty/ingested_at, dwie rewizje jednego dnia, odzyskanie RAW,
  FK i wybór BEA, HTTP/parser error oraz rollback po triggerze SQL przeszły.
  Wcześniejsze FRED/ALFRED w tej bazie zachowano; własną bazę usunięto.
- Rzeczywiste GET API: komplet siedmiu wyników i przyszłe daty opisane wyżej.
- Końcowy Chrome bez fixture'ów API: **40 scenariuszy**, EN/PL,
  **1366 / 390 px**, **24 odpowiedzi API HTTP 200**, bez wyjątków JS
  i poziomego overflow. Siedem odczytów, przyszłe puste Actual, ★★★,
  szczegóły źródeł, Escape/fokus, nawigacja, sześć kart, limit wydarzeń
  i BEA w tooltipie Overview. Obejrzano zrzuty desktop/mobile.
- UI sprawdzano pod wspólną blokadą przez połączenie read-only.
  Liczba/max timestamp source_check_runs i stan/generacja koordynatora
  przed/po pozostawały identyczne. Blokadę zwolniono; innych importerów
  nie uruchamiano i nie podmieniano odpowiedzi API.
- Whitespace poprawny. Nie pomijano testów, nie zwiększano timeoutów,
  sporadyczny błąd nawigacji MCI nie wystąpił w pełnych przebiegach.

Przegląd/testy wykryły i poprawiły: zależność wrappera R1 od lokalnej zmiennej
po wydzieleniu zegara, niepełny syntetyczny nagłówek SAAR, brak kontroli
kwartału tabeli, uzależnienie cold bindingu od okresu FRED oraz brak pobrania
zegara z własnego wiersza harmonogramu. Dwie starsze kontrole liczby operacji
zachowano po włączeniu BEA do tego samego odczytu DB; asercja wyników źródeł
używa teraz identyfikatorów zamiast pozycji FRED w liście. Nie osłabiono
globalnych blokad testów sieci/DB. Pierwszy typecheck nowego fixture wykazał
brak wymaganych pól typu; uzupełniono fixture. Helper Chrome miał nieprawidłowy
selektor formularza zakresu; po poprawce powtórzono pełne przebiegi. Początkowo
Docker był wyłączony: próba PostgreSQL skończyła się timeoutem; uruchomiono
istniejący Docker Desktop i zachowany kontener, bez resetu wolumenu.

## Zakres plików i Git

23 pliki R2:

- `app/analytics/bea_direct.py` — nowy.
- `app/analytics/calendar_agenda.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/overview_readings.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/source_checks.py`
- `app/ingestion/sync_bea_reports.py` — nowy.
- `app/ingestion/sync_calendar_periods.py`
- `frontend/src/api/macrolens.ts`
- `frontend/src/brief/EconomyBrief.tsx`
- `frontend/src/brief/readingComparisons.ts`
- `frontend/src/brief/readingHoverText.ts`
- `frontend/src/calendar/BeaEvidence.tsx` — nowy.
- `frontend/src/calendar/BeaEvidence.test.tsx` — nowy.
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/calendarComparisons.ts`
- `frontend/src/calendar/calendarPresentation.ts`
- `frontend/src/i18n/pl.json`
- `tests/conftest.py`
- `tests/test_overview_refresh.py`
- `tests/test_bea_direct.py` — nowy.
- `tests/postgres_bea_validation.py` — nowy.
- `docs/audits/calendar-bea-direct-gdp-pio-2026-10-29.md` — ten raport.

Poza zakresem, byte-identyczne względem początku pracy: README.md,
SourceCheckStatus.tsx, SourceCheckStatus.test.tsx, styles.css oraz dwa
wcześniejsze nieśledzone audyty priorytetów i opóźnienia. Nic staged.
Nie dodano sekretów, kluczy, `.env`, RAW, bazy, logów, cache, helperów,
profili i zrzutów do plików repozytorium. Bez commita, pusha i nowego CI.

Końcowy status: **20 modified, 9 untracked**, `main`, HEAD bez zmian.
Pełną listę `git status --short` sprawdzono; cztery modified i dwa untracked
z tego zestawu należą do chronionego wcześniejszego stanu. Nie wykonano
resetu, clean, amend ani zmiany historii.

## Kontrola zamknięcia R2 — 30.10.2026

Potwierdzono `main`, HEAD `3111c81040e6c20ed30d020585af65c553398bf5`,
20 modified / 9 untracked i pusty początkowy staging. Przejrzano pełny diff,
23 pliki R2, audyty R1/opóźnienia/Empire/FT900 i istniejący magazyn dokumentów.
Nie znaleziono nowych niezwiązanych zmian. Sześć chronionych plików zachowano
byte-identycznie i wyłączono z zatwierdzanego zakresu.

Przegląd zaostrzył jedną kontrolę odczytu: BEA wymaga teraz zgodności **obu**
FK obserwacji, source_document_id i publication_document_id, z własnym
dokumentem. Importer już zapisywał oba poprawnie. Dodano regresję błędnego
FK publikacji, sześć przypadków granicy tolerancji, późniejszy FRED i raport
jeszcze nieprzechwycony. **Dokładne ±0,05 pkt proc. jest w tolerancji**;
wartość przekraczająca tę granicę jest konfliktem. Porównanie odbywa się
przez Decimal(str(value)), bez odejmowania float i bez twierdzenia, że
poznano niepublikowane cyfry lub szczegółowy algorytm zaokrąglania BEA.
BEA zachowuje pierwszeństwo również po późniejszym snapshotcie FRED.

Rzeczywista PostgreSQL, wymuszony read-only: ponownie zweryfikowano pięć
receipts/RAW i ich harmonogram, hashe, wynik parsera i 15 wierszy z oboma FK.
Rzeczywisty HTTP do odrębnego API z PGOPTIONS default_transaction_read_only=on
potwierdził daty 26.08, 30.09, 29.10, 25.11 i 23.12. GDP Second Q2 ma
1,5 / 2,1, Third Q2 2,2 / 2,5, Advance Q3 3,4 / 2,2; sześć PIO z 29.10
pozostaje zgodnych z tabelą powyżej. Dwa mieszane Previous pozostają FRED,
bez Difference; precision=1, brak Forecast i brak przyszłych Actual.
PIO za VII bez własnego zaimportowanego BEA zachował odczyty FRED jako
fallback. Nie podmieniano odpowiedzi API i nie wykonywano POST refresh.
Liczba/max timestamp kontroli i stan/generacja koordynatora przed/po były
identyczne. Nie wykonywano nowych pobrań wydawców, ingestion, DDL lub
inicjalizacji bazy użytkownika. Własny proces API zakończono.

Nowe pełne przebiegi working tree: **1066 backend passed** (64,76 s),
**600 frontend passed / 25 plików** z blokadą sieci CI, osobny typecheck
i poprawny production build **543,03 kB**, gzip **157,71 kB**.
Ostrzeżenie Vite ponad 500 kB pozostaje jawne, progu nie zmieniono.
Nie pomijano testów, nie zwiększano timeoutów i nie zmieniano MCI/PIT.
Sporadyczny błąd nawigacji MCI nie wystąpił w tym pełnym przebiegu.

`tests/postgres_bea_validation.py` przeszedł ponownie na własnej losowej
bazie. Oprócz wcześniejszych scenariuszy sprawdza nowy nieznany hash bez
zmiany wartości: zapisuje przechwyconą reprezentację, nie ogłasza rewizji
liczby. Kolejność pobrań nadal nie dowodzi kolejności nieoznaczonych wersji
wydawcy; ograniczenie pozostaje jawne. Test kontroluje dwa przejścia rewizji,
RAW, FRED/ALFRED, parser/HTTP error, obie referencje SQL i rollback po triggerze.
Uodporniono jego syntetyczny zegar projekcji na uruchomienie po dacie fixture,
gdy faktyczne capture używa już późniejszego zegara; produkcyjnego zegara
ani interwałów nie zmieniano. Własną bazę usunięto. Pierwsza próba przed
uruchomieniem Dockera zakończyła się timeoutem połączenia; nie policzono
jej jako sukcesu. Uruchomiono istniejący kontener bez resetu wolumenu.

Wcześniejsze 40 scenariuszy Chrome pozostaje wynikiem wdrożenia z 29.10,
nie nowym przebiegiem przeglądarkowym zamknięcia. Standardowy MacroLens CI
nie uruchamia rzeczywistego PostgreSQL; osobna walidacja nie jest zastępowana
wynikiem offline pytest. Pozostają captured snapshot/current-vintage,
niepełna historia first printów i intraday, niezależne warunki FRED, brak
konsensusu, brak pomiaru latencji nowej publikacji i gwarancji o 08:30 ET.

### Dokładny staging i zatwierdzany zakres

Indeks zawiera dokładnie 23 pliki R2 z powyższej listy, łącznie z niezbędnym
zaostrzeniem FK i testami zamknięcia. Pełny staged diff przejrzano, sprawdzono
wzorce sekretów, nazwy plików i wykluczenie `.env`, RAW, bazy, cache, logów,
helperów oraz artefaktów Chrome. Obie kontrole whitespace przeszły.
Zawartość porównano przez identyfikatory Git, uwzględniając normalizację
LF/CRLF; pierwsze porównanie surowych bajtów ujawniło wyłącznie tę różnicę
zakończeń linii. Ostrzeżenia normalizacji nie są błędami whitespace.

Izolowaną kopię całego indeksu z pozostałymi śledzonymi zależnościami
sprawdzono niezależnie: **1066 backend passed** (49,33 s), **600 frontend
passed / 25 plików**, osobny typecheck, poprawny production build oraz
ponownie rzeczywista walidacja PostgreSQL na własnej bazie. Kopia nie ma
dwóch wcześniejszych nieśledzonych audytów i używa wersji README,
SourceCheckStatus i CSS z HEAD. Nie zależy od niezacommitowanych zmian
użytkownika. Jej pakiet ma **545,08 kB**, gzip **158,18 kB**; różnica wobec
working tree wynika z wyłączenia wcześniejszych zmian. Ostrzeżenie ponad
500 kB zachowano. MCI nie zgłosiło sporadycznego błędu w tym przebiegu.

Pierwszy backend kopii doszedł do 100%, ale nie zakończył procesu i nie
podał podsumowania. Nie policzono go jako sukcesu. Identyczne polecenie
ponowione z szerszym dostępem do plików zakończyło się kodem 0 i wynikiem
1066 passed. Nie ustalono szczegółowej przyczyny niezakończenia pierwszej
próby; nie zmieniano kodu/testów/timeoutów, aby ją obejść. Zidentyfikowane
własne procesy tej niedokończonej próby zakończono. Po testach uzupełniono
wyłącznie dokumentację wyników, jej staging i kopię; kod pozostał identyczny
z walidowanym indeksem. Sześć chronionych SHA-256 nadal zgadza się z początkiem
zamknięcia. Schemat i globalne interwały nie zmieniły się.

Planowany jeden commit: **`Add direct BEA GDP and PCE release readings`**.
Przed zatwierdzeniem `origin/main` nadal wskazywał bazowy `3111c81`.
Pełny hash, wynik zwykłego pusha, URL i zakończony wynik GitHub Actions
oraz końcowy Git zostaną podane w zewnętrznym raporcie Codexa po ich
uzyskaniu. Nie deklaruje się przyszłego sukcesu CI na podstawie lokalnych
testów i nie powstanie drugi commit wyłącznie dla tych informacji.
CI obejmuje offline backend i frontend/typecheck/build, bez rzeczywistego
PostgreSQL. Nie uruchomiono nowych importerów ani kolejnego etapu.
