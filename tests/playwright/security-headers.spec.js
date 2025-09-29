/**
 * Security Headers Tests
 * Tests that all required security headers are properly set
 */

import { test, expect } from '@playwright/test';

// Test configuration
const TEST_CONFIG = {
  baseUrl: process.env.BASE_URL || 'http://localhost:5000',
  timeout: 30000,
};

test.describe('Security Headers', () => {
  test('should have proper security headers on main page', async ({ page }) => {
    const response = await page.goto(`${TEST_CONFIG.baseUrl}/`);

    // Check essential security headers
    expect(response.headers()['x-content-type-options']).toBe('nosniff');
    expect(response.headers()['referrer-policy']).toBe('strict-origin-when-cross-origin');
    expect(response.headers()['x-frame-options']).toBe('DENY');

    // Check content type
    const contentType = response.headers()['content-type'];
    expect(contentType).toContain('text/html');
    expect(contentType).toContain('charset=utf-8');

    // Check cache control for HTML
    const cacheControl = response.headers()['cache-control'];
    expect(cacheControl).toContain('no-cache');
    expect(cacheControl).toContain('max-age=0');

    // Check CSP is present
    expect(response.headers()['content-security-policy']).toBeDefined();
  });

  test('should have proper headers on CSS files', async ({ page }) => {
    const response = await page.goto(`${TEST_CONFIG.baseUrl}/static/css/main.css`);

    // Check content type
    const contentType = response.headers()['content-type'];
    expect(contentType).toBe('text/css; charset=utf-8');

    // Check cache control for static assets
    const cacheControl = response.headers()['cache-control'];
    expect(cacheControl).toContain('max-age=31536000');
    expect(cacheControl).toContain('immutable');

    // Check security headers
    expect(response.headers()['x-content-type-options']).toBe('nosniff');
  });

  test('should have proper headers on JavaScript files', async ({ page }) => {
    const response = await page.goto(`${TEST_CONFIG.baseUrl}/static/js/main.js`);

    // Check content type
    const contentType = response.headers()['content-type'];
    expect(contentType).toBe('text/javascript; charset=utf-8');

    // Check cache control for static assets
    const cacheControl = response.headers()['cache-control'];
    expect(cacheControl).toContain('max-age=31536000');
    expect(cacheControl).toContain('immutable');

    // Check security headers
    expect(response.headers()['x-content-type-options']).toBe('nosniff');
  });

  test('should not have deprecated headers', async ({ page }) => {
    const response = await page.goto(`${TEST_CONFIG.baseUrl}/`);

    // Check that deprecated headers are not present
    expect(response.headers()['expires']).toBeUndefined();
    expect(response.headers()['pragma']).toBeUndefined();
  });

  test('should have proper CSP configuration', async ({ page }) => {
    const response = await page.goto(`${TEST_CONFIG.baseUrl}/`);
    const csp = response.headers()['content-security-policy'];

    expect(csp).toBeDefined();
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("base-uri 'self'");
  });

  test('should load external resources with proper CSP', async ({ page }) => {
    // Test that external CDN resources are allowed by CSP
    await page.goto(`${TEST_CONFIG.baseUrl}/`);

    // Check that Bootstrap CSS loads (external CDN)
    const bootstrapLink = page.locator('link[href*="bootstrap"]').first();
    await expect(bootstrapLink).toBeVisible();

    // Check that Font Awesome loads (external CDN)
    const fontAwesomeLink = page.locator('link[href*="font-awesome"]').first();
    await expect(fontAwesomeLink).toBeVisible();
  });
});
