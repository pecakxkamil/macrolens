# MacroLens — E2D Activation: plan do osobnego zatwierdzenia

Przygotowano **04.11.2026, Europe/Warsaw**, `C:\Projects\macrolens`,
`main`, HEAD **94526c9cf0422dde041c69fd4fdec21549a8b39e**.

**Aktywowano E2D 04.11.2026 w normalnej localhost:5432/macrolens:
apply=created, ponowienie=already_initialized.** Sekcje 1–13 opisują
przygotowanie i stan przed zgodą; wykonanie po wyraźnym zatwierdzeniu
tego samego pełnego hasha opisuje sekcja 14. Backend wznowiono, dotychczasowy
Vite pozostał uruchomiony. Bez stagingu, commita i pusha.

## 1. Stan wejściowy, dokumentacja i ochrona

Potwierdzono HEAD, main, **9 modified / 4 untracked**, pusty indeks.
Przejrzano pełny zastany diff, E2D i zamknięcie, E2C Activation/rollback,
E2B Activation/rollback, dotychczasowe aktywatory, SQL, czytniki i importer.
Zapisano `baseline.json` i `before.diff` w ignorowanym
`data/raw/earnings-report-activation-2026-11-04/`.
Wszystkie 13 wcześniejszych plików zachowano byte-identycznie.
Nie edytowano wcześniejszych aktywacji, danych E2D, UI, API, CI lub zależności.

| Chroniony plik | SHA-256 przed = po |
|---|---|
| README.md | `7c6428c8c202c2c231dd8f7d9fc3d0e77fdfdafa790a987d3b9213227feeba2b` |
| frontend/src/brief/EconomyBrief.test.tsx | `bb5c2f6adac6d3c182e893e0d58fa32ff711aee9d7722feaad0d67ad7c598ed5` |
| frontend/src/brief/EconomyBrief.tsx | `017f87c9f580a10c7125e14cb0415f1556c2fcaa2724295f943eef26b82dfcc1` |
| frontend/src/brief/SourceCheckStatus.test.tsx | `bf0be0ae24a70e6120df2195051d79c21d2a0cc3e58533468c4077e89031fddf` |
| frontend/src/brief/SourceCheckStatus.tsx | `65eb0b5c2e8e8d4211ddc443eff22ff43d9cf9c333d0856483401236310c5900` |
| frontend/src/calendar/CalendarPage.test.tsx | `4e62ca7c6345190a79048dfaa09dd6178e76e141f3e6695607c4eba5edf637d9` |
| frontend/src/calendar/CalendarPage.tsx | `27b776030fb6b63ff915f7e52f3502e5d8defcaa8f5c577e5be7043f16418b91` |
| frontend/src/calendar/calendarAgenda.ts | `57c84376346095d0beb65b3535105cf21dea2221c8705c85d0e004a0d1ece5f0` |
| frontend/src/styles.css | `40ec6e96a1828123d7f368c13ca4475c4c49e8213096309cd3cfd2083d5d545c` |
| docs/audits/calendar-event-impact-audit-2026-10-30.md | `35e876926cea3c82e3b2df837876d6fb3cabd82ba55db67a4de7ad06159f6f1d` |
| docs/audits/calendar-next-releases-priority-2026-10-29.md | `e5dfec193642670d7a50a687f758e423580074b3a29b24b67ead0b3c5a86d839` |
| docs/audits/calendar-release-day-latency-2026-10-29.md | `e447b3616e0d6813fe873186a753fc1a8bb8bd41bcd7d98246161816d0dc719b` |
| docs/audits/equity-earnings-calendar-source-audit-2026-11-02.md | `a6db1f1a877aacb9bc1980608d20a1d1f1609023d64e1a11ef8699ec659b1434` |

## 2. Rzeczywisty cel i kontrolowane okno

| Pole | Potwierdzona wartość |
|---|---|
| Host / port | localhost / 5432 |
| Baza / rola | macrolens / macrolens |
| OID | 16384 |
| Identyfikator klastra | 7682090371041935398 |
| PostgreSQL | 17 |
| Kontener normalnej bazy | macrolens_postgres |
| Read-only odczytów / prepare | on |

Zidentyfikowano launcher **18828**, reloader **18088** i worker **584**,
uruchomione jako `python -m uvicorn app.api.main:app --reload`.
Z rzeczywistego workera odczytano tylko DB_HOST/PORT/NAME/USER i cwd:
localhost/5432/macrolens/macrolens, C:\Projects\macrolens.
Porównano je z niezależnym SQL/pg_control_system. Nie wypisano hasła lub .env.

Przed pierwszym snapshotem potwierdzono brak innych klientów SQL i zatrzymano
wyłącznie ten sprawdzony, bezczynny zestaw procesów Uvicorn. Nie zatrzymano
PostgreSQL lub obcych procesów. **Vite PID 15772** na localhost:5173 pozostał
uruchomiony; sam Vite nie zapisuje do SQL. Szczegóły są w maintenance.json,
processes-before.json i backend-identity.json. Nie zmieniano konfiguracji
R1–R3, interwałów, źródeł, lease lub advisory locks.

## 3. Stabilność wszystkich danych przed planem

Dwa niezależne połączenia REPEATABLE READ READ ONLY dały identyczny stan.
Wspólny snapshot do pg_dump i końcowy odczyt po testach są również zgodne:
**21 tabel / 2 925 246 rekordów**. SHA-256 pochodzi z pełnego binary COPY
uporządkowanego po PK i obejmuje wartości oraz timestampy. To nie statystyki
przybliżone lub samo count. Nie stwierdzono niezależnego aktywnego writera,
innych klientów SQL lub advisory locks w normalnej bazie.

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
| overview_publications | 8 | `32e984bd8a71875cab9a671bc33b6e3f4a768ed2f93756589968a0b2a8ad674c` |
| overview_refresh_state | 1 | `bbd11fb679cf35bee8d4d6486e33da0fb7ae30efb91462574ee118dae73b16ef` |
| publisher_documents | 26 | `c5217a07641f97542e57b33f83cc81474722a08b0f7b8f23a7ea86ba0289e634` |
| release_dates | 804 | `3385a38806129a73cf1fbac215e38c5fb3242f8d672e8eb039b1329adcd43746` |
| series | 58 | `f4cd1add01658ea0d16892004ddf7ef7cce89103de274142672a58f38c1b9ac0` |
| series_release_map | 45 | `e5eb3c6545828d89d6165b879d43305da0588c01ded45618a3731a05235ece84` |
| source_check_runs | 2192 | `0d89c6e158514e5411294dec848ec4dddcef04958d942f7459fc1c688ce97b20` |

Pierwotne osiem tabel Earnings ma pełną projekcję wierszy z ID, dowodami,
datami i historią: `existing-data-manifest.json`, SHA-256
`117085b176552082ace74bbe336aa8455674d5ac6d485050de0b4139732c9562`. Te same kompletne wiersze są osadzone w planie.
Sześć dokumentów i 12 obserwacji E2B zachowano. Normalnie nie istnieją
earnings_report_documents, earnings_report_observations ani earnings_report_guard().
Nie ma częściowego E2D lub kolizji z wykonywanym wzorcem schematu.

Liczba rekordów różni się od wcześniejszego zamknięcia E2D wskutek działania
zwykłego makro między sesjami. Nowy stan ustalono po zatrzymaniu backendu;
nie ignorowano żadnej różnicy wewnątrz tego przygotowania.

## 4. Świeży pełny backup i pełne odtworzenie

Kopia: `data/raw/earnings-report-activation-2026-11-04/macrolens-before-reports-2026-11-04.dump`.

| Kontrola | Wynik |
|---|---|
| pg_dump custom / PGDMP | kod 0; cała baza, --no-owner --no-acl |
| Rozmiar | **30900982 B** |
| SHA-256 | `ee7f251e951f06fe5f87cd8df628d700993c201593c5fd332a1758eebf574ec6` |
| TOC pg_restore --list | kod 0 |
| Pełny pg_restore | kod 0; --exit-on-error --single-transaction --no-owner --no-acl |
| Odtworzone dane | **21 tabel / 2 925 246 rekordów**, wszystkie hash/count identyczne |
| Katalogi | identyczne kolumny, constraints/FK, indeksy, funkcje i triggery |
| Niezwalidowane constraints | **0** |

Źródłowe połączenie było REPEATABLE READ READ ONLY. pg_dump korzystał
z tego samego pg_export_snapshot i PGOPTIONS wymuszającego read-only.
Nie zakładano diagnostycznego lease. Nie użyto dawnej kopii E2B/E2C.
Manifest wiąże kopię z rzeczywistym hostem/portem/bazą/rolą/OID/klastrem,
rozmiarem, hashem i wszystkimi snapshotami. Dowód pełnego restore:
`restore-validation.json`, SHA-256 **`19837716f87b2108e627eeb7ccd8c94ffc50ce671cbbd5d86a3904c87a970196`**.

Restore wykonano wyłącznie na osobnym PostgreSQL 17, loopback **55471**,
kontenerze macrolens_reports_activation_20261104. Owner/ACL nie były
przenoszone; porównanie obejmuje strukturę i pełne dane. Zapisywano faktyczny
identyfikator odtworzonej bazy zwrócony przez PostgreSQL, także skrócenie
pomocniczej długiej nazwy do 63 znaków. Baza kopii została usunięta po
zakończeniu testów; dowód potwierdza owned_database_removed=true.
Nigdy nie odtwarzano danych do normalnej macrolens.

## 5. Dokładny zakres przyszłego apply

Jedyny DDL to zatwierdzony E2D `earnings_report_schema.sql`: dwie nowe
tabele, ich constraints/indeksy, funkcja earnings_report_guard() i cztery
triggery append-only. Nie ma ALTER starych tabel, CASCADE, nowych firm,
aliasów, okresów, wydarzeń lub zmian dat. Wykonane katalogi przed/po
potwierdzają wyłącznie dodanie tych obiektów.

| Tabela | Teraz | Po osobno zatwierdzonym apply |
|---|---:|---:|
| earnings_companies | 53 | 53 |
| earnings_company_aliases | 55 | 55 |
| earnings_periods | 37 | 37 |
| earnings_events | 37 | 37 |
| earnings_source_evidence | 40 | 40 |
| earnings_date_confirmations | 66 | 66 |
| earnings_financial_documents | 6 | 6 |
| earnings_financial_observations | 12 | 12 |
| earnings_report_documents | brak tabeli | 27 |
| earnings_report_observations | brak tabeli | 46 |

Łącznie po przyszłym apply: **23 tabele / 2 925 319 rekordów**,
bez zmiany żadnego z 2 925 246 pierwotnych wierszy. Nowe 73 wiersze to
27 dokumentów (23 release i cztery zapowiedzi) oraz 46 miar (23 Revenue
i 23 reported diluted EPS). Nie ma Forecast, konsensusu, surprise,
beat/miss, FX, przeliczenia ADR lub automatycznego SEC/IR.

ARM, QCOM, PANW i SNOW zachowują null Actual zgodnie z zamrożonym
materiałem E2D. To nie jest ponowna kontrola aktualności ich stron IR.
Pojawienie się nowego raportu wymaga odrębnej weryfikacji i nowego zakresu,
bez cichego dopisania do tego planu. Przyszła NVDA Q3 nadal ma null.
Upływ terminu może zmienić Scheduled na Date passed · release unconfirmed,
nigdy samodzielnie na Published.

## 6. Manifest 27 dokumentów

Wszystkie mają manual_official_report_review, verified_on=2026-11-04,
source_version=2026-11-04-review-1, version=1, bez supersedes/korekty.
Release ma dokładność date-only: brak fikcyjnej godziny lub timestampu.
Pełne metadane, linked_from, facts, fingerprint, CIK/FY/Q/period/event IDs
są w seed-manifest.json i w planie. SHA-256 pliku manifestu:
`045ae02b4b35be560db413d974f64eb96aed263e631df130a236ccddd824de81`. Fingerprint dotyczy lokalnych metadanych,
nie bajtów komunikatu. Nie dopisano fetched_at, first_seen, RAW hash lub
fikcyjnego HTTP receipt. Captured_at powstanie dopiero przy zapisie SQL.

| Ticker / CIK | Okres | Period end | Dowód | Data release | Document ID | Źródło |
|---|---|---|---|---|---|---|
| AAPL / 0000320193 | Q4 FY2026 | 2026-09-26 | earnings_release | 2026-11-02 | `4dc2bac4-4624-5216-8ca8-629e9a6e9c32` | [dokument](https://www.apple.com/newsroom/pdfs/fy2026q4/FY26_Q4_Consolidated_Financial_Statements.pdf) |
| MSFT / 0000789019 | Q1 FY2027 | 2026-09-30 | earnings_release | 2026-10-28 | `6c526cdb-d2b8-59b3-aeea-54ae3728bd03` | [dokument](https://www.microsoft.com/en-us/Investor/earnings/FY-2027-Q1/press-release-webcast) |
| GOOGL / 0001652044 | Q3 2026 | 2026-09-30 | earnings_release | 2026-10-28 | `e3a397c4-6c12-5516-898e-cc24c22c1906` | [dokument](https://s206.q4cdn.com/479360582/files/doc_news/2026/Oct/28/attachments/2026q3-alphabet-earnings-release.pdf) |
| META / 0001326801 | Q3 2026 | 2026-09-30 | earnings_release | 2026-10-21 | `be6d39e5-7995-52f1-9ed7-01db433562e5` | [dokument](https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Third-Quarter-2026-Results/) |
| TSLA / 0001318605 | Q3 2026 | 2026-09-30 | earnings_release | 2026-10-21 | `a70574e9-bd11-53b8-9cb4-128bc261e4dd` | [dokument](https://assets-ir.tesla.com/tesla-contents/IR/TSLA-Q3-2026-Update.pdf) |
| AVGO / 0001730168 | Q3 FY2026 | 2026-08-02 | earnings_release | 2026-09-02 | `22e93397-2e3a-55ec-86d6-1b69ad3a487d` | [dokument](https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-third-quarter-fiscal-year-2026-financial) |
| AMD / 0000002488 | Q3 2026 | 2026-09-26 | earnings_release | 2026-11-03 | `cc399fb1-a9b1-5d85-9dcc-9063902dd486` | [dokument](https://ir.amd.com/news-events/press-releases/detail/1303/amd-reports-third-quarter-2026-financial-results) |
| ORCL / 0001341439 | Q1 FY2027 | 2026-08-31 | earnings_release | 2026-09-10 | `7bdb1318-5e36-55bf-809a-a96562aa0d24` | [dokument](https://investor.oracle.com/investor-news/news-details/2026/Oracle-Announces-Q1-Results-Driven-by-Triple-Digit-Growth-in-Cloud-Infrastructure-Revenues/default.aspx) |
| NFLX / 0001065280 | Q3 2026 | 2026-09-30 | earnings_release | 2026-10-20 | `83e2e676-430b-5cf4-869c-e79230621235` | [dokument](https://ir.netflix.net/files/doc_financials/2026/q3/FINAL-Q3-26-Shareholder-Letter.pdf) |
| MU / 0000723125 | Q4 FY2026 | 2026-09-03 | earnings_release | 2026-09-30 | `4d1ac5c8-0fb7-5042-9ca4-86b1d23ae540` | [dokument](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/default.aspx) |
| QCOM / 0000804328 | Q4 FY2026 | null | earnings_date_announcement | null | `5870eee3-5b49-5333-a561-93d8ba598f29` | [dokument](https://investor.qualcomm.com/news-events/press-releases/news-details/2026/Qualcomm-Schedules-Fourth-Quarter-and-Fiscal-2026-Earnings-Release-and-Conference-Call/default.aspx) |
| TSM / 0001046179 | Q3 2026 | 2026-09-30 | earnings_release | 2026-10-15 | `ec1d4833-2879-5b04-b524-86ddd420d122` | [dokument](https://pr.tsmc.com/english/news/3346) |
| ASML / 0000937966 | Q3 2026 | null | earnings_release | 2026-10-14 | `7b97fb7d-9aec-5098-8491-451c4c614d30` | [dokument](https://www.sec.gov/Archives/edgar/data/937966/000162828026065813/a2026_10x14xpresentation.htm) |
| ARM / 0001973239 | Q2 FY2027 | null | earnings_date_announcement | null | `9b870d0e-ebf1-5b4e-b909-6331f85bf4ff` | [dokument](https://newsroom.arm.com/news/arm-announces-earnings-release-date-for-second-quarter-fiscal-year-ending-2027) |
| AMAT / 0000006951 | Q3 FY2026 | 2026-07-26 | earnings_release | 2026-08-13 | `1d25740c-4b6f-5f5b-96d7-5f5623bcd904` | [dokument](https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-announces-third-quarter-2026-results) |
| LRCX / 0000707549 | Q1 FY2027 | 2026-09-27 | earnings_release | 2026-10-21 | `cfab1e55-c69a-56c2-8b7e-1a9b7d0d660e` | [dokument](https://investor.lamresearch.com/2026-10-21-Lam-Research-Corporation-Reports-Financial-Results-for-the-Quarter-Ended-September-27%2C-2026) |
| KLAC / 0000319201 | Q1 FY2027 | 2026-09-30 | earnings_release | 2026-10-28 | `3ca9e880-69fb-532f-9db1-01fb11e1beb7` | [dokument](https://ir.kla.com/news-events/press-releases/detail/523/kla-corporation-reports-fiscal-2027-first-quarter-results) |
| TXN / 0000097476 | Q3 2026 | 2026-09-30 | earnings_release | 2026-10-21 | `5b0f3234-be2c-54c2-ae8c-a2e1acd667a5` | [dokument](https://www.ti.com/about-ti/newsroom/news-releases/2026/2026-10-21-ti-reports-third-quarter-2026-financial-results-and-shareholder-returns.html) |
| ADBE / 0000796343 | Q3 FY2026 | 2026-08-28 | earnings_release | 2026-09-10 | `65a61898-356d-56ee-95d9-bafe981f890c` | [dokument](https://www.adobe.com/cc-shared/assets/investor-relations/pdfs/01906202/au56y4ter.pdf) |
| CRM / 0001108524 | Q2 FY2027 | 2026-07-31 | earnings_release | 2026-08-26 | `402a72fe-fef4-5e8b-ad89-419638ad9644` | [dokument](https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx) |
| NOW / 0001373715 | Q3 2026 | 2026-09-30 | earnings_release | 2026-10-28 | `237f9723-a034-51d0-937e-a1b961835e80` | [dokument](https://newsroom.servicenow.com/press-releases/details/2026/ServiceNow-Reports-Third-Quarter-2026-Financial-Results/default.aspx) |
| PLTR / 0001321655 | Q3 2026 | 2026-09-30 | earnings_release | 2026-11-02 | `cc0d51b3-855d-5fa6-b064-12f159020215` | [dokument](https://www.sec.gov/Archives/edgar/data/1321655/000132165526000045/a2026q3ex991pressrelease.htm) |
| CRWD / 0001535527 | Q2 FY2027 | 2026-07-31 | earnings_release | 2026-08-26 | `eb6371e0-1454-5a9c-9f26-8697ba19cdfa` | [dokument](https://ir.crowdstrike.com/news-releases/news-release-details/crowdstrike-reports-second-quarter-fiscal-year-2027-financial) |
| PANW / 0001327567 | Q1 FY2027 | 2026-10-31 | earnings_date_announcement | null | `2e3d9f5c-58db-527a-8058-09bb1f73eda5` | [dokument](https://investors.paloaltonetworks.com/node/20971/pdf) |
| SNOW / 0001640147 | Q3 FY2027 | 2026-10-31 | earnings_date_announcement | null | `7c62c2ba-328a-5083-8a80-8efa148ccd03` | [dokument](https://www.snowflake.com/en/news/press-releases/fy27-q3-earnings-date-announcement/) |
| IBM / 0000051143 | Q3 2026 | 2026-09-30 | earnings_release | 2026-10-21 | `f0098f12-bb06-5ea6-b979-a720ea0cf7e3` | [dokument](https://www.sec.gov/Archives/edgar/data/51143/000005114326000093/ibm-20261021xex991.htm) |
| CSCO / 0000858877 | Q4 FY2026 | 2026-07-25 | earnings_release | 2026-08-12 | `9a0407ab-883d-55ed-bcd0-8f971ffaec0d` | [dokument](https://investor.cisco.com/news/news-details/2026/CISCO-REPORTS-FOURTH-QUARTER-AND-FISCAL-YEAR-2026-EARNINGS/default.aspx) |

## 7. Manifest 46 obserwacji i kontrola finansowa

Zweryfikowano zgodność całego zatwierdzonego lokalnego materiału z CIK,
FY/Q/label, istniejącym event/period, oficjalnym hostem/dokumentem i źródłową
metodologią. Nie pobierano nowych SEC/IR i nie zmieniono seeda lub liczb.
TSM zachowuje **TWD / IFRS / akcja zwykła**, ASML **EUR / US GAAP /
akcja zwykła**; brak ustalonego dnia końca okresu ASML pozostaje null.
EPS MU 32.87 nie zastępuje non-GAAP 33.42. NFLX/LRCX/PLTR/CRWD zachowują
źródłowe tysiące; TSM miliardy; pozostałe revenue miliony. Nie pomylono
current quarter z YTD/annual, basic z diluted lub ADR z akcją zwykłą.
GOOG/GOOGL pozostają jednym emitentem. Nie przeniesiono poprzedniego
kwartału do przyszłych Actual; sześć raportów E2B pozostaje bez edycji.

Poniższe canonical Actual są dokładnym Decimal/NUMERIC po skalowaniu,
bez FX. Każda obserwacja jest version=1, supersedes/correction=null.
W planie są również pełne document/event/period/company IDs, precision,
metodologia i fingerprint. Test SQL porównuje **każde pole** manifestu,
a nie tylko liczniki lub kwoty.

| Ticker | Metryka | Źródłowa wartość / skala | Canonical Actual / jednostka | Standard / rodzaj akcji | Observation ID |
|---|---|---|---|---|---|
| AAPL | revenue | 114477 millions | 114477000000 USD | US_GAAP / not_applicable | `93eae6fb-33f1-5815-a361-75359c1b49c8` |
| AAPL | reported_diluted_eps | 2.10 per_share | 2.10 USD/share | US_GAAP / common_share | `e0242f31-79bd-5b69-b1a5-cec0a2679441` |
| MSFT | reported_diluted_eps | 4.92 per_share | 4.92 USD/share | US_GAAP / common_share | `40afb8f2-cc28-5aaf-afde-55bf6b37e87a` |
| MSFT | revenue | 92279 millions | 92279000000 USD | US_GAAP / not_applicable | `ce2ae434-a197-5c93-be17-8a41c68fb4ac` |
| GOOGL | reported_diluted_eps | 2.12 per_share | 2.12 USD/share | US_GAAP / common_share | `07ca787a-9d48-5375-abc3-3cbc32349023` |
| GOOGL | revenue | 127577 millions | 127577000000 USD | US_GAAP / not_applicable | `345fa9bc-427d-5c12-850c-91be396ca024` |
| META | reported_diluted_eps | 3.83 per_share | 3.83 USD/share | US_GAAP / common_share | `9c586661-a973-597d-bd0e-a9c845b2a4c8` |
| META | revenue | 64601 millions | 64601000000 USD | US_GAAP / not_applicable | `bac2fa58-e7ac-518f-add9-a679503b522c` |
| TSLA | reported_diluted_eps | 0.22 per_share | 0.22 USD/share | US_GAAP / common_share | `75fccfc2-047d-5a3a-8937-baf955a1f180` |
| TSLA | revenue | 28046 millions | 28046000000 USD | US_GAAP / not_applicable | `c302988d-e594-5c1a-983f-c2a766cde0cc` |
| AVGO | reported_diluted_eps | 2.68 per_share | 2.68 USD/share | US_GAAP / common_share | `6fe7cc0b-c206-517c-989c-446c2e0b3cca` |
| AVGO | revenue | 29591 millions | 29591000000 USD | US_GAAP / not_applicable | `8d32012e-c444-5bf3-b76e-1a0769fe9cd1` |
| AMD | reported_diluted_eps | 1.46 per_share | 1.46 USD/share | US_GAAP / common_share | `489ff702-da4e-5fe8-9b9b-056553a1ec39` |
| AMD | revenue | 13377 millions | 13377000000 USD | US_GAAP / not_applicable | `759022bd-4977-56db-88c9-e413c956e2a4` |
| ORCL | revenue | 19345 millions | 19345000000 USD | US_GAAP / not_applicable | `1dc3836f-8334-5a75-9b4e-47e0ea92eb40` |
| ORCL | reported_diluted_eps | 1.56 per_share | 1.56 USD/share | US_GAAP / common_share | `43a0a271-d67b-5c81-b2dc-fa94ee91851c` |
| NFLX | revenue | 12874176 thousands | 12874176000 USD | US_GAAP / not_applicable | `e4f42a48-92c5-5b5a-b908-4bb9f1d9e73d` |
| NFLX | reported_diluted_eps | 0.87 per_share | 0.87 USD/share | US_GAAP / common_share | `ee93a74a-c913-50e2-a24f-c04822e9dc95` |
| MU | revenue | 54229 millions | 54229000000 USD | US_GAAP / not_applicable | `bc7f59c7-6b88-5224-85b4-5fad16109e9b` |
| MU | reported_diluted_eps | 32.87 per_share | 32.87 USD/share | US_GAAP / common_share | `d0b393ef-31a7-53cc-934f-44659ecb8d97` |
| TSM | revenue | 1494.24 billions | 1494240000000.00 TWD | IFRS / not_applicable | `56792292-8e97-59c0-82db-7c0811e32756` |
| TSM | reported_diluted_eps | 29.43 per_share | 29.43 TWD/share | IFRS / ordinary_share | `de9abf1c-092c-586d-985f-95520b1bb985` |
| ASML | revenue | 11662 millions | 11662000000 EUR | US_GAAP / not_applicable | `3ddc3a23-cb5e-52b7-aefe-aee2539ea5c3` |
| ASML | reported_diluted_eps | 12.93 per_share | 12.93 EUR/share | US_GAAP / ordinary_share | `f80d8250-0b89-5c8b-8408-9c8c640dfb1a` |
| AMAT | revenue | 9115 millions | 9115000000 USD | US_GAAP / not_applicable | `501ce52b-c82c-5b32-a59a-a9f8623aec58` |
| AMAT | reported_diluted_eps | 3.17 per_share | 3.17 USD/share | US_GAAP / common_share | `8afbccc5-e995-5088-8a88-8dbbb26e01c8` |
| LRCX | revenue | 8219418 thousands | 8219418000 USD | US_GAAP / not_applicable | `19325f32-7117-5940-9d64-60298f2256be` |
| LRCX | reported_diluted_eps | 2.19 per_share | 2.19 USD/share | US_GAAP / common_share | `a420d5dd-f389-5cd3-ae56-9d27c8b6bfe5` |
| KLAC | revenue | 4136 millions | 4136000000 USD | US_GAAP / not_applicable | `3730d4cc-a08b-5e3f-b103-272afc4a1ac8` |
| KLAC | reported_diluted_eps | 1.18 per_share | 1.18 USD/share | US_GAAP / common_share | `6b40bce4-2386-51a6-8304-c3b451d3a942` |
| TXN | reported_diluted_eps | 2.62 per_share | 2.62 USD/share | US_GAAP / common_share | `17629ac9-822d-5ed8-922f-5cdc573df5d3` |
| TXN | revenue | 6055 millions | 6055000000 USD | US_GAAP / not_applicable | `957e2d6a-4ea7-5746-a4db-834845ea2f09` |
| ADBE | reported_diluted_eps | 4.62 per_share | 4.62 USD/share | US_GAAP / common_share | `11e4e7f8-b95d-5c9a-9818-c3977cfb47d3` |
| ADBE | revenue | 6760 millions | 6760000000 USD | US_GAAP / not_applicable | `85d49573-d389-5f43-8260-92c946b024ae` |
| CRM | revenue | 11345 millions | 11345000000 USD | US_GAAP / not_applicable | `bcd2791f-1e81-5fd3-8a46-8f4a7ea4409f` |
| CRM | reported_diluted_eps | 4.29 per_share | 4.29 USD/share | US_GAAP / common_share | `d788eda7-2166-563b-957e-b621a005843e` |
| NOW | reported_diluted_eps | 0.27 per_share | 0.27 USD/share | US_GAAP / common_share | `6e9baa1f-9a6f-53aa-9f1e-f65397ba8cd0` |
| NOW | revenue | 4106 millions | 4106000000 USD | US_GAAP / not_applicable | `77bf5813-9425-525e-b770-a156e273e375` |
| PLTR | revenue | 2313411 thousands | 2313411000 USD | US_GAAP / not_applicable | `1777ba26-5989-5758-af97-8a083005489d` |
| PLTR | reported_diluted_eps | 0.44 per_share | 0.44 USD/share | US_GAAP / common_share | `cdd00a2c-bc65-5702-bca4-964a84c72421` |
| CRWD | reported_diluted_eps | 0.01 per_share | 0.01 USD/share | US_GAAP / common_share | `0b071b80-6169-5130-8963-8daae847f554` |
| CRWD | revenue | 1470897 thousands | 1470897000 USD | US_GAAP / not_applicable | `c2bfcc23-c240-57d5-b990-6217d109707e` |
| IBM | revenue | 17103 millions | 17103000000 USD | US_GAAP / not_applicable | `69653653-0a90-50d9-9927-122b16ce0e96` |
| IBM | reported_diluted_eps | 2.30 per_share | 2.30 USD/share | US_GAAP / common_share | `9965ab12-09c9-5891-9b93-fe14d17c14f4` |
| CSCO | revenue | 17252 millions | 17252000000 USD | US_GAAP / not_applicable | `1a17daa5-23a3-5467-a731-52af2db68218` |
| CSCO | reported_diluted_eps | 0.97 per_share | 0.97 USD/share | US_GAAP / common_share | `bbdfebe1-81a3-530d-905d-5bccc24af9d1` |

## 8. Oddzielny aktywator i bramki

Nowy app/database/activate_earnings_reports.py ma prepare/apply.
Nie jest importowany przez API, startup lub scheduler. Existing CLI E2D
i initializery nadal odrzucają normalną bazę; nie zmieniano ich guardów
lub nazw baz. Dawna propozycja bf5e25c5… nie jest tokenem tego planu.

Prepare jest odczytowe. Wymaga jawnego target, zgodnego katalogu E2C,
53/55/37/37/40/66/6/12 i 21 tabel, pełnego backupu i dowodu restore,
pełnych identycznych snapshotów oraz konflikt-free CIK/FY/period/event.
Plan przechowuje wszystkie pierwotne wiersze Earnings, hashe makro,
cały deterministyczny manifest nowych danych i zamrożone artefakty.

Apply wymaga pełnego zatwierdzonego hasha i dokładnego target. Ponownie
sprawdza kod/SQL/JSON, kopię i dowód, tożsamość, pełne schematy, oryginalne
dane, braki/kolizje store i manifest. Nie przelicza lub nie podmienia planu.
Jedna SERIALIZABLE READ WRITE transaction, search_path public,pg_catalog,
**lock_timeout=5s**, **statement_timeout=120s**, locki **726530019** (wspólne
okno refresh) i **726530020** (ręczny import) obejmuje cały DDL i seed.
Używa dotychczasowej kolejności/semantyki, bez zmiany R1–R3.

Błąd wycofuje dwie nowe tabele i cały seed. Po udanym COMMIT brak
automatycznego rollbacku. Idempotencja dopuszcza wyłącznie kompletny,
identyczny schemat i dokładny seed, bez dodatkowych danych/wersji;
pomija DDL, porównuje wszystkie pola i pełne snapshoty/timestampy.
Partial/foreign schemat lub zmiana starych danych powoduje odmowę.

## 9. Zamrożone artefakty i podpisy

| Artefakt | SHA-256 bajtów |
|---|---|
| app/database/activate_earnings_reports.py | `0027edab2b42c03a2fd6f02272fd26f178828a281be386117d0857d41f503a08` |
| docs/audits/equity-earnings-report-activation-rollback-2026-11-04.md | `7c2a62436c611ece213f60f3a2a2cf40d3a9a6c88e80a8ac3022dac37985a8b8` |
| app/database/earnings_report_schema.sql | `4ceeedb29fd6acdbca5dbf9584065c0506c34897490d79ba50098ecc0cb16709` |
| app/earnings_reports.py | `985bc5e33f599ec1f41b5762411b7ffe2618d29c5dad5e6a4a6bdac0cc889219` |
| config/earnings_reports_manual.json | `339ed7036dd2fd49f8526b177493503390338952ba2e33b05e2a632686bcfea7` |
| app/database/activate_earnings_coverage.py | `0f1510699e4d3ed3318459339c3e7a32315b4f9cb11c5be7affac10a2817ffc0` |
| app/database/activate_earnings.py | `183f77edef67b40640f8773868e5a661014e1427f44923bd9448321d0d4f79f0` |
| app/database/activate_earnings_financials.py | `213b0af4a3293d53cbf300302286b4bfce5357ea7590cac2fc7e17c546435904` |
| app/database/earnings_schema.sql | `7ddad92de5d2dca8f761e6449021a8a2ee46bab031a17c133e2480859e26fd48` |
| app/database/earnings_financial_schema.sql | `9fbbb8bbbabf76ab23546e2e0fd24a0e1727b69812eb4892b3a83a4fef55e7e1` |
| app/database/earnings_coverage_schema.sql | `36d55498a9a465465d102365e056e04e7fabb1ff9b561d2b0fe81f2157ab30eb` |
| app/earnings_coverage.py | `7d8f71da0a71e1f14939f4ac2a4f493b44eb35a40ad1eed2a3ab4cefb96afb02` |
| app/earnings.py | `f58813cd87e7001636bfcd5646947b52d0d4f0b220909eb4cad2ecd501ab93a5` |
| app/earnings_financials.py | `5f0f3bcc123118f05b2bc6139b9748b04ff7ee22f10a5543d10b9ba145b5fe90` |
| config/earnings_manual.json | `c1a0f8117df471cfdf7cb1a2be7daa1d6a4a2581c5c703d4a7d28636e6680ba4` |
| config/earnings_financial_manual.json | `7feb36d2a226e29bada634386c41729dcb8aa92792807ee5c7e21f837c5bb7ad` |
| config/earnings_companies_reviewed.json | `cbe2aaf4faaf00da05273755a234e8a884f2be5c5d2975026cb1f941055309ea` |
| config/earnings_dates_reviewed.json | `95d3eaf20e881c857df6491e12a65f37a9cc25232e51353842227787f42a673e` |
| docs/audits/equity-earnings-coverage-activation-rollback-2026-11-04.md | `10fdd162d420159bb3351529ced352165487714bb1816731aa01054344608092` |

Sygnatura Earnings przed: `89b0c564a720d96fe6ff679f4d17ac7601b45a20091c04aa73f410fd0fb0f6ab`.
Sygnatura Earnings po: `7d426e73da37ee411bcd2c21cbfa02f2d8676f898437889759b0373e15a1fac5`.
Sygnatura makro: `ba1b47aaf7d21b170b579369ca5c20b2e6fee871ee382e15fe519a43d37a2cf5`.
Wzorce katalogów są w schema-reference.json i planie, z rzeczywistego
wykonania PG17. Stare obiekty muszą pozostać identyczne. Zmiana dowolnego
artefaktu, danych, schematu, celu, backupu lub dowodu unieważnia plan.

## 10. Rzeczywiście wykonane testy

| Kontrola | Nowy wynik przygotowania |
|---|---|
| Pełny backend offline | **1343 passed, 87,99 s** |
| Nowe jednostkowe bramki/manifest | **7 passed**, wliczone wyżej |
| Pełny frontend offline, Node 22.23.4 | **672 passed / 32 pliki, 40,44 s** |
| TypeScript noEmit | passed |
| Production build | passed, 5,93 s; największy chunk **407,04 kB**, próg bez zmian |
| Wcześniejsze PostgreSQL | **11/11 passed**, nowe lokalne przebiegi |
| Nowy PostgreSQL E2D Activation | passed, razem **12/12** |
| Pełny restore danych użytkownika | passed; 21 identycznych tabel i katalogi |
| Apply na odtworzonej pełnej kopii | **created**, 23 tabele, nowe 27/46 |
| Ponowienie na kopii | **already_initialized**, wszystkie snapshoty identyczne |
| Rzeczywisty błąd SQL po DDL i pierwszym raporcie | pełny rollback DDL i seeda |
| Odczyty API na pełnej kopii | **28 GET HTTP 200**, brak zmian 23 tabel |
| Końcowy normalny snapshot | identyczny z pierwszym, drugim i backupem |
| Chronione 13 SHA / whitespace / actionlint | passed |

Wszystkie SQL walidacje używały własnego PostgreSQL 17 na 55471 i guarda
publisher HTTP. Nowy test sprawdził prawdziwy backup/restore syntetycznego
stanu oraz bramki: target/token, inny rzeczywisty connection/database,
artefakt/kod/JSON, uszkodzony archive, niezgodny dowód restore, data drift,
schema drift, partial store, exact seed i całą historię E2A/B/C oraz makro.
Ten sam pełny zestaw bramek wykonano także na odtworzonej kopii użytkownika.
Nie uznano syntetycznego backupu za kopię danych użytkownika.

Listę/szczegóły testowano przez rzeczywisty API/SQL na pełnej kopii,
bez fixture odpowiedzi i z wymuszonym read-only. Potwierdzono 23 complete,
cztery null Actual, null Forecast i brak przedwczesnej NVDA. GET nie
wykonywał DDL/importu/HTTP. Nie uruchamiano nowego Chrome lub Actions;
UI/API/kontrakty i workflow pozostały bez edycji. Dawne 359 Chrome i zielone
CI zamknięcia E2D nie są nowymi wynikami przygotowania.

Pierwszy helper identyfikacji użył niedostępnego psutil; zastąpiono go
Windows CIM i istniejącym odczytem czterech niesekretnych pól workera.
Pierwsza próba helpera backupu miała testowe nadpisanie DB_PASSWORD
w pomocniczym procesie i została odrzucona przed dumpem. Usunięto to
nadpisanie, zachowując konfigurację projektu; pełny kolejny backup/restore
przeszedł. Nieudanych prób nie zaliczono jako sukcesów. Nie zmieniano
timeoutów, guardów lub testów w celu ukrycia błędu.

## 11. Oddzielny rollback i ochrona danych

[Plan cofnięcia po COMMIT](equity-earnings-report-activation-rollback-2026-11-04.md)
jest oddzielnym zamrożonym dokumentem, **niewykonanym**. Wymaga osobnej
decyzji, receipt, zgodnego pełnego stanu i wykluczenia późniejszych zależności.
Zakres obejmuje tylko dwie tabele E2D i ich funkcję, bez CASCADE lub usuwania
firm, okresów, eventów, dat i finansów E2B. Późniejsze korekty lub nowe dane
zatrzymują cofnięcie. Nie dostarczono automatycznego post-COMMIT rollbacku.
Pełne odzyskiwanie zawsze najpierw do nowej bazy i osobna decyzja;
nigdy automatycznie nie nadpisywać macrolens starszą kopią.

Normalna baza podczas całego etapu nie otrzymała DDL, importu E2D,
UPDATE/DELETE lub rollbacku. Wszystkie 21 tabel, pierwotne wiersze E2A/B/C,
daty i sześć dokumentów/12 miar E2B pozostały identyczne. Nie zmieniano
K2, Overview, R1–R3, FRED/ALFRED, BEA lub harmonogramów.

## 12. Pliki, cleanup i Git

Dodano tylko pięć plików:

- app/database/activate_earnings_reports.py
- tests/test_earnings_report_activation.py
- tests/postgres_earnings_report_activation_validation.py
- docs/audits/equity-earnings-report-activation-rollback-2026-11-04.md
- docs/audits/equity-earnings-report-activation-2026-11-04.md

Wszystkie 13 wcześniejszych plików pozostaje byte-identycznych.
Końcowo **9 modified / 9 untracked**, indeks pusty, main i HEAD bez zmian.
Bez stagingu, commita, pusha, resetu, clean, amend i globalnego formatowania.
Poprzednie audyty, initializery, kod/dane E2D, zależności i CI bez edycji.

Własne losowe bazy usunięto, w tym pełną odtworzoną kopię. Po kontroli
pełnego ID `2d895ab833c3844f3ffdbc051ed51caf259ebca30534b7e87ecc19aa9075a0e1`,
nazwy, etykiety reports-activation-2026-11-04 i braku pozostawionych baz prób
usunięto wyłącznie własny kontener macrolens_reports_activation_20261104
i anonimowy wolumen. Normalny macrolens_postgres pozostaje uruchomiony.
Nie pozostawiono diagnostycznych sesji, transakcji lub advisory locks.
Backupy, manifesty, dowody, plan i helpery są ignorowane w data/raw.
Nie dodano sekretów lub pełnych komunikatów emitentów do nowych plików.

## 13. Konkretny plan i wznowienie po osobnej zgodzie

Cel: **localhost:5432/macrolens**, rola **macrolens**, OID **16384**,
klaster **7682090371041935398**, PostgreSQL 17.
Plan: `data/raw/earnings-report-activation-2026-11-04/activation-plan.json`.

**Pełny SHA-256 kanonicznego planu:**

`3bb31913e0287d686c8f94f3595ced0ef99d3c084cae46cf545abe48e58aee5f`

**ready_for_apply=true. Nie wykonano normalnego apply.** Backend pozostaje
zatrzymany, aby zachować ważność planu. Sam hash nie jest zgodą. Przed
pierwszym zapisem potrzebne jest wyraźne zatwierdzenie tego pełnego hasha
i dokładnego celu przez użytkownika. Każda zmiana powoduje odmowę,
bez automatycznej podmiany planu lub przenoszenia wcześniejszej zgody.

Po osobnej zgodzie: ponownie sprawdzić cały plan/cel/wersję PG/dane/schematy/
artefakty/backup/dowód; wykonać jedną zatwierdzoną transakcję. Przed restartem
sprawdzić 23 tabele, 27/46, wszystkie pierwotne 21 tabel, schematy,
manifesty i idempotencję. Bez automatycznego rollbacku po COMMIT.

Dopiero potem z katalogu projektu wznowić zwykły backend według README:
`.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload`,
z zachowanym .env i portem 8000. Vite już działa na localhost:5173;
jeśli zostanie zamknięty, uruchomić `npm run dev` w frontend bez override API.
Nie trzymać lease przy restarcie. Sprawdzić rzeczywiste health/API/Calendar,
23 nowe pary i stare E2B, null pozostałych/future NVDA, EN/PL i desktop/mobile,
Makro/Earnings/Wszystkie oraz brak JS/503. Zwykłe zapisy makro po wznowieniu
są dozwolone i odrębne od kontroli integralności migracji.

Nie uruchamiać backendu przed decyzją bez świadomości, że może unieważnić
snapshot. Nie rozpoczęto E2E, automatycznego SEC/IR, nowego seeda lub
schedulera. **Gotowe do osobnego zatwierdzenia.**


## 14. Wykonanie po wyraźnym zatwierdzeniu — 04.11.2026

Użytkownik zatwierdził wyłącznie plan
`3bb31913e0287d686c8f94f3595ced0ef99d3c084cae46cf545abe48e58aee5f`
na localhost:5432/macrolens, rolą macrolens, OID 16384, klaster
7682090371041935398, PostgreSQL 17. Nie zastępowano ani nie przeliczano planu.

### Końcowy preflight, apply i kontrola przed restartem

Ponownie potwierdzono dokładny cel i PG17, brak działającego backendu,
innych klientów SQL i advisory locks, brak częściowego/obcego E2D oraz
pełne hash/count 21 tabel, wszystkie pierwotne wiersze Earnings i schematy.
Wszystkie zamrożone artefakty i dokładny seed były identyczne. Ponownie
sprawdzono backup **30 900 982 B**, jego SHA/format i SHA oraz treść dowodu
pełnego udanego restore. Kontrole read-only przeszły; nie było potrzeby
nowego planu lub omijania bramek. Zapisano nowy manifest 18 zastanych plików.

**Apply: created, COMMIT poprawny.** Jedna transakcja SERIALIZABLE,
locki 726530019/726530020 i limity 5s/120s objęła wyłącznie dwie tabele,
zatwierdzone constraints/indeksy, jedną funkcję, cztery triggery i 73 nowe
wiersze: **27 dokumentów oraz 46 obserwacji**. Bez nowych firm, aliasów,
okresów, wydarzeń, dat, Forecast lub aktualizacji starych wierszy.

| Tabela | Potwierdzony stan po COMMIT |
|---|---:|
| earnings_companies | 53 |
| earnings_company_aliases | 55 |
| earnings_periods | 37 |
| earnings_events | 37 |
| earnings_source_evidence | 40 |
| earnings_date_confirmations | 66 |
| earnings_financial_documents | 6 |
| earnings_financial_observations | 12 |
| earnings_report_documents | 27 |
| earnings_report_observations | 46 |

Łącznie **23 tabele / 2 925 319 rekordów**. Są 23 nowe Revenue Actual
i 23 reported diluted EPS, 23 release i cztery zapowiedzi bez Actual.
ARM/QCOM/PANW/SNOW nie były ponownie weryfikowane lub aktualizowane.

**Idempotencja: already_initialized.** Powtórzenie dokładnie tego samego
planu nie zmieniło żadnego pełnego snapshotu, wersji lub timestampu.
Nie wykonano automatycznego rollbacku po udanym COMMIT.

Jeszcze przed uruchomieniem backendu niezależny odczyt potwierdził
identyczność **wszystkich pierwotnych 21 tabel**, ich 2 925 246 rekordów,
13 tabel makro i pełnych pierwotnych wierszy ośmiu tabel Earnings.
Obie tabele E2B mają identyczne pełne hashe. Wykonany katalog odpowiada
dokładnie zatwierdzonemu wzorcowi: wyłącznie nowe obiekty E2D, bez ALTER
istniejących tabel. Każde pole nowych dokumentów/metryk zgadza się
z manifestem seeda. Nie pozostawiono advisory locks lub transakcji.

Lokalny apply-receipt.json: SHA-256
`6db5ab8eb6a71914f4d4810fe2246108d7b2a60402eeff05ffe19c2f0d15a47d`.
Dowód integrity-before-restart.json: SHA-256
`f1f98c2f5fc6a88168961691506e0b318bbc07582c73ea9116fc889cf78d1cb4`.
Receipts pozostają ignorowane pod data/raw; nie dodano ich do Git.

### Normalny backend i API

Po udanej kontroli integralności wznowiono zwykły
`python -m uvicorn app.api.main:app --reload` z C:\Projects\macrolens,
na 127.0.0.1:8000. Launcher **22508**, reloader **18932**, worker **1800**.
Z rzeczywistego workera ponownie odczytano wyłącznie niesekretne
DB_HOST/PORT/NAME/USER i cwd: localhost/5432/macrolens/macrolens,
C:\Projects\macrolens. Nie wypisywano hasła, pełnego środowiska lub .env.
Nie stosowano izolowanego API, innej bazy, CORS wrappera lub fixture danych.
Nie zmieniono konfiguracji R1–R3 i nie trzymano diagnostycznego lease.

Dotychczasowy **Vite PID 15772** nadal działa na localhost:5173;
nie uruchamiano drugiej instancji. Frontend korzysta z rzeczywistego API
8000 i normalnego macrolens. Normalny Uvicorn załadował aktualny kod E2D.

**35 bezpośrednich GET zakończyło się HTTP 200:** health, 53 unikalnych
emitentów, 34 datowane eventy, szczegóły wszystkich 27 nowych raportów,
GOOG/GOOGL jako jeden event, stary endpoint makro, domena makro i Wszystkie.
Makro 02–08.11 ma **16 wydarzeń**. API zachowuje trzy undated dla audytu;
UI ich nie renderuje. Nowy report_store_status=available.

Porównano wszystkie dokumenty i 46 miar z zatwierdzonym lokalnym ledgerem:
źródłowe/kanoniczne kwoty Decimal, skale, waluty, standardy, rodzaje akcji,
metodologie, źródła, okresy, daty i wersje. Nie wykonywano FX lub zamiany
GAAP na adjusted. Potwierdzono także sześć dotychczasowych raportów E2B.

| Raport | Dokładne Revenue Actual w API | Reported diluted EPS |
|---|---:|---:|
| AAPL Q4 FY2026 | 114477000000 USD | 2.10 USD |
| PLTR Q3 2026 | 2313411000 USD | 0.44 USD |
| AMD Q3 2026 | 13377000000 USD | 1.46 USD |
| MSFT Q1 FY2027 | 92279000000 USD | 4.92 USD |
| TSM Q3 2026 | 1494240000000.00 TWD | 29.43 TWD, IFRS, akcja zwykła |
| ASML Q3 2026 | 11662000000 EUR | 12.93 EUR, US GAAP, akcja zwykła |

Tabela UI skaluje i zaokrągla revenue do dwóch miejsc, np. AAPL 114,48 mld
USD i PLTR 2,31 mld USD. Nie zmienia to dokładnej wartości: szczegóły
zachowują pełne źródłowe 114477 millions i 2313411 thousands, sprawdzone
również w DOM. API zachowuje dokładne liczby jako tekst.

### Chrome na normalnym Calendar

**743 kontrole / 28 zakończonych odpowiedzi API HTTP 200**, zero wyjątków
JavaScript, console.error i HTTP 503. Test używał wyłącznie
http://localhost:5173/#/calendar, rzeczywistego API 8000 i normalnej bazy,
EN/PL, desktop 1366 px i mobile 390 px. Nie podstawiano odpowiedzi.

W każdej konfiguracji sprawdzono status oraz obie pełne źródłowe wartości
w szczegółach wszystkich **23 nowych raportów**, ich standard EPS,
weryfikację i oficjalne źródła. Osobno potwierdzono Apple, PLTR, AMD,
Microsoft, TSM TWD/IFRS i ASML EUR/US GAAP. Wszystkie 23 mają
„Opublikowano · dane zweryfikowane”. Cztery zapowiedzi mają Scheduled
i puste Actual; wszystkie Forecast pozostają `—`, bez surprise/beat/miss.

NVDA Q3 FY2027, 17.11: **ok. 22:20 — wyniki**, call **23:00**, oba Actual
null. Dotychczasowe Intel/Amazon/NVIDIA pozostają bez regresji. INTC ma
21:00+ i call 22:00; AMZN nieznany release oraz osobny call 22:00.
Brak checkboxów tickerów i niedatowanych/nieogłoszonych Q4. Przeszły
Makro/Earnings/Wszystkie, zakresy, jeden nagłówek daty, szczegóły,
Escape/focus, brak zbędnego refetch i wewnętrzny poziomy scroll na telefonie,
bez overflow całej strony. Obejrzano zrzuty desktop EN i mobile PL.
Nie deklaruje to pełnego audytu WCAG.

Chrome nie wykonał żądań do wydawców; nie dodano automatycznego SEC/IR.
Pierwszy pomocniczy test API użył nieistniejącej trasy /calendar/agenda
i otrzymał 404. Poprawiono wyłącznie ignorowany helper na rzeczywiste
endpointy makro i powtórzono pełny zestaw 35 GET. Nie zmieniono aplikacji
i nie zaliczono pierwszej próby jako sukcesu.

Końcowy odczyt po UI potwierdził identyczne **wszystkie 10 tabel Earnings**
ze stanem po COMMIT, bez nowych rekordów, wersji lub timestampów. Wszystkie
pierwotne wiersze zachowano. Do tego odczytu także 13 tabel makro pozostało
identycznych; zwykłe późniejsze zapisy po restarcie są dopuszczalne i nie
stanowią zmian transakcji aktywacji. Nie pozostały diagnostyczne blokady
lub sesje. Własny diagnostyczny Chrome zamknięto.

### Wynik i Git

**E2D działa w codziennym MacroLens: http://localhost:5173/#/calendar.**
Normalny backend i dotychczasowy Vite pozostawiono uruchomione, z zachowaną
konfiguracją odświeżania. Nie wdrożono feedu, nowego etapu lub nowych firm.
ARM/QCOM/PANW/SNOW nadal wymagają osobnej aktualnej weryfikacji Actual.

Zmieniono wyłącznie ten raport spośród 18 zastanych plików. Pozostałe 17,
w tym wszystkie zamrożone artefakty, pozostają byte-identyczne. Wszystkie
13 chronionych plików zachowano. Git: **9 modified / 9 untracked**,
indeks pusty, main i HEAD 94526c9cf0422dde041c69fd4fdec21549a8b39e bez zmian.
Bez stagingu, commita, pusha, resetu, clean i amend. Logi, zrzuty, helpers,
kontrole i receipts pozostają ignorowane pod data/raw.
