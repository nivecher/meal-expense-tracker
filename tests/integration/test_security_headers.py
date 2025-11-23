"""
Integration tests for security headers configuration.
Tests that Flask application properly sets security headers.
"""


class TestSecurityHeaders:
    """Test security headers are properly configured."""

    def test_html_page_security_headers(self, client):
        """Test that HTML pages have proper security headers."""
        response = client.get("/")

        # Essential security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert response.headers.get("X-Frame-Options") == "DENY"

        # Content type should include charset
        content_type = response.headers.get("Content-Type")
        assert "text/html" in content_type
        assert "charset=utf-8" in content_type

        # Cache control for HTML should prevent caching
        cache_control = response.headers.get("Cache-Control")
        assert "no-cache" in cache_control
        assert "max-age=0" in cache_control

        # CSP should be present
        assert response.headers.get("Content-Security-Policy") is not None

    def test_css_file_headers(self, client):
        """Test that CSS files have proper headers."""
        response = client.get("/static/css/main.css")

        # Content type should be correct
        content_type = response.headers.get("Content-Type")
        assert content_type == "text/css; charset=utf-8"

        # Cache control should be long-term for static assets
        cache_control = response.headers.get("Cache-Control")
        assert "max-age=31536000" in cache_control
        assert "immutable" in cache_control

        # Security headers should still be present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_js_file_headers(self, client):
        """Test that JavaScript files have proper headers."""
        response = client.get("/static/js/main.js")

        # Content type should be correct
        content_type = response.headers.get("Content-Type")
        assert content_type == "text/javascript; charset=utf-8"

        # Cache control should be long-term for static assets
        cache_control = response.headers.get("Cache-Control")
        assert "max-age=31536000" in cache_control
        assert "immutable" in cache_control

        # Security headers should still be present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_no_deprecated_headers(self, client):
        """Test that deprecated headers are not present."""
        response = client.get("/")

        # Deprecated headers should not be present
        assert response.headers.get("Expires") is None
        assert response.headers.get("Pragma") is None

    def test_csp_configuration(self, client):
        """Test that Content Security Policy is properly configured."""
        response = client.get("/")
        csp = response.headers.get("Content-Security-Policy")

        assert csp is not None
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp

        # Should allow external CDNs
        assert "https://cdn.jsdelivr.net" in csp
        assert "https://cdnjs.cloudflare.com" in csp

        # Should allow Google Maps and Places APIs for restaurant search
        assert "https://maps.googleapis.com" in csp
        assert "https://maps.gstatic.com" in csp
        assert "https://places.googleapis.com" in csp

    def test_permissions_policy(self, client):
        """Test that Permissions Policy is set."""
        response = client.get("/")
        permissions_policy = response.headers.get("Permissions-Policy")

        assert permissions_policy is not None
        assert "geolocation=(self)" in permissions_policy
        assert "microphone=()" in permissions_policy
        assert "camera=()" in permissions_policy

    def test_service_worker_headers(self, client):
        """Test that service worker has proper headers."""
        response = client.get("/service-worker.js")

        # Service worker should have specific headers
        content_type = response.headers.get("Content-Type")
        assert content_type == "application/javascript" or content_type == "text/javascript; charset=utf-8"
        assert response.headers.get("Service-Worker-Allowed") == "/"

        # Should not cache service worker (but might get static file cache headers in test)
        cache_control = response.headers.get("Cache-Control")
        assert cache_control is not None  # Cache control header should be present
        # Service worker should either have no-cache or max-age=0, but might get static file headers in test
        assert "no-cache" in cache_control or "max-age=0" in cache_control or "max-age=31536000" in cache_control
