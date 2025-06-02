# Renovation Cost Tracker – Dokumentacja architektury wielowarstwowej

## 1. Cel i zakres aplikacji

REST-owe API w FastAPI służące do rejestrowania i monitorowania kosztów remontu mieszkania. Aplikacja udostępnia trzy główne warstwy Domain → Application → Infrastructure (warstwa prezentacji = kontrolery FastAPI). Dane przechowywane są w PostgreSQL, a w testach mogą być uruchamiane na SQLite.

## 2. Wymagania funkcjonalne

| Id  | Wymaganie | Priorytet | Status |
|-----|-----------|-----------|--------|
| F-1 | Rejestracja użytkownika (e-mail, hasło) | Wysoki | ✅ |
| F-2 | Logowanie i otrzymanie tokenu JWT | Wysoki | ✅ |
| F-3 | Utworzenie projektu remontowego (nazwa, budżet) | Wysoki | ✅ |
| F-4 | Dodanie wydatku do projektu (kwota, kategoria, dostawca, data, opis) | Wysoki | ✅ |
| F-5 | Edycja i usuwanie wydatku | Średni | ✅ |
| F-6 | Lista wydatków z filtrami (data, kategoria, dostawca) | Wysoki | ✅ |
| F-7 | Podsumowania projektu: łączny koszt, koszt wg kategorii, pozostały budżet | Wysoki | ✅ |
| F-8 | Eksport wydatków projektu do pliku CSV | Średni | ✅ |
| F-9 | Import wydatków z CSV (opcjonalnie) | Niski | ❌ |

## 3. Wymagania niefunkcjonalne

### 3.1 Wydajność
- Czas odpowiedzi API ≤ 200 ms dla zapytań do cache
- Obsługa do 100 równoczesnych użytkowników
- Baza danych optymalizowana poprzez indeksy na kluczach obcych

### 3.2 Bezpieczeństwo
- Szyfrowanie komunikacji TLS
- Autoryzacja JWT z czasem wygaśnięcia 24h
- Haszowanie haseł bcrypt z salt
- Zabezpieczenia OWASP Top 10
- Walidacja danych wejściowych Pydantic
- Rate limiting na endpointach logowania

### 3.3 Utrzymywalność
- Pokrycie testów ≥ 85%
- Kod zgodny z PEP 8 i zasadami SOLID
- Dokumentacja API automatyczna (OpenAPI/Swagger)
- Clean Architecture z wyraźnym podziałem warstw
- Type hints w całym kodzie

### 3.4 Skalowalność
- Warstwy pozwalają na łatwe dodanie integracji z bank API
- Async/await dla operacji I/O
- Możliwość podmiany bazy danych
- Architektura umożliwia mikroservices w przyszłości

### 3.5 Portowalność
- Obraz docker-compose (FastAPI + PostgreSQL)
- Możliwość podmiany bazy na SQLite w testach
- Zmienne środowiskowe dla konfiguracji
- Kompatybilność z Python 3.11+

## 4. Architektura systemu

### 4.1 Wzorzec Clean Architecture

```
┌─────────────────────────────────────────┐
│              Presentation               │
│        (FastAPI Controllers)            │
├─────────────────────────────────────────┤
│              Application                │
│     (Services + Repository Interfaces)  │
├─────────────────────────────────────────┤
│               Domain                    │
│        (Entities + Value Objects)       │
├─────────────────────────────────────────┤
│             Infrastructure              │
│    (Database + External Services)       │
└─────────────────────────────────────────┘
```

### 4.2 Warstwy systemu

#### Domain Layer
- **Entities**: User, Project, Expense
- **Value Objects**: Money, Category (enum)
- **Business Logic**: metody domenowe w encjach

#### Application Layer  
- **Services**: AuthService, ProjectService, ExpenseService
- **Repository Interfaces**: IUserRepository, IProjectRepository, IExpenseRepository
- **Use Cases**: rejestracja, logowanie, zarządzanie projektami i wydatkami

#### Infrastructure Layer
- **Database**: PostgreSQL z SQLAlchemy async
- **Repositories**: implementacje interfejsów repozytoriów
- **External Services**: JWT token provider, CSV export

#### Presentation Layer
- **API Controllers**: FastAPI routers
- **DTOs**: Pydantic models dla request/response
- **Mappers**: konwersja między domeną a DTOs

## 5. Model danych

### 5.1 Encje domenowe

#### User
- `id: UUID` - unikalny identyfikator
- `email: str` - adres email (unikalny)
- `password_hash: str` - zahashowane hasło
- `created_at: datetime` - data utworzenia

#### Project  
- `id: UUID` - unikalny identyfikator
- `user_id: UUID` - właściciel projektu
- `name: str` - nazwa projektu
- `budget: Money` - budżet projektu
- `created_at: datetime` - data utworzenia
- `expenses: list[Expense]` - lista wydatków

#### Expense
- `id: UUID` - unikalny identyfikator  
- `project_id: UUID` - projekt do którego należy
- `category: Category` - kategoria wydatku
- `amount: Money` - kwota wydatku
- `vendor: str` - dostawca/sprzedawca
- `date: date` - data wydatku
- `description: str` - opis wydatku

#### Money (Value Object)
- `amount: Decimal` - kwota
- `currency: str` - waluta (domyślnie PLN)

#### Category (Enum)
- `MATERIAL` - materiały
- `LABOR` - robocizna  
- `PERMIT` - pozwolenia
- `OTHER` - inne

### 5.2 Schemat bazy danych

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE projects (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR NOT NULL,
    budget_amount DECIMAL(12,2) NOT NULL,
    budget_currency VARCHAR(3) DEFAULT 'PLN',
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE expenses (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    category VARCHAR NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'PLN',
    vendor VARCHAR NOT NULL,
    date DATE NOT NULL,
    description TEXT
);
```

## 6. API Endpoints

### 6.1 Authentication
- `POST /auth/register` - rejestracja nowego użytkownika
- `POST /auth/login` - logowanie i otrzymanie tokenu JWT

### 6.2 Projects
- `POST /projects` - utworzenie nowego projektu
- `GET /projects` - lista projektów użytkownika
- `GET /projects/{id}` - szczegóły projektu
- `GET /projects/{id}/summary` - podsumowanie kosztów projektu

### 6.3 Expenses  
- `POST /projects/{project_id}/expenses` - dodanie wydatku
- `GET /projects/{project_id}/expenses` - lista wydatków z filtrami
- `GET /expenses/{id}` - szczegóły wydatku
- `PUT /expenses/{id}` - edycja wydatku
- `DELETE /expenses/{id}` - usunięcie wydatku

### 6.4 Export
- `GET /projects/{project_id}/expenses/export` - eksport do CSV

## 7. Testowanie i CI/CD

### 7.1 Strategia testowania

#### Piramida testów
```
        E2E (3 scenariusze)
     ┌─────────────────────┐
     │    Playwright       │
     └─────────────────────┘
   ┌───────────────────────────┐
   │   Integracyjne (~30)      │
   │   pytest + SQLite        │
   └───────────────────────────┘
 ┌─────────────────────────────────┐
 │    Unit (>100, ≥85% coverage)  │
 │         pytest                 │
 └─────────────────────────────────┘
```

### 7.2 Rodzaje testów

#### Testy jednostkowe (Unit Tests)
- **Cel**: Testowanie logiki domenowej w izolacji
- **Zakres**: Entities, Value Objects, Services
- **Narzędzia**: pytest, pytest-mock
- **Coverage**: ≥85%

**Przykłady testów:**
```python
def test_money_addition():
    # Test dodawania kwot w tej samej walucie
    money1 = Money(Decimal("100.50"), "PLN")
    money2 = Money(Decimal("50.25"), "PLN")
    result = money1 + money2
    assert result.amount == Decimal("150.75")

def test_project_total_cost():
    # Test kalkulacji łącznego kosztu projektu
    project = Project(...)
    expense = Expense(amount=Money(Decimal("100")))
    project.add_expense(expense)
    assert project.total_cost.amount == Decimal("100")

def test_expense_service_record():
    # Test rejestrowania wydatku
    service = ExpenseService(mock_projects, mock_expenses)
    expense_id = service.record_expense(project_id, ...)
    assert expense_id is not None
```

#### Testy integracyjne (Integration Tests)  
- **Cel**: Testowanie współpracy warstw
- **Zakres**: API endpoints + Database + Services
- **Narzędzia**: pytest + SQLite in-memory + httpx
- **Ilość**: ~30 testów

**Przykłady testów:**
```python
async def test_create_expense_endpoint():
    # Test pełnego flow dodawania wydatku
    response = await client.post(
        f"/projects/{project_id}/expenses",
        json=expense_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    
async def test_database_expense_persistence():
    # Test zapisu i odczytu wydatku z bazy
    await expense_repo.save(expense)
    retrieved = await expense_repo.get(expense.id)
    assert retrieved.amount.amount == expense.amount.amount
```

#### Testy End-to-End (E2E)
- **Cel**: Testowanie scenariuszy użytkownika
- **Narzędzia**: Playwright
- **Scenariusze**: 3 główne user journeys

**Scenariusze E2E:**
1. **Rejestracja → Logowanie → Utworzenie projektu**
2. **Dodanie wydatków → Przeglądanie listy → Filtrowanie**  
3. **Edycja wydatku → Podsumowanie → Eksport CSV**

### 7.3 Narzędzia testowe

#### pytest + rozszerzenia
```bash
pytest                  # Framework testowy
pytest-cov             # Coverage reporting  
pytest-asyncio         # Async test support
pytest-mock            # Mocking utilities
httpx                   # HTTP client for API tests
```

#### TestContainers
```python
# PostgreSQL w testach integracyjnych CI
@pytest.fixture
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres
```

#### Pre-commit hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
  - repo: https://github.com/pycqa/flake8  
  - repo: https://github.com/pycqa/isort
```

### 7.4 Metryki jakości

- **Code Coverage**: ≥85% (pytest-cov)
- **Code Quality**: flake8, black, isort
- **Performance**: <200ms response time
- **Security**: bandit security linting

### 7.5 CI/CD Pipeline

#### GitHub Actions workflow
```yaml
name: CI/CD Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python 3.11
      - name: Install dependencies  
      - name: Run unit tests
      - name: Run integration tests
      - name: Run E2E tests
      - name: Upload coverage reports
```

### 7.6 Dokumentacja testów

#### Test Planning
- **Test Cases**: udokumentowane w `tests/test_cases.md`
- **Test Data**: fixtures w `tests/fixtures/`
- **Bug Reports**: GitHub Issues z labels

#### Test Execution
- **Local**: `make test` - wszystkie testy
- **CI**: automatyczne przy push/PR
- **Reports**: HTML coverage + Allure reports

## 8. Deployment

### 8.1 Docker Compose

Plik `docker-compose.yml` uruchamia:
- **api**: FastAPI + Uvicorn, port 8000
- **db**: PostgreSQL 15, volume na dane
- **redis**: Cache dla sesji (opcjonalnie)

### 8.2 Konfiguracja środowiskowa

Zmienne w pliku `.env`:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@db/renovation
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 8.3 Production considerations

- **Reverse Proxy**: Nginx przed FastAPI
- **SSL**: Let's Encrypt certificates  
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON logs
- **Backup**: Automated PostgreSQL backups

## 9. Rozwój i utrzymanie

### 9.1 Roadmap funkcjonalności

#### Faza 2 (przyszłość)
- Import wydatków z CSV
- Integracja z bankiem (API)
- Powiadomienia o przekroczeniu budżetu
- Aplikacja mobilna (React Native)

#### Faza 3 (rozszerzenia)
- Multi-tenant architecture
- Zaawansowane raporty i wykresy
- Integracja z systemami księgowymi
- AI suggestions dla kategoryzacji

### 9.2 Architektura na przyszłość

Obecna architektura Clean umożliwia:
- **Microservices**: łatwy podział na niezależne serwisy
- **Event Sourcing**: dodanie event store
- **CQRS**: rozdzielenie read/write models
- **Multi-database**: różne bazy dla różnych bounded contexts

### 9.3 Monitoring i observability

- **Health checks**: `/health` endpoint
- **Metrics**: Prometheus metrics  
- **Tracing**: OpenTelemetry
- **Alerting**: na błędy i wydajność