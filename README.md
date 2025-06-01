# Meal Expense Tracker

A Flask-based web application for tracking meal expenses, with features for managing restaurants and expenses.

## Features

- User authentication (login/register)
- Restaurant management
  - Add, edit, and view restaurants
  - Optional location and description fields
- Expense tracking
  - Add and edit expenses
  - Required restaurant field
  - Optional description field
  - Multiple meal types (Breakfast, Lunch, Dinner, Snacks, Groceries, Other)
- Advanced filtering and sorting
  - Search by restaurant, location, or description
  - Filter by meal type
  - Date range filtering
  - Sort by any column (date, restaurant, meal, description, amount)
- Responsive design with Bootstrap
- Persistent database storage

## Setup
This application can be run locally or in a Docker container. Below are the setup instructions for both environments.

## Initial Python Setup (Local Development)

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

6. Run the application locally:
   ```bash
   make run-local
   ```
   The app will be available at http://localhost:5000

## Using Make Commands

- **Run locally (Python):**
  ```bash
  make run-local
  ```
- **Build Docker image:**
  ```bash
  make build
  ```
- **Run in Docker:**
  ```bash
  make run
  ```
- **Stop Docker container:**
  ```bash
  make stop
  ```
- **View logs:**
  ```bash
  make logs
  ```
- **Run tests:**
  ```bash
  make test
  ```
- **Lint code:**
  ```bash
  make lint
  ```
- **Clean up containers and volumes:**
  ```bash
  make clean
  ```

For more, see the `Makefile`.

## Database Management

The application uses SQLite with a persistent volume for data storage. The database is stored in a Docker volume named `meal-expense-db`.

### Backup Database
```bash
docker run --rm -v meal-expense-db:/source -v $(pwd):/backup alpine tar -czf /backup/meal-expense-db-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /source .
```

### Restore Database
```bash
docker run --rm -v meal-expense-db:/target -v $(pwd):/backup alpine sh -c "rm -rf /target/* && tar -xzf /backup/backup-file.tar.gz -C /target"
```

## Common Commands

- Start the application: `docker start meal-expense-app`
- Stop the application: `docker stop meal-expense-app`
- View logs: `docker logs meal-expense-app`
- Rebuild and redeploy:
  ```bash
  docker stop meal-expense-app
  docker rm meal-expense-app
  docker build -t meal-expense-tracker .
  docker run -d -p 5000:5000 -v meal-expense-db:/app/instance --name meal-expense-app meal-expense-tracker
  ```

## Development

The application is built with:
- Flask (Python web framework)
- SQLAlchemy (ORM)
- Bootstrap (Frontend)
- SQLite (Database)

## Environment Variables

Before running the application, create a `.env` file for your configuration:

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
