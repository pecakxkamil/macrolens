# MacroLens — kolory kierunku zmiany w Calendar / Wszystko

06.11.2026, Europe/Warsaw. Poprawka działa bezpośrednio na lokalnym Vite
http://127.0.0.1:5173/#/calendar. Wyłącznie frontend, bez zapisu SQL,
migracji, importu, aktywacji, stagingu, commita lub pusha.

## Reguła i zakres

W Wszystko dodatnia delta jest zielona (#86cfad), ujemna czerwona (#ed9b9b).
Zero, null i brak porównywalnych danych pozostają neutralne. Są to istniejące
kolory porównań dark theme. Nie oznaczają poprawy/pogorszenia ekonomicznego.
Każda linia EPS/Revenue ma niezależną klasę. Actual/Previous nie są kolorowane.
Zachowano sześć kolumn, teksty liczb, układ, godziny, filtry i przewijanie.

Nowy mały changeDirection obsługuje number i bigint. Makro zachowuje istniejące
warunki porównywalności, formatter, tooltip i tone ekonomiczny; dodatkowe pole
direction opisuje znak wyświetlanej delty. Zero przy prezentowanej precyzji
pozostaje neutralne. ComparisonTooltip korzysta z direction wyłącznie po jawnym
colorByDirection w Wszystko. Dane nadal używa starego tone, także w Forecast.

Earnings wykorzystuje dotychczasowe dokładne odejmowanie dziesiętne BigInt.
earningsChange zwraca tekst i kierunek z jednego obliczenia. Dotychczasowy
earningsDifference zachowuje kontrakt string i wartości. Wszystkie wcześniejsze
warunki FY/Q, metodologii, waluty, podstawy akcji i null są zachowane.
Wspólny helper ustala tylko klasę znaku. Nie ma nowego źródła danych.
Istniejąca legenda Wszystko opisuje teraz więcej/zielony, mniej/czerwony,
zero lub brak danych/neutralny; legenda Dane pozostała bez zmian.

## Sprawdzenie

| Kontrola | Wynik |
|---|---|
| Pełny Vitest | **824 passed / 40 plików**, 61,52 s |
| Nowe przypadki | **15 passed** w powyższym zestawie |
| TypeScript noEmit | passed |
| Production build | passed, Vite 3,89 s, największy chunk 407,04 kB |
| Chrome PL/EN, 1366/390 px | **630 kontroli / 16 API GET HTTP 200** |
| Pełne dane 16 tabel Earnings/F1, katalog i referencje | identyczne przed/po |
| Wszystkie 34 datowane obiekty API Earnings | identyczne przed/po |
| F1 V2 | 155 artefaktów zgodne, activated=true/cooldown |

Testy obejmują oba znaki, zero, null, NaN/Infinity, BigInt, niezależność EPS
i Revenue, ujemną zmianę przychodów, brak jednej metryki oraz zachowanie
starego tone dla Dane. Dotychczasowe testy dokładnych różnic i ograniczeń
metodologicznych również przeszły.

Chrome korzystał z normalnego API 8000/Vite 5173 i własnego CDP 9317.
Bez fixture odpowiedzi. Sprawdzono rzeczywisty computedStyle wartości,
nie tylko nazwy klas. Przykłady: dodatnie makro zielone; spadek initial
jobless claims czerwony w Wszystko, zachowane zielone ekonomiczne porównanie
w Dane; ARM i QCOM ujemny EPS czerwony, dodatni Revenue zielony; AMD oba
przyrosty zielone; brak Current NVIDIA/PANW/SNOW neutralny. Ujemny Revenue
i dokładne zero Earnings sprawdzono przypadkami komponentu w obu językach;
nie dopisywano takich wartości do normalnego API.

Zachowano zgodność wszystkich ośmiu wierszy Earnings listopad–grudzień
z API i szczegółowymi Wynikami, sześć/osiem/siedem kolumn odpowiednich
widoków, wspólną chronologię, źródła, ważność, 14 nowcastów i guidance
NVIDIA, przejście do Wyniki, brak overflow strony i przewijanie telefonu.
Obejrzano desktop EN i mobile PL. Zero JS/console.error, HTTP 503 lub
zewnętrznych żądań przeglądarki. Nie jest to pełny audyt WCAG.

## Pliki i ochrona

Zmieniono sześć istniejących plików:

- frontend/src/calendar/calendarComparisons.ts — dodatkowy kierunek delty;
- frontend/src/calendar/ComparisonTooltip.tsx — opcjonalne użycie kierunku;
- frontend/src/calendar/CalendarPage.tsx — włączenie tylko w Wszystko i legenda;
- frontend/src/calendar/earningsComparison.ts — tekst i znak z tego samego obliczenia;
- frontend/src/calendar/UnifiedEarningsValues.tsx — niezależne klasy obu linii;
- frontend/src/calendar/unifiedCalendar.css — dwie klasy kolorów ograniczone do Wszystko.

Dodano frontend/src/calendar/changeDirection.ts i changeDirection.test.tsx
oraz ten raport. Nie zmieniono globalnego CSS, EarningsCalendar, backendu,
F2, zależności, lockfile, CI, Forecast, Market Cap lub monitora.

Zapisano manifest 472 wejściowych plików i pełny diff. **466 plików
pozostało byte-identycznych**; w sześciu koniecznych edycjach zachowano
wcześniejsze prace, także wcześniejsze hunki CalendarPage. Pozostałe
chronione pliki i F2 są nietknięte. Odczyty SQL miały wymuszone read-only.
Monitor Earnings pozostaje activated=true/completed. Cache Market Cap
zachował SHA 94ac71ba663564add359f1740d1c8b9311d1322b6094692b477879ce4628d799.
Zwykła praca makro nie była wyłączana; nie deklaruje się niezmienności
wszystkich jego autonomicznych zapisów.

Własny Chrome zakończono po sprawdzeniu PID/argumentów przez CDP.
Normalne PostgreSQL, API i Vite pozostają działające. Logi, manifesty,
snapshoty i screenshoty są ignorowane w data/raw/calendar-direction-colors-2026-11-06.
Końcowy Git: **20 modified / 52 untracked**, indeks pusty, main/HEAD bez zmian.
Bez reset, clean, git add, amend, force lub globalnego formatowania.
