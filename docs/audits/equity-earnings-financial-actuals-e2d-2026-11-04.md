# MacroLens — E2D: oficjalne Actual, status publikacji i waluty

Wykonano **04.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`, `main`,
HEAD **3537b829a6eb84900f9db8e8218d72d9535c8f52**.

**E2D zaimplementowano i sprawdzono w izolacji. Normalnej bazy nie
aktywowano:** nie ma dwóch nowych tabel ani nowych Actual E2D.
Neutralne etykiety są już dostępne na zwykłym Vite. Sekcje 1–10 opisują
implementację bez stagingu, commita i pusha; osobne zamknięcie Git na późniejsze
zlecenie użytkownika opisuje sekcja 11. Nie dodano feedu lub konsensusu.

## 1. Stan wejściowy i ochrona prac

Potwierdzono HEAD, main, pusty indeks, **9 modified / 9 untracked**.
Przeczytano raporty E2B/Activation/E2C i aktywacji E2C, modele, czytniki,
importery, frontend, testy oraz CI. Pełny diff i SHA wszystkich 18 zastanych
plików zapisano w ignorowanym `data/raw/earnings-e2d-2026-11-04/`.
Wszystkie 18 zachowano byte-identycznie: 13 plików użytkownika i pięć
plików przygotowania/zakończonej aktywacji E2C. CalendarPage, Previous week,
globalny CSS i wcześniejsze raporty nie wymagały edycji.

| Chroniony plik | SHA-256 przed = po |
|---|---|
| app/database/activate_earnings_coverage.py | `0f1510699e4d3ed3318459339c3e7a32315b4f9cb11c5be7affac10a2817ffc0` |
| docs/audits/calendar-event-impact-audit-2026-10-30.md | `35e876926cea3c82e3b2df837876d6fb3cabd82ba55db67a4de7ad06159f6f1d` |
| docs/audits/calendar-next-releases-priority-2026-10-29.md | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` |
| docs/audits/calendar-release-day-latency-2026-10-29.md | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` |
| docs/audits/equity-earnings-calendar-source-audit-2026-11-02.md | `a6db1f1a877aacb9bc1980608d20a1d1f1609023d64e1a11ef8699ec659b1434` |
| docs/audits/equity-earnings-coverage-activation-2026-11-04.md | `5795feb9ce77bef8027706ac4b66676050b4a855e86764103f69c60d6eeaa37a` |
| docs/audits/equity-earnings-coverage-activation-rollback-2026-11-04.md | `10fdd162d420159bb3351529ced352165487714bb1816731aa01054344608092` |
| tests/postgres_earnings_coverage_activation_validation.py | `1355d9453e641ec99f42d2589279b6b5e5ac16525cad1235da36bd7ecde33719` |
| tests/test_earnings_coverage_activation.py | `2c60203f5d48cd2f3f68bbfa6f4dda96c514286d5dc6520feff1ecdc05ad0970` |
| README.md | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` |
| frontend/src/brief/EconomyBrief.test.tsx | `bb5c2f6adac6d3c182e893e0d58fa32ff711aee9d7722feaad0d67ad7c598ed5` |
| frontend/src/brief/EconomyBrief.tsx | `017f87c9f580a10c7125e14cb0415f1556c2fcaa2724295f943eef26b82dfcc1` |
| frontend/src/brief/SourceCheckStatus.test.tsx | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` |
| frontend/src/brief/SourceCheckStatus.tsx | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` |
| frontend/src/calendar/CalendarPage.test.tsx | `4e62ca7c6345190a79048dfaa09dd6178e76e141f3e6695607c4eba5edf637d9` |
| frontend/src/calendar/CalendarPage.tsx | `27b776030fb6b63ff915f7e52f3502e5d8defcaa8f5c577e5be7043f16418b91` |
| frontend/src/calendar/calendarAgenda.ts | `57c84376346095d0beb65b3535105cf21dea2221c8705c85d0e004a0d1ece5f0` |
| frontend/src/styles.css | `40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c` |

## 2. Przyczyna statusu Apple i Palantira

E2C dostarczyło wydarzenia i dowody dat, ale nie zaimportowało nowych
raportów finansowych. Dotychczasowa projekcja publikacji korzystała
z tabel finansowych E2B, których sześć dokumentów dotyczy tylko pilotów.
Ogólny dowód daty i opis `facts` nie są bezpiecznym zamiennikiem
ustrukturyzowanej weryfikacji wydania raportu. Stąd puste Actual i status
niezweryfikowanej publikacji także przy istniejącym oficjalnym komunikacie.

Dodano odrębny zapis dowodu rzeczywistego release i jego wartości.
W izolacji AAPL, PLTR i AMD mają teraz **Published · actuals verified**
oraz obie metryki. Nie wykonano UPDATE ich wcześniejszych potwierdzeń dat.
Na normalnej bazie te nowe dowody pozostają nieaktywowane; sam nowy frontend
nie nadaje Apple statusu Published bez danych backendu.

## 3. Model statusów wyprowadzany przez backend

| Kod | PL / EN | Podstawa |
|---|---|---|
| scheduled | Zaplanowano / Scheduled | Zweryfikowana data, brak dowodu release; termin jeszcze nie minął |
| published_pending | Opublikowano · dane w weryfikacji / Published · financials pending | Oficjalny release; brak obu metryk |
| published_complete | Opublikowano · dane zweryfikowane / Published · actuals verified | Release i obie zweryfikowane metryki |
| published_partial | Opublikowano · dane częściowe / Published · partial data | Release i jedna metryka; etykieta wymienia brak EPS lub przychodów |
| date_passed_unconfirmed | Termin minął · publikacja niepotwierdzona / Date passed · release unconfirmed | Termin minął, brak dowodu release |
| unconfirmed | Publikacja niepotwierdzona / Release unconfirmed | Brak potwierdzonej daty; nadal niewidoczne w głównej tabeli |

Stan pochodzi z dowodów SQL i obserwacji, nie z heurystyki frontendu.
Earnings date announcement nie może zawierać Actual lub dowodzić publikacji.
Dokładny czas release może wykazać przekroczenie terminu; approximate,
AMC/BMO i call nie określają rzeczywistej chwili wydania. Dla takich wpisów
przekroczenie dnia sprawdza się konserwatywnie w źródłowej strefie.
Upływ czasu nigdy nie tworzy Published. URL lub sam jego tytuł również nie.

Odpowiedź zawiera kod, powód statusu i `missing_metrics`. Dowody starego E2B
nadal dają poprawną publikację istniejących sześciu raportów. Zmienny czas
kontroli nie jest dodawany do eventu jako pole `as_of`; API ma swój assembled_at.

## 4. Ręczna kontrola wszystkich 27 wydarzeń

Oficjalne źródła otwarto narzędziem WWW **04.11.2026, 09:39–10:08 UTC
(10:39–11:08 PL)**. To kontrola poranna, przed amerykańskimi publikacjami
po zamknięciu sesji. Sprawdzono dokumenty, bieżącą kwartalną kolumnę,
skonsolidowany revenue, raportowany diluted EPS, waluty i standard.
Nie użyto portali finansowych jako źródła wartości.

**23 wydarzenia mają oficjalny dowód rzeczywistej publikacji i pełne
23 pary Revenue/EPS, czyli 46 obserwacji. Zero raportów częściowych.
Cztery mają tylko zweryfikowaną zapowiedź:** ARM i QCOM na wieczór 04.11,
PANW 18.11 i SNOW 02.12. Ich Actual pozostają null. W chwili kontroli
oficjalne strony ARM/QCOM nie dostarczyły nowego release; istniejąca
zapowiedź nie została uznana za wykonanie publikacji. Dla PANW/SNOW termin
był przyszły. Nie jest to twierdzenie o stanie stron po zakończeniu kontroli.

Tabela dotyczy **seeda i importu izolowanego**, nie normalnej macrolens.
Revenue podano w oryginalnej źródłowej skali; EPS w walucie na akcję.

| Ticker | Okres | Oficjalny release | Status | Revenue Actual | EPS Actual | Waluta | Standard | Źródło |
|---|---|---|---|---|---|---|---|---|
| AAPL | Q4 FY2026 | 2026-11-02 | Opublikowano · dane zweryfikowane | 114477 mln | 2.10 | USD | US GAAP | [dokument](https://www.apple.com/newsroom/pdfs/fy2026q4/FY26_Q4_Consolidated_Financial_Statements.pdf) |
| MSFT | Q1 FY2027 | 2026-10-28 | Opublikowano · dane zweryfikowane | 92279 mln | 4.92 | USD | US GAAP | [dokument](https://www.microsoft.com/en-us/Investor/earnings/FY-2027-Q1/press-release-webcast) |
| GOOGL | Q3 2026 | 2026-10-28 | Opublikowano · dane zweryfikowane | 127577 mln | 2.12 | USD | US GAAP | [dokument](https://s206.q4cdn.com/479360582/files/doc_news/2026/Oct/28/attachments/2026q3-alphabet-earnings-release.pdf) |
| META | Q3 2026 | 2026-10-21 | Opublikowano · dane zweryfikowane | 64601 mln | 3.83 | USD | US GAAP | [dokument](https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Third-Quarter-2026-Results/) |
| TSLA | Q3 2026 | 2026-10-21 | Opublikowano · dane zweryfikowane | 28046 mln | 0.22 | USD | US GAAP | [dokument](https://assets-ir.tesla.com/tesla-contents/IR/TSLA-Q3-2026-Update.pdf) |
| AVGO | Q3 FY2026 | 2026-09-02 | Opublikowano · dane zweryfikowane | 29591 mln | 2.68 | USD | US GAAP | [dokument](https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-third-quarter-fiscal-year-2026-financial) |
| AMD | Q3 2026 | 2026-11-03 | Opublikowano · dane zweryfikowane | 13377 mln | 1.46 | USD | US GAAP | [dokument](https://ir.amd.com/news-events/press-releases/detail/1303/amd-reports-third-quarter-2026-financial-results) |
| ORCL | Q1 FY2027 | 2026-09-10 | Opublikowano · dane zweryfikowane | 19345 mln | 1.56 | USD | US GAAP | [dokument](https://investor.oracle.com/investor-news/news-details/2026/Oracle-Announces-Q1-Results-Driven-by-Triple-Digit-Growth-in-Cloud-Infrastructure-Revenues/default.aspx) |
| NFLX | Q3 2026 | 2026-10-20 | Opublikowano · dane zweryfikowane | 12874176 tys. | 0.87 | USD | US GAAP | [dokument](https://ir.netflix.net/files/doc_financials/2026/q3/FINAL-Q3-26-Shareholder-Letter.pdf) |
| MU | Q4 FY2026 | 2026-09-30 | Opublikowano · dane zweryfikowane | 54229 mln | 32.87 | USD | US GAAP | [dokument](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/default.aspx) |
| QCOM | Q4 FY2026 | — (zapowiedź) | Zaplanowano | — | — | — | niezweryfikowany | [dokument](https://investor.qualcomm.com/news-events/press-releases/news-details/2026/Qualcomm-Schedules-Fourth-Quarter-and-Fiscal-2026-Earnings-Release-and-Conference-Call/default.aspx) |
| TSM | Q3 2026 | 2026-10-15 | Opublikowano · dane zweryfikowane | 1494.24 mld | 29.43 | TWD | IFRS; akcja zwykła | [dokument](https://pr.tsmc.com/english/news/3346) |
| ASML | Q3 2026 | 2026-10-14 | Opublikowano · dane zweryfikowane | 11662 mln | 12.93 | EUR | US GAAP; akcja zwykła | [dokument](https://www.sec.gov/Archives/edgar/data/937966/000162828026065813/a2026_10x14xpresentation.htm) |
| ARM | Q2 FY2027 | — (zapowiedź) | Zaplanowano | — | — | — | niezweryfikowany | [dokument](https://newsroom.arm.com/news/arm-announces-earnings-release-date-for-second-quarter-fiscal-year-ending-2027) |
| AMAT | Q3 FY2026 | 2026-08-13 | Opublikowano · dane zweryfikowane | 9115 mln | 3.17 | USD | US GAAP | [dokument](https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-announces-third-quarter-2026-results) |
| LRCX | Q1 FY2027 | 2026-10-21 | Opublikowano · dane zweryfikowane | 8219418 tys. | 2.19 | USD | US GAAP | [dokument](https://investor.lamresearch.com/2026-10-21-Lam-Research-Corporation-Reports-Financial-Results-for-the-Quarter-Ended-September-27%2C-2026) |
| KLAC | Q1 FY2027 | 2026-10-28 | Opublikowano · dane zweryfikowane | 4136 mln | 1.18 | USD | US GAAP | [dokument](https://ir.kla.com/news-events/press-releases/detail/523/kla-corporation-reports-fiscal-2027-first-quarter-results) |
| TXN | Q3 2026 | 2026-10-21 | Opublikowano · dane zweryfikowane | 6055 mln | 2.62 | USD | US GAAP | [dokument](https://www.ti.com/about-ti/newsroom/news-releases/2026/2026-10-21-ti-reports-third-quarter-2026-financial-results-and-shareholder-returns.html) |
| ADBE | Q3 FY2026 | 2026-09-10 | Opublikowano · dane zweryfikowane | 6760 mln | 4.62 | USD | US GAAP | [dokument](https://www.adobe.com/cc-shared/assets/investor-relations/pdfs/01906202/au56y4ter.pdf) |
| CRM | Q2 FY2027 | 2026-08-26 | Opublikowano · dane zweryfikowane | 11345 mln | 4.29 | USD | US GAAP | [dokument](https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx) |
| NOW | Q3 2026 | 2026-10-28 | Opublikowano · dane zweryfikowane | 4106 mln | 0.27 | USD | US GAAP | [dokument](https://newsroom.servicenow.com/press-releases/details/2026/ServiceNow-Reports-Third-Quarter-2026-Financial-Results/default.aspx) |
| PLTR | Q3 2026 | 2026-11-02 | Opublikowano · dane zweryfikowane | 2313411 tys. | 0.44 | USD | US GAAP | [dokument](https://www.sec.gov/Archives/edgar/data/1321655/000132165526000045/a2026q3ex991pressrelease.htm) |
| CRWD | Q2 FY2027 | 2026-08-26 | Opublikowano · dane zweryfikowane | 1470897 tys. | 0.01 | USD | US GAAP | [dokument](https://ir.crowdstrike.com/news-releases/news-release-details/crowdstrike-reports-second-quarter-fiscal-year-2027-financial) |
| PANW | Q1 FY2027 | — (zapowiedź) | Zaplanowano | — | — | — | niezweryfikowany | [dokument](https://investors.paloaltonetworks.com/node/20971/pdf) |
| SNOW | Q3 FY2027 | — (zapowiedź) | Zaplanowano | — | — | — | niezweryfikowany | [dokument](https://www.snowflake.com/en/news/press-releases/fy27-q3-earnings-date-announcement/) |
| IBM | Q3 2026 | 2026-10-21 | Opublikowano · dane zweryfikowane | 17103 mln | 2.30 | USD | US GAAP | [dokument](https://www.sec.gov/Archives/edgar/data/51143/000005114326000093/ibm-20261021xex991.htm) |
| CSCO | Q4 FY2026 | 2026-08-12 | Opublikowano · dane zweryfikowane | 17252 mln | 0.97 | USD | US GAAP | [dokument](https://investor.cisco.com/news/news-details/2026/CISCO-REPORTS-FOURTH-QUARTER-AND-FISCAL-YEAR-2026-EARNINGS/default.aspx) |

Lista brakujących Actual: **ARM, QCOM, PANW, SNOW**. Powodem jest brak
zweryfikowanego wydanego raportu w chwili kontroli; nie uzupełniano wartości
guidance, forecastem lub liczbą z poprzedniego kwartału. NVDA Q3 FY2027,
17.11, nadal zachowuje null Actual i nie należy do nowych 27 raportów.

### Istotne rozróżnienia finansowe

- Alphabet: bieżące dane 2026 są w drugiej kolumnie; diluted EPS **2,12**,
  nie wcześniejsze 2,87. GOOG/GOOGL pozostają jednym emitentem.
- IBM: **2,30** to total diluted EPS; continuing-only 2,31 nie zastępuje
  wyniku całej spółki. Tesla ma reported diluted **0,22**, nie non-GAAP.
  Meta **3,83** uwzględnia raportowany koszt, bez zastąpienia adjusted EPS.
- TSM: **IFRS/TIFRS, TWD**, 29,43 na akcję zwykłą. Nie zaimportowano
  dolarowego EPS na ADR, nie wykonano FX lub przeliczenia ADR.
- ASML: źródłowa prezentacja raportuje **US GAAP, EUR**, diluted EPS
  12,93 na akcję zwykłą. Nie oznaczono go IFRS na podstawie kraju emitenta.
  IR zwróciło 403; użyto oficjalnej prezentacji wyników w SEC EX99.2.
  Nie obchodzono ograniczenia. Dokładny dzień końca okresu nie został
  ustalony z przejrzanego dokumentu: `period_end=null`, bez zgadywania.
- NFLX/LRCX/PLTR/CRWD podają revenue w tysiącach, TSM w miliardach,
  pozostałe pozycje w milionach. Source precision jest przechowywane.
  Nie mieszano trzech miesięcy z YTD/TTM lub segmentów z konsolidacją.

Poza jawnym brakiem dnia ASML końce opublikowanych okresów zapisano
w ręcznym ledgerze JSON. Dla zapowiedzi brakujące końce okresów pozostają
null. Nowe fakty nie nadpisują `earnings_periods` ani historii E2C.

## 5. Minimalne rozszerzenie i oddzielny importer

DDL dodaje tylko `earnings_report_documents` i
`earnings_report_observations`, ich constraints/indeksy, funkcję
`earnings_report_guard()` i cztery triggery. Nie wykonuje ALTER E2A/B/C
lub makro. Dokument oddziela zapowiedź od release, przechowuje emitenta,
okres, źródło, date-only release, verified_on, wersję i podstawę raportowania.
Obserwacja ma źródłową i kanoniczną wartość NUMERIC, jednostkę, walutę,
standard, rodzaj akcji, precision i metodologię.

Złożone FK i guard pilnują spółki/okresu/eventu/dokumentu. SQL kontroluje
skalowanie, skończoność, jednostkę, walutę, diluted, historię i zgodność
podstawy wartości z dokumentem. UPDATE, DELETE i TRUNCATE są blokowane.
Wersja wymaga dokładnego poprzednika i jawnego correction_reason;
release nie może zostać cofnięty do zapowiedzi. INSERT wersji blokuje event.
Znany wcześniejszy fingerprint nie reaktywuje starej obserwacji.

`app/earnings_reports.py` jest odrębnym importerem bez HTTP. Waliduje całą
partię przed transakcją, używa dotychczasowego locka 726530020, Decimal,
rejestru CIK/FY/Q/label i ręcznego ledgeru finansowego. Odrzuca innego
emitenta/hosta/okres, basic/non-GAAP, niespójny standard, ADR, jednostkę,
niepoprawną skalę, forecast i duplikaty okresu w partii. Zero i ujemne EPS
są dozwolone. Nie usuwa allowlist trzech firm z importerów E2A/E2B.

CLI i initializer odrzucają bazy poza własnym prefiksem
`macrolens_earnings_e2b_e2c_e2d_`. Przy zastanym schemacie initializer
wymaga pełnej zgodnej sygnatury; częściowy lub obcy stan jest odrzucany.
Nie dodano ścieżki aktywacji normalnej bazy.

Fingerprint jest hashem lokalnych metadanych, nie bajtów komunikatu IR.
Captured_at oznacza czas lokalnego zapisu; verified_on to data ręcznego
odczytu. Nie utworzono fikcyjnych fetched_at, first_seen, HTTP receipts,
SEC accession lub RAW hash. Nie kopiowano pełnych komunikatów do repo/RAW.
Ręczny capture nie dowodzi first print ani kompletnej historii restatement.

## 6. Czytnik, API i frontend

Istniejący czytnik po E2B dołącza E2D w tej samej transakcji
REPEATABLE READ READ ONLY. GET nie wykonuje DDL/importu/HTTP/source checks.
Brak obu nowych tabel daje `report_store_status=not_activated`; częściowy
store powoduje kontrolowany błąd. Nowe `reported_eps_actual` obsługuje
raportowane diluted EPS obu standardów. IFRS nie trafia do dawnego pola
`gaap_diluted_eps_actual`. Decimal pozostaje tekstem w JSON.

Najnowsza wersja dokumentu jest spójnym snapshotem dowodów; brakująca
metryka nie dziedziczy po cichu wartości starego dokumentu. Historia jest
zachowana. Stare kontrakty i odczyt istniejących sześciu raportów działają.

Nagłówek: **Wszystkie spółki · Dane raportowane przez emitentów**;
kolumna **EPS raportowany**, Actual / Prognoza. Waluta jest przy wartości,
brak Actual daje samo `—`. Szczegóły pokazują emitenta/CIK/kwartał,
okres i release/date precision/call, powód statusu, reported diluted
US GAAP lub IFRS, akcję zwykłą/ADR, oryginalną jednostkę, źródło,
weryfikację i historię. Techniczne UUID nie zastępują źródła.

Forecast pozostaje null/`—`; brak surprise, beat/miss lub guidance jako
konsensusu. Nie zmieniono CalendarPage, makro/hooka, ukrywania undated,
filtrów, wspólnych nagłówków dat lub braku checkboxów. Mobile ma wewnętrzny
scroll tabeli; Escape i powrót fokusu pozostają obsługiwane.

## 7. Wykonane testy

| Kontrola | Końcowy wynik tego etapu |
|---|---|
| Pełny backend offline | **1336 passed, 42,89 s** |
| Pełny frontend offline, Node 22.23.4 | **672 passed / 32 pliki, 24,22 s** |
| TypeScript noEmit | passed, 5,05 s |
| Production build | passed, 4,53 s; największy chunk **407,04 kB**, próg bez zmian |
| Nowy PostgreSQL 17 E2D | passed |
| Wszystkie wcześniejsze PostgreSQL | **10/10 passed**, nowe lokalne przebiegi |
| Chrome, rzeczywiste izolowane API/SQL | **359 kontroli / 24 odpowiedzi API 200**, zero JS/console errors/503 |
| Dodatkowe bezpośrednie API | **29 GET HTTP 200**, 27 szczegółów i dwie listy |
| Normalna baza read-only | wszystkie **21 hash/count** i schematy identyczne |
| Chronione pliki / whitespace / indeks | passed |

Backend ma 36 nowych przypadków ponad 1300; frontend osiem ponad 664.
Testy obejmują wszystkie stany publikacji, release vs announcement,
call/termin, zero/ujemne EPS, null, GAAP/IFRS, diluted vs basic, ADR,
jednostki/waluty, błędny FY/CIK/skalę, brak forecast i no-HTTP.

Nowa rzeczywista walidacja SQL sprawdziła pending → partial → full,
27 dokumentów i 46 obserwacji, idempotencję, wersje i nieodtwarzanie starej
wersji, append-only, FK/CHECK, obcy/partial schemat, rollback całego
DDL+seeda po rzeczywistym błędzie SQL oraz całej późniejszej partii.
Przetestowano prawdziwe GET listy/szczegółów przez TestClient na SQL,
bez podstawiania odpowiedzi. Pełne stare 21 tabel pozostało identyczne.

Dziesięć regresji: Empire, FT900, BEA Direct, BEA release/R3, E2A,
E2A Activation, E2B, E2B Activation, E2C i E2C Activation.
Aktywatory wykonywały prawdziwe syntetyczne backup/restore/fresh/upgrade.
Używały własnych losowych baz, kontrolnych nazw i guarda publisher HTTP.
Do wymaganej walidacji E2C Activation tymczasowo zmieniono nazwę wyłącznie
własnego kontenera, potem przywrócono ją. Nie zmieniano guardów lub bazy
normalnej. Nie uruchamiano nowego GitHub Actions i nie zmieniono workflow.

Chrome: production preview **4195**, API **8025**, PostgreSQL **55467**,
EN/PL, 1366/390 px, bez fixture odpowiedzi. API wrapper dodawał tylko CORS
własnego preview. Wymuszono read-only i lease 726530019 wyłącznie na izolacji,
aby stary hook nie uruchomił makroimportera. Wszystkie **23 tabele** tej bazy
zachowały pełne hash/count przed/po UI. Makro było syntetyczne, nie stanowi
nowego pomiaru żywej publikacji makro. Nie kopiowano normalnych danych.

Potwierdzono wszystkie 23 pary i cztery Scheduled z null, Apple/PLTR/AMD,
TSM TWD/IFRS i ASML EUR/US GAAP, sześć starych raportów, przyszłą NVDA
22:20 orientacyjne / call 23:00, INTC 21:00+ / 22:00 i AMZN nieznany
release / call 22:00. Przeszły Makro/Earnings/Wszystkie, zakresy, źródła,
Escape/focus, jeden nagłówek daty, brak zbędnego GET Earnings, checkboxów,
undated, overflow całej strony i żądań wydawców. Obejrzano desktop EN
i mobile PL; nie deklaruje się pełnego audytu WCAG.

W pierwszych próbach nowy test obecności EPS ujawnił użycie truthiness
zamiast jawnego None; poprawiono przed pełnym przebiegiem. Test UI miał
niejednoznaczny selektor IFRS, doprecyzowany bez pomijania asercji.
Helper wydruku wymagał jawnego UTF-8 zamiast Windows cp1250; helper preview
raz uruchomiono z błędnego cwd. Pierwszy pomocniczy odczyt normalnego API
trafił na poprzedni worker przed autoreload; po przeładowaniu potwierdzono
nowy kontrakt not_activated. Nieudanych prób nie zaliczono jako sukcesów.
Nie zwiększano timeoutów ani nie osłabiano testów lub guardów.

## 8. Normalna baza pozostała bez zmian E2D

Każde połączenie diagnostyczne miało wymuszone read-only. Ponownie
potwierdzono localhost:5432/macrolens, macrolens, OID **16384**, klaster
**7682090371041935398**, PostgreSQL 17. Pełne binary COPY uporządkowane po PK
porównano przed, po smoke i po bezpośrednich GET: **21 tabel / 2 925 154
rekordy, wszystkie wartości i timestampy identyczne**. Obie sygnatury
schematów również identyczne. Brak obu tabel E2D potwierdzono w SQL.

| Tabela | Rekordy przed = po | SHA-256 przed = po |
|---|---:|---|
| alfred_backfills | 15 | `e3b943e5151b7ddda3a7e2a7fe355528bb266f3630344728f9429ce59497b65e` |
| computed_features | 1048238 | `5640ff0f6589eeb0e3169274556535d437579de7afb70dd6419d9fed9e4f77df` |
| earnings_companies | 53 | `b92057648ce360869268fe7abdeda36c3b3644edf9ca06ef9344faed73e1873c` |
| earnings_company_aliases | 55 | `e216ffddfe8a270f6bb0d0480ccef8d8abfcd83d64e06fd59dff5bf560e34806` |
| earnings_date_confirmations | 66 | `d37b9798d60e4c5b26b591dd6ae231fe6fb564039dd6978429d982e3aeee8e29` |
| earnings_events | 37 | `def7c57e19a5f99aeb914c933e27299f0c316dd209d87ed1cabecc01a4afa46a` |
| earnings_financial_documents | 6 | `306598e20cedde0ddc8b0e5d74d8e55c34ed096c079f6eb6b3c9203553d839e5` |
| earnings_financial_observations | 12 | `c7b17b5730bbb87cbc98185d7910bce6b63c92ca51624d0cfd757b76f0197308` |
| earnings_periods | 37 | `f6702bca1c268484a59f74818aa10112991d80f8c9aa6e466a57455763dd746e` |
| earnings_source_evidence | 40 | `b85460b06a85c7ecf873f9ba83f5610520ad389f3fcf1f883be4cd5fc417f64e` |
| economic_releases | 18 | `9fad16df8f5a9011ff2a46915e956e7c964e57a4b9ce9e7e3f190d3b38c14cc9` |
| ism_documents | 22 | `70de199f658a1528704162235a2d365e92fbc7e84aa5116d998f386e4fa70efd` |
| ism_observations | 264 | `a76ed493a80e36cca32c566636565544e180f3a4a590d411ed21f44734892ab3` |
| observation_vintages | 1873249 | `784778cb76ce1ab8bec7a89da26164c405efda1be973b4ee47c61f5b4eee7e6f` |
| overview_publications | 8 | `ce662da435f23984a9d9ed4bacb96783f87f68ec7adfbdb4a6e0f6758f1b11ba` |
| overview_refresh_state | 1 | `99768b6b2f2b6a2f48410451a0452939bff588969410d5d4125309807e924445` |
| publisher_documents | 26 | `c5217a07641f97542e57b33f83cc81474722a08b0f7b8f23a7ea86ba0289e634` |
| release_dates | 804 | `3385a38806129a73cf1fbac215e38c5fb3242f8d672e8eb039b1329adcd43746` |
| series | 58 | `f4cd1add01658ea0d16892004ddf7ef7cce89103de274142672a58f38c1b9ac0` |
| series_release_map | 45 | `e5eb3c6545828d89d6165b879d43305da0588c01ded45618a3731a05235ece84` |
| source_check_runs | 2100 | `c625a515cd9d338a1ae38cea15f73168c28c1f43c3bcdf332e0fdfb2d59a057e` |

Zachowane: 53 companies, 55 aliases, 37 periods/events, 40 evidence,
66 confirmations i sześć dokumentów/12 obserwacji E2B. Nie wykonano
normalnego DDL, importu, aktywacji lub rollbacku. Nie zatrzymano zwykłego
backendu/Vite. Uvicorn autoreload odczytał nowy kod, a bezpośredni normalny
GET zwraca HTTP 200 i not_activated. Zwykły Vite zawiera neutralne etykiety;
nowe 23 pary i dowody publikacji działają **wyłącznie w izolacji**.

Nie zmieniano R1–R3, K2, Overview, FRED/ALFRED, BEA, harmonogramów,
interwałów lub konfiguracji źródeł. Nie zakładano normalnego lease.
Pozostawiono działające API 8000 i Vite 5173 do codziennego korzystania.

## 9. Późniejsza aktywacja — propozycja, niewykonana

Lokalne `activation-proposal.json` ma **ready_for_apply=false**.
Hash kanoniczny:
`bf5e25c515e7bcbbacca1e045e0a03fc8521548d9c7e93858558272bd100a096`.
To propozycja zakresu, nie gotowy plan/token apply i nie zgoda na zapis.
Nie używa się wcześniejszych zgód E2B/E2C.

1. Osobno uzgodnić okno serwisowe i potwierdzić rzeczywisty target,
   brak procesów zapisujących oraz dwa stabilne pełne odczyty wszystkich
   21 tabel. Zatrzymać zidentyfikowany backend, pozostawiając PostgreSQL.
2. Wykonać świeży pełny pg_dump custom, manifest celu/SHA/rozmiar/TOC
   oraz pełny restore do własnej bazy z porównaniem danych i katalogów.
   W E2D nie wykonywano nowego backupu normalnych danych; wcześniejszy
   backup E2C nie jest aktualnym zabezpieczeniem przyszłego etapu.
3. Przygotować i przetestować osobny runner prepare/apply: dokładny target,
   zamrożone artefakty, wzorzec wykonany na PG17, jedna SERIALIZABLE
   transaction, locki 726530019/726530020, jawne limity lock/statement.
   DDL i seed muszą razem podlegać rollbackowi przy błędzie.
4. Przed pierwszym zapisem uzyskać osobną wyraźną zgodę na **nowy kompletny
   plan i pełny hash** po backup/restore. Zmiana danych/artefaktów/target
   zatrzymuje operację; bez automatycznej podmiany zatwierdzonego planu.
5. Planowany zakres: dwie nowe tabele z ochroną; **27 dokumentów** (23 release
   i cztery zapowiedzi) oraz **46 obserwacji**. Bez nowych firm/eventów,
   bez UPDATE E2A/B/C, z zachowaniem starych sześciu dokumentów/12 miar.
6. Po COMMIT, przed restartem, sprawdzić pełne pierwotne 21 tabel, schemat,
   wszystkie nowe wiersze i idempotencję bez nowych wersji/timestampów.
   Potem wznowić normalne API/Vite i wykonać rzeczywiste API/Chrome.
   Cofnięcie po COMMIT wymaga osobnej decyzji i sprawdzenia późniejszych
   zależności; bez automatycznego rollbacku, CASCADE lub nadpisania bazy.

Nie rozwiązano podstawy automatycznego feedu, retencji pełnych dokumentów
lub konsensusu i nie dodano tych funkcji. Ręczne publiczne fakty nie są
deklaracją licencji na pełne archiwum/redystrybucję dokumentów.

## 10. Pliki, sprzątanie i końcowy Git

E2D obejmuje **11 plików**, cztery modyfikacje i siedem nowych:

- app/earnings.py
- app/earnings_reports.py — nowy
- app/database/earnings_report_schema.sql — nowy
- config/earnings_reports_manual.json — nowy
- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/earningsFinancialPresentation.ts
- frontend/src/calendar/earningsTypes.ts
- frontend/src/calendar/EarningsReports.test.tsx — nowy
- tests/test_earnings_reports.py — nowy
- tests/postgres_earnings_report_validation.py — nowy
- docs/audits/equity-earnings-financial-actuals-e2d-2026-11-04.md — ten raport

Wszystkie 18 początkowych SHA zachowano. Zależności, lockfile, CI,
globalny CSS i chronione pliki pozostają bez edycji. Końcowo **13 modified /
16 untracked**, indeks pusty, main i HEAD bez zmian. Nie wykonano stagingu,
commita, pusha, resetu, clean, amend lub globalnego formatowania.

Własne API/preview/Chrome zakończono; izolowany lease zwolniono w finally,
a własne losowe bazy usunięto. Po sprawdzeniu pełnego ID
`23e6f9e0f7a8a8f8f6cb80aa8c761adad033e71e08914e9c3aa705aebcb13833`,
nazwy i etykiety earnings-e2d-2026-11-04 usunięto wyłącznie własny
`macrolens_earnings_e2d_20261104` i anonimowy wolumen. Przed usunięciem
pozostały tylko własne control/postgres/template. Normalny macrolens_postgres,
backend i Vite pozostały poza sprzątaniem. Brak diagnostycznych blokad.

Manifesty, pełny diff, propozycja, logi, helpery, referencja schematu
i zrzuty są ignorowane w data/raw. Końcowe logi pełnych testów są również
w ignorowanym `data/raw/earnings-close-2026-11-03/e2d-final-*`.
Nie dodano sekretów lub pełnych komunikatów do zakresu Git.

## 11. Zamknięcie E2C Activation i E2D w Git — 04.11.2026

Na osobne zlecenie potwierdzono początkowy HEAD/main
3537b829a6eb84900f9db8e8218d72d9535c8f52, **13 modified / 16 untracked**
i pusty indeks. Zapisano nowy manifest wszystkich 29 plików i pełny diff
w ignorowanym `data/raw/earnings-e2d-close-2026-11-04/`. Chronione 13 plików
użytkownika zachowano byte-identycznie i wyłączono z obydwu commitów.

Pierwszy commit **f3790400b18e297b8344d60537d21ad3c9d287a4**,
**Add safe earnings coverage activation**, obejmuje dokładnie pięć
plików E2C Activation i minimalny krok ci.yml, razem sześć plików.
Nie zmieniono produkcyjnego aktywatora lub rollbacku. Test przyjmuje
także service ID Actions pod bramką roli CI, kontrolnej bazy i loopback.
Pierwsza dokładna kopia indeksu miała **340 zgodnych blob IDs** i nie
zawierała E2D lub wcześniejszych prac użytkownika.

Drugi commit **Add verified earnings actuals and publication statuses**
obejmuje dokładnie 11 plików E2D z sekcji 10 i minimalny krok ci.yml,
razem **12 plików**. CI ma teraz **11 nazwanych walidacji PostgreSQL**,
z zachowaniem wszystkich dziewięciu wcześniejszych oraz E2C Activation.
E2D korzysta z własnej nazwy kontrolnej, tworzy losową bazę i nie łączy
się z normalną macrolens. Zależności, lockfile, uprawnienia i timeouty
workflow pozostają bez zmian. Actionlint przeszedł.

### Ponowny przegląd finansów i kodu

Ponownie odczytano pierwotne źródła MU, NFLX, LRCX, PLTR, TSM i ASML
z tabeli sekcji 4. Potwierdzono odpowiednio revenue **54229 mln USD,
12874176 tys. USD, 8219418 tys. USD, 2313411 tys. USD, 1494.24 mld TWD
i 11662 mln EUR** oraz reported diluted EPS **32.87, 0.87, 2.19, 0.44,
29.43 i 12.93**. TSM pozostaje TIFRS/IFRS na akcję zwykłą, a ASML US GAAP
na akcję zwykłą, bez zmiany null period_end. Nie znaleziono sprzeczności
wymagającej zmiany liczb; JSON ma identyczne bajty względem wejścia.

Kontrola całego seeda potwierdziła 27 dokumentów, w tym 23 release i cztery
zapowiedzi, 23 pełne pary / 46 miar, zero częściowych i brak Actual
ARM/QCOM/PANW/SNOW na moment wcześniejszego porannego odczytu. Nie dodawano
nowych raportów, forecast, surprise lub beat/miss. Przejrzano statusy,
append-only, aktualne wersje, jednostki/skalowanie, FK/okresy/CIK, brak HTTP
i projekcję starego E2B. Kod produkcyjny zachowano bez zmian zamknięcia.

Jedyna korekta testu E2D ustala jawny czas porannego audytu przy sprawdzaniu
Scheduled w rzeczywistym teście SQL. Przyszła data uruchomienia CI nie
może zmieniać historycznej asercji na Date passed. Produkcyjny zegar nadal
działa normalnie; release nigdy nie wynika z samego upływu terminu.

### Nowe wyniki staging-only

| Kontrola | E2C Activation — pierwszy indeks | E2D — drugi indeks |
|---|---|---|
| Pełny backend offline | **1300 passed, 55,43 s** | **1336 passed, 54,53 s** |
| Pełny frontend offline, Node 22.23.4 | **662 passed / 31 plików** | **670 passed / 32 pliki** |
| TypeScript noEmit | passed | passed |
| Production build | passed, 4,53 s | passed, 3,38 s |
| Największy chunk | **407,04 kB** | **407,04 kB** |
| Wszystkie PostgreSQL | **10/10 passed** | **11/11 passed** |
| Actionlint / staged i working diff --check | passed | passed |

Druga kopia zawiera **347 zgodnych blob IDs**, HEAD po pierwszym commicie
plus tylko staged E2D. Chronione pliki pochodzą w niej z HEAD, nie z working
tree. Różnica dwóch testów frontendowych względem 672 z sekcji 7 pochodzi
z niezacommitowanego CalendarPage.test użytkownika; nie usunięto testów
i nie dołączono jego zmian dla wyrównania liczników.

Wszystkie walidacje PostgreSQL wykonano na własnym PostgreSQL 17,
loopback **55469**, losowych bazach i z guardem publisher HTTP.
Przeszły prawdziwe backup/restore, fresh/upgrade, SQL rollback, bramki,
idempotencja, E2A/B/C i E2C Activation. Nowe E2D potwierdziło 27/46,
pending/partial/full, rewizje i stale captures, FK/CHECK/append-only,
rzeczywisty API/SQL oraz pełne zachowanie 21 wcześniejszych tabel.

Pierwszy helper PostgreSQL nie przeszedł lokalnego sprawdzenia ownership
Git w eksportowanej kopii. Dodano wyłącznie process-local safe.directory
tej kopii i wykonano cały zestaw ponownie z kodem 0. Nie osłabiono guarda
HTTP, timeoutów lub asercji. Nieudanej próby nie zaliczono jako sukcesu.

### Chrome dokładnego indeksu i normalna baza

Production preview **4197**, rzeczywiste API **8027**, własny PostgreSQL
**55469**, wyłącznie kod drugiego indeksu. Nowy wynik: **359 kontroli /
35 zakończonych odpowiedzi API 200**, zero JS/console errors i HTTP 503.
Przeszły EN/PL, 1366/390 px, wszystkie stany i wartości objęte helperem,
Apple/PLTR/AMD, cztery Scheduled, brak przedwczesnej NVDA, stare E2B,
GAAP/IFRS/TWD/EUR/USD, źródła, release/call, Escape/focus, Makro/Earnings/
Wszystkie, zakresy, brak checkboxów/undated i zbędnego refetch, wewnętrzny
scroll telefonu oraz brak overflow całej strony. Obejrzano desktop EN
i mobile PL. Nie deklaruje to pełnego audytu WCAG.

Nie podstawiano odpowiedzi; wrapper dodawał tylko CORS własnego preview.
API było read-only, lease znajdował się wyłącznie na izolacji. Pełne dane
**23 tabel** izolacji przed/po UI są identyczne. Nie było żądań wydawców.

Normalne localhost:5432/macrolens sprawdzono tylko read-only: ta sama rola,
OID 16384, klaster 7682090371041935398, **21 tabel / 2 925 200 rekordów**.
Pełne hash/count i obie sygnatury są identyczne między początkiem i końcem
tego zamknięcia. Liczba różni się od sekcji 8, bo zwykła aplikacja działała
między etapami; stan wejściowy zamknięcia odczytano na nowo. Nadal 53 firmy,
37 eventów, sześć dokumentów/12 obserwacji E2B i **brak obu tabel E2D**.
Nie wykonano normalnego DDL/importu/apply/rollbacku ani restartu aplikacji.

### Granice commitów i zakończenie

Przejrzano cały staged diff, ścieżki, jednostki, sekrety i whitespace.
Żaden z 13 chronionych plików, .env, data/raw, logów, zrzutów, helperów
lub kopii nie jest wystawiony. Wszystkie 13 hashy nadal zgadza się
z manifestem wejścia. Po walidacji zmieniono jedynie ten raport i jego
staging; kod odpowiada przetestowanej kopii indeksu.

Własne API/preview/Chrome zakończono i zwolniono izolowany lease; własne
losowe bazy usunięto. Usunięto wyłącznie własny kontener testowy z wolumenem
po kontroli pełnego ID
`c5cf5b9109dd2bd726250f64904fee455ca820c2508f6a21d748b4da946701a1`,
etykiety i braku pozostawionych baz testowych. Normalny
macrolens_postgres, backend 8000 i Vite 5173 pozostają poza sprzątaniem.

Pełny SHA drugiego commita, wynik zwykłego pusha i URL oraz zakończone
wyniki trzech jobów Actions będą w odpowiedzi końcowej po uzyskaniu wyników.
Nie tworzy się dodatkowego commita dla metadanych po pushu i nie deklaruje
sukcesu CI na podstawie lokalnych testów. Po obu commitach pozostaje
**9 modified / 4 untracked**, indeks pusty, wszystkie wcześniejsze prace
użytkownika zachowane. Bez amend, force push, resetu lub clean.

E2D nadal nie jest aktywne w normalnym PostgreSQL. Propozycja z sekcji 9
pozostaje ready_for_apply=false; wymaga osobnego przygotowania runnera,
okna serwisowego, świeżego backup/restore i wyraźnej zgody na nowy plan.
Nie rozpoczęto E2E, automatycznego feedu lub dodawania nowych firm.
