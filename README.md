# Meal Expense Tracker

A Flask-based web application for tracking meal expenses, with features for managing restaurants and expenses.

## Features

- User authentication (login/register)
- Restaurant management
  - Add, edit, and view restaurants
  - Optional location and description fields
- Expense tracking
  - Add and edit expenses
  - Multiple meal types (Breakfast, Lunch, Dinner, Snacks, Groceries, Other)
- Advanced filtering and sorting
  - Search by restaurant, location, or description
  - Filter by meal type
  - Date range filtering
  - Sort by any column
- Responsive design with Bootstrap
- Persistent database storage

## Setup

### Local Development

1. Clone the repository:
   ```bash
git clone <repo-url>
cd meal-expense-tracker
```

2. Create and activate a virtual environment:
   ```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
   ```bash
pip install -r requirements-dev.txt
```

4. Create your environment file:
   ```bash
cp .env.sample .env
# Edit .env and fill in your secrets and configuration values
```

5. Initialize the database (optional, for local dev):
   ```bash
python init_db.py
```

6. Run the application:
   ```bash
make run-local
```
The app will be available at http://localhost:5000

### Docker

1. Build and run:
   ```bash
make build
make run
```

2. Common commands:
   ```bash
# Stop container
make stop

# View logs
make logs

# Clean up
make clean

# Run tests
make test

# Lint code
make lint
```

1. Copy the sample environment file:
   ```bash
   cp .env.sample .env
   ```
2. Edit `.env` and fill in your secrets and configuration values as needed.

- `SECRET_KEY`: Flask secret key (use a random value in production)
- `SQLALCHEMY_DATABASE_URI`: Database URI (default is SQLite for local dev)
- `GOOGLE_MAPS_API_KEY`: (Optional) Google Maps API key for map features

## License

MIT License
