# MacroLens — etap 3D: FT900 U.S. International Trade in Goods and Services

Weryfikacja: **29.10.2026**, Europe/Warsaw, `C:\Projects\macrolens`.
Gałąź `main`, HEAD **`cae63e39f9de1a434b0c98df6525ee9f878eb360`**.
Dodano oficjalny harmonogram FT900 i jeden bezpośredni odczyt salda łącznego
Census/BEA. **Bez stagingu, commita i pusha.** Pięć wcześniejszych plików
zachowano byte-identycznie; sprawdzono ich SHA-256 przed i po pracy.

## 1. Stan początkowy i zakres

Przeczytano audyty priorytetów i Empire State, aktualny schemat oraz procedurę
`python -m app.database.init_db`, importer i magazyn dokumentów 3C, binding
kalendarza, adaptery Census/BEA, koordynator, API, frontend i testy.
W kodzie, katalogu i konfiguracji nie było FT900/BOPGSTB. Rzeczywista PostgreSQL
w transakcji read-only (`transaction_read_only=on`) nie miała tych serii ani
dokumentów źródła `census_bea_ft900`. Stan ten zweryfikowano, zamiast przyjmować
go wyłącznie z wcześniejszego audytu.

Źródła produkcyjne są bezpośrednie. FRED służył tylko porównaniu na stronie
serii; nie dodano BOPGSTB do katalogu, mapowań, obserwacji lub ALFRED.
Nie zmieniono metodologii istniejących publikacji, MCI/PIT ani kart Overview.

## 2. Definicja i odrębność publikacji

Pełny **U.S. International Trade in Goods and Services (FT900)** opracowują
**U.S. Census Bureau i U.S. Bureau of Economic Analysis**. Jedna miesięczna
publikacja oznacza jedno wydarzenie i jeden wiersz miary:
**Total Goods and Services Balance, Seasonally Adjusted, Balance of Payments Basis**.

```text
Saldo w mln USD = Exports Total − Imports Total
Actual w mld USD = saldo w mln USD / 1000
Previous = saldo za bezpośrednio poprzedni miesiąc, również / 1000
Difference = Actual − Previous, w mld USD
```

Deficyt ma znak ujemny, nadwyżka dodatni. Nie użyto wartości bezwzględnej,
m/m, annualizacji, deflatora, goods-only Census basis ani wkładu eksportu netto
do realnego GDP. Eksport i import są wejściami/provenance tej samej wersji
arkusza, bez osobnych wydarzeń i pełnoprawnych wierszy wyników.

Osobne tabele **Advance Economic Indicators** i **FT900a — Steel Products**
nie są źródłem dat lub wyników FT900. M3 i GDP również nie zastępują FT900.
Parser harmonogramu ogranicza się do własnej sekcji FT900; parser PDF wymaga
własnego pełnego tytułu, miesiąca, daty, zegara i nagłówka salda goods and services.
Osobnego BEA Annual Update nie dodano jako nowego wydarzenia.

## 3. Oficjalny harmonogram

Wykorzystano [tabelę FT900 Census](https://www.census.gov/foreign-trade/schedule.html)
oraz odrębnie wybrane wiersze [BEA full schedule](https://www.bea.gov/news/schedule/full).
BEA potwierdza wcześniejsze daty publikacji w 2026; Census podaje aktualne
konkretne terminy 2026–2027 i jawne TBD. Przy nakładaniu się okresów daty muszą
być zgodne. Konflikt nie jest rozstrzygany arbitralnie datą pobrania.

Łącznie zapisano **25 wydarzeń**: 13 dat publikacji w 2026 i 12 w 2027.
Każda ma 08:30 `America/New_York`. Poniżej pełny zapisany zakres; okres jest
miesiącem statystycznym, a nie miesiącem daty publikacji.

| Publikacja | Okres | Godzina PL |
| --- | --- | --- |
| 08.01.2026 | X 2025 | 14:30 |
| 29.01.2026 | XI 2025 | 14:30 |
| 19.02.2026 | XII 2025 | 14:30 |
| 12.03.2026 | I 2026 | **13:30** |
| 02.04.2026 | II 2026 | 14:30 |
| 05.05.2026 | III 2026 | 14:30 |
| 09.06.2026 | IV 2026 | 14:30 |
| 07.07.2026 | V 2026 | 14:30 |
| 04.08.2026 | VI 2026 | 14:30 |
| 03.09.2026 | VII 2026 | 14:30 |
| 06.10.2026 | VIII 2026 | 14:30 |
| 04.11.2026 | IX 2026 | 14:30 |
| 08.12.2026 | X 2026 | 14:30 |
| 07.01.2027 | XI 2026 | 14:30 |
| 04.02.2027 | XII 2026 | 14:30 |
| 09.03.2027 | I 2027 | **14:30** |
| 06.04.2027 | II 2027 | 14:30 |
| 05.05.2027 | III 2027 | 14:30 |
| 09.06.2027 | IV 2027 | 14:30 |
| 07.07.2027 | V 2027 | 14:30 |
| 05.08.2027 | VI 2027 | 14:30 |
| 08.09.2027 | VII 2027 | 14:30 |
| 06.10.2027 | VIII 2027 | 14:30 |
| 04.11.2027 | IX 2027 | 14:30 |
| 07.12.2027 | X 2027 | 14:30 |

XI i XII 2027 są **TBD**. API zachowuje listę tych okresów, bez wymyślonych
dat 2028. Przeliczenie stosuje IANA, nie stałe UTC−5 ani stałe sześć godzin.
09.03.2027 poprzedza zmianę czasu w USA, dlatego daje 14:30 PL; syntetyczny
16.03.2027 daje 13:30 PL, lecz nie jest dopisanym terminem.

ID **`ft900:YYYY-MM:monthly`** zależy od miesiąca statystycznego. Nakładające
się dowody są deduplikowane. Zmiana daty zachowuje ID i historię; krótszy
harmonogram lub błąd nie usuwa ostatnich potwierdzonych wydarzeń.

## 4. Zbadany Exhibit 1 XLSX

[Bieżąca strona FT900](https://www.census.gov/foreign-trade/Press-Release/current_press_release/index.html)
rzeczywiście udostępnia [Exhibit 1 XLSX](https://www.census.gov/foreign-trade/Press-Release/current_press_release/exh1.xlsx).
Pobrany arkusz ma 57 zapisanych wierszy, trzy lata 2024–2026, SA oraz jednostkę
mln USD. Nagłówki grupujące Balance / Exports / Imports znajdują się nad
podkolumnami Total / Goods / Services. Na końcu są puste przyszłe miesiące,
wiersz poprzedniej opublikowanej wersji lipca i przypis BOP.

Parser ZIP/XML używa standardowej biblioteki, bez instalacji nowego silnika
Excel. Rozwiązuje relacje workbook/worksheet i shared/inline strings; nie
zakłada właściwej nazwy ani aktywnego arkusza. Wymaga dokładnie jednego
właściwego tytułu Exhibit 1, SA, jednostki **In millions of dollars** i BOP basis.
Scalone nagłówki są rozwijane wyłącznie do rozpoznania kolumn. Właściwe pola
Total są wykrywane semantycznie, także po zamianie kolejności grup.

W kontrolowanym pliku VIII to **B46 / E46 / H46**: saldo / eksport / import.
Te adresy są zapisanym wynikiem rozpoznania, nie stałymi parsera.
Rok pochodzi z jawnego wiersza roku. Miesiące mają własne tożsamości;
sumy roczne/YTD i „as published last month” nie stają się dodatkowymi obserwacjami.

Zera, ujemne saldo, przecinki tysięcy i `(R)` są obsługiwane. Oznaczenie rewizji
pozostaje metadanymi. Niekompletna trójka liczb, niewłaściwy typ, niefinitywność,
duplikat okresu, wewnętrzny pusty historyczny wiersz lub niejednoznaczne nagłówki
powodują błąd. Całkowicie puste przyszłe miesiące nie tworzą obserwacji.
Formuły w wejściowych komórkach są odrzucane; nie ma wykonywania Excel,
zewnętrznych relacji lub encji XML. Sprawdzane są również ZIP i limity rozmiaru.

Wszystkie trzy wartości są z tego samego snapshotu. Równanie eksport − import
musi zgadzać się z saldem z tolerancją **1,5 mln USD**, wynikającą z trzech
niezależnie zaokrąglonych liczb do mln. Dla VII: 310723 − 403550 = −92827,
wobec drukowanego −92826; różnica 1 mln jest zgodna z jawną uwagą arkusza.
Nie poprawiono drukowanego salda dla uzyskania idealnej równości.

## 5. Bezpieczny Actual i dokument publikacji

Archiwalne URL-e znaleziono na [oficjalnej liście Census](https://www.census.gov/foreign-trade/Press-Release/ft900_index.html),
bez konstruowania niezweryfikowanych adresów. Własny PDF potwierdza miesiąc,
pełny FT900, datę i 08:30 EDT/EST. Data i dzień tygodnia oraz IANA muszą być
spójne z harmonogramem. Zestaw steel/advance nie przechodzi tej walidacji.

Latest Actual wymaga opublikowanego własnego raportu, dokładnego miesiąca
Exhibit 1, właściwych pól i poprawnej arytmetyki. Bilans najnowszego miesiąca
musi zgadzać się z komunikatem w granicach jego rzeczywistego zaokrąglenia;
np. 0,1 mld w komunikacie oznacza tolerancję 50 mln, a 0,01 mld — 5 mln.
Konflikt nie jest naprawiany ręcznym wpisaniem wyniku.

Nowy PDF przy starym XLSX pozostawia nowy Actual pusty. Nowy miesiąc XLSX bez
własnej publikacji nie jest przyjmowany jako potwierdzenie wyniku. Sam zegar,
nowy timestamp lub nowy hash niczego nie publikuje. Nie ma fallbacku do FRED
ani liczbowego fallbacku z PDF. PDF jest niezależnym dowodem publikacji/walidacji,
a źródłem obserwacji pozostaje Exhibit 1.

API rozróżnia harmonogram, dokument, walidację Exhibit 1, brak nowego okresu,
przyszły Actual, rewizję i błąd źródła. Dostępny PDF z brakującym zweryfikowanym
wierszem ma osobną przyczynę `ft900_exhibit1_unconfirmed`. Błąd źródła pozostaje
błędem/partial również wtedy, gdy można pokazać wcześniejszy poprawny wynik.

## 6. Kontrolowane dane i porównanie ekonomiczne

Zapisano tylko **cztery poziomy V–VIII 2026**. Maj jest potrzebnym kontekstem
Previous dla czerwca; bez własnego PDF nie otrzymuje przez to Actual majowego
wydarzenia. Nie pobierano całej historii obserwacji ani archiwów XLSX ZIP.

| Publikacja / okres | Saldo źródłowe mln USD | Actual mld USD | Previous mld USD | Difference mld USD |
| --- | ---: | ---: | ---: | ---: |
| 04.08 / VI 2026 | −71182 | −71,182 | −75,752 | +4,570 |
| 03.09 / VII 2026 | −92826 | −92,826 | −71,182 | −21,644 |
| 06.10 / VIII 2026 | −105572 | −105,572 | −92,826 | **−12,746** |
| 04.11 / IX 2026 | — | **—** | **−105,572** | — |
| 08.12 / X 2026 | — | **—** | — | — |
| 07.01.2027 / XI 2026 | — | **—** | — | — |

Forecast jest wszędzie pusty, `consensus_status=not_integrated`. Previous oznacza
dokładnie poprzedni miesiąc; dla X nie podstawiono ostatniego dostępnego VIII.
Przyszłe Actual mają `not_yet_published`, bez syntetycznych obserwacji.

Dla VIII: **315182 − 420754 = −105572 mln USD**. Wartości rozpoznano z arkusza,
nie wpisano ich do kodu aplikacji. [Komunikat BEA za VIII](https://www.bea.gov/news/2026/us-international-trade-goods-and-services-august-2026)
niezależnie potwierdza deficyt 105,6 mld i poprzedni zrewidowany 92,8 mld.
MacroLens zachowuje znak salda i dokładność źródłową; nie zmienia −105,572
na dodatnią wielkość deficytu. Zaokrąglenia komunikatu nie zastępują poziomów.

Przeczytano własne raporty [VI](https://www.census.gov/foreign-trade/Press-Release/ft900/ft900_2606.pdf),
[VII](https://www.census.gov/foreign-trade/Press-Release/ft900/ft900_2607.pdf)
i [VIII](https://www.census.gov/foreign-trade/Press-Release/ft900/ft900_2608.pdf).
Ich nagłówki podają odpowiednio deficyt **73,3 / 88,6 / 105,6 mld USD**.
Bieżące wartości VI/VII różnią się od dawnych komunikatów wskutek późniejszych
rewizji: −71,182 zamiast zaokrąglonego −73,3 oraz −92,826 zamiast −88,6.
Różnic nie ukryto; historyczny API jest current-vintage i sygnalizuje je.
Raport VIII potwierdza już zrewidowany lipiec 92,8. Te porównania nie tworzą
kompletnej historii dokładnych first printów.

Diagnostycznie [FRED BOPGSTB](https://fred.stlouisfed.org/series/BOPGSTB)
pokazuje V −75752, VI −71182, VII −92826 i VIII −105572 mln USD — zgodnie
z bieżącym Exhibit 1. Nie użyto FRED API ani nie importowano jego szeregu.

## 7. Magazyn, provenance i rewizje

Ponownie wykorzystano istniejące **publisher_documents**, **series** i
**observation_vintages**. Źródło to `census_bea_ft900`, lokalny identyfikator
`CENSUS_FT900_TOTAL`. W bazie pozostają dokładne wartości w mln jako NUMERIC;
Decimal służy walidacji i zapisowi. API zwraca liczbowe mld oraz dokładne
`source_value_millions` / `previous_source_value_millions`, źródłowe pola,
arkusz, adresy komórek, jednostkę, SA/BOP i oznaczenie `(R)`.

Obserwacja ma FK do wersji XLSX i własnego dokumentu publikacji. URL bieżącego
XLSX jest zmienny: trwałą tożsamość daje zapisany RAW, rzeczywisty SHA-256,
receipt UUID i czas pobrania, nie sam adres `current_press_release`.
RAW jest adresowany hashem i nie jest nadpisywany. Hash zawsze dotyczy
faktycznych bajtów; błędne HTTP również pozostaje diagnostyką.

Złożona projekcja harmonogramu obejmuje Census, BEA i własne linki dokumentów.
Ma jawny **projection_version** i typ receipt `schedule:<wersja>`; to identyfikator
projekcji, nie fikcyjny hash RAW. Pole `raw_hash` nadal jest hashem odpowiedzi
Census, a metadane zawierają osobny prawdziwy dowód BEA i archiwum.
Zmiana tylko BEA lub dokumentu może więc zostać zachowana przy tym samym
RAW Census. Zwykły identyczny import pozostaje idempotentny.

Przy rewizji salda zapisuje się nowy receipt, poprzednią i nową wartość oraz ID
poprzedniego dokumentu. Starszy znany hash nie zastępuje nowszej wersji.
Wycofanie najnowszego okresu lub usunięcie zachowanego miesiąca odrzuca plik.
Nie ma uniwersalnego dowodu kolejności dla dowolnego nieznanego wcześniej,
nieoznaczonego snapshotu dostawcy; nie przedstawia się tego jako rozwiązania
wszystkich przypadków starych kopii.

Jedna dzienna obserwacja może zostać zaktualizowana tego samego dnia.
RAW i receipts pozwalają odzyskać przechwycone wersje i przejścia rewizji,
lecz nie jest to osobny wiersz SQL każdej zmiany intraday ani pełna historia
wszystkich wersji wydawcy. Pierwsze pobranie bieżącej historii w tym etapie
nie staje się historycznym first printem. Czas planowany, fetched_at i
nieznana chwila pierwszej dostępności są odrębne.

## 8. Rzeczywisty import i koordynator

Pierwszy kontrolowany import rozpoczęto **2026-10-29T11:53:12.349518+00:00**.
Siedem odpowiedzi HTTP 200: Census schedule, BEA schedule, archiwum, trzy
wskazane PDF VI–VIII i jeden Exhibit 1. Poprzednia ograniczona diagnostyka
obejmowała osiem pobrań tych źródeł, w tym bieżącą stronę z linkiem XLSX.
Nie pobierano danych innych rodzin. Standardowe RAW znajdują się w ignorowanym
`data/raw/census_bea_ft900/`, a diagnostyka/logi/profile w
`data/raw/ft900-trade-2026-10-29/`.

Zwykły adapter ma **pięć żądań**: dwa harmonogramy, archiwum, najnowszy własny
PDF i XLSX. Starsze dwa PDF były wyłącznie kontrolowanym zakresem audytu.
Adapter korzysta z dotychczasowego advisory lock, budżetu, cooldown i wolnego
interwału **6 godzin**, bez nowego pollera/usługi lub intensyfikacji innych źródeł.
Zapis dokumentów, harmonogramu, obserwacji i końcowego statusu kontroli jest
transakcyjny; błąd SQL wycofuje całość. Koordynator publikuje spójną generację
Overview. RAW nieudanego zapisu może pozostać wyłącznie diagnostyką.

Ponowne zwykłe sprawdzenie rozpoczęto **2026-10-29T12:01:27.747253+00:00**.
Pięć żądań, sukces, **4 → 4 obserwacje**, zero zmienionych wyników i brak zmian
`ingested_at`. Pełne pozostałe **1 562 523 obserwacje** miały identyczny SHA-256
przed/po obu kontrolach: `311f13f59f1759d3157efdf9ac48516441f63db01f0f907a3a23257ed23beb8e`.
Końcowa generacja: **`2cb77320-f4bb-4928-ab35-9cb9abc30702`**.

Przykładowe zachowane hashe kontrolowanych bajtów:

- Exhibit 1: `c65f3ce503ae5866756794c04eac6e6c965e83fbdfa9d69a8b32dec076c2ece5`.
- PDF VI: `a67052e2f6f97dcd8a4fb46530464dc093eea26251b9ca153f658a09957e7eef`.
- PDF VII: `c122b8ccee947c58859597a7549bb5dcb6691add3e405180ab915d43f6c43aa0`.
- PDF VIII: `77f2632c996c1545827eac6be06fc0f0f730876f8711afb4a1f001f9c1ea2826`.

Nie gwarantujemy wyniku dokładnie o 08:30 ET. PDF i XLSX mogą aktualizować się
w różnych chwilach; interwał sprawdzania może opóźnić odczyt. Brak jest pomiaru
latencji kolejnej nowej publikacji. Poprawne pobranie historii nie jest SLA.

## 9. Schemat PostgreSQL i osobna walidacja

**Nie zmieniono schematu ani `init_db`.** Addytywne tabele i nullable FK z 3C
wystarczają; nie dodano tabeli obserwacji ani drugiego cache. Standardową
procedurą instalacji/aktualizacji pozostaje `python -m app.database.init_db`.
W rzeczywistej bazie użytkownika nie uruchamiano DDL ani resetu.

Mimo braku migracji dodano jawny test **`tests/postgres_ft900_validation.py`**.
Na wygenerowanej, odrębnej bazie z rzeczywistym PostgreSQL i syntetycznym HTTP
potwierdza on idempotencję, UUID i datetime w provenance, zmianę projekcji BEA,
zachowanie wcześniejszych wierszy FRED/ALFRED, dwie rewizje lipca tego samego
dnia i ich odzyskanie z RAW. Trigger SQL wymusza awarię po zapisach dokumentów:
obserwacje i receipts są wycofane, próba ma error. Test usuwa wyłącznie własną
bazę `macrolens_ft900_test_<uuid>`; baza użytkownika pozostaje bez zmian.
Skrypt jest osobną kontrolą lokalną, poza domyślnym offline pytest.

Pierwsza próba tej kontroli wykryła niedeterministyczny czas ZIP w fixture,
który zmieniał bajty rzekomo identycznego pliku. Ustawiono stały timestamp
syntetycznego ZIP, a pełna kontrola następnie przeszła. Obsłużono także
serializację rzeczywistych UUID/datetime archiwalnych receipts przy projekcji.

## 10. Prawa i atrybucja

[BEA FAQ 147](https://www.bea.gov/help/faq/147) opisuje public-domain informacji
wydawcy, o ile nie wskazano inaczej, i prosi o atrybucję. Sprawdzono również
[polityki Census](https://www.census.gov/about/policies.html) oraz
[DS027](https://www2.census.gov/foia/ds_policies/ds027.pdf): wskazują ogólną
zasadę dla prac pracowników i wyjątki dotyczące cudzych prac oraz możliwej
ochrony poza USA. Nie przeniesiono tych ustaleń na logo, wszystkie materiały
stron, każdą jurysdykcję lub całą aplikację.

Calendar, Overview, API i eksport tekstowy zachowują **U.S. Census Bureau**
oraz **U.S. Bureau of Economic Analysis**, oryginalny tytuł FT900, źródło
Exhibit 1, własny dokument, miesiąc, wersje, przeliczenie mln → mld, informację
o rewizjach i brak sugerowania endorsement. Nie użyto logo. Niezależne warunki
FRED i zgodność całego modelu MacroLens pozostają nierozstrzygnięte; nie
deklaruje się gotowości publicznego demo na podstawie tego etapu.

## 11. UI, API i regresje

EN: **U.S. Trade Balance — Goods and Services**, miara **Trade Balance — SA**.
PL: **Bilans handlowy USA — towary i usługi**, miara **Bilans handlowy — SA**.
Jednostki **USD bn / mld USD**, do trzech miejsc, bez utraty źródłowej wartości
w bazie/API. Różnice pozostają neutralne; nie są prognozą reakcji giełdy.
Istniejąca kategoria Growth and consumer, redakcyjne **★★**, filtry, kolumny,
sortowanie, countdown, układ mobilny i klawiatura pozostają zachowane.

Overview nadal ma sześć kart i najwyżej cztery wydarzenia; nie dodano karty
Trade Balance. Wybór może pominąć FT900 przy większej liczbie ważniejszych
publikacji. Nowa pozycja w przyszłym oknie i atrybucja są sprawdzane w EN/PL.
Odczyt Calendar nie uruchamia importera. FT900 nie przechodzi przez binding
FRED/ALFRED i nie jest dodane do ogólnego katalogu wykresów. Ukryto dla niego
link „View indicator”, który prowadziłby do nieobsługiwanej strony.

Nie zmieniono plików definicji Empire State, istniejących miar Employment,
CPI/PPI/Retail, FOMC, ISM, Michigan lub ADP. Michigan/ADP nadal mają blokadę
liczb. Nie zmieniono metodologii MCI/PIT, istniejących gwiazdek i reguł
konsensusu; poprzednie testy pozostały w zestawie.

## 12. Pełna walidacja

- Backend: **979 passed**, w tym **53 nowe przypadki FT900**; końcowy pełny
  przebieg 38,88 s. Parsery, znaki/zero, SA/BOP/Total, nagłówki i arkusze,
  lata, TBD, IANA/DST, konflikty, tolerancje, puste komórki, formuły/XML/ZIP,
  opóźniony XLSX, przyszłe puste Actual, Previous, stale replay, rewizje,
  idempotencja, RAW, rollback, API i sześciogodzinny cooldown.
- Frontend working tree: **569 passed**, 22 pliki, blokada sieci zgodna z CI.
  Dodano cztery przypadki EN/PL Calendar/Overview. Wynik obejmuje zachowane
  wcześniejsze zmiany użytkownika; nie przypisuje im się nowych testów FT900.
- Production build: **passed**. Główny pakiet **526,91 kB**, ponad 500 kB;
  jawne ostrzeżenie Vite, bez zmiany progu.
- Oddzielna rzeczywista walidacja PostgreSQL: **passed**; bez migracji schematu.
- Rzeczywiste API: VI–VIII oraz cztery wymagane daty 06.10, 04.11, 08.12,
  07.01. Dodatkowo 09.03 i 06.04.2027: 14:30 PL, właściwy miesiąc, pusty
  przyszły Actual/Forecast, jedno wydarzenie i jedna miara, źródłowe mln w API.
- Chrome bez fixture'ów odpowiedzi API: **32 scenariusze**, EN/PL, **1366/390 px**,
  **72 odpowiedzi API HTTP 200**, zero wyjątków JavaScript i overflow.
  VI–VIII i IX–XI, jednostki/znaki/Previous, szczegóły, źródła, filtry kategorii
  i ★★★, brak wygenerowanego 2028, Escape/fokus, sześć kart i limit czterech.
  Obejrzano końcowe zrzuty desktop/mobile. Countdown jest także sprawdzony
  automatycznie po wcześniejszej publikacji tego samego dnia.
- Cała kontrola prawdziwego UI odbyła się pod wspólną blokadą, więc normalne
  POST aplikacji nie uruchamiały innych importerów. Nie podmieniano odpowiedzi
  API ani koordynatora. Po kontroli blokadę zwolniono.
- `git diff --check`: **passed**. Nie pomijano testów i nie zwiększano timeoutów.
  Znany sporadyczny błąd nawigacji MCI nie wystąpił w pełnych przebiegach.

Próby nowych fixture wykryły problem importu helpera i powtórzony pusty miesiąc;
poprawiono fixture. Helper Chrome początkowo wymagał jednostki również w wierszu,
w którym wszystkie liczby są puste; poprawiono helper, zachowując neutralne
kreski UI. Końcowy pełny przebieg jest opisany wyżej. Kontrola wizualna wykryła
też nieobsługiwany link do wykresu FT900; po poprawce powtórzono frontend,
build i pełne Chrome. Nie instalowano nowych pakietów i nie ukrywano ostrzeżeń.

## 13. Pozostałe ograniczenia

Brak konsensusu, kompletnej historii first printów i wszystkich zmian intraday.
Bieżące historyczne poziomy mogą zawierać rewizje miesięczne i roczne.
Są tylko cztery lokalne poziomy V–VIII, nie cały historyczny szereg. TBD XI/XII
2027 nie generuje wydarzeń. Zmiana struktury PDF/XLSX lub sprzeczne dowody mogą
wymagać przeglądu zamiast zgadywania. Nie badano latencji w chwili następnej
publikacji. Pozostają BLS 403 i ograniczenia wcześniejszych integracji oraz
nierozstrzygnięte kwestie całego modelu FRED/PostgreSQL/RAW/cache.

Ręcznie: Calendar → Date range → **06.10.2026**, potem **04.11.2026**,
**08.12.2026** i **07.01.2027**. Sprawdź 14:30, znak ujemny, mld USD, Previous,
źródła i odrębność Advance Goods. Włącz ★★★ — FT900 znika; wybierz Growth and
consumer — pozostaje. Przełącz EN/PL i sprawdź szczegóły, Escape i fokus.

## 14. Końcowy Git — pełna lista

`main` / `cae63e39f9de1a434b0c98df6525ee9f878eb360`, bez zmiany HEAD.
**22 modified, 6 untracked**, pusty staging. Bez commita, pusha, resetu, clean
i zmian historii. Nie uruchamiano nowego CI. Nie rozpoczęto kolejnego etapu.

Zastane, zachowane byte-identycznie i poza zakresem etapu:

- `README.md` — modified.
- `frontend/src/brief/SourceCheckStatus.tsx` — modified.
- `frontend/src/brief/SourceCheckStatus.test.tsx` — modified.
- `frontend/src/styles.css` — modified.
- `docs/audits/calendar-next-releases-priority-2026-10-29.md` — untracked.

Zmodyfikowane w 3D:

- `app/analytics/calendar_agenda.py`
- `app/analytics/calendar_readings.py`
- `app/analytics/overview_refresh.py`
- `app/analytics/release_calendar.py`
- `app/analytics/source_checks.py`
- `frontend/src/api/macrolens.ts`
- `frontend/src/brief/EconomyBrief.tsx`
- `frontend/src/brief/EconomyBrief.test.tsx`
- `frontend/src/brief/briefModel.ts`
- `frontend/src/brief/upcomingEvents.ts`
- `frontend/src/calendar/CalendarPage.tsx`
- `frontend/src/calendar/CalendarPage.test.tsx`
- `frontend/src/calendar/calendarAgenda.ts`
- `frontend/src/calendar/calendarComparisons.ts`
- `frontend/src/calendar/calendarPresentation.ts`
- `frontend/src/i18n/pl.json`
- `tests/conftest.py`
- `tests/test_source_checks.py`

Nowe pliki etapu:

- `app/analytics/ft900_calendar.py`
- `app/ingestion/sync_ft900.py`
- `tests/test_ft900.py`
- `tests/postgres_ft900_validation.py`
- `docs/audits/calendar-ft900-trade-2026-10-29.md` — ten raport.

Sekrety, `.env`, lokalna baza, RAW, cache, logi, profile Chrome i zrzuty nie
wchodzą do zmian repozytorium. Schemat, konfiguracja serii i pięć zastanych
plików pozostają bez zmiany treści.

## 15. Kontrola zamknięcia etapu — 29.10.2026

Stan wejściowy zamknięcia potwierdzono: `main`, HEAD
`cae63e39f9de1a434b0c98df6525ee9f878eb360`, 22 modified, 6 untracked,
pusty staging. Przejrzano pełny diff, nowe moduły, wspólne zależności z Empire,
testy, dokumentację oraz listę ignorowanych plików. Wybrano dokładnie
**23 pliki etapu wymienione w sekcji 14**; nie znaleziono dodatkowych
niezwiązanych zmian. Nie zmieniono `schema.sql`, `init_db`, katalogu serii,
definicji Empire ani innych rodzin i MCI/PIT.

### Metodologia, dane i provenance

Ponownie odczytano rzeczywistą bazę w transakcji read-only
(`transaction_read_only=on`), zweryfikowano hashe wszystkich sześciu zapisanych
receipts FT900 i sparsowano zapisany oficjalny Exhibit 1. Potwierdzono właściwy
arkusz, Total Balance/Exports/Imports, SA, BOP, mln USD, `(R)` oraz zachowanie
drukowanego salda przy różnicy 1 mln w równaniu lipca. Tolerancji 1,5 mln
nie zmieniono. Rzeczywiste GET API ponownie potwierdziły:

| Okres | Actual mld USD | Previous mld USD | Forecast |
| --- | ---: | ---: | --- |
| VI 2026 | −71,182 | −75,752 | — |
| VII 2026 | −92,826 | −71,182 | — |
| VIII 2026 | −105,572 | −92,826 | — |
| IX 2026, 04.11 | — | −105,572 | — |
| X 2026, 08.12 | — | — | — |

Różnica VIII nadal wynosi −12,746 mld USD, bez m/m i bez kierunkowego koloru.
Nie dodawano obserwacji ani nowych pobrań dostawców. Wcześniejsza kontrola
Chrome pozostaje wynikiem wdrożenia, nie nowym przebiegiem zamknięcia.

Sprawdzono 25 stabilnych tożsamości harmonogramu, sześć wymaganych przyszłych
dat i okresów, brak wydarzeń TBD XI/XII 2027 oraz konwersje 12.03.2026 → 13:30
i 09.03.2027 → 14:30 PL. Daty publikacji i okresy są odrębne. Scenariusze
starych PDF/XLSX po terminie, opóźnionego XLSX, miesiąca bez publikacji,
konfliktu ponad zaokrąglenie, starego znanego hasha, zmiany samego hasha
i rewizji starszego miesiąca są w zachowanym zestawie testów.
Sprawdzono także neutralność, źródła Census/BEA, przeliczenie mln → mld,
current-vintage, brak endorsement i brak linku do nieobsługiwanego wykresu FT900.

Przegląd wykrył dwa konkretne przypadki parsera wymagające poprawy:

- Rozwijanie scalonych komórek mogło wypełnić pustą komórkę liczbową wartością
  sąsiednią. Ograniczono je do rozpoznanych nagłówków Balance/Exports/Imports/Period;
  scalony pusty input liczbowy pozostaje błędem.
- Formuła bez zapisanej wartości w pustym przyszłym wierszu mogła zostać
  pominięta razem z wierszem. Kontrola formuł odbywa się teraz przed obsługą
  pustych przyszłych miesięcy i odrzuca także ten przypadek.

Dodano dwa testy regresyjne. To zaostrzenie walidacji, bez zmiany metodologii
lub liczb. Po poprawce zapisany prawdziwy XLSX nadal przechodzi parser.

### Pełna ponowna walidacja i rzeczywisty PostgreSQL

Working tree po poprawkach: **981 passed backend**, **569 passed frontend**
w 22 plikach, poprawny production build **526,91 kB** i `git diff --check`.
Poprzedni pełny backend 979/979 również przeszedł; przyrost do 981 to dwa
opisane przypadki parsera. Nie usuwano ani nie pomijano testów.

Na izolowanej kopii dokładnej zawartości stagingu, z resztą śledzonych
zależności z HEAD i bez pięciu wcześniejszych plików, uzyskano ponownie
**981 passed backend**, **569 passed frontend**, poprawny build **528,96 kB**
oraz poprawną rzeczywistą walidację PostgreSQL. Kopia używa wcześniejszych
wersji SourceCheckStatus/styles z HEAD, co wyjaśnia różnicę rozmiaru pakietu.
Oba buildy zachowują ostrzeżenie ponad 500 kB, bez zmiany progu.
W żadnym pełnym przebiegu zamknięcia nie wystąpił sporadyczny błąd nawigacji MCI.
Nie zwiększano timeoutów i nie zmieniano modułu MCI.

`python tests/postgres_ft900_validation.py` przeszedł na working tree, ponownie
po poprawce i na stagingu. Za każdym razem używał wyłącznie własnej losowo
nazwanej bazy testowej. Sprawdzono idempotencję, rzeczywiste UUID/datetime,
zmianę BEA przy niezmienionym Census, dwie rewizje tego samego dnia,
odzyskiwanie ich z RAW i zachowanie wcześniejszych danych FRED/ALFRED.
Wymuszony błąd SQL wycofał nowe dokumenty oraz obserwacje, zachowując stan sprzed
importu i zapisując error próby. Nie powstały częściowe zatwierdzone dokumenty
importu ani osierocone referencje. Własne bazy testowe usunięto; baza użytkownika
nie była inicjalizowana ani modyfikowana w zamknięciu. Nie było nowej migracji.

### Zatwierdzany zakres i informacje po pushu

Planowany jeden commit: **`Add official FT900 trade balance calendar and readings`**.
Lista 23 plików w sekcji 14 pozostaje dokładnym zakresem stagingu. Przejrzano
pełny staged diff, porównano go z wybraną zawartością, sprawdzono
`git diff --cached --check`, wzorce sekretów i brak artefaktów.
`data/raw/ft900-trade-2026-10-29/probe.py` oraz wszystkie RAW, cache, logi,
profile i zrzuty są ignorowane i nie należą do stagingu.

Pięć plików pozostało poza stagingiem, z identycznymi SHA-256:

- `README.md`
- `frontend/src/brief/SourceCheckStatus.tsx`
- `frontend/src/brief/SourceCheckStatus.test.tsx`
- `frontend/src/styles.css`
- `docs/audits/calendar-next-releases-priority-2026-10-29.md`

Sekcję zapisano przed ostatecznym commitem. Pełny hash i tytuł, wynik zwykłego
pusha, rzeczywisty URL i wyniki GitHub Actions oraz końcowy `git status`
zostaną podane w zewnętrznym raporcie Codexa po ich uzyskaniu. Przed commitem
zdalny `origin/main` wskazywał ten sam `cae63e3`. Sukces lokalny nie jest
deklaracją przyszłego wyniku CI. Standardowy workflow uruchamia offline
backend i frontend/build, bez serwisu PostgreSQL — osobna powyższa kontrola
nie jest częścią jego domyślnego zestawu.

Pozostają current-vintage, brak kompletnej historii first printów i intraday,
TBD XI/XII 2027, brak konsensusu oraz brak SLA publikacji wyniku o 08:30 ET.
Warunki FRED i zgodność całego MacroLens pozostają nierozstrzygnięte.
Nie deklaruje się gotowości publicznego demo ani nie rozpoczyna kolejnego etapu.
