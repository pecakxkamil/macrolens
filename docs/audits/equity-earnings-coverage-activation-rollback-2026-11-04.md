# E2C Activation — plan cofnięcia po COMMIT, niewykonany

Nie jest zgodą na rollback. Wymaga osobnej decyzji, receipt udanego apply,
zgodnej tożsamości bazy i świeżej kopii. Nie uruchamiać rollbacków E2A/E2B.

Porównać aktualny schemat i pełne dane z receipt; późniejsze confirmations,
aliasy, dokumenty finansowe lub inne zależności zatrzymują cofnięcie.
Wyłącznie w osobno zatwierdzonej transakcji SERIALIZABLE, pod lockami
726530019/726530020 i limitami 5s/120s, rozważyć usunięcie dokładnie
nowych ID z manifestu w kolejności zależności oraz przywrócenie starego
CHECK. Bez CASCADE, bez UPDATE/DELETE pierwotnych rekordów i bez usuwania
nowych poprawnych zapisów innych etapów. Append-only triggery blokują
usuwanie historii; ich ewentualna zmiana wymaga osobnego narzędzia,
przeglądu i zgody. Ten etap nie dostarcza automatycznego rollbacku po COMMIT.

Nie nadpisywać normalnej bazy starszą kopią. Pełne odzyskanie najpierw
przetestować do nowej bazy przez pg_restore --exit-on-error
--single-transaction --no-owner --no-acl, następnie porównać dane
i uzgodnić osobną decyzję. Błąd przed COMMIT wycofuje całą transakcję
aktywacji, łącznie ze zmianą CHECK i seedem.
