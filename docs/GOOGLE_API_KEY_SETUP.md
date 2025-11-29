# Google API Key Setup Guide

## API Key Restrictions

When setting up your Google Maps API key, you need to configure restrictions appropriately based on where your requests come from.

### Server-Side Requests (Python/Backend)

For server-side requests (Flask backend, CLI scripts, etc.), you should use **IP address restrictions**, not referrer restrictions.

**Why?** Server-side requests don't include HTTP referrer headers, so referrer restrictions will block them.

### Browser-Side Requests (JavaScript/Frontend)

For browser-side requests (JavaScript in web pages), you should use **HTTP referrer restrictions**.

## Configuration Options

### Option 1: Separate API Keys (Recommended)

Use two different API keys:

1. **Backend API Key**: No restrictions (or IP restrictions) for server-side use
2. **Frontend API Key**: HTTP referrer restrictions for browser-side use

### Option 2: Single API Key with IP Restrictions

For development or if using a single API key:

1. Remove HTTP referrer restrictions
2. Use IP address restrictions instead
3. Add your server's IP addresses to the allowed list

### Option 3: Single API Key with Both Restrictions

You can set both IP and referrer restrictions, but this can be complex to manage.

## Testing Script Issues

If you see this error when running `scripts/test_google_places_essentials.py`:

```
Error: 403 Client Error: Forbidden
"message": "Requests from referer <empty> are blocked."
"reason": "API_KEY_HTTP_REFERRER_BLOCKED"
```

**Solutions:**

1. **Remove referrer restrictions** (for server-side testing):

   - Go to Google Cloud Console → APIs & Services → Credentials
   - Edit your API key
   - Under "Application restrictions", select "None" or "IP addresses"
   - Save

2. **Add allowed referrer** (if you want to keep referrer restrictions):

   - Edit your API key
   - Under "Application restrictions", select "HTTP referrers"
   - Add: `localhost:5000/*` (for local testing)
   - Add your production domain for production use

3. **Use IP restrictions** (recommended for server-side):
   - Edit your API key
   - Under "Application restrictions", select "IP addresses"
   - Add your server's IP addresses
   - Save

## Environment Variables

The test script uses:

- `GOOGLE_API_KEY` or `GOOGLE_MAPS_API_KEY` from `.env`
- `GOOGLE_API_REFERRER_DOMAIN` for the Referer header (optional, defaults to `localhost:5000`)

## References

- [Google Cloud Console - API Key Restrictions](https://console.cloud.google.com/apis/credentials)
- [Google Maps Platform - API Key Best Practices](https://developers.google.com/maps/api-security-best-practices#api_key_restrictions)
