# MacroLens — E2E: osobne Previous i minimalistyczne Szczegóły

Wykonano **04.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`, `main`,
HEAD `94526c9cf0422dde041c69fd4fdec21549a8b39e`.

**Nowy widok działa lokalnie na normalnym Vite/API. Previous z istniejącego
E2B działa bez importu. Nowe 23 raporty historyczne / 45 miar przygotowano
i sprawdzono wyłącznie w izolacji. Nie aktywowano ich w normalnej bazie.**
Nie wykonano stagingu, commita ani pusha.

## 1. Widok

Dokładnie siedem kolumn: Spółka, Czas wyników · Polska, EPS aktualny,
EPS poprzednio, Przychody aktualne, Przychody poprzednio, Szczegóły.
Cztery kolumny finansowe zachowują Actual / Prognoza i osobne dwie linie.
Previous jest mniejsze, prognozy pozostają null/`—`, waluta jest przy każdej
wartości. Brak wartości nie jest zerem. Spółka jest wyrównana do lewej,
pozostałe kolumny do środka. Mobile korzysta z wewnętrznego scrolla.

Usunięto kolumnę Status, a nie statusy API. „Szczegóły / Źródło” zmieniono
na „Szczegóły” (EN: Details). Zachowano wcześniejsze usunięcie opisów
date-only i wstępu/stopki Earnings, grupowanie dni, zakresy i filtry domen.

Panel pokazuje nazwę/ticker/kwartał, dostępny koniec okresu i datę wyników,
czas oraz osobną konferencję, status, podstawę EPS i poprzedni okres.
Zachowuje rozróżnienie Published, Scheduled, pending/partial i terminu
minionego bez dowodu publikacji. Nie renderuje CIK/UUID, wersji,
captured_at, surowych jednostek, opisów audytowych ani powtórzonych kwot.
Oficjalne linki są deduplikowane. Poprzednia wartość ma link do swojego
raportu; zapowiedź nie jest nazywana raportem finansowym, a źródło call
pojawia się tylko dla potwierdzonego komponentu call. Pełne historie
i provenance pozostają w API i bazie.

## 2. Czytnik i porównywalność

Dodano osiem pól `current/previous_eps/revenue_actual/forecast`,
`previous_period`, status dostępności store i historię poprzednich raportów.
Stare pola API, statusy publikacji oraz modele E2A–E2D pozostają dostępne.
Current nigdy nie otrzymuje Previous; brak konsensusu oznacza null.

Klucz porównania obejmuje company_id, CIK, FY i dokładny kwartał fiskalny:
Q2→Q1, Q3→Q2, Q4→Q3, Q1→Q4 poprzedniego FY. Nie ma wyszukiwania
najbliższego dostępnego raportu. Sprawdzane są waluta, standard,
metodologia EPS i podstawa akcji. Nie wykonuje się FX, ADR lub własnego
przeliczenia splitu. E2B ma jawnie ograniczony model USD/US GAAP/common
share; jego raportowane diluted EPS jest normalizowane do tej samej
semantyki co E2D, z zachowaniem odrębności wyniku przypadającego Intel.

Wykorzystywane są najpierw istniejące eventy E2B/E2D. Ich aktualny snapshot
ma pierwszeństwo także wtedy, gdy dana metryka jest pusta: historyczny
store nie uzupełnia po cichu wycofanej metryki. Wersja historycznego
dokumentu jest kompletnym snapshotem, bez dziedziczenia pominiętego EPS.

Całość działa w dotychczasowym REPEATABLE READ READ ONLY przed filtrowaniem
dat. Historia jest pobierana zbiorczo: kontrola dostępności i jeden SELECT,
bez SQL/requestu dla każdego wiersza. GET nie wykonuje DDL, importu ani
HTTP do wydawców. Brak store jest obsługiwany jako `not_activated`.

## 3. Działające przykłady E2B w normalnej aplikacji

| Bieżący / poprzedni okres | EPS aktualny / poprzednio, USD | Revenue aktualne / poprzednio, USD |
|---|---|---|
| INTC Q3 / Q2 2026 | 0,60 / −2,16 | 16,513 / 16,128 mld |
| AMZN Q3 / Q2 2026 | 1,89 / 5,75 | 201,944 / 200,606 mld |
| NVDA Q2 / Q1 FY2027 | 2,46 / 2,39 | 96,221 / 81,615 mld |

Tabela zaokrągla revenue do dwóch miejsc w miliardach, np. Intel
16,51 / 16,13 mld USD. Przyszła NVDA Q3 FY2027 zachowuje Current null,
ale może pokazać Q2: 2,46 USD i 96,22 mld USD. Prognozy są puste.

Zakres 01.05–31.12.2026 ma 34 datowane wydarzenia / 30 emitentów:

| Środowisko | Wydarzenia z jakimkolwiek Previous | Bez Previous | Emitenci z Previous / bez |
|---|---:|---:|---:|
| Normalna baza, tylko istniejące E2B/E2D | 4 | 30 | 3 / 27 |
| Izolacja z nową historią | 27 | 7 | 26 / 4 |

W całym rejestrze 53 firm oznacza to odpowiednio 50 i 27 firm bez
jakiegokolwiek Previous dla datowanego wydarzenia; część nie ma eventu.
Trzy starsze pierwsze raporty pilotów nie mają poprzednika, choć te same
firmy mają Previous przy kolejnym raporcie. W izolacji cztery firmy bez
Previous to ARM, QCOM, PANW, SNOW. Nie rozszerzano ich danych.

## 4. Audyt 23 wcześniejszych raportów

Oficjalne źródła odczytano narzędziem WWW 04.11.2026. Ledger
`config/earnings_previous_reviewed.json` przechowuje dokładne FY/Q,
period_end, release_date, verified_on, źródło, oryginalną skalę/precision,
standard, walutę, podstawę akcji i notatkę kontroli. To ręcznie zweryfikowane
metadane, nie hash bajtów pobranego dokumentu lub dowód first print.
Nie archiwizowano pełnych komunikatów i nie tworzono fikcyjnych HTTP receipts.

W poniższej tabeli EPS jest reported diluted na akcję zwykłą/common,
USD i US GAAP, z jawnymi wyjątkami TSM i ASML. Revenue jest skonsolidowane,
za kwartał, w oryginalnej skali źródła; nie YTD, segment, guidance lub adjusted.
Tabela opisuje **wyłącznie dane izolowane**, a nie nowy import normalnej bazy.

| Ticker | Poprzedni okres | Koniec okresu | Release | Revenue | EPS | Waluta / standard | Oficjalne źródło |
|---|---|---|---|---|---|---|---|
| AAPL | Q3 FY2026 | 2026-06-27 | 2026-07-30 | 109417 mln | 2.02 | USD / US_GAAP | [raport](https://www.apple.com/newsroom/pdfs/fy2026q3/FY26_Q3_Consolidated_Financial_Statements.pdf) |
| MSFT | Q4 FY2026 | 2026-06-30 | 2026-07-29 | 90007 mln | 4.81 | USD / US_GAAP | [raport](https://www.microsoft.com/en-us/investor/earnings/fy-2026-q4/press-release-webcast) |
| GOOGL | Q2 2026 | 2026-06-30 | 2026-07-22 | 119796 mln | 9.11 | USD / US_GAAP | [raport](https://s206.q4cdn.com/479360582/files/doc_news/2026/Jul/22/attachments/2026q2-alphabet-earnings-release.pdf) |
| META | Q2 2026 | 2026-06-30 | 2026-07-29 | 60801 mln | 6.18 | USD / US_GAAP | [raport](https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Second-Quarter-2026-Results/) |
| AMD | Q2 2026 | 2026-06-27 | 2026-08-04 | 11536 mln | 1.38 | USD / US_GAAP | [raport](https://ir.amd.com/news-events/press-releases/detail/1295/amd-reports-second-quarter-2026-financial-results) |
| TSLA | Q2 2026 | 2026-06-30 | 2026-07-22 | 28236 mln | 0.32 | USD / US_GAAP | [raport](https://www.sec.gov/Archives/edgar/data/1318605/000162828026049270/tsla-20260630.htm) |
| AVGO | Q2 FY2026 | 2026-05-03 | 2026-06-03 | 22187 mln | 1.91 | USD / US_GAAP | [raport](https://investors.broadcom.com/node/64371/pdf) |
| NFLX | Q2 2026 | 2026-06-30 | 2026-07-16 | 12559938 tys. | 0.80 | USD / US_GAAP | [raport](https://s22.q4cdn.com/959853165/files/doc_financials/2026/q2/FINAL-Q2-26-Shareholder-Letter.pdf) |
| ORCL | Q4 FY2026 | 2026-05-31 | 2026-06-10 | 19184 mln | 1.45 | USD / US_GAAP | [raport](https://investor.oracle.com/investor-news/news-details/2026/Oracle-Announces-Record-Q4-and-FY-2026-Results-Driven-by-Cloud-Infrastructure--Cloud-Applications/) |
| MU | Q3 FY2026 | 2026-05-28 | 2026-06-24 | 41456 mln | 24.67 | USD / US_GAAP | [raport](https://investors.micron.com/node/50671/pdf) |
| TSM | Q2 2026 | 2026-06-30 | 2026-07-16 | 1270.38 mld | 27.25 | TWD / IFRS | [raport](https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/2026-07/a80d7933be643644081584087731f73b22ea5a2c/2Q26%20EarningsRelease.pdf) |
| ASML | Q2 2026 | nieustalony | 2026-07-15 | 9326 mln | 7.58 | EUR / US_GAAP | [raport](https://ourbrand.asml.com/asset/9078cf4d-91fd-4dd9-a5d5-d1caab6dc046/2026_07_15_Presentation-Investor-Relations-Q2-2026.pdf) |
| AMAT | Q2 FY2026 | 2026-04-26 | 2026-05-14 | 7910 mln | 3.51 | USD / US_GAAP | [raport](https://ir.appliedmaterials.com/node/29236/pdf) |
| LRCX | Q4 FY2026 | 2026-06-28 | 2026-07-29 | 6722238 tys. | 1.81 | USD / US_GAAP | [raport](https://investor.lamresearch.com/2026-07-29-Lam-Research-Corporation-Reports-Financial-Results-for-the-Quarter-Ended-June-28%2C-2026) |
| KLAC | Q4 FY2026 | 2026-06-30 | 2026-07-28 | 3657556 tys. | 1.04 | USD / US_GAAP | [raport](https://ir.kla.com/news-events/press-releases/detail/518/kla-corporation-reports-fiscal-2026-fourth-quarter-and-full) |
| TXN | Q2 2026 | 2026-06-30 | 2026-07-22 | 5463 mln | 2.14 | USD / US_GAAP | [raport](https://www.ti.com/about-ti/newsroom/news-releases/2026/2026-07-22-ti-reports-second-quarter-2026-financial-results-and-shareholder-returns.html) |
| ADBE | Q2 FY2026 | 2026-05-29 | 2026-06-11 | 6618 mln | 4.25 | USD / US_GAAP | [raport](https://www.adobe.com/cc-shared/assets/investor-relations/pdfs/11606202/a5543arefgt.pdf) |
| CRM | Q1 FY2027 | 2026-04-30 | 2026-05-27 | 11133 mln | 2.42 | USD / US_GAAP | [raport](https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-First-Quarter-Fiscal-2027-Results/default.aspx) |
| NOW | Q2 2026 | 2026-06-30 | 2026-07-22 | 3987 mln | 0.29 | USD / US_GAAP | [raport](https://newsroom.servicenow.com/press-releases/details/2026/ServiceNow-Reports-Second-Quarter-2026-Financial-Results/default.aspx) |
| PLTR | Q2 2026 | 2026-06-30 | 2026-08-03 | 1935464 tys. | 0.41 | USD / US_GAAP | [raport](https://investors.palantir.com/files/2026%20Q2%20PLTR%2010-Q.pdf) |
| CRWD | Q1 FY2027 | 2026-04-30 | 2026-06-03 | 1385629 tys. | — (split) | USD / US_GAAP | [raport](https://ir.crowdstrike.com/node/16821/pdf) |
| IBM | Q2 2026 | 2026-06-30 | 2026-07-22 | 17162 mln | 2.27 | USD / US_GAAP | [raport](https://newsroom.ibm.com/2026-07-22-IBM-RELEASES-SECOND-QUARTER-RESULTS) |
| CSCO | Q3 FY2026 | 2026-04-25 | 2026-05-13 | 15841 mln | 0.85 | USD / US_GAAP | [raport](https://s21.q4cdn.com/812015656/files/doc_news/CISCO-REPORTS-THIRD-QUARTER-EARNINGS-2026.pdf) |

CRWD: oficjalny Q1 FY2027 podaje EPS 0,11 USD przed splitem 4:1
(handel po splicie od 02.07.2026). Do porównania zaimportowano tylko revenue;
EPS null, bez dzielenia 0,11 przez cztery i bez pozornej zgodności ze źródłem
Q2. KLA Q4 ma już retroaktywnie skorygowany EPS 1,04 po splicie 10:1
z 11.06; Netflix 0,80 także jest już skorygowane w samym dokumencie.

Alphabet: 2026 jest drugą kolumną dokumentu; diluted 9,11, nie basic 9,23
i nie porównawcze 2,31. Meta 6,18, AMD 1,38 i Adobe 4,25 zachowują GAAP
łącznie z raportowanymi kosztami/korzyściami. IBM total diluted 2,27.

TSM: TWD, TIFRS/IFRS, EPS 27,25 na zwykłą akcję; nie USD 4,31/ADR.
Standard potwierdza również [oficjalne sprawozdanie w SEC](https://www.sec.gov/Archives/edgar/data/1046179/000104617926000541/a2026q2consolidatedreport-.htm).
ASML: US GAAP, EUR, diluted 7,58; nie basic 7,59. Dokładny dzień końca
okresu nie został ustalony z przejrzanej prezentacji i pozostaje null.
Nie zgadywano daty na podstawie etykiety Q2.

Tesla: duży deck nie został otwarty przez narzędzie WWW z powodu limitu
rozmiaru. Użyto oficjalnego 10-Q wskazanego przez IR, z kwartalną kolumną.
Datę release 22.07 potwierdza [tabela IR](https://ir.tesla.com/).
Broadcom IR HTML zwrócił 403; odczytano oficjalny PDF, bez obchodzenia blokady.
Dla Palantira strona news renderowała pusty szkielet; wartości potwierdzono
w oficjalnym kwartalnym 10-Q. Nie zmieniano bieżących danych E2D.

## 5. Store wyłącznie dla historii

Jedna nowa tabela `earnings_historical_reports` przechowuje atomowy JSONB
snapshot raportu i jego metryk oraz osobne klucze emitenta/FY/Q, wersję,
poprzednika, correction_reason, fingerprint i lokalny captured_at.
FK wskazuje wyłącznie istniejącego emitenta. Nie wymaga nowego
`earnings_events` ani `earnings_periods`. Dzięki temu porównanie finansowe
nie generuje sztucznego kalendarza.

SQL blokuje UPDATE/DELETE/TRUNCATE, sprawdza dokładnego poprzednika wersji,
tożsamość, typ dokumentu, daty, standard/walutę, dwie unikalne metryki,
skalowanie, precision i diluted/share basis. INSERT blokuje emitenta.
Importer zatwierdza całą partię względem lokalnego reviewed ledgeru,
używa Decimal i locka 726530020. Poprawka wymaga zaktualizowanego,
przejrzanego ledgeru i jawnej przyczyny; znany stary fingerprint nie
reaktywuje poprzedniej wersji. Inicjalizator i importer odrzucają normalną
bazę, dopuszczając własny prefiks `macrolens_earnings_e2b_e2c_e2d_e2e_`.
Zastany schemat wymaga zgodnej pełnej sygnatury. Brak podpięcia importera
do API, startupu lub harmonogramu.

## 6. Nowe wyniki walidacji

| Kontrola | Wynik |
|---|---|
| Pełny backend offline | **1362 passed**, pytest 55,90 s |
| Pełny frontend offline, Node 22.23.4 | **680 passed / 32 pliki**, 29,96 s |
| TypeScript noEmit | passed |
| Production build | passed, Vite 4,11 s; największy chunk 407,04 kB |
| Dotychczasowe PostgreSQL 17 | **12/12 passed** |
| Nowy rzeczywisty PostgreSQL E2E | passed: 23 raporty / 45 miar |
| Chrome izolowany, prawdziwe API/SQL | **1325 kontroli, 28 odpowiedzi API 200**, dodatkowo 37 GET 200 |
| Chrome normalny Vite/API | **1053 kontrole, 28 odpowiedzi API 200**, dodatkowo 37 GET 200 |
| JavaScript / console.error / HTTP 503 | zero |
| Publisher HTTP w GET / Chrome | zero |
| Chronione pliki, pusty indeks, diff --check | passed |

Regresje obejmują Empire, FT900, BEA Direct, BEA release/R3, E2A i Activation,
E2B i Activation, E2C i Activation, E2D i Activation. Własny PostgreSQL 17
działał tylko na loopback 55473, z losowymi bazami i guardem publisher HTTP.
Pierwszy przebieg ostatniego testu Activation odrzucił nazwę kontenera;
po kontroli ID/etykiety dostosowano nazwę własnego kontenera do istniejącej
bramki i powtórzono ostatni test z sukcesem. Nie osłabiono guarda.

Nowe testy sprawdzają rollover FY, dokładny kwartał, braki, zero/ujemne EPS,
waluty, GAAP/IFRS, ADR/common, metodologię, skalowanie, null Current z
Previous, brak prognoz, GOOG/GOOGL, wersje/append-only/idempotencję,
stare capture i brak dziedziczenia pominiętego EPS. Rzeczywisty błąd SQL
wycofał razem DDL i seed; późniejsze niedozwolone INSERT także odrzucono.
Pełne 23 stare tabele były identyczne po nowym imporcie/testach.

Chrome: normalny Vite 5173 / API 8000 oraz osobny production preview 4199 /
API 8029 / izolacja 55473. Nie podstawiano odpowiedzi. Wrapper izolacji
dodawał tylko CORS, API było read-only z lease wyłącznie na izolacji.
Wszystkie **24 tabele izolacji** miały identyczne pełne snapshoty przed/po UI.
EN/PL, 1366/390 px, 34 datowane wiersze, wszystkie cztery metryki porównane
z API i ledgerami, źródła, okresy, call, siedem kolumn, mniejszy Previous,
wewnętrzny scroll, brak overflow strony, Escape/focus, domeny i zakresy.
Obejrzano zrzuty desktop EN i mobile PL obu środowisk. To nie pełny audyt WCAG.

Początkowe testy frontendowe oczekiwały usuniętego Statusu i technicznej
historii; zastąpiono te oczekiwania sprawdzeniem nowego kontraktu oraz
zachowanych danych i źródeł. Pierwszy helper Chrome klikał programowo bez
ustawienia fokusu; poprawiono wyłącznie helper, aby wysłać Escape z linku
w panelu i sprawdzić powrót do przycisku. Nieudanych prób nie zaliczono
do sukcesów. Naprawiono też kodowanie UTF-8 pomocniczej edycji przed buildem.

## 7. Ochrona normalnych danych

Tożsamość potwierdzono niezależnym SQL read-only: localhost:5432/macrolens,
rola macrolens, OID 16384, klaster 7682090371041935398. Pełne binary COPY
po PK przed/po: **23 tabele**, wszystkie **10 tabel Earnings byte-identyczne**,
obie pełne reprezentacje katalogów schematu identyczne. Nie ma tabeli historii.

Zachowane liczniki: **53 companies, 55 aliases, 37 periods, 37 events,
40 source evidence, 66 confirmations, 6 dokumentów/12 miar E2B,
27 dokumentów/46 miar E2D**. Nie wykonano normalnego DDL, importu historii,
UPDATE/DELETE, aktywacji, rollbacku lub nowego zapisu finansowego.

Normalny backend i Vite działały przez ten etap. Pełna baza wzrosła pomiędzy
odczytami z **2 951 589 do 2 963 328 rekordów**. Zmiany wystąpiły wyłącznie
w computed_features, observation_vintages, overview_publications,
overview_refresh_state, publisher_documents i source_check_runs podczas
zwykłej pracy aplikacji makro. Nie deklaruje się identyczności tych sześciu
tabel. Siedem pozostałych tabel makro oraz wszystkie Earnings są identyczne.
Każda sesja diagnostyczna normalnej bazy miała read-only; nie blokowano
zwykłej pracy makro lease'em i nie zmieniano R1–R3/K2/Overview/źródeł.

Dodatkowy odczyt niesekretnych ustawień procesów nie został wykonany:
automatyczny przegląd uprawnień zgłosił limit użycia narzędzia. Nie obchodzono
tego ograniczenia. Tożsamość SQL i testy normalnego API/UI przeszły.

## 8. Osobna późniejsza aktywacja historii — niewykonana

`data/raw/earnings-e2e-2026-11-04/activation-proposal.json` opisuje zakres
z `ready_for_apply=false`. Nie jest tokenem apply ani zgodą na zapis.

Potencjalny zakres to jedna tabela historii, jej constraints/indeksy,
funkcja i trzy triggery oraz 23 snapshoty zawierające 45 miar. Bez nowych
firm, okresów, eventów i bez zmiany obecnych tabel. Brakujące Previous EPS
CRWD wymaga odrębnego zweryfikowanego źródła zgodnej podstawy, bez zgadywania.

Późniejszy etap wymaga osobnego runnera i pełnego planu, aktualnego targetu,
uzgodnionego okna serwisowego, stabilnych snapshotów, świeżego pełnego
backup/restore na PG17 oraz testów planu na kopii. Dopiero potem osobna zgoda
na pełny hash, transakcja DDL+seed i kontrola idempotencji/integralności przed
restartem. Nie stosuje się wcześniejszego tokenu E2D. Nie wykonuje się
automatycznego rollbacku po COMMIT. Nie dodano automatycznego feedu.

## 9. Pliki i zakończenie

Zmiany E2E obejmują osiem istniejących plików:

- app/earnings.py
- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/earningsTypes.ts
- frontend/src/calendar/earnings.css
- frontend/src/calendar/EarningsCalendar.test.tsx
- frontend/src/calendar/EarningsFinancials.test.tsx
- frontend/src/calendar/EarningsCoverage.test.tsx
- frontend/src/calendar/EarningsReports.test.tsx

Siedem nowych plików:

- app/earnings_previous.py
- app/earnings_history.py
- app/database/earnings_history_schema.sql
- config/earnings_previous_reviewed.json
- tests/test_earnings_previous.py
- tests/postgres_earnings_history_validation.py
- docs/audits/equity-earnings-previous-results-e2e-2026-11-04.md

Manifest wejściowy 23 zastanych zmienionych/nieśledzonych plików i pełny diff
są w ignorowanym data/raw/earnings-e2e-2026-11-04. E2E zmieniło z nich
wyłącznie cztery właściwe pliki Earnings UI/testów/CSS; **pozostałe 19 są
byte-identyczne**, w tym wszystkie 13 chronionych plików użytkownika,
aktywator E2D, jego testy i dwa raporty. Poprzednich audytów nie edytowano.
Zależności, lockfile, CI i globalny CSS bez zmian tego etapu.

Końcowo **18 modified / 16 untracked**, indeks pusty, main i HEAD bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend i globalnego formatowania.
Własne API/preview/Chrome zakończono, lease izolacji zwolniono w finally,
losowe bazy usunięto. Przed usunięciem własnego kontenera sprawdzono pełny ID
`9bd259cf009e495a9c8f84fe12933695d306c70d8f38ff87303e5b3efeb6a871`,
etykietę i brak baz poza control/postgres/template. Usunięto tylko ten
kontener i jego anonimowy wolumen. Normalny PostgreSQL, API 8000 i Vite 5173
pozostawiono działające. Logi, screenshoty, helpery i manifesty pozostają
ignorowane w data/raw; nie dodano pełnych komunikatów lub sekretów do Git.
