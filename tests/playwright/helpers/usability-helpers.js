/**
 * Usability Helper Utilities for Playwright Tests
 *
 * Provides helper functions for common user actions, accessibility checks,
 * performance measurement, and form validation testing.
 */

/**
 * Login helper function
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} username - Username to login with
 * @param {string} password - Password to login with
 * @param {string} baseUrl - Base URL of the application
 */
export async function loginUser(page, username, password, baseUrl) {
  // Add small delay to avoid rate limiting if multiple tests run quickly
  await page.waitForTimeout(500);

  await page.goto(`${baseUrl}/auth/login`);
  await page.waitForLoadState('networkidle');

  await page.fill('input[name="username"]', username);
  await page.fill('input[name="password"]', password);

  // Submit the form - wait for navigation after clicking submit
  // Use Promise.all to wait for both the click and navigation
  const submitButton = page.locator('input[type="submit"], button[type="submit"]').first();
  await submitButton.waitFor({ state: 'visible', timeout: 5000 });

  // Wait for navigation after form submission
  // Login redirects to home page (/) which then redirects authenticated users to /expenses
  try {
    await Promise.all([
      page.waitForURL('**/', { timeout: 15000 }),
      submitButton.click(),
    ]);
  } catch (error) {
    // Check if we got rate limited (429)
    const response = await page.waitForResponse(
      (response) => response.url().includes('/auth/login') && response.status() === 429,
      { timeout: 2000 }
    ).catch(() => null);

    if (response) {
      throw new Error('Rate limit exceeded (429). Please wait before running tests again.');
    }
    throw error;
  }

  // Wait for page to fully load
  await page.waitForLoadState('networkidle');

  // After login, the home page may redirect to /expenses for authenticated users
  // Wait a moment and check if we're redirected
  await page.waitForTimeout(1000);

  // If we're still on home page, check if there's a redirect happening
  const currentUrl = page.url();
  if (currentUrl.endsWith('/') || currentUrl.match(/\/$/)) {
    // Wait for potential redirect to expenses
    try {
      await page.waitForURL('**/expenses', { timeout: 3000 });
    } catch {
      // If no redirect happens, that's okay - we're logged in on home page
    }
  }

  await page.waitForLoadState('networkidle');
}

/**
 * Logout helper function
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function logoutUser(page) {
  // Look for logout link/button - common patterns
  const logoutLink = page.locator('a[href*="logout"], button:has-text("Logout"), a:has-text("Logout")').first();
  if (await logoutLink.isVisible({ timeout: 2000 })) {
    await logoutLink.click();
    await page.waitForLoadState('networkidle');
  }
}

/**
 * Measure page load time
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} url - URL to measure
 * @returns {Promise<number>} Load time in milliseconds
 */
export async function measurePageLoadTime(page, url) {
  const startTime = Date.now();
  await page.goto(url);
  await page.waitForLoadState('networkidle');
  const loadTime = Date.now() - startTime;
  return loadTime;
}

/**
 * Check if element is accessible via keyboard navigation
 * @param {import('@playwright/test').Locator} element - Element to check
 * @returns {Promise<boolean>} True if accessible via keyboard
 */
export async function isKeyboardAccessible(element) {
  const tabIndex = await element.getAttribute('tabindex');
  const isDisabled = await element.isDisabled();
  const isVisible = await element.isVisible();

  // Element is keyboard accessible if:
  // - It's visible
  // - Not disabled
  // - Has tabindex >= 0 or is a focusable element by default
  if (!isVisible || isDisabled) {
    return false;
  }

  if (tabIndex === null || parseInt(tabIndex) >= 0) {
    return true;
  }

  // Check if it's a naturally focusable element
  const tagName = await element.evaluate((el) => el.tagName.toLowerCase());
  const naturallyFocusable = ['a', 'button', 'input', 'select', 'textarea'].includes(tagName);

  return naturallyFocusable;
}

/**
 * Check if form field has proper label association
 * @param {import('@playwright/test').Locator} field - Form field to check
 * @returns {Promise<{hasLabel: boolean, hasAriaLabel: boolean, hasPlaceholder: boolean}>}
 */
export async function checkFormFieldAccessibility(field) {
  const id = await field.getAttribute('id');
  const ariaLabel = await field.getAttribute('aria-label');
  const ariaLabelledBy = await field.getAttribute('aria-labelledby');
  const placeholder = await field.getAttribute('placeholder');

  let hasLabel = false;
  if (id) {
    const label = await field.locator(`..`).locator(`label[for="${id}"]`).first();
    hasLabel = await label.count() > 0;
  }

  return {
    hasLabel: hasLabel || !!ariaLabelledBy,
    hasAriaLabel: !!ariaLabel,
    hasPlaceholder: !!placeholder,
    isAccessible: hasLabel || !!ariaLabelledBy || !!ariaLabel,
  };
}

/**
 * Wait for success message to appear
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<boolean>} True if success message found
 */
export async function waitForSuccessMessage(page, timeout = 5000) {
  try {
    const successSelectors = [
      '.alert-success',
      '.toast-success',
      '[role="alert"]:has-text("success")',
      '.notification-success',
    ];

    for (const selector of successSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 1000 })) {
        return true;
      }
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Wait for error message to appear
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<string | null>} Error message text or null
 */
export async function waitForErrorMessage(page, timeout = 5000) {
  try {
    const errorSelectors = [
      '.alert-danger',
      '.alert-error',
      '.toast-error',
      '[role="alert"]:has-text("error")',
      '.notification-error',
      '.error-message',
    ];

    for (const selector of errorSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 1000 })) {
        const text = await element.textContent();
        return text ? text.trim() : null;
      }
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Count clicks needed to complete an action
 * @param {Function} action - Async function that performs the action
 * @returns {Promise<number>} Number of clicks performed
 */
export async function countClicksForAction(action) {
  // This is a simplified version - in practice, you'd intercept click events
  // For now, we'll estimate based on the action complexity
  let clickCount = 0;

  // This would need to be implemented with event listeners in a real scenario
  // For now, return a placeholder
  await action();
  return clickCount;
}

/**
 * Check mobile viewport usability
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} width - Viewport width
 * @param {number} height - Viewport height
 * @returns {Promise<{touchTargets: number, smallTargets: number, issues: string[]}>}
 */
export async function checkMobileUsability(page, width = 375, height = 667) {
  await page.setViewportSize({ width, height });
  await page.waitForLoadState('networkidle');

  const issues = [];
  let smallTargets = 0;

  // Check for touch targets (buttons, links) that are too small
  const interactiveElements = await page.locator('button, a, input[type="submit"], input[type="button"]').all();
  for (const element of interactiveElements) {
    const box = await element.boundingBox();
    if (box) {
      // Minimum touch target size is 44x44 pixels (Apple HIG, Material Design)
      if (box.width < 44 || box.height < 44) {
        smallTargets++;
        const text = await element.textContent();
        issues.push(`Small touch target: ${text?.trim() || 'unnamed'} (${box.width}x${box.height}px)`);
      }
    }
  }

  return {
    touchTargets: interactiveElements.length,
    smallTargets,
    issues,
  };
}

/**
 * Test keyboard navigation through a form
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string[]} fieldSelectors - Array of CSS selectors for form fields in order
 * @returns {Promise<{success: boolean, issues: string[]}>}
 */
export async function testKeyboardNavigation(page, fieldSelectors) {
  const issues = [];
  let currentField = null;

  try {
    // Start from first field
    await page.focus(fieldSelectors[0]);
    currentField = fieldSelectors[0];

    // Tab through fields
    for (let i = 1; i < fieldSelectors.length; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100); // Small delay for focus

      const focusedElement = await page.evaluate(() => {
        const active = document.activeElement;
        return active ? active.getAttribute('id') || active.tagName : null;
      });

      // Check if focus moved to expected field
      const expectedSelector = fieldSelectors[i];
      const isFocused = await page.locator(expectedSelector).evaluate((el) => el === document.activeElement);

      if (!isFocused) {
        issues.push(`Focus did not move to expected field: ${expectedSelector}`);
      }
    }

    return {
      success: issues.length === 0,
      issues,
    };
  } catch (error) {
    issues.push(`Keyboard navigation error: ${error.message}`);
    return {
      success: false,
      issues,
    };
  }
}

/**
 * Measure time to complete a task
 * @param {Function} task - Async function representing the task
 * @returns {Promise<{duration: number, success: boolean}>}
 */
export async function measureTaskDuration(task) {
  const startTime = Date.now();
  let success = false;

  try {
    await task();
    success = true;
  } catch (error) {
    console.error('Task failed:', error);
  }

  const duration = Date.now() - startTime;
  return { duration, success };
}

/**
 * Check if loading states are shown during async operations
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {Function} triggerAction - Function that triggers an async action
 * @returns {Promise<{hasLoadingState: boolean, loadingSelector: string | null}>}
 */
export async function checkLoadingStates(page, triggerAction) {
  const loadingSelectors = [
    '.spinner',
    '.loading',
    '[aria-busy="true"]',
    '.btn:has-text("Loading")',
    '.btn[disabled]',
  ];

  let hasLoadingState = false;
  let foundSelector = null;

  // Trigger the action
  const actionPromise = triggerAction();

  // Check for loading indicators immediately after
  await page.waitForTimeout(100);

  for (const selector of loadingSelectors) {
    try {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 500 })) {
        hasLoadingState = true;
        foundSelector = selector;
        break;
      }
    } catch {
      // Continue checking other selectors
    }
  }

  // Wait for action to complete
  await actionPromise;

  return {
    hasLoadingState,
    loadingSelector: foundSelector,
  };
}
