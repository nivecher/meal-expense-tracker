"""
Main blueprint routes.

This module contains the route handlers for the main blueprint.
"""

import os
from datetime import datetime

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_login import login_required

from . import bp


@bp.route("/favicon.ico")
def favicon():
    """Serve the favicon.ico file.

    Returns:
        The favicon.ico file
    """
    return send_from_directory(
        os.path.join(current_app.root_path, "static/img/favicons"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@bp.route("/about")
def about():
    """Render the about page.

    Returns:
        Rendered about page template
    """
    return render_template("main/about.html")


@bp.route("/terms")
def terms():
    """Render the terms of service page.

    Returns:
        Rendered terms of service template with current datetime
    """
    return render_template("main/terms.html", now=datetime.utcnow())


@bp.route("/privacy")
def privacy():
    """Render the privacy policy page.

    Returns:
        Rendered privacy policy template with current datetime
    """
    return render_template("main/privacy.html", now=datetime.utcnow())


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    """Render the contact page and handle form submissions.

    Returns:
        Rendered contact template with form
    """
    from .forms import ContactForm

    form = ContactForm()

    if form.validate_on_submit():
        # In a real application, you would process the form here
        # For example, send an email or save to database
        flash("Thank you for your message! We will get back to you soon.", "success")
        return redirect(url_for("main.contact"))

    return render_template("main/contact.html", form=form)


# TODO test code
@bp.route("/test/static/<path:filename>")
def test_static(filename):
    """Test route to verify static file serving.

    Args:
        filename: Name of the file to serve from static folder

    Returns:
        The requested static file
    """
    # Debug information
    static_folder = current_app.static_folder
    full_path = os.path.join(static_folder, filename)
    exists = os.path.exists(full_path)

    # Log debug information
    current_app.logger.info(f"Static folder: {static_folder}")
    current_app.logger.info(f"Requested file: {filename}")
    current_app.logger.info(f"Full path: {full_path}")
    current_app.logger.info(f"File exists: {exists}")

    if not exists:
        return f"File not found: {full_path}", 404

    return send_from_directory(static_folder, filename)


@bp.route("/debug/routes")
def debug_routes():
    """Debug endpoint to list all registered routes."""
    from flask import current_app

    output = []
    for rule in current_app.url_map.iter_rules():
        methods = ",".join(rule.methods)
        line = f"{rule.endpoint}: {rule.rule} [{methods}]"
        output.append(line)

    return "<br>".join(sorted(output))


@bp.route("/")
@login_required
def index():
    """Redirect to the expense listing page."""
    return redirect(url_for("expenses.list_expenses"))


# TODO debug (remove)
@bp.route("/api/config/google-maps-key")
def get_google_maps_key():
    """Return the Google Maps API key.

    Returns:
        JSON response containing the Google Maps API key or an error message
    """
    key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not key:
        return jsonify({"error": "Google Maps API key not configured"}), 500
    return jsonify({"apiKey": key})


# TODO debug (remove)
@bp.route("/api/config/google-maps-id")
def get_google_maps_id():
    """Return the Google Maps Map ID.

    Returns:
        JSON response containing the Google Maps Map ID or an error message
    """
    key = current_app.config.get("GOOGLE_MAPS_MAP_ID")
    if not key:
        return jsonify({"error": "Google Maps Map ID not configured"}), 500
    return jsonify({"mapId": key})


# TODO test code
@bp.route("/test/mime-test")
def mime_test():
    """Test MIME type for JavaScript files.

    This route returns a simple HTML page that tests the MIME type of a JavaScript file.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MIME Type Test</title>
        <script type="module">
            import('/static/js/test-module.js')
                .then(module => {
                    console.log('Module loaded successfully');
                    module.testModule();
                })
                .catch(error => {
                    console.error('Error loading module:', error);
                    document.body.innerHTML += `<p>Error: ${error.message}</p>`;
                });
        </script>
    </head>
    <body>
        <h1>MIME Type Test</h1>
        <p>Check the browser console for test results.</p>
    </body>
    </html>
    """


@bp.route("/test/google-places")
@login_required
def google_places_test():
    """Test page for Google Places API integration.

    This page provides a testing interface for the Google Places API functionality.
    It allows users to search for places and view the results on a map.

    Returns:
        str: Rendered template for the Google Places test page.
    """
    return render_template("test/google_places_test.html", title="Google Places Test")
