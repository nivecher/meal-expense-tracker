from locust import HttpUser, between, task  # type: ignore[import-not-found]


class MealExpenseUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Log in at the start of each user session."""
        self.client.post("/auth/login", {"username": "testuser", "password": "testpass"})

    @task(3)
    def view_restaurants(self) -> None:
        """View the restaurants page."""
        self.client.get("/restaurants/")

    @task(2)
    def view_expenses(self) -> None:
        """View the expenses page (main index)."""
        self.client.get("/")

    @task(1)
    def add_restaurant(self) -> None:
        """Add a new restaurant."""
        self.client.post(
            "/restaurants/add",
            {
                "name": "Test Restaurant",
                "address": "123 Test St",
                "type": "restaurant",
                "description": "A test restaurant",
            },
        )

    @task(1)
    def export_restaurants(self) -> None:
        """Export restaurants to CSV."""
        self.client.get("/restaurants/export")
