# Load Testing with Locust

## Quick Start

1. Ensure your app is running locally at http://localhost:5000
2. Install Locust (if not already):
   ```bash
   pip install locust
   ```
3. Run Locust in headless mode:
   ```bash
   python3 -m locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s --host=http://localhost:5000
   ```
   - `-u 10`: 10 users
   - `-r 2`: spawn rate (users/sec)
   - `-t 30s`: test duration

## Endpoint Coverage

The default `locustfile.py` covers:

- Login (`/auth/login`)
- List restaurants (`/restaurants/`)
- Add restaurant (`/restaurants/add`)
- Export restaurants (`/restaurants/export`)
- List expenses (main index: `/`)

To add more flows, edit [`locustfile.py`](locustfile.py).

## Test User Setup

Ensure a test user (default: `testuser`/`testpass`) exists in your database. You can create one using the Flask shell or by registering via the app.

## Troubleshooting

- If you see `locust: command not found`, use `python3 -m locust ...` as above.
- If you get authentication errors, ensure the test user exists in your database with the correct credentials (see `locustfile.py`).
- If you see 404 errors, check that the endpoints in `locustfile.py` match your Flask app's blueprints. The expenses list is at `/`, not `/expenses/`.
- For Docker-based testing, consider running Locust in a container and pointing it to your app's network.

## Customizing

- Edit `locustfile.py` to add or modify user flows and endpoints.
- Adjust user count, spawn rate, and duration as needed for your environment.

## Example Makefile Target

Add this to your Makefile for convenience:

```makefile
load-test:
	python3 -m locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s --host=http://localhost:5000
```

Then run:

```bash
make load-test
```

## CI Integration

The `make load-test` target is used in CI workflows to ensure load tests run automatically.
