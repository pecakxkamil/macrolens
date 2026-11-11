# MacroLens — brak Actual po Employment Situation

06.11.2026, Europe/Warsaw, `C:\Projects\macrolens`.

**Diagnoza potwierdzona. Normalne Actual nadal są puste. Naprawa produkcyjnego
pobierania nie została wdrożona: wymaga zmiany backendu chronionego przez
aktywną autoryzację F1 V2. Nie wykonano APPLY, DDL ani importu BLS do normalnej
bazy. Poniższa propozycja nie jest wykonywalnym planem aktywacji.**

## Przyczyna

To dwa równoczesne problemy. Rzeczywiste odpowiedzi FRED dla wszystkich
sześciu serii kończyły się na wrześniu. Osobno sprawdzono wersję ALFRED
z jawnymi `realtime_start=realtime_end=2026-11-06`: również bez października.
Samo pominięcie bramki metadanych nie dostarczyłoby więc obecnie wyników.

Jednocześnie `refresh_fred()` w `app/analytics/overview_refresh.py` pobiera
obserwacje dopiero po zmianie last_updated, lokalnej sygnatury lub konfiguracji
transformacji. Nie uwzględnia potwierdzonej godziny publikacji i brakującego
okresu. Może zatem pomijać nowe obserwacje przy niezmienionych metadanych.
Tak zachowały się rzeczywiste kontrole po publikacji: sukces kontroli oznaczał
`metadata_unchanged`, a nie pobranie obserwacji.

SQL nie zawiera październikowych obserwacji tych sześciu serii. API prawidłowo
wiąże wydarzenie `release:50:2026-10-01:main` z październikiem i 14:30 PL,
zwracając `observation_missing`. Chrome pokazuje te same null. Nie znaleziono
danych ukrytych przez cache frontendu lub błędnie wybranego miesiąca.

Czytnik ma dodatkowe zabezpieczenia świeżości metadanych, a trzy poziomy
Employment także własną bramkę. Ewentualna poprawka samego pobierania musi
sprawdzić odczyt końcowy; nie należy usuwać tych zabezpieczeń globalnie.
Bezpośredni BLS wymaga własnego, udowodnionego provenance, bez udawania FRED.

## Kontrole każdej miary

Wszystkie godziny w tabeli: **Europe/Warsaw, 06.11.2026**. Kontrola FRED
obejmuje rzeczywiste HTTP metadanych i obserwacji, zapisane diagnostycznie
poza SQL. Ostatnia kontrola aplikacji poniżej dotyczy wyłącznie metadanych.

| Miara / FRED | Diagnostyczne pobranie obserwacji FRED | Ostatnia kontrola metadanych aplikacji | Najnowszy okres FRED/SQL | BLS / normalne API Actual |
|---|---|---|---|---|
| NFP / PAYEMS | 15:05:55 | 15:27:08 | wrzesień | +165 tys. / null |
| U-3 / UNRATE | 15:05:57 | 15:27:19 | wrzesień | 4,1% / null |
| AHE m/m / CES0500000003 | 15:05:57 | 15:26:52 | wrzesień | +0,4% / null |
| Participation / CIVPART | 15:05:58 | 15:26:54 | wrzesień | 61,9% / null |
| U-6 / U6RATE | 15:05:59 | 15:27:18 | wrzesień | 7,9% / null |
| Weekly hours / AWHAETP | 15:06:00 | 15:26:51 | wrzesień | 34,4 / null |

Późniejszy osobny odczyt ALFRED z jawną datą wersji także kończył się na
wrześniu; dokładne czasy każdej odpowiedzi są w
`data/raw/nfp-missing-actuals-2026-11-06/alfred-explicit-release-day.json`.

Ostatni zapis lokalnego snapshotu FRED ma `ingested_at` 26.10 10:25:50
dla PAYEMS, UNRATE, AHE, CIVPART oraz 28.10 15:48:57 dla U6RATE/AWHAETP.
To wartości SQL bez strefy, **czas zapisu, nie dowód ostatniego HTTP**.
Nie znaleziono dla tych serii wiersza kontroli z jawnym
`observation_fetch_status=fetched`. Nie oznacza to, że historycznie nigdy
nie pobierano obserwacji; starsze ścieżki nie zapisują tego pola.

## Odświeżanie i godzina 10:08

Najpierw wykorzystano istniejący POST
`/api/v1/economy/us/brief/refresh`. Pierwszy zwrócił istniejący cooldown.
Po jego upływie prawidłowy job wystartował o **15:11:11** i zakończył się
o **15:11:48**, status partial, nowa publikacja
`27861cb5-5aee-4592-a3d5-0a517f626ea8`. Wszystkie sześć kontroli ponownie
zwróciło metadata_unchanged; sześć Actual pozostało null. Nie skracano
cooldown, nie zmieniano source_versions ani metadanych ręcznie.

Następne wybudzenie sprawdzono na pozostawionej stronie, bez nawigacji lub
ręcznego POST: Chrome wysłał POST **15:26:48.250**, job ruszył
15:26:48.313. Dotarł do sześciu kontroli metadanych, lecz zakończył się
`refresh_interrupted` o 15:27:23. Dev autoreload wymienił proces API
o 15:27:20 po dodaniu pliku testowego. Nie wykonano ręcznego restartu.
**Tego przebiegu nie zaliczono jako udanego pełnego automatycznego importu.**
Zachowano poprzednią publikację; następny termin to 15:42:23.

Nie stwierdzono 429/backoff sześciu serii jako przyczyny ich braku.
Standardowa przerwa wynosi 15 minut po zakończeniu joba. Ścieżka specjalnych
wybudzeń po publikacji obejmuje BEA; Employment nie ma analogicznej polityki.
Frontend uruchamia standardowe zadanie, gdy strona jest aktywna/widoczna.
Nie jest to niezależny harmonogram importu makro przy zamkniętej przeglądarce.

Stopka pochodzi z `calendar_agenda.scoped_check()`: wybiera **najstarsze
checked_at wymaganych źródeł**, także kalendarzy. Kontrola `fred:calendar`
zakończyła się o 09:08:25 UTC, czyli **10:08:25 PL**. Kalendarze mają osobny
interwał sześciogodzinny. Zakończenie nowego joba obserwacji/metadanych nie
przesuwa tego minimum. Spinner oznacza stan zadania, nie dostępność Actual.
Nie zmieniono UI, kolorów ani semantyki stopki.

## Oficjalny BLS i rewizje

[Komunikat BLS](https://www.bls.gov/news.release/empsit.nr0.htm) oraz
[tabela A-15](https://www.bls.gov/news.release/empsit.t15.htm) potwierdzają
sześć wartości kontrolnych. Bezpośrednie pobrania HTML otrzymały 403;
nie obchodzono odmowy. Oficjalne Public API BLS odpowiedziało HTTP 200
na jedną anonimową zbiorczą prośbę o sześć serii, bez konta lub klucza.
[Dokumentacja API](https://www.bls.gov/developers/api_signature_v2.htm).

Oryginalne JSON: 6189 B, capture **15:08:13 PL**, SHA-256
`b2b8d8cef801e82471d0b7aa6c33de893d56c0b5dfa74ad5733f30fa84e65e76`.
RAW, payload żądania i receipt pozostają ignorowane. Nie zadeklarowano
zachowania oryginalnego HTML, którego downloader nie otrzymał.

Mapowanie SA: PAYEMS→CES0000000001, UNRATE→LNS14000000,
AHE→CES0500000003, CIVPART→LNS11300000, U6RATE→LNS13327709,
AWHAETP→CES0500000002. Parser wymaga pełnego zestawu i właściwych miesięcy.
Payrolls z tej samej odpowiedzi: październik 159293, wrzesień 159128,
sierpień 159068 tys.; różnice wynoszą 165 i 60 tys.
AHE z 38,00/37,86 daje 0,369783…%, czyli 0,4% po zaokrągleniu do jednego
miejsca. Oznaczono to jako wyliczenie z opublikowanych poziomów dolarowych,
nie procent rzekomo dostarczony przez API. Komunikat potwierdza 0,4%.

ALFRED ma wrześniowy pierwszy odczyt 29 tys. z poziomów 159044−159015
w wersji 02.10. Nie nadpisano go rewizją 60 tys. Normalne API nadal ma
Previous=29 tys. Ewentualne przyszłe Current BLS i Previous BLS muszą
pochodzić ze wspólnego capture; 60 tys. byłoby jawną bieżącą rewizją
poprzedniego miesiąca, a nie first print. API BLS nie jest archiwum first print.

## Minimalny plan autoryzacji — niewykonany

Normalny target potwierdzony read-only: localhost:5432/macrolens, PG17,
macrolens, OID 16384, system_identifier 7682090371041935398.
F1 V2 nadal dopuszcza manifest 155 artefaktów i plan
`8e70cec78af59999f5e6e75c5e9b67c97f7be69f23ac071f9e56c93896b654c3`.
Normalny backend nie został zmieniony. Nie usuwano kontroli hashy.

Konieczny zakres produkcyjnego rozwiązania:

1. Potwierdzony release 50 / okres / czas uruchamia ograniczone pobranie
   obserwacji niezależnie od niezmienionych metadanych. Trwały claim przed
   HTTP, minimum 15 minut, okno dwóch godzin, respektowanie Retry-After
   i budżetu. Po pojawieniu się okresu zaprzestać dodatkowych prób.
2. Gdy FRED nadal nie ma okresu: przejrzany adapter sześciu SA serii BLS,
   jedno żądanie zbiorcze. Oryginał, SHA, capture i metody w istniejącym
   publisher_documents. Kontrole/claim w istniejącym source_check_runs;
   konserwatywny trwały limit anonimowego API, błędy też liczone.
   Bez DDL i bez wpisywania BLS jako FRED/ALFRED.
3. Źródłowa projekcja w calendar_readings, powiązana z potwierdzonym
   wydarzeniem i dokumentem. Nie nadpisywać observation_vintages first print,
   nie mieszać zależności dwóch capture. Zachować alternatywne źródła i rewizje.
4. Wybudzanie przez istniejący lifecycle/coordinator, również bez otwartej
   strony; bez edycji aktywnej policy monitora Earnings lub nowego timera.
5. Oddzielny protokół zatwierdzenia upgrade backendu F1: nowy pełny manifest,
   ciągłość starej policy, kontrolowany runner, append-only autoryzacja i token.
   Obecny runner UI V2 nie zatwierdza dowolnej kolejnej rewizji backendu.
   Potem świeży backup/pełny restore, próba klonu, rollout w oknie i dopiero
   osobna zgoda na finalny wykonywalny plan. Bez niezatwierdzonego APPLY.

Obecnie przygotowano tylko niepodłączony parser diagnostyczny i testowaną
politykę prób w `integrations/nfp_release_diagnostics.py`. Nie ma w nich SQL,
HTTP, importu, rejestracji w lifecycle ani uprawnienia normalnego workera.
Transport BLS, zapis, projekcja, trwały budżet i upgrade F1 **wymagają
implementacji i walidacji**. Nie wykonano próby produkcyjnego rozwiązania
na klonie ani nie przygotowano pozornego tokenu apply.

Zamrożony opis zakresu i SHA zastanych krytycznych plików:
`data/raw/nfp-missing-actuals-2026-11-06/minimal-authorization-proposal.json`.
Hash **propozycji**, `ready_for_apply=false`:
`ba06fa8764a11f777ba29cb80be30812763b7ce0881f5aab64bcc1b8d9adc5b9`.
Nie jest to hash do zatwierdzenia APPLY; finalny kod i plan będą inne.

## Walidacja i stan końcowy

- Pełny backend offline: **1608 passed**, 83,19 s. Po dodaniu jeszcze
  jednego scenariusza końcowy zestaw diagnostyka/refresh/Employment:
  **58 passed**, 4,48 s, w tym 11 nowych przypadków.
- Testy odtwarzają pominięcie HTTP w istniejącym refresh mimo dostępnego
  nowego payloadu. Osobny test kandydackiej polityki: identyczne metadane,
  brak miesiąca przy pierwszej próbie, październik przy drugiej dopuszczonej
  próbie; bez nowej próby po pięciu minutach. To nie jest dowód wdrożenia.
- Rzeczywista odpowiedź BLS sparsowana i sprawdzona dla wszystkich sześciu
  miar; osobno testy braków, duplikatów, NSA, NaN, zależności i błędu API.
- Chrome na normalnym API/Vite, PL/EN, 1366/390: **34 kontrole, 12 API 200**.
  Oba widoki pokazują sześć null; właściwe daty/godziny i brak overflow.
  Osobna obserwacja automatycznego wybudzenia: 11 kontroli / 57 API 200,
  ale job error — nie zaliczono sukcesu importu. Obejrzano zrzut desktop PL.
- Pełne snapshoty 13 tabel Earnings i trzech Forecast, katalogi i referencje
  są identyczne przed/po końcowym oknem diagnostycznym. F1 authorization
  sprawdzona niezależnie: activated=true/cooldown. Earnings:
  activated=true, loop_running=true, completed. F2 pozostał nieaktywny.
- Końcowe normalne API: sześć Actual null; Previous NFP 29 tys., U-3 4,2%,
  AHE 0,132415…%, participation 61,8%, U-6 7,6%, hours 34,4.
  Nie deklaruje się naprawy ani niezawodności następnych publikacji.

Nie zmieniono frontendu, więc nie powtarzano TypeScript/build/Vitest.
Nie uruchomiono migracji ani syntetycznych testów SQL w normalnej bazie.
Wszystkie bezpośrednie zapytania diagnostyczne SQL były read-only; zwykły,
autoryzowany refresh zapisywał swoje checks/stan i publikację. Nie twierdzi
się, że cała pracująca baza makro była niezmienna.

Zachowano byte-identycznie wszystkie **491 zastanych plików** z manifestu,
w tym wcześniejsze UI, chronione prace oraz F2. Dodano wyłącznie helper,
jego test i ten raport. Końcowo **30 modified / 71 untracked**, indeks pusty,
main/HEAD bez zmian. Bez stagingu, commita, pusha, reset/clean/amend/force
lub globalnego formatowania. Własny Chrome zakończono; normalne usługi
pozostają uruchomione. RAW/receipts/logi/zrzuty są ignorowane.
