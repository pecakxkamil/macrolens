# MacroLens — Calendar UI i autoryzacja F1 V2: wdrożone

05.11.2026, Europe/Warsaw, C:\Projects\macrolens, main.

**Zatwierdzony plan wykonano w normalnym PostgreSQL. Nowy Calendar działa
na Vite 5173, API 8000. F1 i monitor Earnings pozostają aktywne.**
Dokument gotowości opisuje wcześniejszy stan; ten raport opisuje zakończone
wdrożenie po odpowiedzi użytkownika „tak zatwierdzam”.

## Zgoda i wykonanie

Zatwierdzony i wykonany kanoniczny SHA-256:

`8e70cec78af59999f5e6e75c5e9b67c97f7be69f23ac071f9e56c93896b654c3`

Przed zapisem ponowne CLI plan zwróciło identyczny hash. Wszystkie 14 plików
delivery miało dokładne hashe wejściowe. Target pozostał localhost:5432/macrolens,
PG17, rola macrolens, OID 16384, klaster 7682090371041935398.
Zachowano zgodny backup/pełny restore opisany w
[raporcie gotowości](macrolens-calendar-ui-f1-authorization-final-2026-11-05.md),
bez podmiany zatwierdzonego planu.

API/Vite były już zatrzymane w chwili kontroli procesów i portów; nie
zakończono cudzych procesów. CLI apply zakończyło się kodem 0,
outcome=created i COMMIT. Powstał dokładnie jeden wpis
`activation-ui-revision` w forecast_refresh_checks. Oryginalna activation-policy
oraz jej historyczny plan/manifest pozostały identyczne. Bez DDL, UPDATE,
DELETE lub importu prognoz.

Niezależne CLI verify przeszło przed instalacją. Instalator sprawdził
wszystkie hashe, zachował stare bajty/token i zainstalował dokładne 14 plików
oraz token V2. Kolejne verify uruchomione z normalnego kodu także przeszło.
Dostarczono również nowy plik testów autoryzacji z przetestowanego patcha.
Nie wykonywano restore/rollbacku normalnej bazy.

Następnie uruchomiono normalne API Uvicorn z autoreload na 127.0.0.1:8000
i Vite na 127.0.0.1:5173. Dotychczasowy lifecycle Earnings uruchomił także
F1. Pliki aktywnej aplikacji nie były podmieniane przy działającym starym
workerze. PostgreSQL pozostawał uruchomiony.

## Wynik funkcjonalny

Zwykłe otwarcie Calendar wybiera **Wszystko**. Kolejność:
**Wszystko | Dane | Wyniki**, EN **All | Data | Earnings**.
Wybrana domena przetrwała rzeczywisty cykl odświeżania, a ponowne zwykłe
otwarcie wróciło do All. Słownik 53 CIK porządkuje 37 nazw, m.in.
„Advanced Micro Devices, Inc.”. Bez zmiany nazw SQL, tickerów lub aliasów.

Zachowano Current/Previous, Forecast, Market Cap i źródła. Prawdziwy
Calendar/API potwierdził Previous AMD 1.38 USD / 11.54 mld USD, AAPL
2.02 USD / 109.42 mld USD i PLTR 0.41 USD / 1.94 mld USD oraz ich właściwe
poprzednie kwartały. CRWD Previous EPS i ARM/QCOM Previous pozostają null;
ARM/QCOM Current Actual pozostają dostępne. Jest 14 nowcastów makro i
guidance Revenue NVIDIA, bez fikcyjnego Forecast EPS.

Manifest workera V2 obejmuje 155 artefaktów backendu/config/bibliotek.
Zwykła zmiana wyglądu React nie wymaga kolejnej rewizji SQL. Kontrole
krytycznego kodu, targetu, schematu, referencji, praw i źródeł pozostają.

## Kontrola po wdrożeniu

Chrome na **normalnym Vite/API/SQL**, PL/EN, 1366/390 px, bez fixture:
**328 kontroli / 49 odpowiedzi API GET 200**, zero błędów JS/console.error
i HTTP 503. Sprawdzono nazwy, domeny, Previous, prognozy, źródła, liczbę
kolumn, wewnętrzny scroll telefonu i brak overflow strony. Przeglądarka
nie wysyłała żądań do wydawców. Obejrzano desktop EN i mobile PL po
przewinięciu do wartości. Nie jest to pełny audyt WCAG.

Na zainstalowanym kodzie nowe testy autoryzacji: **11 passed, 8.88 s**.
Kod delivery odpowiada przygotowanej kopii z wynikami 1588 backend,
775 frontend, TypeScript/build, 22 regresje PG oraz pełną próbą rewizji.
Nie utożsamia się lokalnych wyników z GitHub Actions.

Niezależny końcowy odczyt SQL po Chrome potwierdził:

- wszystkie 13 tabel Earnings byte-identyczne z wcześniejszym snapshotem;
- forecast_vintages: 20, forecast_freezes: sześć null, pełne hashe bez zmian;
- forecast_refresh_checks: 2→3; binary COPY dwóch starych wpisów identyczne;
- dokładnie zatwierdzoną rewizję i niezmienioną oryginalną policy;
- oba katalogi schematu identyczne, wszystkie 155 artefaktów zgodne;
- F1 activated=true, cooldown, added=0, frozen=0;
- Earnings loop_running=true, activated=true, completed, checked=0;
- Market Cap cache 49/53, niezmieniony SHA 94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799.

Zwykłe makro mogło pracować równolegle. Nie wymagano identyczności jego
zmiennych wierszy ani nie zmieniano jego konfiguracji. Pomocniczy pierwszy
odczyt integralności wymagał ustawienia PYTHONPATH; powtórzony odczyt
przeszedł. W odziedziczonym helperze Chrome poprawiono wyłącznie opis
środowiska w metadanych: faktyczne żądania od początku trafiały do normalnych
portów 5173/8000, co zapisano w wynikach.

## Pliki i zakończenie

Spośród 445 plików manifestu wejściowego 435 zachowano byte-identycznie;
pozostałe dziesięć zmieniono dokładnie według delivery. W dwóch współdzielonych
CalendarPage dodano tylko zatwierdzone hunki, zachowując wcześniejsze prace.
Pozostałe chronione pliki, F2 i wcześniejsze audyty zachowano. Doszły nowe
pliki autoryzacji/słownika/testów. Nie modyfikowano ledgerów finansowych,
Market Cap, kodu monitora ani F2.

Receipt, oba verify, stary token/pliki, końcowe hashe, logi i zrzuty są
ignorowane w data/raw/calendar-ui-f1-final-2026-11-05. Własny Chrome testowy
zakończono; **normalne API 8000 i Vite 5173 pozostawiono działające**.
Brak diagnostycznych lease/blokad. Nie wykonano stagingu, commita, pusha,
reset/clean/amend/force ani globalnego formatowania; HEAD pozostaje
c42cf6c411c85a64927fe5c6b3cf98f9e906c871. Nie uruchamiano nowego Actions.
