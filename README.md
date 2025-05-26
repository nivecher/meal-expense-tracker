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

1. Install Docker if you haven't already
2. Clone the repository
3. Build and run the application:
   ```bash
   docker build -t meal-expense-tracker .
   docker run -d -p 5000:5000 -v meal-expense-db:/app/instance --name meal-expense-app meal-expense-tracker
   ```
4. Access the application at http://localhost:5000

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

## License

MIT License
