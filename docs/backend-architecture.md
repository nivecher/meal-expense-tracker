# Backend Architecture & Design

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Target Architecture](#target-architecture)
4. [Project Structure](#project-structure)
5. [Core Components](#core-components)
6. [Implementation Plan](#implementation-plan)
7. [Testing Strategy](#testing-strategy)
8. [Development Workflow](#development-workflow)

## Overview

This document defines the target architecture and implementation plan for the Meal Expense Tracker backend, following
TIGER principles (Testable, Incremental, Goal-oriented, Explicit, Responsibility-focused).

## Design Principles

### T - Testable

- Write code that is easy to test in isolation
- Use dependency injection for external services
- Keep business logic pure and side-effect free when possible
- Aim for high test coverage of business logic

### I - Incremental

- Make small, focused changes
- Each commit should be a single logical change
- Break down large features into smaller, deliverable pieces
- Refactor in small, safe steps

### G - Goal-oriented

- Each function/method should have a single responsibility
- Code should be written to solve specific business problems
- Document the "why" behind important decisions
- Align code structure with business domains

### E - Explicit

- Make dependencies explicit
- Use clear, descriptive names for variables, functions, and classes
- Make type contracts explicit with type hints
- Document complex algorithms and business rules

### R - Responsibility-focused

- Follow the Single Responsibility Principle
- Group related functionality together
- Separate concerns between layers (presentation, business logic, data access)
- Design for change by isolating volatile components

## Target Architecture

### Layered Architecture

1. **API Layer**: Handles HTTP requests/responses, request validation, and authentication
2. **Service Layer**: Contains business logic and coordinates between different components
3. **Data Access Layer**: Handles database operations and data persistence
4. **Domain Models**: Define the core business entities and their relationships

### Key Technical Decisions

- **Web Framework**: Flask 3.1.1 with Blueprints for route organization
- **Database**: SQLAlchemy ORM with PostgreSQL
- **API**: RESTful design with JSON:API specification
- **Authentication**: Session-based authentication with Flask-Login
- **Validation**: Pydantic models for request/response validation
- **Testing**: Pytest with factory_boy for test data generation

### Quality Attributes

- **Maintainability**: Clear separation of concerns and consistent code style
- **Testability**: Dependency injection and pure functions where possible
- **Performance**: Efficient database queries with eager loading where needed
- **Security**: Input validation, CSRF protection, and secure password hashing
- **Scalability**: Stateless services that can be horizontally scaled

## Project Structure

```text
app/
├── api/                     # API endpoints
│   ├── v1/                  # API version 1
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── expenses.py      # Expense management
│   │   └── restaurants.py   # Restaurant management
│   └── __init__.py
├── auth/                    # Authentication module
│   ├── __init__.py
│   ├── models.py            # User model
│   ├── schemas.py           # Request/response schemas
│   └── services.py          # Business logic
├── expenses/                # Expenses module
│   ├── __init__.py
│   ├── models.py            # Expense model
│   ├── schemas.py
│   └── services.py
├── restaurants/             # Restaurants module
│   ├── __init__.py
│   ├── models.py            # Restaurant model
│   ├── schemas.py
│   └── services.py
├── core/                    # Core functionality
│   ├── config.py            # Configuration
│   ├── exceptions.py        # Custom exceptions
│   └── security.py          # Security utilities
├── db/                      # Database package
│   ├── __init__.py
│   └── session.py           # Database session management
├── static/                  # Static files
└── tests/                   # Test suite
├── conftest.py          # Test fixtures
├── unit/                # Unit tests
└── integration/         # Integration tests
```

## Core Components

### API Layer

- **Routes**: Defined in Blueprints under `app/api/v1/`
- **Request Validation**: Pydantic models in `*/schemas.py`
- **Authentication**: Session validation and user context
- **Error Handling**: Consistent error responses and status codes

### Service Layer

- **Business Logic**: Implemented in `*/services.py`
- **Dependency Injection**: Services receive database session
- **Transaction Management**: Handled at the service level
- **Data Validation**: Input validation before processing

### Data Access Layer

- **Models**: SQLAlchemy models in `*/models.py`
- **Relationships**: Defined between User, Expense, and Restaurant
- **Query Building**: Using SQLAlchemy Core for complex queries
- **Migrations**: Alembic for database schema migrations

### Domain Models

- **User**: Authentication and profile information
- **Expense**: Meal expenses with amount, date, and category
- **Restaurant**: Restaurant information and metadata
- **Category**: Expense categories and budgeting

## Implementation Plan

### Phase 1: Foundation (2-3 weeks)

#### 1. Setup & Configuration

- Initialize Pydantic for request/response schemas
- Set up dependency injection for database sessions
- Configure structured logging

#### 2. Authentication Service

- Implement Flask-Login authentication
- Add user registration and login endpoints
- Set up password hashing and verification

#### 3. Core Services

- Implement base service class
- Add error handling middleware
- Set up API documentation with OpenAPI

### Phase 2: Core Functionality (3-4 weeks)

1. **Expense Management**

- [ ] CRUD operations for expenses
  - [ ] Expense filtering and search
  - [ ] Receipt image upload and storage

1. **Restaurant Integration**

- [ ] Google Places API integration
  - [ ] Restaurant search and details
  - [ ] Caching for external API calls

1. **Reporting**

- [ ] Basic expense reporting
  - [ ] Category-based spending analysis
  - [ ] Export functionality (CSV/PDF)

### Phase 3: Enhanced Features (2-3 weeks)

1. **User Preferences**

- [ ] Default categories
  - [ ] Currency and locale settings
  - [ ] Notification preferences

1. **Advanced Features**

- [ ] Recurring expenses
  - [ ] Budget tracking
  - [ ] Multi-user expense sharing

## Testing Strategy

### Unit Testing

- Test individual functions and methods in isolation
- Mock external dependencies
- Focus on business logic and edge cases

### Integration Testing

- Test API endpoints with TestClient
- Verify database interactions
- Test authentication and authorization

### Test Data Management

- Use factory_boy for test data generation
- Set up test database with fixtures
- Clean up test data after each test

## Development Workflow

### Local Development

1. Create and activate virtual environment
2. Install dependencies: `pip install -r requirements-dev.txt`
3. Set up environment variables in `.env`
4. Run database migrations: `flask db upgrade`
5. Start development server: `flask run`

### Code Quality

- Run linters: `make lint`
- Run type checking: `make typecheck`
- Run tests: `make test`
- Check test coverage: `make coverage`

### Git Workflow

1. Create feature branch: `git checkout -b feature/name`
2. Make small, focused commits
3. Push branch and create pull request
4. Address code review feedback
5. Squash and merge when approved

- **Backward Compatibility**: Ensure existing features continue to work
- **Test Coverage**: Add tests for all new and modified code

### Phase 1: Immediate Improvements (1-2 weeks)

1. **Code Organization**

- Add request/response schemas with Pydantic
  - Separate business logic into service layer
  - Improve error handling

1. **API Improvements**

- Add input validation
  - Standardize response formats
  - Document API endpoints

1. **Testing**

- Add unit tests for services
  - Add integration tests for API endpoints
  - Set up test data factories

## Phase 1: Code Organization

### 1. Request/Response Schemas

- Add Pydantic models for all API requests/responses
- Centralize validation logic
- Example:

```python

## schemas/restaurants.py
from pydantic import BaseModel

class RestaurantBase(BaseModel):

name: str
address: str | None = None
phone: str | None = None

class RestaurantCreate(RestaurantBase):

pass

class RestaurantResponse(RestaurantBase):
  id: int
  created_at: datetime
  updated_at: datetime
```

### 2. Service Layer

- Move business logic from routes to service modules
- Keep routes focused on HTTP concerns
- Example:

```python

## services/restaurant_service.py
from sqlalchemy.orm import Session
from . import models, schemas

def create_restaurant(

db: Session,
restaurant: schemas.RestaurantCreate,
user_id: int

  ) -> models.Restaurant:

db_restaurant = models.Restaurant(
  **restaurant.dict(),
user_id=user_id
)
db.add(db_restaurant)
db.commit()
db.refresh(db_restaurant)
return db_restaurant

```

### 3. Error Handling

- Centralized error handling
- Consistent error responses
- Example:

```python

## errors/handlers.py
from flask import jsonify
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):

@app.errorhandler(400)
def bad_request(error):
  return jsonify({
  "error": "Bad Request",
  "message": str(error)
  }), 400

```

## Project Structure (Phase 1)

```bash
app/
├── api/
│   ├── **init**.py
│   ├── routes.py           # API routes (to be split if > 300 lines)
│   └── schemas.py          # Request/response models (new)
│
├── auth/                   # Authentication
│   ├── **init**.py
│   ├── models.py
│   ├── routes.py
│   └── services.py         # Move business logic here
│
├── expenses/               # Expenses feature
│   ├── **init**.py
│   ├── models.py
│   ├── routes.py
│   ├── schemas.py         # New for request/response models
│   └── services.py        # New for business logic
│
├── models/                # Base models
│   ├── **init**.py
│   └── base.py
│
├── restaurants/           # Restaurants feature
│   ├── **init**.py
│   ├── models.py
│   ├── routes.py
│   ├── schemas.py        # New for request/response models
│   └── services.py       # New for business logic
│
├── static/               # Static files
├── templates/            # Jinja2 templates
│
└── utils/                # Utility functions
├── **init**.py
├── decorators.py
└── filters.py

tests/
├── conftest.py          # Test fixtures
├── unit/                # Unit tests
│   ├── auth/
│   ├── expenses/
│   └── restaurants/
└── integration/         # Integration tests
└── api/

```

## Core Components (Phase 1)

### 1. API Layer

- **Routes**: Handle HTTP requests/responses
- **Validation**: Use Pydantic schemas for input validation
- **Error Handling**: Consistent error responses
- **Documentation**: Basic API documentation in docstrings

### 2. Service Layer (New)

- **Business Logic**: Move from routes to service modules
- **Database Access**: Handle all database operations
- **Dependency Injection**: Pass database session as parameter
- **Example**:

```python

## services/restaurant_service.py (2)
from sqlalchemy.orm import Session
from .. import models, schemas

def get_restaurant(db: Session, restaurant_id: int):
  return db.query(models.Restaurant)\
  .filter(models.Restaurant.id == restaurant_id)\
  .first()

```

### 3. Data Models

- **SQLAlchemy Models**: Define database schema
- **Relationships**: Define model relationships
- **Helper Methods**: Add model methods for common operations

## Testing Strategy (Phase 1)

### 1. Unit Tests

- **Scope**: Test individual functions/methods
- **Tools**: pytest + pytest-mock
- **Example**:

```python

## tests/unit/restaurants/test_services.py
def test_create_restaurant(db_session):
  from app.restaurants import services, schemas

  ## Test data
  restaurant_data = {"name": "Test Restaurant"}

  ## Call service
  result = services.create_restaurant(
  db=db_session,
  restaurant=schemas.RestaurantCreate(**restaurant_data),
  user_id=1
  )

```

## Assertions

assert result.name == "Test Restaurant"
assert db_session.query(models.Restaurant).count() == 1

### 2. Integration Tests

- **Scope**: Test API endpoints with test client
- **Tools**: pytest + Flask test client
- **Example**:

```python

## tests/integration/test_restaurants.py

def test_create_restaurant_endpoint(client, auth, db_session):

# Login
auth.login()

# Test data (2)
data = {"name": "Test Restaurant"}

# Make request
response = client.post(
  "/api/restaurants",
  json=data,
  headers={"Content-Type": "application/json"}
)

# Assertions (2)
assert response.status_code == 201
assert response.json["name"] == "Test Restaurant"

```

## Development Workflow (Phase 1)

### 1. Local Development Setup

```bash

## Create and activate virtual environment
Python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

## Install dependencies
pip install -r requirements-dev.txt

## Set environment variables
cp .env.example .env
## Edit .env with your configuration

## Run database migrations
flask db upgrade

## Start development server
flask run --debug

```

### 2. Code Quality Tools

- **Linting**: `flake8`
- **Formatting**: `black` + `isort`
- **Type Checking**: `mypy`
- **Security**: `bandit`

### 3. Git Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes
3. Run tests: `pytest`
4. Format code: `black . && isort .`
5. Commit changes: `git commit -m "Add your feature"`
6. Push branch: `git push origin feature/your-feature`
7. Create pull request

### 4. Testing Commands

```bash

## Run all tests
pytest

## Run specific test file
pytest tests/unit/test_restaurants.py

## Run with coverage
pytest --cov=app tests/

## Run integration tests
pytest tests/integration/

```

## Next Steps

### After Phase 1

1. **API Versioning**: Add `/api/v1/` prefix
2. **Documentation**: Add OpenAPI/Swagger
3. **Advanced Testing**: Add property-based testing
4. **Performance**: Add caching and query optimization

### Future Improvements

1. **Background Jobs**: For long-running tasks
2. **Monitoring**: Add logging and metrics
3. **Deployment**: Improve CI/CD pipeline
