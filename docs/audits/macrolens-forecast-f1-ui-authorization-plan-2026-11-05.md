# MacroLens — osobny plan autoryzacji F1 dla Calendar UI

Przygotowano 05.11.2026, Europe/Warsaw, na wyraźne rozszerzenie zakresu przez
użytkownika: „Tak, przygotuj też osobny plan F1”. **Propozycja, bez wykonania.
ready_for_apply=false.** Zgoda dotyczy przygotowania planu, nie zapisu policy.

## Powiązanie z konkretną poprawką

[Patch Calendar](../patches/macrolens-calendar-ui-cleanup-2026-11-05.patch)
ma SHA-256 `aeee918881db29a3228cfdeef5882f276eed8deffbdc87bf2c406ee5e42f3338`.
Obejmuje osiem zmienionych i dwa nowe pliki frontend/src. Manifest przed/po,
pełne 260 obecnych oraz 262 kandydackie artefakty są w ignorowanym
`data/raw/calendar-ui-cleanup-2026-11-05/f1-ui-authorization-proposal.json`.
Kanoniczny hash tej **propozycji**, nie tokenu APPLY:

`d57df02ca2f04d208a63b8c54896154930f0219eb5a48a2869240f56acb824d2`

Obecna autoryzacja nadal wskazuje plan
`33fb364f3f518a193d7d451c9dfad6f1d5e005eec2a67c8a01ab626c6c531289`.
Target: localhost:5432/macrolens, PG17, rola macrolens, OID 16384,
klaster 7682090371041935398. Tożsamość zweryfikowano read-only.

`app/database/activate_forecast_f1.py:21` obejmuje hashem cały frontend/src,
łącznie z testami. `authorized()` porównuje ten manifest z tokenem i niezmienną
policy. `policy_row()` wymaga dokładnie jednego activation-policy. Istniejące
prepare odrzuca już aktywowany store. Zatem dotychczasowy runner nie obsługuje
tej migracji. Sam patch UI zmieniłby manifest i zatrzymał F1.

## Proponowana implementacja następnego etapu

1. W osobnej kopii przygotować kontrolowany runner prepare/apply/verify rewizji
   autoryzacji oraz świadomy rewizji odczyt runtime. Zachować walidację pierwotnej
   policy, targetu, schematu, zależności, danych referencyjnych i wszystkich
   artefaktów. Nie usuwać frontendu z manifestu i nie pomijać kontroli hashy.
2. Przewidzieć append-only wpis `activation-ui-revision` w istniejącym
   forecast_refresh_checks, wskazujący poprzedni plan, pełny nowy manifest,
   dokładny patch, target i nowy hash planu. Stara activation-policy pozostaje
   bez UPDATE/DELETE. Nie dodawać kolejnego activation-policy. Runner musi
   odrzucać nieciągłą/obcą rewizję i sprawdzać idempotencję. Ten format jest
   propozycją wymagającą walidacji z obecnym SQL guardem, nie gotowym payloadem.
3. Zamrozić również finalny kod runnera i runtime. Liczba 262 dotyczy tylko
   kandydackiego UI; przyszłe zmiany backendu zmienią końcowy manifest i hash.
   Nie przedstawiać obecnej propozycji jako wykonywalnego planu.
4. Wykonać świeży pełny backup normalnego targetu, TOC i pełny restore na
   własnym PG17. Na pełnym klonie przetestować migrację, rollback transakcji,
   konkurencyjność, błędny target/hash, częściowy stan, idempotencję,
   przerwanie procesu i restart. Potwierdzić wcześniejsze dane, katalogi,
   runtime F1 i Earnings oraz rzeczywiste API/Chrome poprawionego UI.
5. Przygotować finalny kompletny plan z nowym pełnym hashem. Dopiero wtedy
   uzyskać osobną zgodę na konkretny target, hash i okno wdrożenia.

## Przejście środowiska i granice

Plików aplikacji, transakcji PostgreSQL i tokenu nie można uznać za jeden
atomowy zapis. Finalna procedura musi jawnie ustalić krótkie okno wdrożenia,
obsługę procesu API/autoreload oraz wznowienie workera po niezależnej
weryfikacji. Nie wolno najpierw podmienić UI i liczyć na automatyczną naprawę
policy. Po zgodzie: kontrolowany zapis rewizji, weryfikacja i dopiero wydanie
nowego tokenu/wznowienie runtime w przetestowanej kolejności. Przerwanie przed
COMMIT wycofuje transakcję. Cofnięcie po COMMIT wymaga osobnej decyzji;
bez automatycznego restore normalnej bazy.

Zachować wszystkie prognozy, wersje i freezes; stan sprawdzony teraz to
20 vintages, sześć null freezes i dwa checks. Nie importować nowych prognoz
ani nie zmieniać zakresu Cleveland, guidance, cutoff, praw lub cooldown.
Zmienia się tylko autoryzacja konkretnej prezentacji UI i konieczny kod tej
autoryzacji. Monitor Earnings, Actual/Previous, Market Cap, F2 oraz makro
pozostają poza zakresem. Dane zmienne podczas zwykłej pracy trzeba ocenić
ponownie przy finalnym prepare; nie utrwalać dzisiejszych liczników jako
bezterminowego warunku.

W tym etapie nie zmieniono żadnego normalnego artefaktu F1, tokenu, policy
lub wiersza SQL. Nie wykonano restartu, stagingu, commita ani pusha.
