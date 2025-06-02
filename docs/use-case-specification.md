# Specyfikacja przypadków użycia - Renovation Cost Tracker

## UC1: Register Account

**Aktor główny**: User  
**Cel**: Utworzenie nowego konta użytkownika w systemie  
**Poziom**: User Goal  

### Warunki wstępne:
- Użytkownik ma dostęp do systemu
- Email nie jest już zarejestrowany

### Scenariusz podstawowy:
1. Użytkownik wybiera opcję rejestracji
2. System wyświetla formularz rejestracji
3. Użytkownik wprowadza email i hasło
4. System waliduje dane:
   - Email ma poprawny format
   - Hasło spełnia wymagania bezpieczeństwa (min. 8 znaków)
   - Email nie istnieje w systemie
5. System tworzy nowe konto
6. System wysyła potwierdzenie rejestracji
7. Użytkownik zostaje przekierowany do strony logowania

### Scenariusze alternatywne:
- **3a**: Email już istnieje → System wyświetla błąd
- **3b**: Hasło za słabe → System wyświetla wymagania
- **3c**: Niepoprawny format email → System wyświetla błąd walidacji

---

## UC2: Login to System

**Aktor główny**: User  
**Cel**: Zalogowanie się do systemu i otrzymanie tokenu dostępu  

### Warunki wstępne:
- Użytkownik ma zarejestrowane konto

### Scenariusz podstawowy:
1. Użytkownik wprowadza email i hasło
2. System waliduje dane logowania
3. System generuje token JWT
4. System zwraca token i dane użytkownika
5. Użytkownik zostaje przekierowany do dashboard

### Scenariusze alternatywne:
- **2a**: Niepoprawne dane → System wyświetla błąd
- **2b**: Konto zablokowane → System informuje o blokadzie

---

## UC4: Create Project

**Aktor główny**: User  
**Cel**: Utworzenie nowego projektu remontowego  

### Warunki wstępne:
- Użytkownik jest zalogowany

### Scenariusz podstawowy:
1. Użytkownik wybiera opcję "Nowy projekt"
2. System wyświetla formularz projektu
3. Użytkownik wprowadza:
   - Nazwę projektu
   - Budżet (kwotę i walutę)
4. System waliduje dane:
   - Nazwa nie jest pusta
   - Budżet > 0
5. System tworzy projekt i przypisuje do użytkownika
6. System wyświetla potwierdzenie i szczegóły projektu

---

## UC9: Add Expense

**Aktor główny**: User  
**Cel**: Dodanie wydatku do projektu  

### Warunki wstępne:
- Użytkownik jest zalogowany
- Projekt istnieje i należy do użytkownika

### Scenariusz podstawowy:
1. Użytkownik otwiera szczegóły projektu
2. Użytkownik wybiera "Dodaj wydatek"
3. System wyświetla formularz wydatku
4. Użytkownik wprowadza:
   - Kwotę
   - Kategorię (MATERIAL/LABOR/PERMIT/OTHER)
   - Dostawcę/Sprzedawcę
   - Datę
   - Opis (opcjonalnie)
5. System waliduje dane:
   - Kwota > 0
   - Data nie z przyszłości
   - Wszystkie wymagane pola wypełnione
6. System zapisuje wydatek
7. System aktualizuje podsumowanie projektu
8. System wyświetla potwierdzenie

### Scenariusze alternatywne:
- **4a**: Kwota przekracza pozostały budżet → System ostrzega
- **5a**: Błędne dane → System wyświetla błędy walidacji

---

## UC12: View Expense List

**Aktor główny**: User  
**Cel**: Przeglądanie listy wydatków projektu  

### Warunki wstępne:
- Użytkownik jest zalogowany
- Projekt istnieje i należy do użytkownika

### Scenariusz podstawowy:
1. Użytkownik otwiera szczegóły projektu
2. System wyświetla listę wydatków z:
   - Datą
   - Kategorią
   - Kwotą
   - Dostawcą
   - Opisem
3. Lista jest sortowana według daty (najnowsze pierwsze)
4. System wyświetla podsumowanie:
   - Łączny koszt
   - Koszt według kategorii
   - Pozostały budżet

---

## UC13: Filter Expenses

**Aktor główny**: User  
**Cel**: Filtrowanie wydatków według kryteriów  
**Rozszerza**: UC12

### Scenariusz podstawowy:
1. Użytkownik otwiera listę wydatków
2. Użytkownik wybiera filtry:
   - Zakres dat (od-do)
   - Kategoria
   - Dostawca
   - Zakres kwot (min-max)
3. System stosuje filtry
4. System wyświetla przefiltrowaną listę
5. System aktualizuje podsumowania dla filtrów

---

## UC15: View Project Summary

**Aktor główny**: User  
**Cel**: Przeglądanie podsumowania kosztów projektu  

### Warunki wstępne:
- Użytkownik jest zalogowany
- Projekt istnieje i należy do użytkownika

### Scenariusz podstawowy:
1. Użytkownik otwiera szczegóły projektu
2. System wyświetla podsumowanie:
   - Budżet całkowity
   - Wydane środki łącznie
   - Pozostały budżet
   - Procent wykorzystania budżetu
   - Koszty według kategorii (wykres kołowy)
   - Trend wydatków w czasie (wykres liniowy)
   - Liczba wydatków
   - Średni wydatek

---

## UC18: Export to CSV

**Aktor główny**: User  
**Cel**: Eksport danych wydatków do pliku CSV  

### Warunki wstępne:
- Użytkownik jest zalogowany
- Projekt ma wydatki

### Scenariusz podstawowy:
1. Użytkownik otwiera listę wydatków projektu
2. Użytkownik wybiera "Eksportuj do CSV"
3. System może zastosować aktualne filtry
4. System generuje plik CSV z kolumnami:
   - Data
   - Kategoria
   - Kwota
   - Waluta
   - Dostawca
   - Opis
5. System oferuje pobranie pliku
6. Plik ma nazwę: "expenses_[projekt]_[data].csv"

### Scenariusze alternatywne:
- **3a**: Brak wydatków → System informuje o pustej liście
- **4a**: Błąd generowania → System wyświetla komunikat błędu

---

## Reguły biznesowe

### RB1: Budżet projektu
- Budżet musi być liczbą dodatnią
- Waluta domyślna to PLN
- System ostrzega gdy wydatki przekraczają 90% budżetu
- System blokuje dodawanie gdy wydatki przekraczają 110% budżetu

### RB2: Wydatki
- Data wydatku nie może być z przyszłości
- Kwota musi być dodatnia
- Kategoria musi być z predefiniowanej listy
- Opis jest opcjonalny (max 500 znaków)

### RB3: Bezpieczeństwo
- Użytkownik może zarządzać tylko swoimi projektami
- Sesja wygasa po 24 godzinach
- Hasło musi mieć minimum 8 znaków

### RB4: Walidacja
- Email musi być unikalny w systemie
- Nazwa projektu musi być unikalna dla użytkownika
- System używa Decimal dla precyzyjnych obliczeń finansowych