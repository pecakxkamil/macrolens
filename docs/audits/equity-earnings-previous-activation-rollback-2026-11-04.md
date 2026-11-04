# E2E Activation — granice cofnięcia

Przed COMMIT błąd wycofuje razem DDL i 23 snapshoty / 45 metryk w jednej
transakcji SERIALIZABLE. Pierwotne 23 tabele muszą pozostać identyczne.

Po COMMIT nie ma automatycznego rollbacku. Cofnięcie wymaga osobnej decyzji
użytkownika, kontroli późniejszych zależności i świeżego zabezpieczenia danych.
Nie stosować CASCADE, nadpisania normalnej bazy lub wcześniejszego backupu
bez nowej weryfikacji. Nie odtwarzać backupu do normalnego PostgreSQL w tym etapie.

Prepare i testy na własnym klonie nie są zgodą na apply. Zapis do normalnej
bazy wymaga osobnego zatwierdzenia pełnego SHA-256 planu oraz dokładnego
celu, zatwierdzonego okna bez innych klientów, ponownej zgodności danych,
artefaktów, backupu i dowodu restore. Zmiana któregokolwiek zatrzymuje apply.
