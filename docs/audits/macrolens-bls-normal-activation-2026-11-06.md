# MacroLens — normalna aktywacja BLS

06.11.2026, Europe/Warsaw, `C:\Projects\macrolens`, main,
HEAD `c42cf6c411c85a64927fe5c6b3cf98f9e906c871`.

**APPLY wykonano i zatwierdzono COMMIT. Normalne API oraz Calendar → Wszystko
i Dane pokazują sześć odczytów BLS. Zainstalowano dokładnie 13 zatwierdzonych
plików i token version=3. Bez DDL, stagingu, commita i pusha.**

## Zastosowany plan i kontrole

Pełny hash zatwierdzonego i zastosowanego planu:

`374e93e3c7f21cf232db989e0532045c073328f71b2e4c3e5b3da3265499e2ad`

Plan pozostaje niezmieniony w
`data/raw/bls-production-upgrade-2026-11-06/normal-reviewed-final.json`.
Target potwierdzony read-only: localhost:5432/macrolens, PG17,
rola macrolens, OID 16384, system_identifier 7682090371041935398.

Sprawdzono historyczne policy, token F1 V2 i 155 artefaktów, autoryzację
monitora Earnings, hashe przed/po 13 plików i cały manifest kandydata.
Read-only CLI plan potwierdziło dokładnie zatwierdzony hash, również po
wykonaniu końcowego backupu. Nie dopasowywano planu do nowego stanu.

Powtarzane kontrole normalnego F1, monitora i Calendar dały dziewięć HTTP 200;
Calendar podczas zwykłego zadania makro odpowiadał około 14–16 s, bez
powtarzających się timeoutów. Sprawdzono procesy i ich rzeczywiste komendy.

Pierwsza pomocnicza kontrola gotowości zatrzymała procedurę przed APPLY,
ponieważ działało zwykłe zadanie makro. Zaczekano na jego naturalne
zakończenie o 18:00:24 PL i powtórzono backup/restore oraz kontrole.
Osobny guard drzewa procesów zatrzymał pierwszą próbę zatrzymania usług
przed wysłaniem Stop-Process: wykrył conhost. Zweryfikowano ścieżkę,
rodzica i poprawny podpis Microsoft; nie zatrzymywano go osobnym poleceniem.
Po ponownej identyfikacji i kontroli zatrzymano tylko wskazane API/Vite.
Żaden z tych przypadków nie spowodował zmiany zatwierdzonego planu.

## Backup i wykonanie

Końcowy użyty pg_dump custom: **33 953 015 B**, SHA-256:

`ebc628db26fcb8317cb0e2c1f53dc870914320dc87de06e99663017817764e03`

Manifest: `data/raw/bls-normal-activation-2026-11-06/post-refresh-backup/normal-backup.json`.
Eksport: jeden REPEATABLE READ READ ONLY, pg_export_snapshot oraz pg_dump
z wymuszonym read-only, ten sam snapshot. TOC i pełny restore na własnym
PG17/55547 przeszły: **29 tabel / 3 307 597 rekordów**, pełne uporządkowane
binary COPY i katalogi zgodne, zero niezwalidowanych constraints.

Zapisano komendy i tożsamości procesów API 19020/1976/21792 i Vite 8072.
Po ich zakończeniu potwierdzono wolne porty, brak pozostałych writerów
i dostępność lease. PostgreSQL pozostawiono uruchomiony.

APPLY z kopii review zwróciło `created`; niezależne verify `verified`.
Wykonano dokładnie trzy INSERT-y: dokument `bls:employment`, seed receipt
`reviewed_snapshot_import_not_new_http` i `activation-bls-revision`.
Bez zapisu do observations, computed_features, Earnings, vintages lub freezes.

Pełna kontrola po COMMIT, przed wznowieniem usług, potwierdziła:

- tylko trzy zatwierdzone tabele otrzymały po jednym wierszu;
- wszystkie wcześniejsze wiersze tych tabel pozostały identyczne;
- pozostałe 26 tabel były byte-identyczne z końcowym backupem;
- schemat i katalogi pozostały zgodne z planem, bez DDL.

Instalator zachował stare bajty i token w `normal-install-archive`, dostarczył
13 dokładnych plików z plan.delivery i token version=3. Osobny proces verify
uruchomiony już z normalnego kodu zakończył się sukcesem. API i Vite wznowiono
zapisanymi komendami. Nie wykonano restore normalnej bazy ani usuwania rewizji.

Receipts i dowody: `normal-apply-receipt.json`, `normal-verified.json`,
`installed-code-verified.json`, `commit-integrity.json` w ignorowanym
`data/raw/bls-normal-activation-2026-11-06`.

## Rzeczywiste API i Calendar

| Miara | Actual | Previous | Zmiana |
|---|---:|---:|---:|
| NFP | 165 tys. | 60 tys. | +105 tys. |
| U-3 | 4,1% | 4,2% | −0,1 pkt proc. |
| Wynagrodzenie godzinowe m/m | 0,4% | 0,3% | +0,1 pkt proc. |
| Aktywność zawodowa | 61,9% | 61,8% | +0,1 pkt proc. |
| U-6 | 7,9% | 7,6% | +0,3 pkt proc. |
| Tygodniowy czas pracy | 34,4 godz. | 34,4 godz. | 0 |

Każdą parę odczytano z normalnego API i sprawdzono osobno w obu widokach,
PL/EN, 1366/390 px. Godzina publikacji pozostaje 14:30 PL. Previous pochodzi
z tej samej odpowiedzi BLS. AHE jest jawnie pochodne i zaokrąglone do jednego
miejsca. NFP 60 tys. jest rewizją września, a nie historycznym first print.
ALFRED 02.10: 159044−159015=**29 tys. pozostało nienaruszone**; potwierdzono
pełną integralnością observations i osobnym końcowym odczytem tej wersji.

Zachowano oryginalny capture BLS z przygotowania, 16:23:32.459984 PL, SHA:
`e60010ae46d44e5aa5d7e8dd951e6e98b3b0c21a5b7998149c845d1ced8475dd`.
Nowy seed INSERT nie udaje nowego HTTP. Wykres NFP ma dziewięć porównywalnych
zmian z tego samego dokumentu; nie połączono go ze starszą historią FRED.

## Runtime i walidacja

F1: `activated=true`, `cooldown`, zgodne **159 artefaktów**, token version=3.
Pierwotna policy i rewizja UI zachowane. Earnings: `activated=true`,
`loop_running=true`, `completed`. Końcowy niezależny SQL potwierdził autoryzację
obu oraz identyczność wszystkich **16 pełnych tabel Earnings/Forecast**
względem stanu po zatwierdzonym COMMIT. F2 pozostał nieaktywny.

Chrome na **normalnym Vite 5173/API 8000/SQL**, bez podstawiania odpowiedzi:
**87 kontroli / 16 API HTTP 200**, zero błędów JS, HTTP 503 i żądań
przeglądarki do wydawców. Sprawdzono sześć/osiem kolumn Wszystko/Dane,
14 nowcastów, źródło BLS, rozróżnienie 60/29, wykres, kierunki delt,
siedem kolumn Wyniki, osiem wydarzeń, guidance NVIDIA, Market Cap oraz
brak overflow. Obejrzano desktop PL i telefon PL z wykresem.

Zainstalowano dokładne bajty wcześniej przetestowanego kandydata:
1633 backend, 945 frontend / 45 plików, TypeScript i build oraz rzeczywiste
próby PG17 opisane w raporcie przygotowania. **Nie przedstawia się tych
zestawów jako ponownie uruchomionych podczas tego wdrożenia.** Tutaj wykonano
świeży pełny restore, kontrolę SQL/manifestu, normalne verify i rzeczywiste UI.

Przed otwarciem własnego Chrome obserwowano istniejący zegar backendu przez
70 sekund. Tick Earnings przesunął się z 18:14:44 do 18:15:44 PL; zarejestrowany
listener BLS wykonał odczyty SQL odpowiadające ścieżce workera (29 próbek,
trzy połączenia). Dowód: `automatic-clock-observation.json`. Wybudzanie
korzysta z istniejącego lifecycle, bez nowego timera i bez wywołania z GET.

**Ograniczenie:** normalne wdrożenie nastąpiło po dwugodzinnym oknie publikacji.
Worker prawidłowo nie wykonał nowego HTTP: jeden dokument, jeden seed receipt,
zero nowych claimów HTTP. Nie wymuszano zegara ani pobrania poza oknem.
Następne potwierdzone publikacje są obsługiwane automatycznie w zatwierdzonym
zakresie i limitach, przy działającym lifecycle Earnings; przyszłej rzeczywistej
publikacji nie przetestowano jeszcze w normalnym środowisku. Końcowy widok
zachowuje istniejący komunikat o częściowo niesprawdzonych innych źródłach
makro; nie oznacza on brakujących sześciu odczytów BLS. Nie rozszerzano naprawy
na inne źródła ani semantykę stopki.

## Ochrona i zakończenie

Manifest wejściowy obejmował 496 plików. Zmieniono dziewięć zastanych,
zatwierdzonych ścieżek; **487 pozostało byte-identyczne**. Cztery nowe pliki
backendu i wszystkie dziewięć zmian odpowiadają dokładnie plan.delivery.
Zachowano wcześniejsze hunki Calendar, chronione prace i cały F2.
Poza zatwierdzoną dostawą dodano tylko ten raport; dowody pozostają ignorowane.

Własny Chrome 9351 zakończono przez CDP po kontroli PID/argumentów. Własny PG17
usunięto z wolumenem po sprawdzeniu pełnego ID
`52f3cacf3a1fdd5eb121032f7c8780291161e5b8c2d9acb3f5886aa272b0fef0`,
etykiety, wyłącznie własnych baz i braku innych klientów. Pierwszy helper
sprzątania wymagał nieobecnego websockets; użyto istniejącego modułu Node ws,
bez instalowania zależności. Backupy, receipts, review i logi zachowano.
Normalny PostgreSQL, API 8000 i Vite 5173 pozostają uruchomione.

Końcowo **33 modified / 78 untracked**, indeks pusty, main/HEAD bez zmian.
Bez stagingu, commita, pusha, reset/clean/amend/force i globalnego formatowania.
