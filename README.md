# Meal Expense Tracker

A web application for tracking meal-related expenses, built with Flask and Docker.

## Features

- Track meal expenses with categories (Breakfast, Lunch, Dinner, etc.)
- User authentication
- Responsive design
- Docker containerization

## Prerequisites

- Docker
- Docker Compose (optional)

## Setup and Running

1. Clone the repository:
```bash
git clone <repository-url>
cd meal-expense-tracker
```

2. Build and run with Docker:
```bash
docker build -t meal-expense-tracker .
docker run -p 5000:5000 meal-expense-tracker
```

The application will be available at http://localhost:5000

## Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
flask run
```

## Environment Variables

- `SECRET_KEY`: Flask secret key for session management
- `FLASK_ENV`: Set to 'production' or 'development'

## License

MIT 