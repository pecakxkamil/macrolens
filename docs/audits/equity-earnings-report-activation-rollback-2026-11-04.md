# E2D Activation — osobny plan cofnięcia po COMMIT, niewykonany

Nie jest zgodą na rollback. Wymaga osobnej decyzji, receipt apply,
zgodnej tożsamości bazy i świeżej kopii. Nie uruchamiać rollbacków E2A/B/C.

W jednej osobno zatwierdzonej transakcji SERIALIZABLE, pod lockami
726530019 i 726530020, lock_timeout=5s i statement_timeout=120s:

1. Potwierdzić target/klaster/OID/rolę i pełne hash/count wszystkich tabel
   z receipt. Późniejsze dokumenty, obserwacje, korekty, nowe zależności
   lub zmiana pierwotnych danych zatrzymują plan; nie usuwać ich automatycznie.
2. Potwierdzić manifest 27/46 i pełną historię oraz wykluczyć zależne widoki,
   FK, funkcje lub inne obiekty. Jakakolwiek niespodziewana zależność oznacza
   odmowę. Nie używać CASCADE lub wyłączać append-only do DELETE historii.
3. Po osobnym przeglądzie narzędzia usunąć wyłącznie
   earnings_report_observations, earnings_report_documents i funkcję
   earnings_report_guard() zwykłym DROP bez CASCADE. Nie usuwać firm,
   aliasów, okresów, eventów, dat ani dokumentów/obserwacji E2B.
4. Przed COMMIT porównać pełne pierwotne 21 tabel i schematy z planem
   aktywacji. Błąd wycofuje całą transakcję, także DROP.

Nie dostarczono automatycznego rollbacku po udanym COMMIT. Zmiany makro
po wznowieniu aplikacji wymagają osobnego przeglądu, bez nadpisywania ich
starszą kopią. Pełne odzyskiwanie najpierw do nowej bazy przez pg_restore
--exit-on-error --single-transaction --no-owner --no-acl, potem porównanie
i osobna decyzja. Nigdy automatycznie nie nadpisywać macrolens.
