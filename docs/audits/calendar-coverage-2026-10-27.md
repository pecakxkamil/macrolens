# MacroLens — audyt pokrycia kalendarza ekonomicznego USA

**Data weryfikacji: 27.10.2026.** Odczyt lokalnej bazy i API: ok. 18:15–18:25 UTC / 19:15–19:25 Europe/Warsaw. Weryfikacja źródeł internetowych: 27.10.2026. To audyt i plan, bez wdrożenia.

**Wniosek:** MacroLens ma większość podstawowych grup oficjalnych danych USA oraz oba ISM, ale jeszcze nie zapewnia samodzielnego przygotowania do każdej sesji na S&P 500/Nasdaq. Najpilniejsze są osobne wydarzenia Fed oraz ciągłość już istniejących harmonogramów. Brakuje też badań nastrojów, ADP i S&P Global flash PMI. Nie należy zastępować tych luk większą liczbą rutynowych aktualizacji rentowności.

## Zakres, metoda i stan projektu

- Gałąź `main`, HEAD `be0800d` — `Add offline GitHub Actions CI for backend and frontend`; zgodna z lokalnym `origin/main`. Poprzednie commity: `8e8a490` (ISM), `7cbe626` (kalendarz/Overview), `51edb5c` (czytelność). Nie zakładano czystego working tree.
- Zastane zmiany: `README.md`, `frontend/src/brief/SourceCheckStatus.tsx`, `frontend/src/brief/SourceCheckStatus.test.tsx`, `frontend/src/styles.css` — usunięcie szczegółów sprawdzenia z Overview. Zachowano je bez modyfikacji w tym audycie.
- Historia porównawcza: **01.09–26.10.2026**, a publikacje z 27.10 opisano osobno. Przyszły horyzont: **27.10.2026–25.01.2027**, czyli do daty oddalonej o 90 dni. Data w tabeli „najbliższa” oznacza najwcześniejszą potwierdzoną datę w tym przedziale; publikacje już zakończone 27.10 są jawnie oznaczone.
- Sprawdzono wszystkie grupy i daty w PostgreSQL, cały katalog, mapowania oraz zapisane harmonogramy/dowody, nie tylko tydzień w UI. `connection.read_only = True`, a `SHOW transaction_read_only` zwróciło `on`. Zapytania: wyłącznie `SELECT`/`SHOW`; transakcje zakończono rollbackiem.
- Rzeczywisty `GET /api/v1/calendar?start_date=2026-09-01&end_date=2027-01-25&include_readings=true` zwrócił HTTP 200. Niezależna projekcja przez istniejące funkcje `list_calendar_events` i `load_results` w transakcji read-only potwierdziła liczby. Nie wywoływano POST odświeżania ani nie otwierano UI wyzwalającego taki POST.
- Publikacja danych API: `7e9bf3ba-851b-4aed-8a09-d4a1cb6e1eee`. Stan koordynatora przy odczycie: `partial`, zakończony 18:12:04 UTC. To zastany wynik wcześniejszej pracy aplikacji, nie odświeżenie wykonane przez audyt.
- Nie zmieniono kodu, konfiguracji, ważności, bazy, RAW ani cache. Nie uruchomiono ingestion, backfillu, pełnych testów ani buildu. Utworzono tylko ten dokument. Nie wykonano commita/pusha.

### Przejrzane ścieżki projektu

[Katalog](../../config/series.yaml), [zapytania kalendarza](../../app/analytics/release_calendar.py), [mapowania odczytów](../../app/analytics/calendar_readings.py), [projekcja API](../../app/analytics/calendar_agenda.py), [dowody okresów](../../app/analytics/calendar_evidence.py), [godziny](../../app/analytics/release_times.py), [koordynator](../../app/analytics/overview_refresh.py), [adapter BLS](../../app/ingestion/bls_schedule.py), [harmonogramy wydawców](../../app/ingestion/sync_calendar_periods.py), [FOMC](../../app/ingestion/sync_fomc_calendar.py), [ISM discovery](../../app/ingestion/discover_ism.py), [importer ISM](../../app/ingestion/import_ism.py), [harmonogram ISM](../../app/ingestion/sync_ism_calendar.py), [odczyty ISM](../../app/analytics/ism_calendar.py), [ważność/Overview](../../frontend/src/brief/upcomingEvents.ts), [UI kalendarza](../../frontend/src/calendar/CalendarPage.tsx).

Przejrzano istniejące testy `test_calendar_*`, `test_bls_schedule.py`, `test_ism*.py`, `test_fomc_calendar.py`, `test_release_calendar.py`, `test_source_checks.py`, `test_overview_refresh.py` oraz frontendowe testy kalendarza i `upcomingEvents`. Pokrywają m.in. dowody okresów, etapy rewizji, DST, brak nowego dokumentu, duplikaty i zakresy kontroli. Ich obecność nie jest dowodem kompletności kalendarza zewnętrznego; w zadaniu dokumentacyjnym nie uruchamiano ich ponownie.

## A. Rzeczywiste pokrycie

### Grupy, wydarzenia i odczyty to różne wielkości

| Wielkość | Wynik | Znaczenie |
| --- | ---: | --- |
| Grupy w `economic_releases` | 18 | Zawierają techniczną grupę FRED `FOMC Press Release` |
| Wiersze dat w `release_dates`, cała baza | 804 | Wszystkie zapisane daty, również rutynowe aktualizacje; nie liczba raportów makro |
| Grupy faktycznie projektowane do kalendarza | **20** | 17 grup FRED + oficjalna decyzja FOMC + 2 grupy ISM; techniczny FRED FOMC jest wykluczony |
| Grupy z zaimplementowanym powiązaniem wyniku i co najmniej jednym potwierdzonym okresem | **18** | Dwie pozostałe to H.15 i PMMS: mają terminy/serie, lecz odczyty w kalendarzu nie są powiązane z okresem |
| Wydarzenia API, 01.09.2026–25.01.2027 | **208** | W tym 83 rutynowe H.15; nie należy na tej podstawie wyliczać „procentu rynku” |
| Wiersze miar API w tym przedziale | **525** | Jedno wydarzenie może mieć wiele miar |
| Wiersze z ustalonym `reference_period` | **163** | Nie oznacza to 163 opublikowanych wyników; obejmuje również przyszłe okresy |
| Grupy z kompletem pól dla wszystkich pokazanych publikacji historycznych 01.09–26.10 | **10** | Data, godzina, okres, Actual i Previous; kompletność pól nie gwarantuje historycznego first printu |
| Pozostałe grupy w historycznej próbie | **9 częściowych + 1 bez wystąpienia** | ECI nie miało publikacji w tym przedziale; pozostałych dziewięć ma konkretne luki wymienione poniżej |
| Grupy z potwierdzonym pełnym pokryciem jednocześnie całej historii i przyszłych 90 dni | **Nie potwierdzono dla żadnej** | Nie oznacza to, że każda grupa ma brakującą przyszłą datę. Dla części brakuje dowodu kompletności harmonogramu; niektóre styczniowe publikacje wypadają już poza oknem |

Pomocniczy, węższy wynik: **10 grup** miało komplet daty/godziny/okresu/Actual/Previous dla wszystkich swoich pokazanych publikacji **01.09–26.10**: Employment Situation, CPI, PPI, JOLTS, Claims, GDP, Income and Outlays, CFNAI, NFCI i New Home Sales. Dla ECI nie było w tym historycznym przedziale żadnej publikacji — to nie luka miesięczna, ponieważ raport jest kwartalny. Nie kwalifikowano go jednak jako historycznie zweryfikowanego. Ten wynik nie potwierdza stycznia, pełnej automatyzacji ani first printów.

### Techniczna inwentaryzacja wszystkich istniejących grup

`DB` = liczba wszystkich zapisanych dat danej grupy; `H` = kompletne wydarzenia / wszystkie wydarzenia API 01.09–26.10, przy wąskim kryterium opisanym wyżej. `F` = liczba wydarzeń API 27.10–25.01, również tych zakończonych 27.10. Zasięg FRED w bazie i zasięg projekcji z dodatkowych plików nie są tożsame.

| Grupa / ID | DB: daty, min–max | H | F / ostatnia data API | Odczyty i najważniejsza luka |
| --- | --- | --- | --- | --- |
| Employment Situation / 50 | 14; 20.11.2025–04.12.2026 | 2/2 | 2 / 04.12 | PAYEMS, UNRATE, earnings MoM; CIVPART/UNEMPLOY są w mapie serii, ale nie w `SPECS` odczytów raportu. Grudniowy termin w bazie nie ma lokalnego dowodu okresu/godziny |
| CPI / 10 | 14; 24.10.2025–10.12.2026 | 2/2 | 2 / 10.12 | Headline/core MoM i YoY; lokalne dowody okresów kończą się na 10.11 |
| PPI / 46 | 4; 10.09–15.12.2026 | 2/2 | 2 / 15.12 | Tylko PPIFIS MoM; brak core i YoY |
| ECI / 11 | 5; 10.12.2025–30.10.2026 | brak publikacji | 1 / 30.10 | ECIALLCIV QoQ; okres Q3 i poprzedni Q2 potwierdzone; brak wynikowej próby z IX–X |
| JOLTS / 192 | 13; 09.12.2025–01.12.2026 | 2/2 | 2 / 01.12 | JTSJOL; brak quits/hires/layoffs jako odczytów |
| Claims / 180 | 59; 20.11.2025–31.12.2026 | 8/8 | 10 / 31.12 | ICSA i CCSA, odrębne tygodnie; reguła DOL obejmuje 2027, ale projekcja nie generuje brakujących styczniowych dat |
| Retail Sales / 9 | 16; 25.11.2025–16.12.2026 | 1/3 | 3 / 15.01.2027 | RSAFS MoM; dwie wrześniowe daty bez okresu/godziny. Styczeń dodany z oficjalnego overlay; brak ex autos/control |
| GDP / 53 | 14; 23.12.2025–23.12.2026 | 1/1 | 3 / 23.12 | GDPC1 QoQ annualized; późniejsze szacunki porównują ten sam kwartał; brak deflatora |
| Personal Income and Outlays / 54 | 15; 05.12.2025–23.12.2026 | 1/1 | 3 / 23.12 | 6 miar: headline/core PCE MoM, core YoY, real income, real spending, saving rate |
| M3 / 95 | 30; 18.11.2025–23.12.2026 | 2/3 | 5 / 23.12 | DGORDER MoM; advance/full rozróżnione. 02.09 bez okresu i etapu; styczniowy full 07.01 jest w dowodach, ale nie w API |
| New Residential Construction / 27 | 23; 09.01–23.12.2026 | 2/3 | 5 / 23.12 | HOUST/PERMIT; 24.09 bez okresu; potwierdzony 20.01.2027 jest w dowodach, ale nie w API |
| New Home Sales / 97 | 12; 13.01–23.12.2026 | 1/1 | 3 / 23.12 | HSN1F; dzisiejsze dane dostępne; następna styczniowa publikacja 27.01 jest już poza oknem 90 dni |
| CFNAI / 219 | 13; 22.12.2025–21.12.2026 | 2/2 | 2 / 21.12 | Poziom indeksu; brak ciągłości styczniowego harmonogramu |
| NFCI / 221 | 64; 16.10.2025–30.12.2026 | 8/8 | 10 / 30.12 | Poziom indeksu; odrębne tygodnie i świąteczne przesunięcia |
| PMMS / 190 | 65; 09.10.2025–31.12.2026 | 0/8 | 10 / 31.12 | MORTGAGE30US jest w Overview/Explorerze; w kalendarzu brak potwierdzonego okresu/godziny i Actual/Previous |
| H.15 / 18 | 306; 09.10.2025–31.12.2026 | 0/38 | 45 / 31.12 | Cztery miary DFF/DGS2/DGS10/DFII10 mają mapowanie techniczne, ale brak referencji i godzin; domyślne filtry je ukrywają |
| FRED FOMC Press Release / 101 | 122; 01.09–31.12.2026 | wykluczony | wykluczony | Dzienne aktualizacje DFEDTARL/U nie są decyzjami; prawidłowo wyłączone na rzecz oficjalnej grupy poniżej |
| Oficjalna decyzja FOMC | poza `release_dates`; 16 decyzji w 2026–2027 | 0/1 | 2 / 09.12 | Wrześniowy wynik jest, lecz brak historycznej godziny. W przyszłości 28.10 i 09.12 mają 14:00 NY; daty 2027 są zapisane bez godzin |
| ISM Manufacturing | pliki harmonogramu: 12 dat 2026 | 1/2 | 2 / 01.12 | Własny dokument tylko za IX, wydany 01.10; VIII nie wolno odtwarzać jako first printu z tabeli za IX |
| ISM Services | pliki harmonogramu: 12 dat 2026 | 1/2 | 2 / 03.12 | Własny dokument tylko za IX, wydany 05.10; analogiczna luka historyczna |

### Zasięg przyszłych harmonogramów a dostępność wyników

Najdalsze zapisane daty nie oznaczają ciągłego pokrycia:

- **FRED:** ostatnie zapisane daty to 31.12.2026. Ostatnia udana kontrola deklaruje zakres 26.09.2026–25.04.2027, ale to zakres zapytania, nie obietnica kompletnej listy terminów. W API ze stycznia są tylko **Retail Sales 15.01 i G.17 15.01** dzięki osobnemu overlay.
- **Oficjalne dowody wyprzedzają wydarzenia:** Retail/G.17 mają tabelaryczne daty/okresy do XII 2027, SOC do XII 2027, M3 do VI 2027. Overlay tworzący daty z dowodów dotyczy BLS oraz 9/13; sama obecność dowodu SOC/M3 nie tworzy wydarzenia bez daty FRED. To rzeczywista luka projekcji, nie brak oficjalnego harmonogramu.
- **BLS:** lokalne dowody Employment/CPI do XI 2026, PPI i JOLTS do XII, ECI do 30.10. Bezpośrednia próba pobrania strony Employment podczas audytu zwróciła **403**. Narzędzie odczytu WWW pokazało jawne oficjalne tabele, m.in. NFP **08.01.2027**, CPI **13.01**, PPI **14.01**. Ich brak w aplikacji nie oznacza odwołania publikacji. [BLS-EMP] [BLS-CPI] [BLS-PPI]
- **ISM:** potwierdzony kalendarz 2026, ostatnie publikacje 01/03.12. Jawne zapowiedzi kolejnych raportów potwierdzają 02/04.11. Próba HTTP rocznego harmonogramu dała **200 z CAPTCHA**, nie poprawny harmonogram. Nie znaleziono tabeli 2027 na odczytanej stronie; stycznia nie wolno zgadywać. [ISM]
- **FOMC:** daty do 08.12.2027; obecny plik potwierdza godziny tylko 28.10 i 09.12.2026. Pierwsza decyzja 2027 przypada 27.01, dwa dni poza badanym przyszłym oknem; nie jest dowodem luki wewnątrz tych 90 dni. Daty dalszych posiedzeń są według Fed warunkowe. [FED-CAL]
- **DOL:** reguła tygodni i wyjątki świąteczne do końca 2027 są zapisane; to nie to samo co lista rzeczywiście wyświetlanych wydarzeń. [DOL]

### Aktualne wyniki i wersje: przykłady kontrolne

- 27.10 revised permits: **1398 / 1403 tys. SAAR**, okres IX / VIII; Actual jest teraz dostępny. W dzisiejszym odczycie nie ma już `revised_permits_provider_pending`. Poprzedni audyt poprawnie opisywał wcześniejsze opóźnienie FRED — nie należy przepisywać go na stan bieżący. Wynik jest `current_vintage`; 1398 w historycznym wierszu initial 20.10 nie staje się pierwotnym 1400 tylko dlatego, że wiersz ma dawną datę.
- 27.10 DGORDER: **1,8442% / 0,1231%**, IX / VIII, `current_vintage`; New Home Sales: **676 / 680 tys. SAAR**, IX / VIII. Brak wyniku w dawnym zrzucie nie jest dowodem bieżącej luki mapowania.
- 02.11/04.11 ISM: Actual pusty, Previous **54,5 / 54,9 pkt**, okres X / IX. W październikowych publikacjach za IX własne dokumenty dają **54,5 / 54,6** oraz **54,9 / 55,4**. W bazie jest 10 wersji dokumentów, wszystkie z głównym miesiącem IX 2026; nie oznacza to 10 odrębnych publikacji. Zweryfikowano zgodność SHA-256 wszystkich 10 istniejących plików RAW.
- 29.10 Claims: ICSA dotyczy **24.10**, CCSA **17.10**; poprzednie wartości **194 000 / 1 728 000**. Future Actual pozostaje pusty, choć istnieje potwierdzona reguła okresu.
- `current_vintage` może uwzględniać późniejsze rewizje. `stored_date_vintage` daje dostępność na poziomie dnia, nie dowód wartości dokładnie o godzinie publikacji. Własny dokument ISM potwierdza wersję raportu, nie first print każdego miesiąca jego tabeli.

## Porównanie z pięcioma kalendarzami zewnętrznymi

Odczytano legalnie dostępne strony bez logowania, omijania CAPTCHA lub ukrytych endpointów. Kalendarze służyły do wykrywania braków, nie do ustalania praw do wyników ani zastępowania wydawcy. Nie kopiowano konsensusu ani treści raportów.

| Źródło, sprawdzone 27.10.2026 | Faktycznie dostępny zakres | Co wnosi / czego nie dowodzi |
| --- | --- | --- |
| [FinancialJuice][FJ] | Przekierowanie do `/home`; tekstowy szkielet, nagłówki/filtry, bez kompletnej tabeli wydarzeń | **Porównanie niepełne.** Nie da się stwierdzić, których konkretnych wydarzeń brak względem pełnego FinancialJuice ani potwierdzić 90 dni |
| [Investing][INV] | Publiczny wykaz z 27.10: m.in. CB Confidence, Case-Shiller, Richmond, durable/core capital goods oraz aukcja 5Y | Próba bieżącego dnia, nie pełne IX–X ani 90 dni. Nieruchomości i aukcje mają również osobne kalendarze; nie traktować ich jako publikacji makro |
| [Forex Factory IX][FF-IX], [X][FF-X], [XI][FF-XI], [XII][FF-XII], [I 2027][FF-I] | IX–X: historyczne listy USD; XI–XII: przyszłe wiersze z pustymi wynikami; I 2027: interfejs bez wierszy USD w odczycie | Najszersza sprawdzona próba; pokazuje osobno konferencję/SEP, Michigan prelim/final, S&P flash/final, CB, regionalne indeksy, aukcje. Styczeń nie jest kompletny |
| [Trading Economics USA][TE] | Odczyt od końca X do części XI: osobne typy, m.in. Michigan, S&P, handel, factory orders, aukcje | Przydatna kontrola nazw; ma odrębne consensus i modelowy forecast. Brak dowodu pełnej historii IX i całego przyszłego okna |
| [FXEmpire][FXE] | Interfejs kalendarza i filtry; bez odczytywalnej kompletnej tabeli | **Porównanie niepełne.** Nie przypisano temu źródłu żadnego potwierdzenia konkretnego terminu |

Odczyt tekstowy nie zachowuje wiarygodnie wszystkich ikon/kolorów high impact. Nie przepisano ich jako gwiazdek MacroLens. P1/P2/P3 poniżej to ocena redakcyjna użyteczności do przygotowania sesji, a nie gwarancja ruchu indeksu.

Próbki historyczne ujawniają realne różnice: FF z IX pokazuje projekcje, konferencję i Michigan prelim/final; FF z X konferencję 28.10 i protokół 07.10; MacroLens w tym samym okresie ma jedynie odrębną decyzję FOMC. Próby XI–XII nie zostały potraktowane jako oficjalne potwierdzenie ani ekstrapolowane na I 2027.

## B. Główna tabela porównawcza

**Legenda:** `CZ` — istnieje, lecz częściowo; `T` — termin/seria bez powiązanego okresu/wyniku; `N` — brak integracji; `M` — brak miary wewnątrz istniejącej publikacji. `O1` — konkretna data u wydawcy; `O2` — jawna reguła wydawcy; `E3` — wyłącznie kalendarz pomocniczy; `?` — niepotwierdzone. Wszystkie odsyłacze sprawdzono 27.10.2026; nieudane odczyty są opisane zamiast uznane za potwierdzenie.

Godzina `NY` oznacza `America/New_York`, `CT` — `America/Chicago`; PL jest konwersją IANA dla wskazanej daty. Wartości `—` oznaczają brak zweryfikowanego dowodu, nie zero. Zewnętrzna kolumna wskazuje potwierdzoną próbę/rodzinę, a nie pełną równoważność dostawców. `lokalne FRED` oznacza istniejący importer, nie gwarancję pierwszego wyniku o czasie publikacji.

| Publikacja | Kategoria | MacroLens obecnie | Zewnętrzne kalendarze | Oficjalne źródło | Najbliższa potwierdzona data | Okres i godzina | Dostępność wyniku | Automatyzacja | Priorytet | Luka / ograniczenie |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Decyzja FOMC | Fed | CZ, osobna oficjalna grupa | FF/TE | [FED-CAL], [FED-X] | O1 28.10 | Posiedzenie 27–28.10; 14:00 NY / 19:00 PL | Oficjalny target range; future pusty | Istnieje parser decyzji i harmonogramu | P1, istniejące ★★★ | Historia godzin i przyszłe potwierdzenia ograniczone; brakujące są wydarzenia poniżej, nie sama decyzja |
| Konferencja po FOMC | Fed | N | FF | [FED-X], [FED-XII] | O1 28.10; też 09.12 | 14:30 NY / 19:30 PL 28.10; 20:30 PL 09.12 | Wideo/transkrypt, bez Actual/Previous | Bezpłatny parser oficjalnego kalendarza, nowy typ bez liczb | **P1** | Nie jest tym samym co decyzja o 14:00 |
| FOMC Minutes | Fed | N | FF | [FED-XI], [FED-XII] | O1 18.11; następnie 30.12 | Protokół 27–28.10; 14:00 NY / 20:00 PL | Oficjalny dokument, bez odczytu liczbowego | Oficjalne miesięczne kalendarze + link dokumentu | **P1** | Nie wyliczać dat wyłącznie z reguły „trzy tygodnie” |
| SEP, w tym dot plot | Fed | N | FF jako projections | [FED-CAL], [FED-XII] | O1 posiedzenie 09.12* | Projekcje grudniowe; osobny dowód godziny SEP do potwierdzenia, nie wyprowadzać go z zegara decyzji | Oficjalne projection materials | Nowa identyfikacja SEP/załączników | **P1** | Gwiazdka przy posiedzeniu oznacza SEP; 28.10 bez SEP. Dot plot składnikiem, nie osobnym wydarzeniem |
| Zaplanowane wystąpienia przewodniczącego Fed | Fed | N | FF: wystąpienia Fed | [FED-X] | — dla przyszłego okresu; historia 15.10 potwierdzona | Osoba/rola, temat, miejsce i strefa konkretnego wydarzenia | Link, ewentualnie przemówienie/wideo | Częściowo; oficjalny kalendarz aktualizowany stopniowo | **P1 warunkowo** | Brak 90-dniowej gwarancji. Nie każda dyskusja jest wystąpieniem o polityce pieniężnej |
| Inne istotne wystąpienia FOMC | Fed | N | FF | [FED-X] i kalendarze banków regionalnych | —, wymagana zapowiedź konkretnej osoby | Bez uniwersalnej godziny/okresu | Nieliczbowe | Wiele oficjalnych źródeł, większy koszt utrzymania | P2 | Board calendar nie obejmuje wszystkich prezesów regionalnych |
| Beige Book | Fed | N | FF | [FED-XI] | O1 25.11 | 14:00 NY / 20:00 PL | Oficjalny raport jakościowy | Bezpłatna publikacja Fed, nowy typ nieliczbowy | P2 | Nie jest SEP ani protokołem |
| SLOOS | Fed/kredyt | N | Niewymagana równoważność | [FED-XI] | O1 02.11 | 14:00 NY / 20:00 PL; ankieta kredytowa | Raport i tabele Fed | Osobny parser/miary; bezpłatne źródło | P2 | Nieregularne dokładne daty, nie każdy kwartał ma identyczny dzień |
| Employment Situation: NFP, unemployment, earnings | Praca | CZ | FF | [BLS-EMP], [BLS-REPORT] | O1 06.11 | X 2026; 08:30 NY / 14:30 PL | Lokalne FRED; trzy miary, przyszły Actual pusty | Istnieje; BLS HTTP 403 | P1, istniejące ★★★ | Brak potwierdzonych lokalnie okresów grudniowego/styczniowego wydarzenia |
| JOLTS | Praca | CZ | FF/TE | [BLS-JOLTS] | O1 03.11 | IX; 10:00 NY / 16:00 PL | JTSJOL; local current-vintage | Istnieje, ograniczony harmonogram | P2 | Brak quits/hires/layoffs jako miar; nie nowy termin |
| Initial + Continuing Claims | Praca | CZ | FF | [DOL] | O2/O1 29.10 | ICSA tydz. 24.10, CCSA 17.10; 08:30 NY / 13:30 PL | Poprzednie 194 tys./1,728 mln; future Actual pusty | Istnieje, reguła tygodni + wyjątki | P1 w przygotowaniu, obecne ★★ | Daty kończą się 31.12 mimo reguły 2027 |
| ECI | Praca/inflacja | CZ | FF | [BLS-ECI] | O1 30.10 | Q3; 08:30 NY / 13:30 PL | ECIALLCIV QoQ; previous Q2 | Istnieje; dowód okresu ograniczony | P2 | Brak publikacji w IX nie jest luką; Q4 29.01 poza oknem |
| ADP National Employment Report | Praca | N; brak serii w katalogu | FF XI | [ADP-RELEASE], [ADP]; [ADP-FRED] pomocniczo | O1 04.11 | X 2026; 08:15 NY / 14:15 PL, jawna zapowiedź w komunikacie ADP z 30.09 | Bezpłatny raport miesięczny z rewizją poprzedniego miesiąca; nie ma wyniku lokalnie | Discovery/parser komunikatów ADP; nowy adapter, nie obecny ISM parser | **P1** | Następny raport potwierdzony, pełny 90-dniowy harmonogram i prawa redystrybucji niepotwierdzone; ADP nie zastępuje NFP |
| ADP weekly NER pulse | Praca | N | INV/FF | [ADP] | 27.10 na indeksowanej stronie; dalej 10.11 | Tygodniowa miara odmienna od monthly NER | Publiczne materiały, brak integracji | Osobny typ miary/okresu | P3 | Nie utożsamiać tygodniowego eventu widocznego 27.10 z monthly payrolls |
| CPI headline/core | Inflacja | CZ, 4 miary | FF | [BLS-CPI] | O1 10.11 | X; 08:30 NY / 14:30 PL | Headline/core MoM i YoY | Istnieje; BLS blokuje HTTP | P1, istniejące ★★★ | Daty grudniowe istnieją bez lokalnego dowodu okresu; styczeń nieobecny |
| PPI headline | Inflacja | CZ | FF | [BLS-PPI], [PPI-REPORT] | O1 13.11 | X; 08:30 NY / 14:30 PL | PPIFIS MoM, nie koszty produkcji | Istnieje | P2 | Brak core i YoY; obecny domyślny poziom medium |
| GDP: advance/second/third | Wzrost | CZ | FF | [BEA] | O1 29.10 | Q3 advance; 08:30 NY / 13:30 PL | GDPC1; previous zależny od etapu | Istnieje; dowody etapu | P1, istniejące ★★★ | Pełna historia wersji niekompletna; price index brak |
| Personal Income and Outlays / PCE | Konsumpcja/inflacja | CZ, 6 miar | FF | [BEA] | O1 29.10 | IX; 08:30 NY / 13:30 PL | PCEPI/PCEPILFE, real income/spending, saving | Istnieje | P1, istniejące ★★★ | Nominalne income/spending i headline PCE YoY nie są osobnymi miarami tej tabeli |
| Retail Sales | Konsumpcja | CZ | FF | [RETAIL] | O1 17.11 | X; 08:30 NY / 14:30 PL | RSAFS MoM | Istnieje, overlay do 2027 | P1 przygotowanie, obecne ★★ | Brak ex autos/control; dwie historyczne daty bez okresu |
| Industrial Production / Capacity | Wzrost | CZ | FF | [G17] | O1 17.11 | X; 09:15 NY / 15:15 PL | INDPRO MoM + TCU | Istnieje, overlay do 2027 | P2 | Historyczny TCU 18.09 bez dowodu konkretnego wyniku; nie brak serii |
| Durable Goods advance / full M3 | Wzrost | CZ | INV/FF/TE | [M3], [M3-RESULT] | O1 27.10 opublikowane; full 03.11 | IX; advance 08:30 NY / 13:30 PL, full 10:00 / 16:00 PL | DGORDER MoM; wynik z 27.10 już jest | Istnieje, etapy osobne | P2 | Brak core capital goods i pełnego total factory orders; styczeń nieprojektowany |
| ISM Manufacturing PMI | Wzrost | CZ, ★★★ | FF | [ISM] | O1 02.11 | X; 10:00 NY / 16:00 PL | Własny dokument; Actual —, Previous 54,5 pkt | Istniejące discovery/import; kalendarz blokowany | P1, już obecne | Brak własnego dokumentu VIII oraz potwierdzonej tabeli 2027 |
| ISM Services PMI | Wzrost | CZ, ★★★ | FF | [ISM] | O1 04.11 | X; 10:00 NY / 16:00 PL | Actual —, Previous 54,9 pkt | Jak wyżej | P1, już obecne | Nie mylić z S&P Global; nie dodawać ponownie |
| CFNAI | Wzrost | CZ | Nie stwierdzono braku względem próby | [CHICAGO] | O1 23.11 | X; 08:30 NY / 14:30 PL | Poziom indeksu | Istnieje | P3 | Zasięg do XII; CFNAI nie jest Chicago PMI |
| NFCI | Warunki finansowe | CZ | Nie stwierdzono braku względem próby | [CHICAGO] | O1 28.10 | Tydz. 23.10; 08:30 NY / 13:30 PL | Poziom indeksu, future pusty | Istnieje | P3 | Zasięg do XII; nie sygnał natychmiastowy |
| Housing Starts + initial Permits | Mieszkania | CZ | FF | [SOC] | O1 18.11 | X; 08:30 NY / 14:30 PL | HOUST i PERMIT SAAR | Istnieje | P2 | Brak wydarzenia 20.01.2027 mimo dowodu |
| Revised Permits | Mieszkania | CZ, odrębny etap | Brak wymogu osobnego wpisu dostawcy | [SOC] | O1 27.10 opublikowane; dalej 25.11 | IX; 08:00 NY / 13:00 PL | 1398 / 1403 tys. SAAR | Istnieje, dowód konkretnej rewizji | P2 | Nie „brak wyniku”: teraz już dostępny; Previous to VIII, nie initial IX |
| New Home Sales | Mieszkania | CZ | INV/FF | [SOC] | O1 27.10 opublikowane; dalej 25.11 | IX; 10:00 NY / 15:00 PL | 676 / 680 tys. SAAR | Istnieje | P2 | FRED nie gwarantuje natychmiastowego first printu |
| PMMS mortgage rates | Mieszkania | T; dane są w Overview | Niepełna próba | [PMMS], [PMMS-PDF] | O1 29.10 | Wydawca: tydz. 22–28.10; 12:00 NY / 17:00 PL | MORTGAGE30US istnieje, Calendar puste | Import obserwacji istnieje; brakuje dowodu/bindingu | P3 | Brak godziny w aplikacji; świąteczna zmiana na środę nie może być zgadywana |
| H.15 stopy/rentowności | Warunki finansowe | T; domyślnie ukryte | TE: odrębne market data | [H15] | W bazie 27.10, oficjalna dokładna godzina niepotwierdzona tutaj | Różne daty obserwacji wewnątrz zestawu | Serie w Overview/Explorerze, Calendar puste | Rutynowe FRED updates | P3 | Nie mylić z aukcją, decyzją Fed ani „nowym wynikiem spreadu” |
| Michigan Consumer Sentiment prelim/final | Nastroje | N | FF/TE | [UM-DATES], [UM], [UM-FAQ] | O1 06.11 / 20.11 | XI; daty pewne; 10:00 NY / 16:00 PL w kalendarzu wtórnym, brak osobnego potwierdzenia zegara w odczytanym PDF | Publiczne podsumowania; kompletne data-site po embargo | Nowy parser etapów i źródła godzin | **P1** | Prawa i timely dostęp odrębne; nie odtwarzać prelim z późniejszego final |
| Michigan inflation expectations 1Y / long-term | Nastroje/inflacja | M w przyszłej grupie Michigan | FF/TE | [UM-RESULT], [UM-FAQ] | Te same O1 06/20.11 | Ten sam miesiąc i etap; konkretna długość horyzontu | Publiczny raport zawiera miary; brak lokalnie | Wspólny dokument, bez nowej daty | **P1** | Nie mieszać średniej/mediany i 1Y z długim horyzontem |
| CB Consumer Confidence + Expectations | Nastroje | N | INV/FF | [CB] | O1 24.11; 27.10 opublikowane | XI; 10:00 NY / 16:00 PL | Headline i expectations w publicznym komunikacie | Parser komunikatu; szereg/eksport wymagają sprawdzenia praw | P2 | Expectations częścią raportu, nie drugim terminem; pełne historyczne dane komercyjne |
| S&P Global US flash Manufacturing/Services/Composite | Wzrost | N | FF XI | [SP-PMI] | — O1; E3 23.11 | XI; E3 09:45 NY / 15:45 PL | Publiczne news releases, szersze dane licencjonowane | Nowy discovery/parser; kalendarz HTTP 403 | **P1** | Nie przenosić reguły ISM. Termin E3 nie może dostać statusu potwierdzonego |
| S&P Global final Manufacturing/Services | Wzrost | N | FF/TE | [SP-PMI] | — O1; E3 02/04.11 | X; E3 09:45 NY / 15:45 PL | Jak wyżej | Nowe rozróżnienie flash/final | P2 | Prywatne źródło, inne niż ISM; pełnej automatyzacji nie potwierdzono |
| Chicago Business Barometer / Chicago PMI | Wzrost | N | FF IX; INV event | [CHI-PMI] | — O1; E3 30.10 | X; E3 09:45 NY / 14:45 PL | Publiczna informacja za IX; płatne/proprietary materiały MNI | Nowy parser tylko do dozwolonego publicznego materiału | P2 | Osobny produkt ISM Chicago/MNI; nie CFNAI i nie national ISM. Nie korzystać z kopii dokumentów subskrybenckich |
| Empire State Manufacturing | Wzrost | N | FF | [NYFED] | O1 16.11 | XI; 08:30 NY / 14:30 PL | Publiczne raporty i szeregi | Nowy adapter; bezpłatne źródło regionalnego Fed | P2 | Nie jest próbą całych USA |
| Philadelphia Fed MBOS | Wzrost | N | FF | [PHILLY] | O1 19.11 | XI; 08:30 NY / 14:30 PL | Publiczne dane także historyczne | Nowy adapter, istniejący model miar | P2 | Potrzebne zgodne wersje seasonal revisions |
| Richmond manufacturing/services | Wzrost | N | INV/FF | [RICHMOND] | O1 27.10 opublikowane; dalej 24.11 | X/XI; okno 10:00–10:10 NY, PL 15:00–15:10 dziś / 16:00–16:10 w XI | Publiczne raporty/dane | Nowy parser; zegar jako okno, nie sztuczna sekunda | P3 | Oficjalne źródło nie obiecuje jednej dokładnej minuty |
| Dallas manufacturing | Wzrost | N | FF / TE | [DALLAS] | O1 30.11 | XI; 09:30 CT / 16:30 PL | Publiczne tabele i historia | Nowy adapter | P3 | Wydawca rozpoczyna publikowanie o 09:30 CT, nie gwarantuje momentu wszystkich plików |
| Core PPI MoM/YoY + headline YoY | Inflacja | M w istniejącym PPI | FF | [PPI-REPORT], [BLS-PPI] | O1 13.11, wspólny termin | X; 08:30 NY / 14:30 PL | Dozwolona definicja core musi być wybrana | Rozszerzenie miar i potwierdzenie serii FRED | P1 | Ex food/energy oraz ex food/energy/trade to różne definicje; nie nowa publikacja |
| GDP Price Index / deflator | Inflacja/wzrost | M w GDP | FF | [GDP-PRICE], [BEA] | O1 29.10 | Q3 advance; 08:30 NY / 13:30 PL | Oficjalny BEA; GDP price index i deflator nie są dowolnie zamienne | Nowa miara, ta sama data/etap | P2 | Nie stosować wzoru YoY do opublikowanej dynamiki kwartalnej |
| Retail ex Autos / Control Group | Konsumpcja | M w Retail | FF | [RETAIL], [RETAIL-RESULT] | O1 17.11 | X; 08:30 NY / 14:30 PL | Publiczne tabele; brak serii lokalnie | Istniejący pipeline + dokładne definicje/komponenty | **P1 dla miar** | Nie nowy termin; control nie jest po prostu „ex autos” |
| Core Capital Goods Orders | Wzrost | M w M3 | INV | [M3-RESULT], [M3] | O1 27.10 opublikowane; full 03.11 | IX; etap advance/full | Publiczne Census nondefense ex aircraft | Rozszerzenie M3 | P2 | „Durable ex transportation” to inna miara; nie zamieniać |
| Trade Balance, goods and services | Handel | N | FF/TE | [BEA] | O1 04.11 | IX; 08:30 NY / 14:30 PL | BEA/Census, darmowe raporty i szeregi | Nowa grupa, istniejący FRED może obsłużyć wybrane szeregi | P2 | Odrębne od advance goods trade; netto eksport nie jest całym GDP |
| Import / Export Prices | Inflacja | N | FF | [BLS-XM] | O1 17.11 | X; 08:30 NY / 14:30 PL | Oficjalne BLS; darmowe serie | Rozszerzenie BLS groups/mapowania, blokada nadal istotna | P2 | Nowa grupa publikacji, nie część CPI/PPI |
| Nonfarm Productivity + Unit Labor Costs | Praca/inflacja | N | FF/TE: productivity/costs | [BLS-PROD], [PROD-RESULT] | O1 05.11; revised 08.12 | Q3 preliminary; 08:30 NY / 14:30 PL | Oficjalne kwartalne miary, historia | Nowa grupa; dwie miary i etapy | P2 | Dynamika annualizowana, poziomy i rewizje muszą pozostać rozróżnione |
| Existing Home Sales | Mieszkania | N | FF | [NAR-DATES] | O1 12.11 | X; 10:00 NY / 16:00 PL | Publiczny komunikat, historia/prawa ograniczone | Harmonogram łatwy; wynik warunkowy prawami | P2 | NAR nie jest Census; dostęp publiczny nie daje licencji eksportu |
| Pending Home Sales | Mieszkania | N | FF / TE: housing | [NAR-DATES], [NAR-PHS] | O1 18.11 | X wg rocznej tabeli; 10:00 NY / 16:00 PL | Publiczny komunikat; ograniczenia NAR | Nowa grupa; konieczne rozwiązanie sprzeczności okresu | P2 | Jedna sekcja strony PHS błędnie nazywa przyszły okres IX, inna X. Nie ufać bezwarunkowo jednemu zdaniu |
| NAHB Housing Market Index | Mieszkania | N | FF XI | [NAHB-DATES], [NAHB] | O1 17.11 | XI; 10:00 NY / 16:00 PL | Publiczny headline i tabele historyczne; prawa do sprawdzenia | Nowy adapter | P2/P3 | Nagłówek tabeli „2027” zawiera też XI–XII 2026; parser musi czytać rok z wiersza |
| S&P Cotality Case-Shiller HPI | Mieszkania | N | INV/FF | [CASE] | O1 27.10 opublikowane; kolejnej nie potwierdzono | VIII; publiczna strona potwierdza datę/okres, godzina tylko wtórna | Publiczne nagłówki; reszta licencjonowana | Nowy parser; wiele indeksów/SA/NSA | P2 | Aktualna nazwa Cotality, wcześniej CoreLogic; nie mieszać national i composite-20 |
| US Treasury 10Y / 30Y auctions | Kontekst rynkowy | N | FF/TE | [TREASURY], [AUCTIONS] | Oficjalnie **tentative** 10.11 / 12.11 | Tenor, CUSIP, announcement/auction/settlement; clock z konkretnego ogłoszenia | Ogłoszenia/wyniki publiczne; high yield, bid-to-cover | Możliwy osobny adapter Treasury XML; nie wykorzystywać H.15 jako wyniku aukcji | **P2, osobna warstwa** | Kalendarz tentative nie jest final announcement; nie udawać finalnego potwierdzenia |
| OPEX / futures expirations | Kontekst rynkowy | N | Nie klasyczny kalendarz makro | [CBOE], [CME] | Roczny kalendarz dostępny; konkretna data zależy od produktu | AM/PM settlement, ostatni handel i expiry to różne chwile | Brak „Actual” makro | Osobna koncepcja kalendarza kontraktów | P2 | Nie dodawać ogólnego „wygasanie wszystkiego”; nie każdy piątek ma takie samo znaczenie |
| Święta i skrócone sesje NYSE/Nasdaq | Kontekst sesji | N | INV: osobny kalendarz | [NYSE], [NASDAQ] | O1 26.11 zamknięte; 27.11 krótka sesja | 27.11 close 13:00 NY / 19:00 PL; też 24.12 krótka, 25.12 zamknięte | Status sesji, bez odczytu | Niska złożoność, oficjalne tabele 2026/2027 | **P1 dla organizacji sesji** | Osobny pasek kontekstu; święto bankowe nie musi oznaczać zamknięcia giełdy |
| Wyniki megacapów | Kontekst indeksów | N | Dostawcy mają osobne earnings calendars | [MSFT-IR], [AMZN-CALL]; [AAPL-IR], [NVDA-IR], [AMZN-IR] | O1 Microsoft 28.10; Amazon call 29.10 | MSFT FY27 Q1, godzina niepotwierdzona; AMZN Q3 call 17:00 NY / 22:00 PL | Oficjalne IR/SEC, bez zweryfikowanego konsensusu | Kuratorowana lista spółek + parsery; brak jednego darmowego pewnego API | **P1 kontekst, osobna warstwa** | Call Amazon nie dowodzi dokładnej godziny publikacji wyniku; dwa przykłady nie stanowią pełnego kalendarza na 90 dni |
| NFIB / Leading Economic Index | Dodatkowe makro | N | FF: NFIB; CB publiczne produkty | [NFIB], [CB] | — w tym audycie | Potrzebny jawny harmonogram i odrębny wskaźnik | Prywatne, częściowo publiczne publikacje | Warunkowo; wymagają sprawdzenia dostępu i praw | P3 | NFIB zwrócił 403; nie priorytet przed brakującym Fed/nastrojami |
| Construction Spending / Business Inventories | Dodatkowe makro | N; full factory orders to brak miary M3 | FF/TE | [CENSUS], [RETAIL] | Dla retail inventories O1 17.11 | Inventories IX; 10:00 NY / 16:00 PL; nie sales X o 08:30 | Publiczne Census | Osobny binding okresu; nie automatycznie wszystkie serie | P3 | Część raportów ukazuje się tego samego dnia, ale ma inny okres/godzinę |
| EIA Weekly Petroleum Status | Energia/kontekst | N | FF | [EIA] | — dokładnej przyszłej daty nie odczytano z tej strony | Tydzień i świąteczne wyjątki wymagają osobnych dowodów | Publiczne CSV/JSON/PDF | Możliwe bez płatnej usługi, nowy parser/wyjątki | P3 dla tych indeksów | Sytuacyjnie ważniejsze przy szoku energetycznym; nie dodawać API stocks jako równoznacznego EIA |
| Atlanta Fed GDPNow | Modelowy kontekst | N | INV/TE | [GDPNOW] | O1 28.10 | Model Q3; dokładna godzina niepotwierdzona | Publiczna estymacja modelowa | Możliwe, lecz osobny typ informacji | P3 | To nie oficjalny GDP ani konsensus; nigdy do kolumny Prognoza raportu GDP |

## C. Rzeczywiste braki i priorytety

### P1 — najpierw

1. **Osobna konferencja FOMC, Minutes i SEP** z oficjalnych harmonogramów, z linkami do publikacji. Nie dodawać ponownie samej decyzji; dot plot jako część SEP. To najlepiej potwierdzony i najłatwiejszy bezpłatny nowy zakres.
2. **Ciągłość istniejącego rdzenia na ≥90 dni:** przyjęcie zweryfikowanych oficjalnych terminów także wtedy, gdy data nie dotarła do FRED; przede wszystkim BLS w I 2027, HOUST 20.01 i M3 full 07.01. Wykrywanie luk ma precedencję przed dokładaniem mało istotnych aktualizacji H.15.
3. **Michigan prelim/final i oczekiwania inflacyjne:** osobne etapy i wersje. Kalendarz do 2027 jest jawny; wynik z dozwolonego publicznego źródła wymaga osobnej walidacji dostępu i godziny. Publiczne data-site ma czterotygodniowe embargo po final; nie jest źródłem gwarantowanych natychmiastowych wyników. [UM-FAQ]
4. **S&P Global flash PMI:** duża przydatność informacyjna, ale gotowość wdrożenia niższa przez 403/licencję. Do potwierdzenia dat i legalnej dostępności można zacząć od samego harmonogramu/linku; bez fałszywych Actual.
5. **ADP monthly** jako wysoki priorytet uzupełnienia pracy. Komunikat ADP potwierdza następny raport za X: 04.11 o 08:15 NY. Potrzebne są adapter, wersjonowanie i weryfikacja praw, a nie zgadywanie daty. Różni się od NFP i tygodniowego pulse; nie wymaga automatycznego nadania ★★★. [ADP-RELEASE]
6. **Miary wewnątrz rdzenia:** Retail control/ex autos i precyzyjnie zdefiniowany core PPI. Nie mnożą liczby grup publikacji.
7. **Kontekst sesji:** święta i skrócone sesje. Dla intraday operacyjnie krytyczne, ale jako osobna prezentacja. Aukcje 10Y/30Y i wyniki wybranych megacapów ocenić w tej samej oddzielnej koncepcji, a nie dopisywać hurtowo do tabeli makro.

### P2 — następny etap

Consumer Confidence/Expectations, Philly/Empire, Trade Balance, Import/Export Prices, Productivity/ULC, GDP price index, core capital goods, Existing/Pending Home Sales, NAHB, Case-Shiller, Chicago PMI, ważne przemówienia członków FOMC, Beige Book i SLOOS. S&P final może współdzielić parser flash, ale zachowuje osobne daty i etapy. NAHB ma dobry publiczny harmonogram; licencja/publiczny eksport pozostają bramką. Treasury 10Y/30Y i expiry to P2 w osobnej warstwie kontekstu; nie nowe raporty makro.

### P3 — później lub zależnie od kontekstu

Richmond/Dallas, NFIB/LEI, dodatkowe inventories/construction, EIA, ADP weekly pulse, GDPNow oraz kompletowanie H.15/PMMS jako odczytów w tabeli. Dane H.15/PMMS już istnieją w innych widokach; ich dopracowanie nie zastąpi brakujących wydarzeń P1. Nie są to rekomendacje handlowe ani prognozy reakcji cen.

### Gwiazdki i Overview

Obecne wspólne reguły dają ★★★ decyzji FOMC, Employment, CPI, PCE, GDP i obu ISM. Claims/Retail mają redakcyjne ★★, mimo że mogą być P1 w przygotowaniu. Inne grupy dziedziczą high/medium/low; domyślne filtry pokazują ≥2, „Tylko ★★★” ukrywa m.in. PPI/JOLTS/G.17 i Claims/Retail. H.15 low ukrywa filtr domyślny — to nie brak wydarzenia w bazie.

Propozycja do osobnego etapu: konferencja i SEP jako kluczowe wydarzenia Fed, Minutes również jawnie rozważone w tej grupie; ADP jako tracked ★★, Michigan/flash jako potencjalne kluczowe po walidacji. Dodatkowe miary PPI/Retail dziedziczą znaczenie istniejącej publikacji. P1 nie wymusza automatycznie ★★★. Nie zmieniono żadnej gwiazdki w tym audycie.

Overview pokazuje wybrane wydarzenia w oknie siedmiu dni i najwyżej cztery pozycje. ISM Services poza tym oknem lub brak piątego wydarzenia w podglądzie nie jest brakiem pełnego kalendarza. Rozszerzenia powinny zachować ten limit; kompletność ocenia się w Calendar, a nie po samym Overview.

## D. Brakujące miary bez nowych terminów

| Istniejący lub planowany raport | Miara | Obecny katalog / możliwość ponownego użycia | Warunek poprawnego wdrożenia |
| --- | --- | --- | --- |
| Employment Situation | Participation Rate | **CIVPART jest w katalogu i lokalnej historii**, ma mapę release 50; brak odczytu w `SPECS` | Dołączyć do wspólnego potwierdzonego miesiąca; nie osobne wydarzenie |
| Employment Situation | U-6, Average Weekly Hours | Brak odpowiednich serii w obecnym katalogu; oficjalne A-15 i B-2 | Wybrać SA/NSA, jednostkę i serię; ten sam czas/okres co raport. UNEMPLOY też istnieje lokalnie, ale brak go w odczytach kalendarza [BLS-REPORT] [BLS-U6] |
| PPI | Core MoM/YoY, headline YoY | PPIFIS istnieje tylko z MoM; innych wymaganych core serii nie skonfigurowano | Zdefiniować core oraz poprawny indeks bazowy; nie zmieniać istniejącego PPIFIS [PPI-REPORT] |
| GDP | GDP price index / deflator | Brak osobnej serii; GDPC1 nie pozwala ich wywnioskować | Zachować etap estimate i właściwą kwartalną dynamikę [GDP-PRICE] |
| Retail | Ex autos, control | Brak odpowiednich źródeł w katalogu, nie da się wyliczyć z RSAFS samego | Oficjalna kompozycja control, historyczne komponenty i wspólny miesiąc [RETAIL-RESULT] |
| M3 advance/full | Nondefense capital goods ex aircraft, durable ex transportation, total factory orders | Obecny DGORDER opisuje durable goods, nie komplet factory orders | Oddzielne miary i tożsamość advance/full. Full factory orders nie wymaga drugiego duplikatu tego samego full M3 [M3-RESULT] |
| Income and Outlays | Nominal income/spending, headline PCE YoY | PCEPI istnieje; nominalne szeregi nie są zarejestrowane | PCEPI YoY z dokładnego miesiąca; realnych PCEC96/DSPIC96 nie nazywać nominalnymi [BEA] |
| JOLTS | Hires, quits, layoffs | Tylko JTSJOL w katalogu | Oddzielne serie/liczniki, ten sam dowód miesiąca [BLS-JOLTS] |
| ISM Manufacturing/Services | Prices, Employment, New Orders/Business Activity | Publiczne dokumenty zawierają więcej tabel, ale importer waliduje tylko główny 12-miesięczny PMI | Rozszerzyć istniejący importer i wersje; nie nowa usługa ani nowy termin. Indeksy surowe, bez `%` [ISM] |
| Michigan | Inflation expectations 1Y/long-term, expectations/current conditions | Wspólna planowana publikacja, brak integracji teraz | Prelim/final osobno; nie utożsamiać długiego horyzontu z ustaloną długością bez definicji [UM-RESULT] |
| CB Confidence | Expectations / Present Situation | Wspólny publiczny komunikat; brak lokalnej integracji | Ten sam okres; zakres automatycznego przechowywania/eksportu dopiero po weryfikacji praw [CB] |
| SEP | Dot plot, mediana projekcji | Brak integracji; oficjalne projection materials | Składniki SEP, nie dodatkowa sztuczna data i nie consensus rynkowy [FED-CAL] |

## E. Realistyczny plan wdrożenia — bez implementacji

### Etap 1: wydarzenia Fed i kontrola zasięgu obecnego kalendarza

**Zakres:** conference, Minutes, SEP; bez nowych prognoz liczbowych. Równolegle jawny pomiar końca pokrycia każdej istniejącej grupy i wykrycie udokumentowanych dat nieobecnych w projekcji.

**Źródła:** oficjalne miesięczne strony Fed i FOMC; zapisane/zweryfikowane tabele BLS/Census/G.17. Wykorzystać istniejący koordynator, advisory lock, budżety i atomowe cache.

**Technicznie:** dodać jawne rodzaje wydarzeń nieliczbowych do API/TypeScript i stabilne identyfikatory; istniejące `event_id`, FOMC bez FRED ID oraz `expects_numeric_result` są punktem wyjścia, nie gotowym kompletnym modelem konferencji. Zachować relację do posiedzenia i dokumentu. Uogólnić dopuszczony overlay harmonogramów bez zgadywania okresów.

**Ryzyka:** duplikat decyzja/SEP, mylenie minutes z meeting day, brak godzin historycznych, stare daty przy zmianie planu, roczniki 2027 i 403.

**Akceptacja:** 28.10 decyzja 19:00 PL i konferencja 19:30; Minutes 18.11 20:00; SEP tylko przy grudniowym posiedzeniu; brak sztucznego dot-plot eventu; daty styczniowe NFP/CPI/PPI/HOUST/M3 z dowodami pojawiają się bez FRED-latest-pair inference. Testy zmiany czasu, braku materiału, modyfikacji terminu i braku numerycznego wyniku. Niedostępność źródła zachowuje poprzednie dowody i jawny status.

### Etap 2: domknięcie miar istniejących publikacji i dostępne dane urzędowe

**Zakres:** participation/hours/U-6, core PPI i brakujące miary Retail/M3/GDP; potem Trade Balance, Productivity/ULC i Import/Export Prices.

**Źródła:** BLS, BEA, Census, wybrane zweryfikowane serie FRED przez istniejący importer. Nie przyjmować, że wykrycie serii wystarcza do bindingu.

**Technicznie:** katalog/transformacje dopiero po weryfikacji metadanych; nowe specyfikacje miar, a tylko dla trzech nowych rodzin także grupy kalendarza i źródła okresów. Bez zmian MCI/PIT.

**Ryzyka:** core definition, SA/NSA, różne miesiące w tym samym dokumencie, annualized vs YoY, rewizje z tego samego miesiąca, bieżąca wartość w historycznej publikacji.

**Akceptacja:** każda nowa miara ma ścisłą definicję/źródło/okres; nie powstają duplikaty godzin; przyszły Actual pusty; poprzedni okres lub wcześniejszy estimate oznaczony jawnie; zero i brak danych rozróżnione; brak konsensusu pozostaje `—`.

### Etap 3: nastroje, ADP i PMI prywatne — najpierw bramki dostępu/praw

**Zakres:** Michigan prelim/final + inflation expectations, ADP monthly, CB, S&P flash/final. ISM dodatkowe składowe tylko przez istniejący pipeline. Chicago PMI później.

**Źródła:** publiczne materiały wydawców i jawne kalendarze. Dla Michigan dostępna tabela 2027; komunikat ADP z 30.09 potwierdza datę, godzinę i okres następnego raportu mimo dynamicznej strony głównej. Dla ADP zweryfikować automatyczne wykrywanie następnych komunikatów i szerszy harmonogram. S&P obecnie blokuje bezpośredni kalendarz.

**Technicznie:** nowe adaptery dokumentów; wspólny kontrakt provenance i wersjonowania można ponownie wykorzystać, ale nie wkładać obcych dokumentów do tabel ISM bez odrębnego projektu. Harmonogram może działać bez wyniku; wyniku nie pobierać z subskrybenckiej kopii ani „ukrytego API”.

**Ryzyka:** embargo Michigan, prawa NAR/TCB/S&P/ISM, publiczne nagłówki kontra pełne szeregi, current-vintage kontra prelim, niejednoznaczna godzina i błędne metadane indeksu wyszukiwarki.

**Akceptacja:** dowód konkretnego etapu i miesiąca; starszy dokument nie nadpisuje nowszego; brak nowego dokumentu po terminie nie wytwarza Actual; ponowny import nie duplikuje; prawa osobno dla użytku lokalnego, publicznego ekranu i eksportu. Jeśli brak legalnego, bezpłatnego źródła wyników — tylko potwierdzony termin i link z jawnym ograniczeniem.

### Etap 4: regionalne uzupełnienie i housing

**Zakres:** najpierw Empire/Philly, następnie wybrane NAR/NAHB i Case-Shiller, na końcu Richmond/Dallas. Nie dodawać wszystkich raportów tylko dlatego, że mają publiczną stronę.

**Źródła:** regionalne Fed i oficjalne kalendarze wydawców; NAR roczny harmonogram, NAHB tabelaryczny 2027. Publiczny dostęp NAR nie jest zgodą na magazynowanie/redystrybucję wyników — takie ograniczenie jest wprost na stronie PHS.

**Technicznie:** lekkie adaptery dat/raportów, ponowne użycie cache/limitów; wsparcie przedziału czasu publikacji Richmond zamiast fikcyjnej punktowej godziny.

**Ryzyka:** źródła regionalnych Fed mają własne warunki; różne SA/NSA i regiony; sprzeczność opisu okresu NAR; płatna dłuższa historia.

**Akceptacja:** brak wymieszania indeksów krajowych/regionalnych i Case-Shiller national/composite; poprawny okres; błędy źródeł nie stają się sukcesem; zakres praw zapisany przed eksportem.

### Etap 5: oddzielny kontekst sesji, dopiero po zatwierdzeniu koncepcji

**Zakres:** święta/early close, następnie wybrane Treasury 10Y/30Y, ograniczona lista megacapów i expiry konkretnych kontraktów.

**Źródła:** NYSE/Nasdaq, Treasury ogłoszenia/XML, Cboe/CME oraz oficjalne IR spółek. Bez płatnego earnings/consensus API.

**Technicznie:** osobna warstwa/kategoria informacyjna, a nie masowe dopisywanie wierszy do makro. Pola: venue, security/contract, CUSIP, company, timezone, final/tentative, release vs call vs settlement.

**Ryzyka:** stock-vs-bond holiday, AM/PM expiry, data tentative, zmiana godziny call, różnice między earnings date a faktyczną publikacją, utrzymanie wielu serwisów IR.

**Akceptacja:** poprawna sesja 26/27.11, 24/25.12, 01/18.01; brak kolumn Actual/Forecast dla zamknięcia giełdy; Treasury tentative odróżnione od final announcement; brak zmyślonego konsensusu i automatycznej daty spółki z cykliczności. Wspólny podgląd Overview nadal maksymalnie cztery wydarzenia.

## F. Granice kompletności i automatyzacji

1. **Brak 100% pokrycia rynku.** Nie obejmie nieplanowanych komentarzy, geopolityki, informacji o taryfach, nagłych komunikatów spółek ani zmiany rozkładu ryzyka. To kalendarz, nie serwis newsowy ani gwarancja przygotowania na każdą reakcję.
2. **Brak zweryfikowanego bezpłatnego konsensusu z prawami wykorzystania.** Wartość na ekranie Investing/TE nie jest automatycznie dostępnym API/licencją. TE rozróżnia consensus i swój modelowy forecast. Żadnego z nich nie zastępować Previous, GDPNow ani własną prognozą.
3. **Nie real-time.** Istniejące minimalne interwały: FRED 15 min, harmonogramy/ISM zwykle 6 h, BLS harmonogram per URL zwykle 24 h; job/cooldown i limity opóźniają wykrycie. FRED może otrzymać wynik po wydawcy. Dzisiejsze pozwolenia ilustrują różnicę między publikacją a dostępnością w pipeline.
4. **403/CAPTCHA nie dają pełnej automatyzacji.** BLS i ISM w tym audycie ponownie nie udostępniły normalnej odpowiedzi backendowi. S&P kalendarz także 403. Narzędzie WWW/indeksowana strona pomaga w audycie, ale nie jest dowodem, że aplikacja potrafi to automatycznie pobierać.
5. **Darmowy odczyt nie oznacza prawa do publicznego ekranu/eksportu.** Dla NAR wykryto jawne ograniczenie przechowywania i redystrybucji bez zgody; Michigan ma copyright i embargo danych; ISM zachowuje już zapisane ograniczenia lokalnego użycia. Dla ADP/TCB/S&P/MNI/NAHB i giełd nie potwierdzono w tym audycie pełnej licencji do publicznego datasetu. Nie deklarować gotowości publicznego demo z tymi wynikami. Materiały urzędowe i strony regionalnych Fed też wymagają sprawdzenia właściwych warunków/atrybucji, a FRED nie znosi praw pierwotnego wydawcy.
6. **Niepełne first printy.** Lokalny ALFRED nie jest pełną historią intraday. Aktualny komunikat z tabelą historii nie rekonstruuje dawnych prelim/first releases. Nie wdrażać backfillu pod pozorem uzupełnienia kalendarza.
7. **Ostrożność wobec samego oficjalnego HTML.** Wykryto rozbieżny opis przyszłego miesiąca na NAR PHS; indeks wyszukiwarki pokazał starszą, błędnie wydobytą wersję roczników Michigan, podczas gdy bieżący PDF potwierdza poprawne lata 2026/2027. Użyto bieżącego PDF, nie wyniku wyszukiwania jako rozstrzygającej tabeli. NAHB ma mieszany nagłówek 2027/wiersze 2026. Parser ma walidować tożsamość i konflikty, nie tylko „coś sparsować”.
8. **Porównanie pięciu agregatorów jest częściowe.** Szczególnie FinancialJuice/FXEmpire oraz styczeń FF nie pozwalają ogłosić kompletnej zgodności. Brak odczytywalnego wiersza nie dowodzi, że dostawca nie obsługuje publikacji.

## Źródła i poziom potwierdzenia — rejestr z 27.10.2026

Wszystkie źródła poniżej służą audytowi. Ich odczyt nie został zapisany jako nowy source-check w aplikacji. Strony dynamiczne i nieudane odczyty nie otrzymują statusu świeżej udanej kontroli harmonogramu.

| Źródło | Faktycznie potwierdzone / ograniczenie |
| --- | --- |
| [FED-CAL] | Oficjalne posiedzenia, SEP przy wybranych posiedzeniach, historia minutes/statement; przyszłe daty 2027 warunkowe |
| [FED-X], [FED-XI], [FED-XII] | Osobne wiersze minutes, meeting i conference, konkretne zegary; speech history; Beige/SLOOS. Nie rozciągać dzisiejszej listy wystąpień na 90 dni |
| [BLS-EMP], [BLS-CPI], [BLS-PPI], [BLS-JOLTS], [BLS-ECI], [BLS-XM], [BLS-PROD] | Jawne tabele dat/okresów 2026/2027 w narzędziu WWW; zwykły HTTP próbki Employment 403 |
| [BEA], [GDP-PRICE] | Daty i etapy GDP/PCE/trade, price index; bieżący harmonogram BEA nie stanowi kompletnego kalendarza 2027 |
| [SOC], [M3], [RETAIL], [G17] | Opublikowane przyszłe tabele/reguły, także część 2027; data wydawcy nie jest automatycznie datą już istniejącą w projekcji |
| [DOL], [CHICAGO], [PMMS], [PMMS-PDF] | Osobne tygodnie/wyjątki, regionalne release dates, PMMS zegar 12:00 i okres Thursday–Wednesday |
| [ISM] | Jawne 2026 i wyjątki; brak odczytanej tabeli 2027; bezpośredni HTTP 200 CAPTCHA. Istniejące własne dokumenty za IX są osobnymi dowodami wyniku |
| [ADP-RELEASE], [ADP], [ADP-FRED] | Komunikat ADP z 30.09 wprost zapowiada raport za X na 04.11 o 08:15 ET. Strona główna w bezpośrednim HTTP jest szkieletem; nie wyklucza to dostępności komunikatów. FRED tylko pomocniczo; nie dowodzi zegara |
| [UM-DATES], [UM-RESULT], [UM-FAQ] | Bieżący PDF s. 9: 06/20.11, 04/18.12, 08/22.01; raporty prelim/final; opóźnienie data-site. Dokładny publisher clock nadal do osobnego potwierdzenia |
| [CB] | Wspólny headline/Expectations, następny 24.11 10:00 ET; brak pełnej otwartej licencji szeregu |
| [SP-PMI], [CHI-PMI] | S&P kalendarz 403, brak potwierdzenia przyszłych US dat w tym odczycie; publiczny Chicago raport historyczny dostępny, nie zgoda na użycie subskrybenckiego materiału |
| [NYFED], [PHILLY], [RICHMOND], [DALLAS] | Konkretne daty i dostępne historie; Richmond okno czasowe, Dallas CT oraz brak gwarancji momentu wszystkich plików |
| [NAR-DATES], [NAR-PHS], [NAHB-DATES], [CASE] | Publiczne daty/okresy; licencje odrębne; NAR rozbieżność okresu, Case-Shiller potwierdzony as-of VIII / published 27.10 |
| [TREASURY], [AUCTIONS] | Ogłoszenia/publiczne formaty i **tentative**, m.in. 10Y 10.11, 30Y 12.11, styczeń 2027. Sam PDF nie potwierdza finalnego CUSIP/clock |
| [NYSE], [NASDAQ], [CBOE], [CME] | Oficjalne kalendarze sesji/kontraktów; nie zastępować ich jednym domyślnym „OPEX” |
| [MSFT-IR], [AMZN-CALL], [AAPL-IR], [NVDA-IR], [AMZN-IR] | Microsoft IR potwierdza FY27 Q1 28.10. Amazon komunikatem z 15.10 zapowiada Q3 call 29.10 o 14:00 PT / 17:00 ET. Call nie dowodzi zegara publikacji wyników. Pozostałe odczytane listy są dynamiczne/niepełne; brak pełnego 90-dniowego pokrycia |
| [EIA], [GDPNOW], [NFIB] | EIA ma publiczne formaty/archiwum, GDPNow wskazuje następny dzień aktualizacji; NFIB 403. Bez nowych integracji |

### Zapytania kontrolne do odtworzenia (wyłącznie read-only)

Przykład agregacji wszystkich dat, bez wielokrotnego liczenia przez join z seriami:

```sql
BEGIN READ ONLY;
SHOW transaction_read_only;
SELECT r.release_id, r.name, count(d.release_date) AS stored_dates,
       min(d.release_date) AS first_date, max(d.release_date) AS last_date
FROM economic_releases r
LEFT JOIN release_dates d USING (release_id)
GROUP BY r.release_id, r.name ORDER BY r.release_id;

SELECT r.release_id, r.name, array_agg(m.series_id ORDER BY m.series_id)
FROM economic_releases r
JOIN series_release_map m USING (release_id)
GROUP BY r.release_id, r.name ORDER BY r.release_id;

SELECT series_id, report_month, min(published_at), max(published_at), count(*)
FROM ism_documents GROUP BY series_id, report_month;
ROLLBACK;
```

Wykonane zapytania potwierdziły `transaction_read_only=on`. Sprawdzenie rzeczywistego API i niezależnej projekcji dało te same 208 wydarzeń. Nie uruchamiano testów, bo kodu nie zmieniono. Końcowa kontrola ma potwierdzić, że jedynym nowym plikiem zadania jest ten raport, a cztery wcześniejsze modyfikacje pozostają zachowane.

[FJ]: https://www.financialjuice.com/
[INV]: https://www.investing.com/economic-calendar/
[FF-IX]: https://www.forexfactory.com/calendar?month=sep.2026
[FF-X]: https://www.forexfactory.com/calendar?month=oct.2026
[FF-XI]: https://www.forexfactory.com/calendar?month=nov.2026
[FF-XII]: https://www.forexfactory.com/calendar?month=dec.2026
[FF-I]: https://www.forexfactory.com/calendar?month=jan.2027
[TE]: https://tradingeconomics.com/united-states/calendar
[FXE]: https://www.fxempire.com/tools/economic-calendar
[FED-CAL]: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
[FED-X]: https://www.federalreserve.gov/newsevents/2026-october.htm
[FED-XI]: https://www.federalreserve.gov/newsevents/2026-november.htm
[FED-XII]: https://www.federalreserve.gov/newsevents/2026-december.htm
[BLS-EMP]: https://www.bls.gov/schedule/news_release/empsit.htm
[BLS-CPI]: https://www.bls.gov/schedule/news_release/cpi.htm
[BLS-PPI]: https://www.bls.gov/schedule/news_release/ppi.htm
[BLS-JOLTS]: https://www.bls.gov/schedule/news_release/jolts.htm
[BLS-ECI]: https://www.bls.gov/schedule/news_release/eci.htm
[BLS-XM]: https://www.bls.gov/schedule/news_release/ximpim.htm
[BLS-PROD]: https://www.bls.gov/schedule/news_release/prod2.htm
[BLS-REPORT]: https://www.bls.gov/news.release/empsit.toc.htm
[BLS-U6]: https://www.bls.gov/news.release/empsit.t15.htm
[PPI-REPORT]: https://www.bls.gov/news.release/ppi.toc.htm
[PROD-RESULT]: https://www.bls.gov/news.release/prod2.toc.htm
[BEA]: https://www.bea.gov/news/schedule/full
[GDP-PRICE]: https://www.bea.gov/data/prices-inflation/gdp-price-index
[SOC]: https://www.census.gov/construction/soc/schedule.html
[M3]: https://www.census.gov/manufacturing/m3/release_schedule.html
[M3-RESULT]: https://www.census.gov/manufacturing/m3/adv/current/index.html
[RETAIL]: https://www.census.gov/retail/release_schedule.html
[RETAIL-RESULT]: https://www.census.gov/retail/index.html
[CENSUS]: https://www.census.gov/economic-indicators/
[G17]: https://www.federalreserve.gov/releases/g17/default.htm
[DOL]: https://oui.doleta.gov/unemploy/archive.asp
[CHICAGO]: https://www.chicagofed.org/research/data/data-release-calendar
[PMMS]: https://www.freddiemac.com/pmms
[PMMS-PDF]: https://www.freddiemac.com/pmms/docs/PMMS_Publication_Calendar.pdf
[H15]: https://www.federalreserve.gov/releases/h15/
[ISM]: https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/
[ADP]: https://adpemploymentreport.com/Default.aspx
[ADP-RELEASE]: https://mediacenter.adp.com/2026-09-30-ADP-National-Employment-Report-Private-Sector-Employment-Increased-by-90,000-Jobs-in-September
[ADP-FRED]: https://fred.stlouisfed.org/releases/calendar?rid=194&vs=2026-01-01&ve=2026-12-31
[UM-DATES]: https://data.sca.isr.umich.edu/fetchdoc.php?docid=75443
[UM]: https://data.sca.isr.umich.edu/
[UM-RESULT]: https://data.sca.isr.umich.edu/fetchdoc.php?docid=82114
[UM-FAQ]: https://data.sca.isr.umich.edu/faq.php
[CB]: https://www.conference-board.org/topics/consumer-confidence/
[SP-PMI]: https://pmi.spglobal.com/Public/Release/ReleaseDates?language=en&os=0
[CHI-PMI]: https://chicago.ismworld.org/news-publications/reports/research-survey/
[NYFED]: https://www.newyorkfed.org/survey/empire/empiresurvey_overview
[PHILLY]: https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/manufacturing-business-outlook-survey
[RICHMOND]: https://www.richmondfed.org/region_communities/regional_data_analysis/business_surveys/about
[DALLAS]: https://www.dallasfed.org/research/surveys/tmos
[NAR-DATES]: https://www.nar.realtor/press-releases/nar-releases-2026-statistical-news-release-schedule
[NAR-PHS]: https://www.nar.realtor/research-and-statistics/housing-statistics/pending-home-sales
[NAHB-DATES]: https://www.nahb.org/news-and-economics/housing-economics/indices/nahb-wells-fargo-housing-market-index-release-dates
[NAHB]: https://www.nahb.org/news-and-economics/housing-economics/indices/housing-market-index
[CASE]: https://www.spglobal.com/spdji/en/index-family/indicators/sp-cotality-case-shiller/
[TREASURY]: https://www.treasurydirect.gov/auctions/auction-announcements/
[AUCTIONS]: https://www.treasury.gov/resource-center/data-chart-center/quarterly-refunding/Documents/auctions.pdf
[NYSE]: https://www.nyse.com/markets/hours-calendars
[NASDAQ]: https://www.nasdaq.com/market-activity/stock-market-holiday-schedule
[CBOE]: https://cdn.cboe.com/resources/options/Cboe2026OPTIONSCalendar.pdf
[CME]: https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.calendar.html
[AAPL-IR]: https://investor.apple.com/investor-relations/default.aspx
[NVDA-IR]: https://investor.nvidia.com/events-and-presentations/events-and-presentations/default.aspx
[AMZN-IR]: https://ir.aboutamazon.com/events/default.aspx
[MSFT-IR]: https://www.microsoft.com/en-us/investor/default
[AMZN-CALL]: https://press.aboutamazon.com/2026/10/amazon-com-to-webcast-third-quarter-2026-financial-results-conference-call
[EIA]: https://www.eia.gov/petroleum/supply/weekly/
[GDPNOW]: https://www.atlantafed.org/research-and-data/data/gdpnow
[NFIB]: https://www.nfib.com/surveys/small-business-economic-trends/
