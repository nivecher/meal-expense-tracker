# CSRF Protection Implementation

This document outlines the CSRF (Cross-Site Request Forgery) protection implementation for the Meal Expense Tracker API gateway.

## Overview

The application implements comprehensive CSRF protection for both web forms and API endpoints. CSRF protection prevents malicious websites from making unauthorized requests on behalf of authenticated users.

## Architecture

### Backend Implementation

#### 1. CSRF Configuration (`app/extensions.py`)

- **CSRF Protection**: Enabled by default for all environments
- **Token Generation**: Uses Flask-WTF's `generate_csrf()` function
- **Token Validation**: Custom decorator for API routes
- **Error Handling**: Standardized error responses for CSRF failures

#### 2. API Route Protection (`app/api/__init__.py`)

```python
@validate_api_csrf
def api_endpoint():
    # Route implementation
```

The `validate_api_csrf` decorator:

- Validates CSRF tokens from `X-CSRFToken` headers
- Skips validation for GET requests (read-only)
- Returns standardized error responses for failures
- Respects CSRF configuration settings

#### 3. Response Headers

All API responses include CSRF tokens in headers:

```
X-CSRFToken: <generated_token>
```

### Frontend Implementation

#### 1. Unified CSRF Token Utility (`app/static/js/utils/csrf-token.js`)

```javascript
// Get CSRF token from meta tag or form input
const token = get_csrf_token();

// Add CSRF token to headers
add_csrf_to_headers(headers);
```

#### 2. API Request Utilities (`app/static/js/utils/api-utils.js`)

All API requests automatically include CSRF tokens:

```javascript
const response = await apiRequest("/api/v1/expenses", {
  method: "POST",
  body: data,
});
```

#### 3. Form Submission

Forms use the unified CSRF token handling:

```javascript
const formData = new FormData(form);
const response = await fetch(url, {
  method: "POST",
  headers: {
    "X-CSRFToken": getCSRFToken(),
  },
  body: formData,
});
```

## API Gateway Configuration

### Terraform Configuration (`terraform/modules/api_gateway/main.tf`)

The API Gateway CORS configuration includes CSRF headers:

```hcl
allow_headers = [
  "Content-Type",
  "Authorization",
  "X-Requested-With",
  "X-CSRFToken",  # CSRF token header
  "Accept",
  "Origin",
  "Cache-Control"
]

expose_headers = [
  "Content-Length",
  "Content-Type",
  "X-CSRFToken"  # Expose CSRF token to frontend
]
```

## Token Flow

### 1. Initial Page Load

1. Server generates CSRF token for session
2. Token included in HTML meta tag: `<meta name="csrf-token" content="...">`
3. Token also available in form inputs: `<input name="csrf_token" value="...">`

### 2. API Request

1. Frontend retrieves token from meta tag or form input
2. Token included in `X-CSRFToken` header
3. Backend validates token against session
4. Response includes new token in `X-CSRFToken` header

### 3. Form Submission 2

1. Frontend includes token in form data or headers
2. Backend validates token
3. Success/failure response returned

## Error Handling

### CSRF Validation Failures

API endpoints return standardized error responses:

```json
{
  "status": "error",
  "message": "CSRF token is missing or invalid",
  "error_type": "csrf_missing" | "csrf_invalid"
}
```

### Frontend Error Recovery

- Automatic token refresh on validation failures
- User-friendly error messages
- Retry logic for transient failures

## Security Considerations

### 1. Token Expiration

- CSRF tokens expire with session (1 hour default)
- New tokens generated for each response
- Frontend automatically uses latest token

### 2. Same-Origin Policy

- Tokens only valid for same origin
- CORS configuration prevents cross-origin abuse
- Secure cookie settings for session management

### 3. Token Storage

- Tokens stored in session (server-side)
- No sensitive data in client-side storage
- Meta tags and form inputs for token access

## Testing

### Unit Tests (`tests/unit/app/test_csrf_protection.py`)

Comprehensive test coverage:

- GET requests don't require CSRF tokens
- POST/PUT/DELETE requests require valid tokens
- Invalid tokens are rejected
- Response headers include tokens

### Manual Testing

1. **Valid Request**: Include `X-CSRFToken` header with valid token
2. **Missing Token**: Request fails with 403 error
3. **Invalid Token**: Request fails with 403 error
4. **Token Refresh**: New tokens available in response headers

## Configuration

### Environment Variables

```bash
# Enable/disable CSRF protection
WTF_CSRF_ENABLED=True

# CSRF token expiration (seconds)
WTF_CSRF_TIME_LIMIT=3600

# Secret key for token generation
SECRET_KEY=your-secret-key
```

### Lambda Deployment

CSRF protection works in both local development and Lambda environments:

- Session management via signed cookies
- Token generation and validation
- CORS headers properly configured

## Troubleshooting

### Common Issues

1. **Token Not Found**: Check meta tag and form input presence
2. **Validation Failures**: Verify session is active and token is fresh
3. **CORS Errors**: Ensure API Gateway allows `X-CSRFToken` header
4. **Session Issues**: Check session configuration (now using signed cookies)

### Debug Steps

1. Check browser network tab for CSRF headers
2. Verify session cookies are present
3. Confirm API Gateway CORS configuration
4. Review server logs for CSRF validation errors

## Best Practices

1. **Always include CSRF tokens** in state-changing requests
2. **Use the unified token utility** for consistent handling
3. **Handle token refresh** in frontend error recovery
4. **Test CSRF protection** in all environments
5. **Monitor CSRF failures** for potential security issues

## Migration Guide

### From Previous Implementation

1. **API Routes**: Add `@validate_api_csrf` decorator to state-changing endpoints
2. **Frontend**: Update to use unified CSRF token utilities
3. **Testing**: Add CSRF protection tests
4. **Deployment**: Update API Gateway CORS configuration

### Backward Compatibility

- Existing form submissions continue to work
- API endpoints without decorator will fail (add decorator as needed)
- Frontend utilities provide fallback mechanisms
