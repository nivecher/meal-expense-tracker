# Google Maps API Integration Guide

## Overview

This application integrates with Google Maps APIs for restaurant location services, including:

- **Google Places API** for restaurant search and details
- **Google Maps JavaScript API** for interactive maps
- **Google Geocoding API** for address validation

## API Key Configuration

### Environment Variables

Set these environment variables for Google Maps integration:

```bash
# Required: Your Google Maps API key
GOOGLE_MAPS_API_KEY=your-api-key-here

# Optional: Your Google Maps Map ID for advanced features
GOOGLE_MAPS_MAP_ID=your-map-id-here
```

### API Key Restrictions

**⚠️ Important**: Your Google Maps API key must be properly configured in the Google Cloud Console to avoid referrer errors.

## Common Issues and Solutions

### RefererNotAllowedMapError

**Error Message**: `RefererNotAllowedMapError: The current referrer is not allowed`

**Cause**: The API key's referrer restrictions don't include your current domain/port.

**Important Distinction**: This error only affects the **Google Maps JavaScript API** (client-side maps), not the **Google Places API** (server-side restaurant search).

**Why Autocomplete Works but Maps Don't**:

- **Places API**: Server-side REST calls from your Flask backend to `https://places.googleapis.com` - no referrer restrictions
- **Maps JavaScript API**: Client-side script loading from `https://maps.googleapis.com/maps/api/js` - strict referrer restrictions

**Solution**: Add your development URL to the allowed referrers in Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Find your API key and click **Edit**
4. Under **Application restrictions**, add these referrers:
   ```
   127.0.0.1:5001
   localhost:5001
   http://127.0.0.1:5001
   http://localhost:5001
   ```

### API Key Setup Steps

1. **Create API Key**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **API Key**

2. **Enable Required APIs**:
   - **Maps JavaScript API**
   - **Maps Embed API** (free, for restaurant detail map with pin)
   - **Places API** (enables restaurant search and photo access)
   - **Geocoding API**

3. **Configure Referrer Restrictions**:
   - Click on your API key
   - Under **Application restrictions**, select **HTTP referrers (web sites)**
   - Add your development URLs:
     ```
     127.0.0.1:5001
     localhost:5001
     http://127.0.0.1:5001
     http://localhost:5001
     ```

4. **Set Environment Variable**:
   ```bash
   export GOOGLE_MAPS_API_KEY=your-api-key-here
   ```

## Testing the Integration

### Development Testing

1. Start the application:

   ```bash
   flask run --port=5001
   ```

2. Navigate to `http://127.0.0.1:5001/restaurants/find-places`

3. The Google Maps integration should work without referrer errors.

### Troubleshooting

#### Referrer Errors

If you still get referrer errors:

1. **Check the exact URL**: The error message shows the exact URL that needs to be authorized
2. **Verify API key**: Ensure `GOOGLE_MAPS_API_KEY` environment variable is set
3. **Check referrer format**: Make sure you're using the exact format shown in the error

#### Image Loading Issues

If restaurant photos fail to load:

1. **Check API Permissions**:
   - In Google Cloud Console, ensure your API key has **Places API** enabled
   - Verify that photo access is included in your API restrictions

2. **Check Browser Console**:
   - Look for specific error messages about failed image loads
   - The application will show fallback icons when images can't be loaded

3. **Network Issues**:
   - Ensure your development environment can access `https://places.googleapis.com`
   - Check for firewall or proxy issues blocking Google APIs

4. **Quota Limits**:
   - Google Places API has usage quotas that might be exceeded
   - Consider implementing caching or rate limiting

## Production Deployment

For production deployment, add your production domain to the referrer list:

```
https://yourdomain.com
https://www.yourdomain.com
```

## Cost Management

See [Google API Cost Reduction Implementation](GOOGLE_API_COST_REDUCTION.md) for strategies to minimize API costs while maintaining functionality.

## Support

For Google Maps API issues:

1. Check the [Google Maps Platform Support](https://developers.google.com/maps/support) page
2. Review the [JavaScript API Error Reference](https://developers.google.com/maps/documentation/javascript/error-messages)
3. Ensure your API key has the correct permissions and referrer restrictions
