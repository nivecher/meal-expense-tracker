"""Error handlers for the application."""

import os
import traceback

from flask import Blueprint, current_app, render_template
from werkzeug.exceptions import TooManyRequests

bp = Blueprint("errors", __name__)


@bp.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template("errors/404.html"), 404


@bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template("errors/500.html"), 500


@bp.app_errorhandler(429)
@bp.app_errorhandler(TooManyRequests)
def ratelimit_error(error):
    """Handle 429 (Too Many Requests) errors."""
    # Log detailed error information
    current_app.logger.warning(
        "Rate limit exceeded",
        extra={
            "tags": ["rate_limit"],
            "error_type": type(error).__name__,
            "error_args": getattr(error, "args", []),
            "error_attrs": {k: v for k, v in error.__dict__.items() if not k.startswith("_")},
        },
    )

    # Extract rate limit information
    rate_limit_info = {
        "limit": getattr(error, "limit", "5 per minute"),
        "reset_time": getattr(error, "reset_at", "a few minutes"),
        "description": str(getattr(error, "description", "Too many requests. Please try again later.")),
    }

    # Try to render the template
    try:
        # Check if template exists
        template_path = os.path.join(current_app.template_folder, "errors", "429.html")
        current_app.logger.debug(f"Looking for template at: {template_path}")
        if os.path.exists(template_path):
            current_app.logger.debug(f"Template found at: {template_path}")
            return render_template("errors/429.html", error=rate_limit_info), 429
        else:
            current_app.error(f"Template not found at: {template_path}")
    except Exception as e:
        current_app.logger.error(f"Error rendering template: {e}")
        current_app.logger.debug(traceback.format_exc())

    # Fallback response if template rendering fails
    fallback_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>429 - Too Many Requests</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                   line-height: 1.6; color: #333; margin: 0; padding: 20px; }
            .container { max-width: 800px; margin: 50px auto; text-align: center; }
            h1 { color: #dc3545; font-size: 2.5em; margin-bottom: 0.5em; }
            .error-details { background: #f8f9fa; border-left: 4px solid #dc3545;
                            padding: 1em; margin: 1em 0; text-align: left; }
            .btn { display: inline-block; padding: 0.5em 1em; margin: 0.5em;
                  text-decoration: none; color: #fff; background: #007bff;
                  border-radius: 4px; }
            .btn:hover { background: #0056b3; }
            .btn-outline { background: transparent; color: #007bff; border: 1px solid #007bff; }
            .btn-outline:hover { background: #f8f9fa; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>429 - Too Many Requests</h1>
            <div class="error-details">
                <p>You have made too many requests to our server. Please try again later.</p>
                <p>Rate limit: {{ error.limit }}</p>
                <p>Please wait: {{ error.reset_time }}</p>
            </div>
            <div>
                <a href="/" class="btn">Return Home</a>
                <button onclick="window.history.back()" class="btn btn-outline">Go Back</button>
            </div>
        </div>
    </body>
    </html>
    """

    # Render the fallback template with the error info
    from jinja2 import Template

    template = Template(fallback_html)
    return template.render(error=rate_limit_info), 429


def init_app(app):
    """Initialize error handlers with the Flask app."""
    # Register the blueprint with a URL prefix
    app.register_blueprint(bp)

    # Manually register the error handler at the app level to ensure it catches all 429 errors
    @app.errorhandler(429)
    def handle_429(error):
        # Log detailed error information
        app.logger.warning(
            "Rate limit exceeded (app-level handler)",
            extra={
                "tags": ["rate_limit"],
                "error_type": type(error).__name__,
                "error_args": getattr(error, "args", []),
                "error_attrs": {k: v for k, v in error.__dict__.items() if not k.startswith("_")},
            },
        )

        # Create rate limit info with defaults
        rate_limit_info = {
            "limit": getattr(error, "limit", "50 per 1 hour"),
            "reset_time": getattr(error, "reset_time", "a few minutes"),
            "description": str(getattr(error, "description", "Too many requests")),
        }

        # Debug template loading
        app.logger.debug(f"Template folder: {app.template_folder}")

        # Try to render the template
        try:
            # Try different template paths
            template_paths = [
                os.path.join(app.template_folder, "errors", "429.html"),
                os.path.join("errors", "429.html"),
                "errors/429.html",
            ]

            for template_path in template_paths:
                full_path = os.path.abspath(os.path.join(app.root_path, template_path))
                app.logger.debug(f"Trying template path: {template_path} (full path: {full_path})")
                if os.path.exists(full_path):
                    app.logger.info(f"Found template at: {full_path}")
                    try:
                        return render_template("errors/429.html", error=rate_limit_info), 429
                    except Exception as e:
                        app.logger.error(f"Error rendering template {template_path}: {e}")
                        app.logger.debug(traceback.format_exc())

            app.logger.error(f"Template not found in any of these locations: {template_paths}")

        except Exception as e:
            app.logger.error(f"Unexpected error in 429 handler: {e}")
            app.logger.debug(traceback.format_exc())

        # Fallback response if template rendering fails
        fallback_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>429 - Too Many Requests</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                }
                .container {
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #dc3545;
                    font-size: 2.5em;
                    margin-bottom: 0.5em;
                }
                .error-details {
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 1em;
                    margin: 1em 0;
                    border-radius: 4px;
                }
                .btn {
                    display: inline-block;
                    padding: 0.5em 1em;
                    margin: 0.5em;
                    text-decoration: none;
                    color: #fff;
                    background: #007bff;
                    border-radius: 4px;
                    border: none;
                    cursor: pointer;
                }
                .btn:hover {
                    background: #0056b3;
                    text-decoration: none;
                }
                .btn-outline {
                    background: transparent;
                    color: #007bff;
                    border: 1px solid #007bff;
                }
                .btn-outline:hover {
                    background: #f8f9fa;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>429 - Too Many Requests</h1>
                <div class="error-details">
                    <p><strong>Rate limit exceeded</strong></p>
                    <p>You have made too many requests to our server.</p>
                    <p>Rate limit: {{ error.limit }}</p>
                    <p>Please try again in: {{ error.reset_time }}</p>
                    {% if error.description %}
                        <p><em>{{ error.description }}</em></p>
                    {% endif %}
                </div>
                <div>
                    <a href="/" class="btn">Return Home</a>
                    <button onclick="window.history.back()" class="btn btn-outline">Go Back</button>
                </div>
            </div>
        </body>
        </html>
        """

        from jinja2 import Template

        try:
            template = Template(fallback_html)
            return template.render(error=rate_limit_info), 429
        except Exception as e:
            app.logger.error(f"Error rendering fallback template: {e}")
            return (
                f"<h1>429 - Too Many Requests</h1>"
                f"<p>You have exceeded the rate limit of {rate_limit_info['limit']}.</p>"
                f"<p>Please try again in {rate_limit_info['reset_time']}.</p>",
                429,
            )
