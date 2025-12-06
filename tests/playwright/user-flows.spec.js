/**
 * Playwright User Flow Tests
 *
 * Comprehensive usability and user experience tests for the Meal Expense Tracker application.
 * Tests cover authentication, expense management, restaurant management, and navigation flows.
 *
 * @version 1.0.0
 */

import { test, expect } from '@playwright/test';
import {
  loginUser,
  logoutUser,
  measurePageLoadTime,
  waitForSuccessMessage,
  waitForErrorMessage,
  checkMobileUsability,
  testKeyboardNavigation,
  measureTaskDuration,
  checkLoadingStates,
  checkFormFieldAccessibility,
} from './helpers/usability-helpers.js';

// Test configuration
const TEST_CONFIG = {
  baseUrl: process.env.BASE_URL || 'http://127.0.0.1:5000',
  timeout: 30000,
  testUser: {
    username: 'testuser_1',
    password: 'testpass',
  },
  performanceThresholds: {
    pageLoad: 2000, // 2 seconds per requirements
    taskCompletion: 30000, // 30 seconds for complex tasks
  },
};

test.describe('Authentication Flow', () => {
  test('should login with valid credentials', async ({ page }) => {
    const loadTime = await measurePageLoadTime(page, `${TEST_CONFIG.baseUrl}/auth/login`);
    expect(loadTime).toBeLessThan(TEST_CONFIG.performanceThresholds.pageLoad);

    // Use the helper function which handles login and redirects correctly
    await loginUser(page, TEST_CONFIG.testUser.username, TEST_CONFIG.testUser.password, TEST_CONFIG.baseUrl);

    // After login, we should be on expenses page or home page
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/\/expenses|\/$/);

    // If on home page, it may redirect to expenses - wait a moment
    if (currentUrl.endsWith('/') || currentUrl.match(/\/$/)) {
      try {
        await page.waitForURL('**/expenses', { timeout: 3000 });
      } catch {
        // If no redirect, that's okay - we're logged in
      }
    }

    await page.waitForLoadState('networkidle');

    // Verify we're logged in by checking for expenses page content or home page
    const expensesContainer = page.locator('#card-view-container, #table-view-container, .expense-list').first();
    const hasContainer = await expensesContainer.isVisible({ timeout: 2000 }).catch(() => false);

    // If we're on expenses page, container should exist
    if (page.url().includes('/expenses')) {
      expect(hasContainer).toBeTruthy();
    }
  });

  test('should show clear error message for invalid credentials', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/auth/login`);
    await page.waitForLoadState('networkidle');

    await page.fill('input[name="username"]', 'invalid_user');
    await page.fill('input[name="password"]', 'wrong_password');
    await page.click('button[type="submit"]');

    // Wait for error message
    const errorMessage = await waitForErrorMessage(page, 5000);
    expect(errorMessage).not.toBeNull();
    expect(errorMessage).toContain('Invalid');

    // Verify error message is visible and accessible
    const errorElement = page.locator('.alert-danger, .alert-error').first();
    await expect(errorElement).toBeVisible();
  });

  test('should validate login form fields', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/auth/login`);
    await page.waitForLoadState('networkidle');

    // Try to submit empty form
    await page.click('input[type="submit"], button[type="submit"]');

    // Check for validation messages (HTML5 or custom)
    const usernameField = page.locator('input[name="username"]');
    const passwordField = page.locator('input[name="password"]');

    // Check if fields are marked as invalid or have error messages
    const usernameInvalid = await usernameField.evaluate((el) => !el.validity.valid);
    const passwordInvalid = await passwordField.evaluate((el) => !el.validity.valid);

    // At least one should be invalid if validation is working
    expect(usernameInvalid || passwordInvalid).toBeTruthy();
  });

  test('should support keyboard navigation on login form', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/auth/login`);
    await page.waitForLoadState('networkidle');

    const fieldSelectors = ['input[name="username"]', 'input[name="password"]', 'input[type="submit"], button[type="submit"]'];
    const navigationResult = await testKeyboardNavigation(page, fieldSelectors);

    expect(navigationResult.success).toBeTruthy();
    if (navigationResult.issues.length > 0) {
      console.log('Keyboard navigation issues:', navigationResult.issues);
    }
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await loginUser(page, TEST_CONFIG.testUser.username, TEST_CONFIG.testUser.password, TEST_CONFIG.baseUrl);

    // Find and click logout
    const logoutLink = page.locator('a[href*="logout"], button:has-text("Logout")').first();
    if (await logoutLink.isVisible({ timeout: 2000 })) {
      await logoutLink.click();
      await page.waitForLoadState('networkidle');

      // Should redirect to login or home page
      const currentUrl = page.url();
      expect(currentUrl).toMatch(/login|auth|$/);
    }
  });
});

test.describe('Expense Management Flow', () => {
  test.beforeEach(async ({ page }) => {
    await loginUser(page, TEST_CONFIG.testUser.username, TEST_CONFIG.testUser.password, TEST_CONFIG.baseUrl);
  });

  test('should navigate to add expense page', async ({ page }) => {
    const loadTime = await measurePageLoadTime(page, `${TEST_CONFIG.baseUrl}/expenses/add`);
    expect(loadTime).toBeLessThan(TEST_CONFIG.performanceThresholds.pageLoad);

    // Verify form is visible
    const amountField = page.locator('input[name="amount"]');
    await expect(amountField).toBeVisible();
  });

  test('should validate required fields when adding expense', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');

    // Try to submit empty form
    const submitButton = page.locator('button[type="submit"], input[type="submit"]').first();
    await submitButton.click();

    // Wait a moment for validation
    await page.waitForTimeout(500);

    // Check for validation errors
    const amountField = page.locator('input[name="amount"]');
    const dateField = page.locator('input[name="date"]');
    const restaurantField = page.locator('select[name="restaurant_id"]');

    // At least one required field should show validation error
    const amountInvalid = await amountField.evaluate((el) => !el.validity.valid);
    const dateInvalid = await dateField.evaluate((el) => !el.validity.valid);

    expect(amountInvalid || dateInvalid).toBeTruthy();
  });

  test('should add expense successfully', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');

    // Fill in required fields
    const today = new Date().toISOString().split('T')[0];
    await page.fill('input[name="amount"]', '25.50');
    await page.fill('input[name="date"]', today);

    // Select restaurant if available
    const restaurantSelect = page.locator('select[name="restaurant_id"]');
    const restaurantOptions = await restaurantSelect.locator('option').count();
    if (restaurantOptions > 1) {
      // Select first non-empty option
      await restaurantSelect.selectOption({ index: 1 });
    } else {
      // Skip if no restaurants available
      test.skip();
    }

    // Submit form
    const submitButton = page.locator('button[type="submit"], input[type="submit"]').first();
    const { duration } = await measureTaskDuration(async () => {
      await submitButton.click();
      await page.waitForLoadState('networkidle');
    });

    // Check for success message or redirect
    const success = await waitForSuccessMessage(page, 5000);
    const redirected = page.url().includes('/expenses');

    expect(success || redirected).toBeTruthy();
    expect(duration).toBeLessThan(TEST_CONFIG.performanceThresholds.taskCompletion);
  });

  test('should validate expense amount format', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');

    const amountField = page.locator('input[name="amount"]');

    // Test invalid amount (negative)
    await amountField.fill('-10');
    await amountField.blur();
    await page.waitForTimeout(300);

    // Test invalid amount (text)
    await amountField.fill('abc');
    await amountField.blur();
    await page.waitForTimeout(300);

    // Test valid amount
    await amountField.fill('25.50');
    const isValid = await amountField.evaluate((el) => el.validity.valid);
    expect(isValid).toBeTruthy();
  });

  test('should validate date field (no future dates)', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');

    const dateField = page.locator('input[name="date"]');
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().split('T')[0];

    await dateField.fill(tomorrowStr);
    await dateField.blur();
    await page.waitForTimeout(300);

    // Check if date validation prevents future dates
    const maxDate = await dateField.getAttribute('max');
    if (maxDate) {
      const today = new Date().toISOString().split('T')[0];
      expect(maxDate).toBe(today);
    }
  });

  test('should view expense list with pagination', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses`);
    await page.waitForLoadState('networkidle');

    // Check for expense list container
    const expensesContainer = page.locator('#card-view-container, #table-view-container, .expense-list').first();
    await expect(expensesContainer).toBeVisible();

    // Check for pagination controls if expenses exist
    const pagination = page.locator('.pagination, .page-link').first();
    const hasPagination = await pagination.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasPagination) {
      // Verify pagination is functional
      const nextButton = page.locator('.pagination .page-link:has-text("Next"), .page-item:has-text("Next")').first();
      if (await nextButton.isVisible({ timeout: 1000 })) {
        const isDisabled = await nextButton.evaluate((el) => el.closest('.page-item')?.classList.contains('disabled'));
        // If not disabled, clicking should work
        if (!isDisabled) {
          await nextButton.click();
          await page.waitForLoadState('networkidle');
          // Verify we're still on expenses page
          expect(page.url()).toContain('/expenses');
        }
      }
    }
  });

  test('should filter expenses', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses`);
    await page.waitForLoadState('networkidle');

    // Look for filter controls
    const filterButton = page.locator('button:has-text("Filter"), a:has-text("Filter"), [data-bs-toggle="collapse"]').first();
    if (await filterButton.isVisible({ timeout: 2000 })) {
      await filterButton.click();
      await page.waitForTimeout(500);

      // Check if filter form is visible
      const filterForm = page.locator('form:has(input[name*="filter"]), .filter-form, #filter-form').first();
      const isVisible = await filterForm.isVisible({ timeout: 2000 }).catch(() => false);
      expect(isVisible).toBeTruthy();
    }
  });

  test('should edit expense', async ({ page }) => {
    // First, go to expenses list
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses`);
    await page.waitForLoadState('networkidle');

    // Find an edit button/link
    const editButton = page.locator('a[href*="/edit"], button:has-text("Edit"), .btn-edit').first();
    const hasEditButton = await editButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasEditButton) {
      await editButton.click();
      await page.waitForLoadState('networkidle');

      // Verify we're on edit page
      expect(page.url()).toContain('/edit');

      // Verify form is pre-filled
      const amountField = page.locator('input[name="amount"]');
      const amountValue = await amountField.inputValue();
      expect(amountValue).not.toBe('');

      // Make a change and save
      await amountField.fill('30.00');
      const submitButton = page.locator('button[type="submit"], input[type="submit"]').first();
      await submitButton.click();
      await page.waitForLoadState('networkidle');

      // Check for success
      const success = await waitForSuccessMessage(page, 5000);
      expect(success).toBeTruthy();
    } else {
      // Skip if no expenses to edit
      test.skip();
    }
  });

  test('should delete expense with confirmation', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses`);
    await page.waitForLoadState('networkidle');

    // Find delete button
    const deleteButton = page.locator('button:has-text("Delete"), a:has-text("Delete"), .btn-delete').first();
    const hasDeleteButton = await deleteButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasDeleteButton) {
      await deleteButton.click();
      await page.waitForTimeout(500);

      // Check for confirmation dialog
      const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Delete"), .btn-danger').first();
      if (await confirmButton.isVisible({ timeout: 2000 })) {
        await confirmButton.click();
        await page.waitForLoadState('networkidle');

        // Check for success message
        const success = await waitForSuccessMessage(page, 5000);
        expect(success).toBeTruthy();
      }
    } else {
      test.skip();
    }
  });

  test('should check form field accessibility', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');

    const amountField = page.locator('input[name="amount"]');
    const accessibility = await checkFormFieldAccessibility(amountField);

    // At least one accessibility feature should be present
    expect(accessibility.isAccessible).toBeTruthy();
  });
});

test.describe('Restaurant Management Flow', () => {
  test.beforeEach(async ({ page }) => {
    await loginUser(page, TEST_CONFIG.testUser.username, TEST_CONFIG.testUser.password, TEST_CONFIG.baseUrl);
  });

  test('should navigate to add restaurant page', async ({ page }) => {
    const loadTime = await measurePageLoadTime(page, `${TEST_CONFIG.baseUrl}/restaurants/add`);
    expect(loadTime).toBeLessThan(TEST_CONFIG.performanceThresholds.pageLoad);

    // Verify form is visible
    const nameField = page.locator('input[name="name"]');
    await expect(nameField).toBeVisible();
  });

  test('should validate required fields when adding restaurant', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/restaurants/add`);
    await page.waitForLoadState('networkidle');

    // Try to submit empty form
    const submitButton = page.locator('button[type="submit"], input[type="submit"]').first();
    await submitButton.click();
    await page.waitForTimeout(500);

    // Check for validation errors
    const nameField = page.locator('input[name="name"]');
    const nameInvalid = await nameField.evaluate((el) => !el.validity.valid);

    expect(nameInvalid).toBeTruthy();
  });

  test('should add restaurant successfully', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/restaurants/add`);
    await page.waitForLoadState('networkidle');

    // Fill in required fields
    const restaurantName = `Test Restaurant ${Date.now()}`;
    await page.fill('input[name="name"]', restaurantName);

    // Select restaurant type
    const typeSelect = page.locator('select[name="type"]');
    if (await typeSelect.isVisible()) {
      await typeSelect.selectOption({ index: 1 }); // Select first non-empty option
    }

    // Submit form
    const submitButton = page.locator('button[type="submit"], input[type="submit"]').first();
    const { duration, success } = await measureTaskDuration(async () => {
      await submitButton.click();
      await page.waitForLoadState('networkidle');
    });

    // Check for success
    const successMessage = await waitForSuccessMessage(page, 5000);
    expect(successMessage || success).toBeTruthy();
    expect(duration).toBeLessThan(TEST_CONFIG.performanceThresholds.taskCompletion);
  });

  test('should search restaurants', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/restaurants`);
    await page.waitForLoadState('networkidle');

    // Look for search input
    const searchInput = page.locator('input[type="search"], input[name*="search"], input[placeholder*="Search"]').first();
    const hasSearch = await searchInput.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasSearch) {
      await searchInput.fill('test');
      await page.waitForTimeout(500); // Wait for debounce

      // Check if results update
      const results = page.locator('.restaurant-card, .restaurant-item, tbody tr');
      await expect(results.first()).toBeVisible({ timeout: 3000 });
    }
  });

  test('should view restaurant list', async ({ page }) => {
    const loadTime = await measurePageLoadTime(page, `${TEST_CONFIG.baseUrl}/restaurants`);
    expect(loadTime).toBeLessThan(TEST_CONFIG.performanceThresholds.pageLoad);

    // Check for restaurant list container
    const restaurantsContainer = page.locator('.restaurant-list, #restaurants-container, tbody').first();
    await expect(restaurantsContainer).toBeVisible({ timeout: 5000 });
  });

  test('should edit restaurant', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/restaurants`);
    await page.waitForLoadState('networkidle');

    // Find edit button
    const editButton = page.locator('a[href*="/edit"], button:has-text("Edit"), .btn-edit').first();
    const hasEditButton = await editButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasEditButton) {
      await editButton.click();
      await page.waitForLoadState('networkidle');

      // Verify form is pre-filled
      const nameField = page.locator('input[name="name"]');
      const nameValue = await nameField.inputValue();
      expect(nameValue).not.toBe('');

      // Make a change
      await nameField.fill(`${nameValue} (Edited)`);
      const submitButton = page.locator('input[type="submit"], button[type="submit"]').first();
      await submitButton.click();
      await page.waitForLoadState('networkidle');

      // Check for success
      const success = await waitForSuccessMessage(page, 5000);
      expect(success).toBeTruthy();
    } else {
      test.skip();
    }
  });
});

test.describe('Navigation and UX', () => {
  test.beforeEach(async ({ page }) => {
    await loginUser(page, TEST_CONFIG.testUser.username, TEST_CONFIG.testUser.password, TEST_CONFIG.baseUrl);
  });

  test('should have fast page load times', async ({ page }) => {
    const pages = [
      '/expenses',
      '/expenses/add',
      '/restaurants',
      '/restaurants/add',
    ];

    for (const path of pages) {
      const loadTime = await measurePageLoadTime(page, `${TEST_CONFIG.baseUrl}${path}`);
      expect(loadTime).toBeLessThan(TEST_CONFIG.performanceThresholds.pageLoad);
      console.log(`Page ${path} loaded in ${loadTime}ms`);
    }
  });

  test('should navigate between main sections', async ({ page }) => {
    // Start at expenses
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses`);
    await page.waitForLoadState('networkidle');

    // Navigate to restaurants
    const restaurantsLink = page.locator('a[href*="/restaurants"], nav a:has-text("Restaurants")').first();
    if (await restaurantsLink.isVisible({ timeout: 2000 })) {
      await restaurantsLink.click();
      await page.waitForURL('**/restaurants', { timeout: 5000 });
      await page.waitForLoadState('networkidle');
      expect(page.url()).toContain('/restaurants');
    }

    // Navigate back to expenses
    const expensesLink = page.locator('a[href*="/expenses"], nav a:has-text("Expenses")').first();
    if (await expensesLink.isVisible({ timeout: 2000 })) {
      await expensesLink.click();
      await page.waitForURL('**/expenses', { timeout: 5000 });
      expect(page.url()).toContain('/expenses');
    }
  });

  test('should be mobile responsive', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses`);
    await page.waitForLoadState('networkidle');

    // Test mobile viewport
    const mobileUsability = await checkMobileUsability(page, 375, 667);

    // Log issues but don't fail test (informational)
    if (mobileUsability.issues.length > 0) {
      console.log('Mobile usability issues:', mobileUsability.issues);
    }

    // Check that page is still functional on mobile
    const expensesContainer = page.locator('#card-view-container, #table-view-container').first();
    await expect(expensesContainer).toBeVisible();
  });

  test('should show loading states during async operations', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');

    // Fill form
    const today = new Date().toISOString().split('T')[0];
    await page.fill('input[name="amount"]', '25.50');
    await page.fill('input[name="date"]', today);

    // Check for loading state on submit
    const submitButton = page.locator('button[type="submit"]').first();
    const loadingCheck = await checkLoadingStates(page, async () => {
      await submitButton.click();
    });

    // Loading state is optional but good UX
    if (loadingCheck.hasLoadingState) {
      console.log('Loading state found:', loadingCheck.loadingSelector);
    }
  });

  test('should have accessible error messages', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');

    // Try invalid submission
    const submitButton = page.locator('button[type="submit"]').first();
    await submitButton.click();
    await page.waitForTimeout(1000);

    // Check for error messages
    const errorMessage = await waitForErrorMessage(page, 3000);
    if (errorMessage) {
      // Error message should be visible and readable
      const errorElement = page.locator('.alert-danger, .alert-error, [role="alert"]').first();
      await expect(errorElement).toBeVisible();

      // Check if it has proper ARIA attributes
      const ariaLive = await errorElement.getAttribute('aria-live');
      const role = await errorElement.getAttribute('role');
      expect(ariaLive || role).toBeTruthy();
    }
  });
});

test.describe('Critical User Flows', () => {
  test('Login → Add Expense → View Expense → Edit Expense', async ({ page }) => {
    // Login
    await loginUser(page, TEST_CONFIG.testUser.username, TEST_CONFIG.testUser.password, TEST_CONFIG.baseUrl);

    // Add expense
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');

    const today = new Date().toISOString().split('T')[0];
    await page.fill('input[name="amount"]', '30.00');
    await page.fill('input[name="date"]', today);

    const restaurantSelect = page.locator('select[name="restaurant_id"]');
    const restaurantOptions = await restaurantSelect.locator('option').count();
    if (restaurantOptions > 1) {
      await restaurantSelect.selectOption({ index: 1 });

      const submitButton = page.locator('input[type="submit"], button[type="submit"]').first();
      await submitButton.click();
      await page.waitForLoadState('networkidle');

      // View expense (should redirect to list or details)
      expect(page.url()).toMatch(/\/expenses/);

      // Try to edit if edit button is available
      const editButton = page.locator('a[href*="/edit"], button:has-text("Edit")').first();
      const hasEdit = await editButton.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasEdit) {
        await editButton.click();
        await page.waitForLoadState('networkidle');
        expect(page.url()).toContain('/edit');
      }
    } else {
      test.skip();
    }
  });

  test('Login → Add Restaurant → Search Restaurant → Edit Restaurant', async ({ page }) => {
    await loginUser(page, TEST_CONFIG.testUser.username, TEST_CONFIG.testUser.password, TEST_CONFIG.baseUrl);

    // Add restaurant
    await page.goto(`${TEST_CONFIG.baseUrl}/restaurants/add`);
    await page.waitForLoadState('networkidle');

    const restaurantName = `Test Restaurant ${Date.now()}`;
    await page.fill('input[name="name"]', restaurantName);

    const typeSelect = page.locator('select[name="type"]');
    if (await typeSelect.isVisible()) {
      await typeSelect.selectOption({ index: 1 });

      const submitButton = page.locator('input[type="submit"], button[type="submit"]').first();
      await submitButton.click();
      await page.waitForLoadState('networkidle');

      // Search for restaurant
      await page.goto(`${TEST_CONFIG.baseUrl}/restaurants`);
      await page.waitForLoadState('networkidle');

      const searchInput = page.locator('input[type="search"], input[name*="search"]').first();
      if (await searchInput.isVisible({ timeout: 2000 })) {
        await searchInput.fill(restaurantName);
        await page.waitForTimeout(500);

        // Find and edit
        const editButton = page.locator('a[href*="/edit"], button:has-text("Edit")').first();
        const hasEdit = await editButton.isVisible({ timeout: 3000 }).catch(() => false);

        if (hasEdit) {
          await editButton.click();
          await page.waitForLoadState('networkidle');
          expect(page.url()).toContain('/edit');
        }
      }
    }
  });
});
