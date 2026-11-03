# E2B Activation — osobny plan cofnięcia po COMMIT

**Plan niewykonany. Nie jest upoważnieniem do cofnięcia aktywacji.**
Wymaga osobnej zgody na konkretny target, hash planu aktywacji i receipt
z zakończonego apply. Nie uruchamiać dawnego rollbacku E2A.

1. Potwierdzić host/port/bazę/rolę, OID i identyfikator klastra z receipt.
   Uzyskać świeżą kopię i stan przed cofnięciem. W jednej transakcji
   SERIALIZABLE ustawić lock_timeout=5s i statement_timeout=120s,
   search_path public,pg_catalog oraz locki 726530019 / 726530020.
2. Porównać bieżącą sygnaturę schematu i pełne SHA-256/row counts
   tabel z receipt `after_snapshots`. Jakakolwiek późniejsza korekta,
   nowa obserwacja, nowy dokument lub zmiana E2A zatrzymuje ten plan.
   Zmiany makro wymagają ponownego przeglądu, bez nadpisywania ich kopią.
3. Zweryfikować, że cztery period_id / event_id z `additions` zostały
   utworzone przez zatwierdzone apply. Wszystkie pierwotne wiersze sześciu
   tabel E2A muszą być identyczne z `original_e2a_rows` planu. Tej listy
   nie wolno budować po tickerze, bieżącej dacie lub liczbie wierszy.
4. Wykluczyć nowe zależności: date confirmations i source evidence dla
   czterech eventów, inne tabele/FK, widoki lub funkcje zależne od nowych
   obiektów. Każda niespodziewana zależność zatrzymuje cofnięcie. Nie
   usuwać takich danych i nie stosować CASCADE.
5. Dopiero po osobnym zatwierdzeniu usunąć w tej samej transakcji
   `earnings_financial_observations`, `earnings_financial_documents`
   i `earnings_financial_guard()` zwykłym DROP bez CASCADE. Następnie
   usunąć wyłącznie cztery event_id z receipt, po nich cztery period_id.
   Nie usuwać spółek, aliasów ani żadnych date confirmations/evidence.
   Nie usuwać historycznych AMZN Q3 / INTC Q3, przyszłej NVDA Q3 lub Q4.
6. Przed COMMIT porównać wszystkie pierwotne wiersze E2A i wszystkie
   tabele/schemat makro ze stanem przed cofnięciem. Błąd lub różnica
   powoduje rollback całej transakcji, łącznie z DROP i DELETE.

Nie dostarczono automatycznie uruchamianego rollbacku. Ten dokument
zamraża zakres; wykonanie wymaga osobnego przeglądu narzędzia i zgody.
W tym etapie testowano wycofanie nieudanego DDL/importu w transakcji,
nie wykonanie powyższego planu po COMMIT.

Gdy bezpieczne cofnięcie jest niemożliwe, pozostawić stan i podać powód.
Nie przywracać automatycznie całej normalnej bazy starszą kopią. Pełne
odzyskanie najpierw do nowej bazy przez pg_restore --exit-on-error
--single-transaction --no-owner --no-acl, potem porównanie i odrębna decyzja.
