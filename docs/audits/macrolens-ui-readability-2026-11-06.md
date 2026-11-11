# MacroLens — czytelność UI i podglądów Przeglądu

06.11.2026, Europe/Warsaw, C:\Projects\macrolens. Wdrożono bezpośrednio
w działającym lokalnym frontendzie. Bez stagingu, commita i pusha.

## Zmiany

1. Nagłówki sekcji mają 1,8 rem, zgodnie z Kalendarzem. Wybrane wykresy
   zaczynają się od kategorii i zakresów, bez powtórzonego MACROLENS
   i tytułu „Wykresy historyczne”. Zachowano nazwany region dla czytników,
   domyślną zakładkę i bezpośrednie linki do wskaźników.
2. Kreski w liczbowych komórkach kalendarza mają natywny tooltip i opis
   dostępności: potwierdzony brak publikacji, niepotwierdzony okres,
   brak zweryfikowanego Previous, brak prognozy lub porównywalnej pary.
   Przyczyny wynikają z dostępnych pól API. Null Previous nie jest uznawany
   za dowód nieistnienia raportu lub splitu. Bez zakodowanych wyjątków
   tickerów. Zero pozostaje liczbą. Brak kapitalizacji też ma opis.
3. Current/Previous w tabelach mają spójne wyróżnienie i cyfry tabelaryczne.
   Poprzednie EPS/Revenue w Wyniki mają wielkość tekstu taką jak bieżące.
   Prognozy i brakujące wartości pozostają spokojniejsze. Zachowano
   dotychczasowe formatery, precyzję, jednostki, waluty i kolory kierunku.
4. Podglądy w Przeglądzie nie dziedziczą wyrównania liczbowych komórek
   do prawej ani ich grubości. Proza jest wyrównana do lewej, ma normalną
   grubość i interlinię 1,55; etykiety pozostają wyróżnione w linii tekstu.
   Podglądy zmian również używają istniejącego ograniczania do okna,
   z zamykaniem i powrotem fokusu. Same kolumny liczb nadal są wyrównane
   do prawej. Nie zmieniono treści ekonomicznych ani obliczeń Przeglądu.

## Walidacja

- Pełny frontend: **941 passed / 44 pliki**, 62,38 s.
- TypeScript noEmit i build passed; build 4,41 s, największy chunk 407,05 kB.
- Rzeczywisty Chrome/API: **582 kontrole / 46 odpowiedzi HTTP 200**,
  PL/EN i 1366/390 px. Wszystkie dostępne podglądy Przeglądu, wyrównanie,
  grubość, granice okna, zamknięcie/focus, brak overflow; mniejsze nagłówki,
  kolejność zakładek, sześć/osiem/siedem kolumn kalendarza, natywne wskazówki
  braków, zachowane 14 nowcastów i guidance. Zero błędów JS/console.error.
- Obejrzano desktop PL i mobile PL Przeglądu oraz Eksplorację danych.
  Zrzuty końcowe wykonano po zakończeniu animacji otwarcia podglądów.
- Nowe testy odróżniają null od zera, publikację zaplanowaną od
  niepotwierdzonej i brak porównywalnego EPS od nieudowodnionego splitu.

## Pliki i ochrona

Zmienione źródła:

- frontend/src/styles.css
- frontend/src/charts/ChartsPage.tsx
- frontend/src/brief/EconomyBrief.tsx — tylko użycie bounded w istniejącym tooltipie
- frontend/src/calendar/CalendarPage.tsx
- frontend/src/calendar/EarningsCalendar.tsx
- frontend/src/calendar/UnifiedEarningsValues.tsx
- frontend/src/calendar/earnings.css
- frontend/src/calendar/unifiedCalendar.css

Nowe: frontend/src/calendar/MissingValue.tsx i MissingValue.test.tsx.
Zaktualizowano asercje w ChartsPage.test.tsx, language.test.tsx,
navigation/routes.test.tsx i UnifiedCalendar.test.tsx. Dotychczasowe
niezacommitowane hunki zachowano poza niezbędnymi zmianami tego etapu.
**476/488 zastanych plików są byte-identyczne**, w tym F2; pozostałe
12 zawiera opisane zmiany. Ten raport jest nowym plikiem.

Wszystkie **155 artefaktów F1** nadal zgodne. Bez zmian app/config,
backendu, danych, SQL, importu, źródeł, monitorów, zależności lub lockfile.
Zwykłe procesy aplikacji i ich odświeżanie pozostały aktywne; nie deklaruje
się zamrożenia całego makro. Własny Chrome na 9343 zakończono po kontroli
PID, portu i profilu. Normalne API 8000 i Vite 5173 działają.
Manifesty wejściowe, pełny diff, logi i zrzuty są ignorowane w
data/raw/ui-readability-2026-11-06. Indeks pusty, bez reset/clean/amend/force
i globalnego formatowania.
