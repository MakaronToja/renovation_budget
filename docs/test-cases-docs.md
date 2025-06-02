# Dokumentacja metod i sposobów testowania

## 1. Strategia testowania

### 1.1 Cel testowania
Celem testowania jest zapewnienie wysokiej jakości oprogramowania poprzez:
- Weryfikację poprawności implementacji wymagań funkcjonalnych
- Walidację zgodności z wymaganiami niefunkcjonalnymi
- Wykrywanie błędów przed wdrożeniem produkcyjnym
- Zapewnienie stabilności i niezawodności systemu

### 1.2 Piramida testów
```
        E2E Tests (3)
     ┌─────────────────┐
     │   Playwright    │ - Ścieżka użytkownika
     └─────────────────┘
   ┌─────────────────────┐
   │ Integration (~30)   │ - API + DB
   │   pytest + httpx   │
   └─────────────────────┘
 ┌───────────────────────────┐
 │    Unit Tests (>100)      │ - Logika Biznesowa
 │      pytest + mock       │
 └───────────────────────────┘
```

## 2. Testy jednostkowe (Unit Tests)

### 2.1 Zakres testowania
- **Domain Models**: User, Project, Expense, Money
- **Value Objects**: Money operations, Category enum
- **Services**: AuthService, ProjectService, ExpenseService
- **Business Logic**: calculations, validations

### 2.2 Metodologia
- **Test-Driven Development (TDD)** dla nowej funkcjonalności
- **Given-When-Then** pattern dla czytelności
- **Arrange-Act-Assert** struktura testów
- **Mocking** zewnętrznych zależności

### 2.3 Przykłady testów jednostkowych

#### Test Value Object Money
```python
class TestMoney:
    def test_money_addition_same_currency(self):
        # Given
        money1 = Money(Decimal("100.50"), "PLN")
        money2 = Money(Decimal("50.25"), "PLN")
        
        # When
        result = money1 + money2
        
        # Then
        assert result.amount == Decimal("150.75")
        assert result.currency == "PLN"
    
    def test_money_addition_different_currency_raises_error(self):
        # Given
        money1 = Money(Decimal("100"), "PLN")
        money2 = Money(Decimal("50"), "USD")
        
        # When & Then
        with pytest.raises(AssertionError):
            money1 + money2
    
    def test_money_subtraction(self):
        # Given
        money1 = Money(Decimal("100.75"), "PLN")
        money2 = Money(Decimal("25.25"), "PLN")
        
        # When
        result = money1 - money2
        
        # Then
        assert result.amount == Decimal("75.50")
        assert result.currency == "PLN"
```

#### Test Entity Project
```python
class TestProject:
    def test_project_total_cost_calculation(self):
        # Given
        project = Project(
            id=uuid4(),
            user_id=uuid4(),
            name="Bathroom Renovation",
            budget=Money(Decimal("10000"), "PLN"),
            created_at=datetime.now()
        )
        expense1 = Expense(
            id=uuid4(),
            project_id=project.id,
            category=Category.MATERIAL,
            amount=Money(Decimal("1500"), "PLN"),
            vendor="BuildStore",
            date=date.today()
        )
        expense2 = Expense(
            id=uuid4(),
            project_id=project.id,
            category=Category.LABOR,
            amount=Money(Decimal("2500"), "PLN"),
            vendor="WorkerTeam",
            date=date.today()
        )
        
        # When
        project.add_expense(expense1)
        project.add_expense(expense2)
        
        # Then
        assert project.total_cost.amount == Decimal("4000")
        assert len(project.expenses) == 2
    
    def test_remaining_budget_calculation(self):
        # Given
        project = Project(
            id=uuid4(),
            user_id=uuid4(),
            name="Kitchen Renovation",
            budget=Money(Decimal("5000"), "PLN"),
            created_at=datetime.now()
        )
        expense = Expense(
            id=uuid4(),
            project_id=project.id,
            category=Category.MATERIAL,
            amount=Money(Decimal("1200"), "PLN"),
            vendor="Store",
            date=date.today()
        )
        
        # When
        project.add_expense(expense)
        remaining = project.remaining_budget()
        
        # Then
        assert remaining.amount == Decimal("3800")
```

#### Test Service ExpenseService
```python
class TestExpenseService:
    @pytest.fixture
    def mock_project_repo(self):
        return Mock(spec=IProjectRepository)
    
    @pytest.fixture
    def mock_expense_repo(self):
        return Mock(spec=IExpenseRepository)
    
    @pytest.fixture
    def expense_service(self, mock_project_repo, mock_expense_repo):
        return ExpenseService(
            projects=mock_project_repo,
            expenses=mock_expense_repo
        )
    
    def test_record_expense_success(self, expense_service, mock_project_repo, mock_expense_repo):
        # Given
        project_id = uuid4()
        project = Project(
            id=project_id,
            user_id=uuid4(),
            name="Test Project",
            budget=Money(Decimal("10000"), "PLN"),
            created_at=datetime.now()
        )
        mock_project_repo.get.return_value = project
        
        # When
        expense_id = expense_service.record_expense(
            project_id=project_id,
            amount=Decimal("500"),
            category=Category.MATERIAL,
            vendor="TestStore",
            date=date.today(),
            description="Test expense"
        )
        
        # Then
        assert expense_id is not None
        mock_project_repo.get.assert_called_once_with(project_id)
        mock_expense_repo.save.assert_called_once()
        mock_project_repo.save.assert_called_once_with(project)
        assert len(project.expenses) == 1
    
    def test_record_expense_project_not_found(self, expense_service, mock_project_repo):
        # Given
        project_id = uuid4()
        mock_project_repo.get.return_value = None
        
        # When & Then
        with pytest.raises(ValueError, match="Project not found"):
            expense_service.record_expense(
                project_id=project_id,
                amount=Decimal("500"),
                category=Category.MATERIAL,
                vendor="TestStore",
                date=date.today()
            )
    
    def test_list_expenses_with_filter(self, expense_service, mock_expense_repo):
        # Given
        project_id = uuid4()
        expenses = [
            Expense(uuid4(), project_id, Category.MATERIAL, Money(Decimal("100")), "Store1", date.today()),
            Expense(uuid4(), project_id, Category.LABOR, Money(Decimal("200")), "Store2", date.today()),
            Expense(uuid4(), project_id, Category.MATERIAL, Money(Decimal("150")), "Store3", date.today())
        ]
        mock_expense_repo.list_by_project.return_value = expenses
        
        # When
        filtered_expenses = expense_service.list_expenses(
            project_id=project_id,
            category_filter=Category.MATERIAL
        )
        
        # Then
        assert len(filtered_expenses) == 2
        assert all(e.category == Category.MATERIAL for e in filtered_expenses)
```

### 2.4 Metryki testów jednostkowych
- **Coverage Target**: ≥85%
- **Test Count**: >100 testów
- **Performance**: <50ms na test
- **Maintainability**: DRY principle, fixtures, parametrized tests

## 3. Testy integracyjne (Integration Tests)

### 3.1 Zakres testowania
- **API Endpoints**: wszystkie REST endpoints
- **Database Operations**: CRUD operations przez ORM
- **Service Integration**: współpraca Service ↔ Repository
- **Authentication**: JWT token flow

### 3.2 Środowisko testowe
- **Database**: SQLite in-memory dla szybkości
- **HTTP Client**: httpx dla async FastAPI
- **Test Data**: fixtures z przykładowymi danymi
- **Cleanup**: automatyczne czyszczenie po każdym teście

### 3.3 Przykłady testów integracyjnych

#### Test API Authentication
```python
class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_register_user_success(self, test_client):
        # Given
        user_data = {
            "email": "test@example.com",
            "password": "strongpassword123"
        }
        
        # When
        response = await test_client.post("/auth/register", json=user_data)
        
        # Then
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "password" not in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, test_client, existing_user):
        # Given
        user_data = {
            "email": existing_user.email,
            "password": "anotherpassword123"
        }
        
        # When
        response = await test_client.post("/auth/register", json=user_data)
        
        # Then
        assert response.status_code == 400
        assert "already used" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_success(self, test_client, existing_user):
        # Given
        login_data = {
            "email": existing_user.email,
            "password": "password123"  # plain password
        }
        
        # When
        response = await test_client.post("/auth/login", json=login_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
```

#### Test Database Repository
```python
class TestPostgresExpenseRepository:
    @pytest.mark.asyncio
    async def test_save_and_get_expense(self, expense_repo, sample_expense):
        # Given & When
        await expense_repo.save(sample_expense)
        retrieved = await expense_repo.get(sample_expense.id)
        
        # Then
        assert retrieved is not None
        assert retrieved.id == sample_expense.id
        assert retrieved.amount.amount == sample_expense.amount.amount
        assert retrieved.category == sample_expense.category
        assert retrieved.vendor == sample_expense.vendor
    
    @pytest.mark.asyncio
    async def test_list_by_project(self, expense_repo, project_with_expenses):
        # Given
        project_id = project_with_expenses.id
        expected_count = len(project_with_expenses.expenses)
        
        # When
        expenses = await expense_repo.list_by_project(project_id)
        
        # Then
        assert len(expenses) == expected_count
        assert all(e.project_id == project_id for e in expenses)
    
    @pytest.mark.asyncio
    async def test_delete_expense(self, expense_repo, sample_expense):
        # Given
        await expense_repo.save(sample_expense)
        
        # When
        await expense_repo.delete(sample_expense.id)
        
        # Then
        deleted_expense = await expense_repo.get(sample_expense.id)
        assert deleted_expense is None
```

#### Test Complete API Flow
```python
class TestExpenseAPIFlow:
    @pytest.mark.asyncio
    async def test_complete_expense_crud_flow(self, test_client, auth_headers, sample_project):
        project_id = sample_project.id
        
        # Create expense
        expense_data = {
            "amount": 1500.50,
            "category": "MATERIAL",
            "vendor": "BuildMart",
            "date": "2024-01-15",
            "description": "Bathroom tiles"
        }
        
        # CREATE
        response = await test_client.post(
            f"/projects/{project_id}/expenses",
            json=expense_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        expense_id = response.json()["id"]
        
        # READ
        response = await test_client.get(
            f"/expenses/{expense_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["vendor"] == "BuildMart"
        
        # UPDATE
        update_data = {"vendor": "NewBuildMart", "amount": 1600.00}
        response = await test_client.put(
            f"/expenses/{expense_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # LIST
        response = await test_client.get(
            f"/projects/{project_id}/expenses",
            headers=auth_headers
        )
        assert response.status_code == 200
        expenses = response.json()
        assert len(expenses) >= 1
        
        # DELETE
        response = await test_client.delete(
            f"/expenses/{expense_id}",
            headers=auth_headers
        )
        assert response.status_code == 204
        
        # Verify deletion
        response = await test_client.get(
            f"/expenses/{expense_id}",
            headers=auth_headers
        )
        assert response.status_code == 404
```

### 3.4 Fixtures i Setup
```python
@pytest.fixture
async def test_client():
    """HTTP test client for FastAPI"""
    app = create_app()
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_db():
    """In-memory SQLite database for tests"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def auth_headers(test_client, existing_user):
    """Authentication headers with JWT token"""
    login_data = {"email": existing_user.email, "password": "password123"}
    response = await test_client.post("/auth/login", json=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

## 4. Testy End-to-End (E2E)

### 4.1 Narzędzie: Playwright
- **Browser Support**: Chromium, Firefox, Safari
- **Language**: Python + Playwright
- **Parallel Execution**: możliwość równoległego uruchamiania
- **Screenshots**: automatyczne przy błędach

### 4.2 Scenariusze E2E

#### Scenariusz 1: User Registration and Project Creation
```python
async def test_user_registration_and_project_creation(page):
    """Test complete user journey from registration to project creation"""
    
    # Navigate to registration page
    await page.goto("http://localhost:8000/register")
    
    # Fill registration form
    await page.fill('[data-testid="email"]', "testuser@example.com")
    await page.fill('[data-testid="password"]', "strongpassword123")
    await page.fill('[data-testid="confirm-password"]', "strongpassword123")
    
    # Submit registration
    await page.click('[data-testid="register-button"]')
    
    # Verify redirect to login
    await expect(page).to_have_url("http://localhost:8000/login")
    await expect(page.locator('[data-testid="success-message"]')).to_contain_text("Registration successful")
    
    # Login with new account
    await page.fill('[data-testid="email"]', "testuser@example.com")
    await page.fill('[data-testid="password"]', "strongpassword123")
    await page.click('[data-testid="login-button"]')
    
    # Verify redirect to dashboard
    await expect(page).to_have_url("http://localhost:8000/dashboard")
    await expect(page.locator('[data-testid="welcome-message"]')).to_be_visible()
    
    # Create new project
    await page.click('[data-testid="new-project-button"]')
    await page.fill('[data-testid="project-name"]', "Bathroom Renovation")
    await page.fill('[data-testid="project-budget"]', "15000")
    await page.select_option('[data-testid="currency"]', "PLN")
    await page.click('[data-testid="create-project-button"]')
    
    # Verify project creation
    await expect(page.locator('[data-testid="project-title"]')).to_contain_text("Bathroom Renovation")
    await expect(page.locator('[data-testid="project-budget"]')).to_contain_text("15,000.00 PLN")
```

#### Scenariusz 2: Expense Management Flow
```python
async def test_expense_management_flow(page, authenticated_user_with_project):
    """Test adding, editing, and filtering expenses"""
    
    project_id = authenticated_user_with_project["project_id"]
    
    # Navigate to project details
    await page.goto(f"http://localhost:8000/projects/{project_id}")
    
    # Add first expense
    await page.click('[data-testid="add-expense-button"]')
    await page.fill('[data-testid="expense-amount"]', "1500.50")
    await page.select_option('[data-testid="expense-category"]', "MATERIAL")
    await page.fill('[data-testid="expense-vendor"]', "BuildMart")
    await page.fill('[data-testid="expense-date"]', "2024-01-15")
    await page.fill('[data-testid="expense-description"]', "Bathroom tiles and fixtures")
    await page.click('[data-testid="save-expense-button"]')
    
    # Verify expense appears in list
    await expect(page.locator('[data-testid="expense-list"]')).to_contain_text("BuildMart")
    await expect(page.locator('[data-testid="expense-list"]')).to_contain_text("1,500.50")
    
    # Add second expense
    await page.click('[data-testid="add-expense-button"]')
    await page.fill('[data-testid="expense-amount"]', "2500")
    await page.select_option('[data-testid="expense-category"]', "LABOR")
    await page.fill('[data-testid="expense-vendor"]', "PlumberTeam")
    await page.fill('[data-testid="expense-date"]', "2024-01-20")
    await page.click('[data-testid="save-expense-button"]')
    
    # Test filtering by category
    await page.select_option('[data-testid="category-filter"]', "MATERIAL")
    await expect(page.locator('[data-testid="expense-list"]')).to_contain_text("BuildMart")
    await expect(page.locator('[data-testid="expense-list"]')).not_to_contain_text("PlumberTeam")
    
    # Test editing expense
    await page.click('[data-testid="edit-expense-0"]')
    await page.fill('[data-testid="expense-amount"]', "1600")
    await page.click('[data-testid="save-expense-button"]')
    
    # Clear filter and verify total
    await page.select_option('[data-testid="category-filter"]', "ALL")
    await expect(page.locator('[data-testid="total-cost"]')).to_contain_text("4,100.00")
```

#### Scenariusz 3: Project Summary and Export
```python
async def test_project_summary_and_export(page, project_with_expenses):
    """Test project summary view and CSV export functionality"""
    
    project_id = project_with_expenses["project_id"]
    
    # Navigate to project
    await page.goto(f"http://localhost:8000/projects/{project_id}")
    
    # Verify summary section
    await expect(page.locator('[data-testid="total-budget"]')).to_be_visible()
    await expect(page.locator('[data-testid="spent-amount"]')).to_be_visible()
    await expect(page.locator('[data-testid="remaining-budget"]')).to_be_visible()
    await expect(page.locator('[data-testid="budget-progress"]')).to_be_visible()
    
    # Check category breakdown chart
    await expect(page.locator('[data-testid="category-chart"]')).to_be_visible()
    
    # Test CSV export
    with page.expect_download() as download_info:
        await page.click('[data-testid="export-csv-button"]')
    download = await download_info.value
    
    # Verify download
    assert download.suggested_filename.endswith('.csv')
    assert 'expenses' in download.suggested_filename
    
    # Verify export contains expected data
    path = await download.path()
    with open(path, 'r') as file:
        content = file.read()
        assert 'Date,Category,Amount,Currency,Vendor,Description' in content
        assert project_with_expenses["expenses"][0]["vendor"] in content
```

### 4.3 Page Object Pattern
```python
class ProjectPage:
    def __init__(self, page):
        self.page = page
        
    async def navigate_to(self, project_id):
        await self.page.goto(f"http://localhost:8000/projects/{project_id}")
    
    async def add_expense(self, expense_data):
        await self.page.click('[data-testid="add-expense-button"]')
        await self.page.fill('[data-testid="expense-amount"]', str(expense_data['amount']))
        await self.page.select_option('[data-testid="expense-category"]', expense_data['category'])
        await self.page.fill('[data-testid="expense-vendor"]', expense_data['vendor'])
        await self.page.fill('[data-testid="expense-date"]', expense_data['date'])
        if 'description' in expense_data:
            await self.page.fill('[data-testid="expense-description"]', expense_data['description'])
        await self.page.click('[data-testid="save-expense-button"]')
    
    async def get_total_cost(self):
        return await self.page.locator('[data-testid="total-cost"]').inner_text()
    
    async def export_csv(self):
        with self.page.expect_download() as download_info:
            await self.page.click('[data-testid="export-csv-button"]')
        return await download_info.value
```

## 5. Performance Testing

### 5.1 Load Testing z Locust
```python
from locust import HttpUser, task, between

class RenovationUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login and get token
        response = self.client.post("/auth/login", json={
            "email": "testuser@example.com",
            "password": "password123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def view_projects(self):
        self.client.get("/projects", headers=self.headers)
    
    @task(2)
    def view_expenses(self):
        self.client.get("/projects/123/expenses", headers=self.headers)
    
    @task(1)
    def add_expense(self):
        self.client.post("/projects/123/expenses", 
                        json={
                            "amount": 100,
                            "category": "MATERIAL",
                            "vendor": "TestStore",
                            "date": "2024-01-15"
                        },
                        headers=self.headers)
```

### 5.2 Metryki wydajności
- **Response Time**: <200ms dla 95% requestów
- **Throughput**: >1000 requests/sec
- **Concurrent Users**: 100 równoczesnych użytkowników
- **Database**: <50ms query time

## 6. Security Testing

### 6.1 Automated Security Scans
```bash
# OWASP ZAP security scan
zap-baseline.py -t http://localhost:8000

# Bandit static security analysis
bandit -r renovation_cost_tracker/

# Safety dependency scan
safety check
```

### 6.2 Testy manualne z zakrezu cyberbezpieczeństwa
- **Authentication**: JWT token validation
- **Authorization**: user isolation, RBAC
- **Input Validation**: SQL injection, XSS prevention
- **Rate Limiting**: brute force protection
- **HTTPS**: TLS configuration

## 7. Testy CI/CD

### 7.1 GitHub Actions Workflow
```yaml
name: Test Pipeline
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run unit tests
        run: pytest tests/unit/ --cov=renovation_cost_tracker --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python 3.11
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run integration tests
        run: pytest tests/integration/
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test
  
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python 3.11
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install playwright
          playwright install
      - name: Start application
        run: |
          uvicorn renovation_cost_tracker.main:create_app --host 0.0.0.0 --port 8000 &
          sleep 10
      - name: Run E2E tests
        run: pytest tests/e2e/
```

## 8. Testy zarządzaniem danych

### 8.1 Test Fixtures
```python
@pytest.fixture
def sample_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        password_hash=bcrypt.hash("password123"),
        created_at=datetime.now()
    )

@pytest.fixture
def sample_project(sample_user):
    return Project(
        id=uuid4(),
        user_id=sample_user.id,
        name="Test Renovation",
        budget=Money(Decimal("10000"), "PLN"),
        created_at=datetime.now()
    )

@pytest.fixture
def sample_expenses(sample_project):
    return [
        Expense(
            id=uuid4(),
            project_id=sample_project.id,
            category=Category.MATERIAL,
            amount=Money(Decimal("1500"), "PLN"),
            vendor="BuildStore",
            date=date.today(),
            description="Tiles"
        ),
        Expense(
            id=uuid4(),
            project_id=sample_project.id,
            category=Category.LABOR,
            amount=Money(Decimal("2500"), "PLN"),
            vendor="Workers",
            date=date.today(),
            description="Installation"
        )
    ]
```

### 8.2 Database Seeding
```python
async def seed_test_data(session):
    """Seed database with test data for E2E tests"""
    
    # Create test user
    user = UserModel(
        id=uuid4(),
        email="e2e@example.com",
        password_hash=bcrypt.hash("password123"),
        created_at=datetime.now()
    )
    session.add(user)
    
    # Create test project
    project = ProjectModel(
        id=uuid4(),
        user_id=user.id,
        name="E2E Test Project",
        budget_amount=Decimal("20000"),
        budget_currency="PLN",
        created_at=datetime.now()
    )
    session.add(project)
    
    await session.commit()
    return {"user": user, "project": project}
```

## 9. Raport oraz metryki

### 9.1 Raport pokrycia testami
- **Narzędzie**: pytest-cov + coverage.py  
- **Format**: HTML, XML, terminal  
- **Cel**: ≥85% pokrycia linii kodu  
- **Wykluczenia**: pliki migracji, pliki `__init__.py`  

### 9.2 Raport z wykonania testów
- **Narzędzie**: pytest-html  
- **Zawartość**: wyniki testów, czas wykonania, błędy  
- **Integracja z CI**: przesyłanie jako artefakty  
- **Śledzenie historyczne**: analiza trendów  

### 9.3 Metryki wydajności
- **Czasy odpowiedzi**: percentyle (50., 90., 95., 99.)  
- **Przepustowość**: liczba żądań na sekundę  
- **Wskaźniki błędów**: odpowiedzi 4xx, 5xx  
- **Zużycie zasobów**: CPU, pamięć, połączenia z bazą danych  

## 10. Utrzymanie testów

### 10.1 Jakość kodu testów
- **Zasada DRY**: współdzielone fikstury, funkcje pomocnicze  
- **Konwencja nazewnictwa**: opisowe nazwy testów  
- **Dokumentacja**: docstringi dla złożonych scenariuszy testowych  
- **Refaktoryzacja**: regularne usuwanie przestarzałych testów  

### 10.2 Cykl życia danych testowych
- **Izolacja**: każdy test działa niezależnie  
- **Czyszczenie**: automatyczne usuwanie danych po teście  
- **Świeży stan**: reset bazy danych między testami  
- **Deterministyczność**: przewidywalne dane testowe  

### 10.3 Ciągłe doskonalenie
- **Niestabilne testy**: identyfikacja i poprawa  
- **Wydajność**: optymalizacja wolnych testów  
- **Luki w pokryciu**: regularna analiza i poprawa  
- **Aktualizacja narzędzi**: utrzymanie aktualnego stosu testowego
