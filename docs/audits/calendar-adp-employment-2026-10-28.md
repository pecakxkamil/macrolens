# MacroLens — etap 3B: ADP National Employment Report

Weryfikacja **28.10.2026**, `main`, HEAD
`c4926aac9281b928e2c74a6ae56dbfa900c7449c`. Wdrożono **ograniczony kalendarz
miesięcznego ADP NER, metadane dokumentów i oficjalne odnośniki; bez importera
wyników liczbowych**. Bez stagingu, commita i pusha. Cztery wcześniejsze pliki
użytkownika zachowały identyczne SHA-256. Nie rozpoczęto kolejnej integracji.

## Oficjalny zakres i rzeczywiste API

Miesięczne komunikaty wydawcy jednoznacznie podają miesiąc raportu i zapowiedź
następnej publikacji. Odczytano cztery dokumenty z
[1 lipca](https://mediacenter.adp.com/2026-07-01-ADP-National-Employment-Report-Private-Sector-Employment-Increased-by-98,000-Jobs-in-June-Annual-Pay-was-Up-4-4),
[5 sierpnia](https://mediacenter.adp.com/2026-08-05-ADP-National-Employment-Report-Private-Sector-Employment-Increased-by-44,000-Jobs-in-July-Annual-Pay-was-Up-4-4),
[2 września](https://mediacenter.adp.com/2026-09-02-ADP-National-Employment-Report-Private-Sector-Employment-Increased-by-38,000-Jobs-in-August) i
[30 września](https://mediacenter.adp.com/2026-09-30-ADP-National-Employment-Report-Private-Sector-Employment-Increased-by-90,000-Jobs-in-September).
Nie zapisano ich wyników ani treści HTML. Źródłowe URL-e zawierają tytuły
komunikatów; nie są polami obserwacji ani ręcznie wpisanymi wynikami aplikacji.

| Publikacja | Potwierdzony miesiąc | Godzina NY | Godzina PL | Dowód czasu / dokument wydarzenia | Actual / Previous / Forecast |
| --- | --- | --- | --- | --- | --- |
| 01.07.2026 | VI 2026 | Niepotwierdzona | — | Dokument z 01.07; bez wcześniejszej zapowiedzi zegara w zapisanym zakresie | — / — / — |
| 05.08.2026 | VII 2026 | 08:15 | 14:15 | Zapowiedź w dokumencie z 01.07 / dokument z 05.08 | — / — / — |
| 02.09.2026 | VIII 2026 | 08:15 | 14:15 | Zapowiedź z 05.08 / dokument z 02.09 | — / — / — |
| **30.09.2026** | **IX 2026** | **08:15** | **14:15** | Zapowiedź z 02.09 / dokument z 30.09 | — / — / — |
| **04.11.2026** | **X 2026** | **08:15** | **14:15** | Jawna zapowiedź w komunikacie z 30.09; brak dokumentu przyszłego raportu | — / — / — |
| **02.12.2026** | **Niepotwierdzony** | **Niepotwierdzona** | **—** | Widoczna sekcja Calendar na stronie NER; potwierdza tylko datę | — / — / — |

Konwersja używa IANA `America/New_York` → `Europe/Warsaw`. Nie stosuje stałego
offsetu UTC. Testy syntetycznych zegarów obejmują także rozbieżne tygodnie DST
w marcu i październiku. Nie stanowią dowodu rzeczywistego zegara dla tych dat.

**Dla 02.12 nie potwierdzono w odczytanych materiałach miesiąca XI ani godziny
08:15 ET.** Kalendarz wydawcy wyświetla jedynie datę. Gdyby wydawca potwierdził
ten zegar, przeliczenie dałoby 14:15 PL; nie nadano mu teraz statusu confirmed.
Nie przeniesiono informacji z 04.11 ani nie użyto reguły poprzedniego miesiąca.
To jawne ograniczenie względem oczekiwanego przypadku kontrolnego zadania.

[Strona NER](https://adpemploymentreport.com/) i `/about` w bezpośrednim HTTP
zwracają szkielet aplikacji JavaScript (HTTP 200, bez dat w treści).
W zwykłym Chrome rozwinięta sekcja Calendar pokazuje miesięczne Upcoming Reports:
04.11 i 02.12.2026 oraz oddzielną listę tygodniowego NER Pulse. Nie ma w niej
rocznika 2027. Nie znaleziono go również w przejrzanych oficjalnych odnośnikach.
API dla 06.01.2027 nie generuje ADP i zwraca
`not_published_in_checked_sources`, bez twierdzenia o nieistnieniu dokumentów
poza sprawdzonym zakresem.

Pomocniczy [kalendarz FRED, release 194](https://fred.stlouisfed.org/releases/calendar?rid=194&vs=2026-01-01&ve=2026-12-31)
zawiera 12 dat 2026: 07.01, 04.02, 04.03, 01.04, 06.05, 03.06, 01.07, 05.08,
02.09, 30.09, 04.11 i 02.12. Sześć włączonych dat jest z nim zgodnych.
Pozostałych nie dodano z samej listy FRED. Jej godziny są czasem US Central;
nie użyto ich zamiast niezależnego potwierdzenia ADP.
Zakres wdrożenia jest ograniczony, nie stanowi pełnego rocznego harmonogramu wydawcy.

## Miesięczny NER i NER Pulse

[Oficjalne Workforce Data Releases](https://mediacenter.adp.com/workforce-data-releases)
zawierają liczne komunikaty zatytułowane Preliminary Estimate. Ich treść
identyfikuje **NER Pulse**: tygodniową zmianę zatrudnienia w ujęciu czterotygodniowej
średniej, z opóźnieniem publikacji. Nie są wstępnym etapem miesięcznego NER.
Zwykłe strony [Press Releases](https://mediacenter.adp.com/press-releases?l=100)
zawierają również miesięczny raport. Parser wymaga jego dokładnej tożsamości,
datowanego oficjalnego URL-u i jawnego miesiąca w treści.
Odrzuca Preliminary Estimate/Pulse, obce hosty, przyszłe dokumenty, niespójne
daty oraz konflikty okresów. Nie dodano żadnego cotygodniowego wydarzenia.

## Metodologia i seria FRED — analiza bez ingestion

[Oficjalny opis metodologii ADP Research](https://www.adpresearch.com/research/how-representative-is-adp-employment-data)
opisuje administracyjne dane płacowe klientów, a nie ankietę BLS. ADP rozróżnia
pracowników aktywnych na listach płac i faktycznie opłaconych. Miesięczny NER
opiera się na tygodniu obejmującym 12. dzień miesiąca i przeważeniu według
branży, geografii i wielkości pracodawcy przy użyciu QCEW. Dane klientów nie
są samodzielnie pełnym spisem gospodarki. Raport jest niezależny od BLS CES
i nie ma być prognozą NFP. Ekonomicznie chodzi o relacje pracownik–pracodawca
(miejsca pracy), nie koniecznie unikalne osoby.

[ADPMNUSNERSA](https://fred.stlouisfed.org/series/ADPMNUSNERSA):
**Total Nonfarm Private Payroll Employment**, Monthly, Seasonally Adjusted,
**Persons**, źródło Automatic Data Processing, Inc., release **194**.
To poziom zatrudnienia, nie gotowa procentowa dynamika. Nie jest PAYEMS,
BLS Private Payrolls, ofertami pracy ani tygodniowym Pulse.

Ewentualna przyszła, uprawniona integracja wymagałaby:

```text
MonthlyChange[t] = EmploymentLevelSA[t] − EmploymentLevelSA[t−1]
MonthlyChangeThousands[t] = MonthlyChange[t] / 1000
```

Bez dzielenia przez poprzedni poziom i bez procentów. Oba właściwe miesiące
muszą pochodzić z jawnej, zgodnej wersji. Previous oznaczałoby zmianę za
bezpośrednio poprzedni miesiąc z informacją o wersji; rewizja byłaby odrębną informacją.

Kontrolnie różnica dwóch sąsiednich poziomów pokazanych na stronie FRED jest
zgodna z przywołanym w zadaniu wrześniowym wynikiem **90 tys.**; komunikat ADP
potwierdza także wskazaną rewizję sierpnia do **36 tys.** Nie zapisano poziomów
do aplikacji, PostgreSQL ani fixture'ów. W kodzie nie ma tych wyników.

FRED opisuje coroczne przeważenie QCEW w styczniowym raporcie. Komunikat ADP
z 30.09.2026 wskazuje też włączenie danych QCEW ogłoszonych 28.08.2026.
Nie należy więc traktować ogólnej noty rocznej jako kompletnego kalendarza
wszystkich zmian wersji. Nowe dane klientów i benchmarki mogą zmieniać historię;
aktualna różnica poziomów FRED nie jest gwarantowanym historycznym first printem.
Nie zbudowano syntetycznej historii pierwszych publikacji.

## Bramka wykorzystania danych

Weryfikacja warunków: **28.10.2026**.
Stopki rzeczywiście obejrzanych serwisów NER i ADP Research kierują do
[ADP Terms and Conditions](https://www.adp.com/legal.aspx).
Nie znaleziono w przejrzanych odnośnikach osobnej, szerszej licencji NER;
nie wyklucza to istnienia odrębnych umów. Ogólne warunki zastrzegają treści
oraz wykorzystanie publiczne i komercyjne. Nie potwierdzono uprawnienia do wyników MacroLens.

| Zastosowanie | Ustalenie / decyzja |
| --- | --- |
| Prywatny lokalny odczyt | Dostępna strona nie potwierdza automatycznie licencji na wszystkie sposoby dalszego użycia. Nie udzielamy takiej gwarancji. |
| Trwała PostgreSQL | Nie ustalono wyraźnej podstawy dla stałego gromadzenia obserwacji ADP; nie dodano serii ani importera. |
| RAW dokumentów wynikowych | Nie potwierdzono prawa do archiwizacji zestawów wynikowych; nie zachowano ich treści. |
| Publiczne portfolio | Publiczne prezentowanie danych wymaga wyjaśnienia uprawnień/zgody. Nie deklarujemy gotowości demo. |
| Publiczne API / eksport | Brak potwierdzonej licencji na redystrybucję. Liczby nie są udostępniane. |
| Komercyjnie | Konieczne odrębne uzgodnienie warunków z właścicielem. Bez deklaracji uprawnienia. |

Warunki obejmują również odnośniki i znaki towarowe; publiczne wdrożenie
metadanych/linków także nie otrzymuje tutaj ogólnej gwarancji prawnej.
Nie użyto logo ani nie kontaktowano się z wydawcą.

FRED oznacza serię jako chronioną i wymaga uwzględnienia praw właściciela.
[Warunki FRED i API](https://fred.stlouisfed.org/legal/) stanowią odrębny dokument:
obejmują atrybucję i ograniczenia użycia, przechowywania, cache, archiwizacji
i redystrybucji. Dostęp przez FRED nie znosi praw ADP. Zgodność istniejącego
modelu PostgreSQL/RAW/cache pozostaje nierozstrzygnięta, tak jak w poprzednich
audytach. Nie przebudowano tego pipeline'u w tym etapie.

**Decyzja: wyłącznie kalendarz i metadane, bez integracji wyników.**
Nie pobierano szeregu obserwacji ADP, ZIP/CSV historii ani PDF-ów wynikowych.
Podczas czytania jawnych komunikatów przetwarzano HTML przejściowo jedynie
w celu wydobycia okresu, terminu i linku. Nie utrwalano liczb ani kopii tych stron.

## Tożsamość, wersje i statusy

Dla potwierdzonych miesięcy ID ma postać `adp:YYYY-MM:monthly`.
Nie zmienia się wraz z przesunięciem terminu. Wiersz z 02.12 ma trwałe ID
`adp:calendar:2026-12:monthly`: oznacza zapisany wpis kalendarza, **nie miesiąc
badania**. `reference_period=null`, `reference_period_status=unconfirmed`.
Późniejszy jednoznaczny dokument dla tej samej daty może potwierdzić okres
bez zmiany ID; następne aktualizacje dopasowują już ten jawny miesiąc.
Jeśli nie ma dowodu wiążącego przesunięty wpis bez okresu, potrzebny jest przegląd,
a nie zgadywanie tożsamości po sąsiednim miesiącu.

Historia zachowuje poprzedni termin, zegar, link i provenance. Powtórny import
jest idempotentny; historia konfiguracji i snapshotu jest deduplikowana.
Starszy dokument nie zastępuje nowszego dowodu. Przesunięcie daty bez nowego
zegara lub dokumentu unieważnia wcześniejsze przypisania tych pól.
Błąd HTTP/parsera i krótsza lista nie kasują ostatniego poprawnego harmonogramu.

ADP pozostaje `expects_numeric_result=true`, `series=[]`, `measures=[]`.
`result_integration_status=publisher_permission_required`, `result_status=restricted`.
Actual, Previous i Forecast są `null`; konsensus `not_integrated`.
Binding omija liczby FRED, PAYEMS i innych raportów. Upływ terminu ani
pojawienie się Pulse nie tworzą miesięcznego Actual. Dostępny dokument
nie jest utożsamiany z prawem importu jego wartości.

## Koordynator i rzeczywisty przebieg

Nowy adapter korzysta z istniejącego koordynatora, advisory lock, budżetu,
wolnego interwału (domyślnie 6 godzin), source_check_runs, atomowego snapshotu
i publikacji Overview. Nie dodano usługi ani intensywnego pollingu.
Normalna kontrola pobiera publiczny szkielet NER, listę Press Releases i
co najwyżej najnowszy miesięczny komunikat: **trzy żądania**, bez crawlera historii.
Zapowiedź następnego raportu jest parsowana tylko wtedy, gdy dokument
jednoznacznie podaje jego miesiąc i datę; godzina wymaga osobnego tekstu ET.

Szkielet JavaScript nie jest sukcesem odczytu harmonogramu.
`calendar_automation=bounded_announcements_only`, stan źródła **partial**,
`adp_full_schedule_not_automated`. Metadane rozróżniają wykryty najnowszy
dokument miesięczny, nieudany odczyt pełnego kalendarza i celowo niewdrożone
wyniki. Błąd jest przypisany do faktycznego URL-u, nie zawsze do listy.

Kontrolowany przebieg adaptera: **2026-10-28T22:21:33.023636+00:00**,
trzy odpowiedzi HTTP 200, sześć zachowanych wydarzeń, status **partial**.
`config/adp_calendar_evidence.json` zawiera ograniczony przegląd czterech
komunikatów i widocznego Calendar. Każde rzeczywiste pobranie ma prawdziwy
URL, timestamp i SHA-256 odpowiedzi, ale `response_body_retained=false`.
Nie ma fikcyjnego pliku RAW. Jednorazowy odczyt Calendar w Chrome ma metodę
`browser_dom_review`, zakres przeglądu i czas; **bez fikcyjnego hasha HTTP**.

Pierwsza szersza próba trafiła na stary/niejednoznaczny alias kwietniowego
komunikatu: odpowiedź nie potwierdziła miesięcznego dokumentu i parser ją
odrzucił. Próbę zarejestrowano jako nieudaną; nie publikowano jej częściowego
wyniku jako kompletnego harmonogramu. Ukończony przegląd ograniczono do
jednoznacznych komunikatów od lipca. Nie uzupełniano reszty z samych dat FRED.

Cache Overview przebudowano z zapisanych danych pod utrzymywaną wspólną blokadą:
`b23b6277-8f4f-4702-8a0d-8a22050b0a81`. Nie odświeżano pozostałych dostawców.
Weryfikacja PostgreSQL była read-only: brak serii `ADP%`; ostatni `ingested_at`
obserwacji **28.10, 15:48:57.578571 UTC**, przed rozpoczęciem tego zadania.
Nie wykonywano ingestion obserwacji, zmian schematu, resetu ani ALFRED backfillu.

## UI i walidacja

Jeden wiersz miesięcznego NER, kategoria labor, wspólne redakcyjne ★★★.
Potwierdzony miesiąc przy nazwie, oficjalny link i jawne ograniczenie
w szczegółach EN/PL. Gdy link prowadzi do ogólnej listy, etykieta to
„Raporty wydawcy”; dla własnego potwierdzonego dokumentu „Dane u wydawcy”.
Brak dokumentu nie oznacza automatycznie nieodbytej publikacji.
Nie dodano CSS, kolumn, pustych wierszy składowych ani nowych kolorów.
Odliczanie wyklucza niepotwierdzone zegary. Overview zachowuje sześć kart
i wybór najwyżej czterech wydarzeń; bieżące okno nie obejmuje jeszcze 04.11,
a prezentację ADP w przyszłym oknie sprawdzają testy EN/PL.

- Pełny backend: **883 passed**, w tym **28 nowych przypadków ADP**.
- Pełny frontend: **556 passed**, 22 pliki, z blokadą sieci zgodną z CI.
- Production build: poprawny; jawne ostrzeżenie Vite o głównym pakiecie
  **520,25 kB**, powyżej 500 kB. Nie zmieniano progu.
- Testy są offline: syntetyczne dokumenty bez rzeczywistych wyników płacowych.
  Obejmują miesiące, wyjątkowy 30.09, daty i zegary, IANA/DST, Pulse,
  identyfikatory, zmianę terminu, powtórny import, historię, starszy dokument,
  błędy, nieznane okresy/godziny, brak 2027, kontrakt FastAPI, licencyjną
  blokadę liczb, brak kopiowania PAYEMS i zachowanie katalogu.
- Starsze testy źródeł izolują nowy adapter, analogicznie do Michigan/ISM.
  Nie osłabiono globalnych blokad sieci i DB. Wszystkie wcześniejsze testy zachowano.
- Nowe testy EN/PL wykryły znak `?` zamiast apostrofu UTF-8 w opisie Previous;
  poprawiono tekst. Przegląd wykrył także możliwość powielenia historii między
  konfiguracją i snapshotem oraz ID po potwierdzeniu okresu; dodane testy
  potwierdzają poprawki. Nie pomijano testów ani nie zmieniano timeoutów.
- Znany sporadyczny błąd nawigacji MCI nie wystąpił w tych pełnych przebiegach.
  Nie zmieniano MCI, jego testów ani metodologii PIT.
- Rzeczywiste API: daty 01.07, 02.09, 30.09, 04.11, 02.12 oraz brak ADP
  06.01.2027. Poprawne miesiące i statusy; wszystkie liczby ADP puste.
- Chrome bez fixture'ów API: **28 scenariuszy**, EN/PL, **1366 i 390 px**,
  pięć dat, brak 2027 i Overview. **64 odpowiedzi API HTTP 200**, brak wyjątków
  JavaScript i poziomego overflow. Sprawdzono gwiazdki/filtr, countdown
  04.11 i jego brak przy nieznanym zegarze, źródła, licencję, szczegóły,
  Escape/powrót fokusu oraz limit kart/wydarzeń. Obejrzano zrzuty desktop/mobile.
- Kontrola UI odbywała się pod wspólną blokadą: żądania prawdziwej aplikacji
  nie uruchamiały pozostałych importerów. Nie podstawiano odpowiedzi API.
- `git diff --check`: poprawny. Bez stagingu, commita i pusha; nie uruchamiano CI na GitHubie.

## Ograniczenia i końcowy Git

Nie ma pełnej automatycznej synchronizacji kalendarza JavaScript, potwierdzonego
2027 ani kompletnej historii metadanych 2026. Dla 02.12 brakuje dowodu okresu
i zegara; dla 01.07 zegara. Nie ma integracji wyników, konsensusu, licencji
na ich publiczną redystrybucję ani historii first printów. Dotychczasowe
ograniczenia BLS 403, current-vintage, intraday oraz warunków FRED pozostają.
Nie zmieniono wyników i metodologii Employment, Michigan, ISM, Fed, Retail lub PPI.

`main` / `c4926aac9281b928e2c74a6ae56dbfa900c7449c`.
**26 modified, 5 untracked**, nic staged.

Zastane i zachowane byte-identycznie:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`

Zmiany tego etapu:

- `app/analytics/adp_calendar.py` — nowy
- `app/analytics/calendar_agenda.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/release_calendar.py`
- `app/analytics/source_checks.py`
- `app/ingestion/sync_adp_calendar.py` — nowy
- `config/adp_calendar_evidence.json` — nowy
- `frontend/src/api/macrolens.ts`
- `frontend/src/brief/EconomyBrief.tsx`
- `frontend/src/brief/EconomyBrief.test.tsx`
- `frontend/src/brief/briefModel.ts`
- `frontend/src/brief/upcomingEvents.ts`
- `frontend/src/brief/upcomingEvents.test.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/calendarAgenda.ts`
- `frontend/src/i18n/pl.json`
- `tests/test_adp_calendar.py` — nowy
- `tests/test_bls_schedule.py`
- `tests/test_calendar_schedule_continuity.py`
- `tests/test_ism_calendar.py`
- `tests/test_michigan_calendar.py`
- `tests/test_overview_refresh.py`
- `tests/test_release_calendar.py`
- `tests/test_source_checks.py`
- ten raport — nowy

Lokalne metadane diagnostyczne, cache, logi, profil Chrome i zrzuty pozostają
ignorowane. Nie zapisano sekretów, chronionych zestawów wynikowych ani kopii
treści raportów. Nie dodano NER Pulse ani innych publikacji.

Ręcznie: Calendar → Date range → 30.09.2026, 04.11.2026, 02.12.2026.
Sprawdź wrzesień przy wrześniowej publikacji, październik i 14:15 przy 04.11,
nieznany okres/zegar przy 02.12 oraz szczegóły wyjaśniające brak liczb.
Włącz ★★★ — ADP pozostaje widoczny. Przełącz EN/PL i sprawdź Escape/fokus.

## Kontrola zamknięcia etapu — 28.10.2026

Ponownie przejrzano pełny diff i wszystkie 27 plików etapu, w tym konfigurację
dowodów, adapter, projekcję, koordynator, API, interfejs i testy. Cztery wcześniejsze
pliki użytkownika zachowały identyczne SHA-256 i pozostają poza commitem.
Nie znaleziono innych niezwiązanych zmian, sekretów ani lokalnych artefaktów
w stagingu. Zapisane metadane HTTP i ręczny przegląd DOM pozostają odrębne;
nie dopisano fikcyjnych RAW ani potwierdzeń okresu lub zegara.

Kontrola offline potwierdziła sześć dat i ich jawne okresy/godziny oraz konwersję
IANA. Sprawdzono także grudniowy wpis bez okresu: późniejsze potwierdzenie
miesiąca dla tej samej daty zachowuje `adp:calendar:2026-12:monthly`, jeden
wiersz i historię pierwotnego `unconfirmed`. Powtórny merge nie powiela historii;
kolejne jawne przesunięcie terminu po potwierdzeniu miesiąca zachowuje to samo ID.
Nie zmieniano implementacji, nie pobierano danych i nie wykonywano zapisów bazy.

Pełna ponowna walidacja working tree: backend **883 passed**, frontend
**556 passed**, production build poprawny, pakiet główny **520,25 kB**.
Na osobnej kopii dokładnej zawartości stagingu, z pozostałymi zależnościami
z HEAD i bez czterech wcześniejszych zmian użytkownika: **556 passed** oraz
poprawny build, pakiet **522,29 kB**. Kopia zachowuje szczegóły sprawdzenia
Overview z HEAD. Normalizację LF/CRLF skonfigurowaną w Git uwzględniono przy
porównaniu kopii z indeksem. Ostrzeżenie Vite ponad 500 kB pozostaje jawne,
bez zmiany progu. W żadnym pełnym przebiegu nie wystąpił sporadyczny błąd MCI;
nie zmieniano jego kodu, testów, timeoutów ani nie pomijano testów.

`git diff --check` i kontrola staged whitespace przeszły. Zakres commita to
27 plików etapu wymienionych wyżej. Ograniczenia automatyzacji ADP, grudniowego
okresu/zegara, harmonogramu 2027, integracji wyników i praw wykorzystania danych
pozostają aktualne. Wynik nowego GitHub Actions po pushu wymaga osobnego
potwierdzenia; lokalne wyniki nie są deklaracją sukcesu zdalnego workflow.
