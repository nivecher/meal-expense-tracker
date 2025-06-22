#!/usr/bin/env python3
"""List all registered routes in the Flask application."""
from app import create_app


def list_routes():
    """List all registered routes."""
    app = create_app()
    print("\nRegistered routes:")
    print("-" * 80)

    # Get all routes and sort them by URL
    routes = []
    for rule in app.url_map.iter_rules():
        methods = sorted(rule.methods - {"OPTIONS", "HEAD"})
        routes.append({"endpoint": rule.endpoint, "methods": methods, "rule": str(rule)})

    # Sort routes by URL
    routes.sort(key=lambda x: x["rule"])

    # Print routes in a nice format
    for route in routes:
        methods = ", ".join(route["methods"])
        print(f"{route['rule']:60} {methods:20} -> {route['endpoint']}")
    print()


if __name__ == "__main__":
    list_routes()
