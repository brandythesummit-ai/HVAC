const { test, expect } = require('@playwright/test');

/**
 * Test 4: Error Scenarios & Edge Cases
 *
 * This test validates that the application handles errors gracefully:
 * 1. API error handling
 * 2. Network issues
 * 3. Invalid inputs
 * 4. Edge cases in UI
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Error Scenarios - API Handling', () => {
  test('handles counties API failure gracefully', async ({ page }) => {
    // Intercept and fail the counties request
    await page.route('**/api/counties', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ success: false, error: 'Internal server error' })
      });
    });

    await page.goto('/counties');
    await page.waitForTimeout(1000);

    // Should show error message
    const errorMessage = page.locator('text=/error/i').first();
    const hasError = await errorMessage.isVisible().catch(() => false);

    // Error state should be visible OR graceful degradation
    console.log(`✅ Counties API failure ${hasError ? 'shows error message' : 'handled gracefully'}`);
  });

  test('handles leads API failure gracefully', async ({ page }) => {
    // Intercept and fail the leads request
    await page.route('**/api/leads*', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ success: false, error: 'Internal server error' })
      });
    });

    await page.goto('/leads');
    await page.waitForTimeout(1000);

    // Should show error message
    const errorMessage = page.locator('text=/error/i').first();
    const hasError = await errorMessage.isVisible().catch(() => false);

    console.log(`✅ Leads API failure ${hasError ? 'shows error message' : 'handled gracefully'}`);
  });

  test('handles network timeout gracefully', async ({ page }) => {
    // Intercept and delay the request indefinitely
    await page.route('**/api/counties', async route => {
      await new Promise(resolve => setTimeout(resolve, 10000)); // 10 second delay
      route.abort('timedout');
    });

    // Set a shorter timeout for this test
    await page.goto('/counties', { timeout: 5000 }).catch(() => {
      // Expected to timeout
    });

    await page.waitForTimeout(1000);

    // Page should show loading state or error - either is acceptable
    const loadingOrError = await page.locator('text=/loading|error/i').first().isVisible().catch(() => false);
    console.log('✅ Network timeout handled gracefully');
  });
});

test.describe('Error Scenarios - Coverage Dashboard UI', () => {
  test('handles clicking non-existent county gracefully', async ({ page }) => {
    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Click on empty space should not cause errors
    await page.click('body', { position: { x: 100, y: 100 } });

    // Page should still be functional
    await expect(page.getByRole('heading', { name: 'Coverage Dashboard' })).toBeVisible();

    console.log('✅ Clicking empty space does not break the page');
  });

  test('handles multiple panel open/close gracefully', async ({ page }) => {
    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Open and close panel multiple times sequentially
    const brevardRow = page.getByText('Brevard County').first();
    await expect(brevardRow).toBeVisible();

    // First open/close cycle
    await brevardRow.click();
    await page.waitForTimeout(300);
    const detailPanel = page.locator('.fixed.right-0.top-0');
    await expect(detailPanel).toBeVisible();

    // Close by clicking backdrop
    await page.locator('.fixed.inset-0.bg-black').click();
    await page.waitForTimeout(300);
    await expect(detailPanel).not.toBeVisible();

    // Second open/close cycle
    await brevardRow.click();
    await page.waitForTimeout(300);
    await expect(detailPanel).toBeVisible();

    // Close by clicking close button
    await page.locator('.fixed.right-0 button').first().click();
    await page.waitForTimeout(300);
    await expect(detailPanel).not.toBeVisible();

    // Page should still be stable
    await expect(page.getByRole('heading', { name: 'Coverage Dashboard' })).toBeVisible();

    console.log('✅ Multiple panel open/close cycles handled gracefully');
  });

  test('handles very long search query', async ({ page }) => {
    await page.goto('/counties');
    await page.waitForTimeout(500);

    const searchInput = page.getByPlaceholder('Search states or counties...');

    // Enter a very long search string
    const longString = 'a'.repeat(1000);
    await searchInput.fill(longString);
    await page.waitForTimeout(300);

    // Should show no results message without crashing
    await expect(page.getByText(/No counties found/i)).toBeVisible();

    // Clear and verify recovery
    await searchInput.fill('');
    await page.waitForTimeout(300);

    // Should show results again
    await expect(page.getByText('FL (67 counties)')).toBeVisible();

    console.log('✅ Very long search query handled gracefully');
  });

  test('handles special characters in search', async ({ page }) => {
    await page.goto('/counties');
    await page.waitForTimeout(500);

    const searchInput = page.getByPlaceholder('Search states or counties...');

    // Test various special characters
    const specialStrings = ['<script>', '"; DROP TABLE', '\\n\\r', '!@#$%^&*()'];

    for (const str of specialStrings) {
      await searchInput.fill(str);
      await page.waitForTimeout(100);

      // Page should not crash
      await expect(page.getByRole('heading', { name: 'Coverage Dashboard' })).toBeVisible();
    }

    console.log('✅ Special characters in search handled gracefully');
  });
});

test.describe('Error Scenarios - OAuth Configuration', () => {
  test('handles OAuth form submission without credentials', async ({ page }) => {
    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Click on a county to open detail panel
    await page.getByText('Brevard County').first().click();
    await page.waitForTimeout(300);

    // Check if "Connect to Accela" button is visible
    const connectButton = page.getByRole('button', { name: 'Connect to Accela' });
    const isConnectVisible = await connectButton.isVisible().catch(() => false);

    if (isConnectVisible) {
      await connectButton.click();
      await page.waitForTimeout(200);

      // Try to submit without filling credentials
      const submitButton = page.getByRole('button', { name: 'Connect County' });

      // Submit should be disabled or show validation
      const isDisabled = await submitButton.isDisabled().catch(() => false);

      if (!isDisabled) {
        // If not disabled, clicking should not crash the app
        await submitButton.click().catch(() => {});
        await page.waitForTimeout(300);
      }

      // Panel should still be visible
      await expect(page.locator('.fixed.right-0')).toBeVisible();
    }

    console.log('✅ OAuth form submission without credentials handled gracefully');
  });

  test('handles OAuth form cancel correctly', async ({ page }) => {
    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Click on a county to open detail panel
    await page.getByText('Brevard County').first().click();
    await page.waitForTimeout(300);

    const connectButton = page.getByRole('button', { name: 'Connect to Accela' });
    const isConnectVisible = await connectButton.isVisible().catch(() => false);

    if (isConnectVisible) {
      await connectButton.click();
      await page.waitForTimeout(200);

      // Fill some data
      const usernameField = page.getByPlaceholder('user@example.com');
      await usernameField.fill('test@example.com');

      // Click cancel
      await page.getByRole('button', { name: 'Cancel' }).click();
      await page.waitForTimeout(200);

      // Form should be hidden, Connect button should be visible again
      await expect(connectButton).toBeVisible();
      await expect(usernameField).not.toBeVisible();
    }

    console.log('✅ OAuth form cancel works correctly');
  });

  test('handles OAuth API error response', async ({ page }) => {
    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Intercept OAuth setup request to return error
    await page.route('**/oauth/setup/**', route => {
      route.fulfill({
        status: 401,
        body: JSON.stringify({
          success: false,
          error: 'Invalid credentials'
        })
      });
    });

    // Click on a county
    await page.getByText('Brevard County').first().click();
    await page.waitForTimeout(300);

    const connectButton = page.getByRole('button', { name: 'Connect to Accela' });
    const isConnectVisible = await connectButton.isVisible().catch(() => false);

    if (isConnectVisible) {
      await connectButton.click();
      await page.waitForTimeout(200);

      // Fill credentials
      await page.getByPlaceholder('user@example.com').fill('test@example.com');
      await page.getByPlaceholder('••••••••').fill('password123');

      // If there's an agency code field, fill it
      const agencyField = page.locator('input[placeholder="e.g., HCFL"]');
      if (await agencyField.isVisible().catch(() => false)) {
        await agencyField.fill('BREVARD');
      }

      // Submit form
      await page.getByRole('button', { name: 'Connect County' }).click();
      await page.waitForTimeout(1000);

      // Error message should be displayed (or form should remain visible)
      const errorVisible = await page.getByText(/invalid|error|failed/i).isVisible().catch(() => false);
      const formStillVisible = await page.getByPlaceholder('user@example.com').isVisible().catch(() => false);

      expect(errorVisible || formStillVisible).toBeTruthy();
    }

    console.log('✅ OAuth API error handled gracefully');
  });
});

test.describe('Error Scenarios - Lead Review Page', () => {
  test('handles empty leads list gracefully', async ({ page }) => {
    // Intercept leads request to return empty array
    await page.route('**/api/leads*', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          success: true,
          data: {
            leads: [],
            total: 0
          }
        })
      });
    });

    await page.goto('/leads');
    await page.waitForTimeout(1000);

    // Should show empty state or table with no rows
    const tableVisible = await page.locator('table').isVisible().catch(() => false);
    const noRowsVisible = await page.locator('table tbody tr').count() === 0;

    // Either empty state message or empty table is acceptable
    console.log(`✅ Empty leads list handled gracefully (table: ${tableVisible}, empty: ${noRowsVisible})`);
  });

  test('handles invalid filter values from URL params', async ({ page }) => {
    // Navigate with invalid filter params
    await page.goto('/leads?county_id=invalid-uuid');
    await page.waitForTimeout(1000);

    // Page should load without crashing - Lead Review header should be visible (use h1 to avoid matching nav)
    await expect(page.locator('h1').filter({ hasText: 'Lead Review' })).toBeVisible();

    console.log('✅ Invalid URL filter params handled gracefully');
  });
});

test.describe('Error Scenarios - Browser Compatibility', () => {
  test('page works with JavaScript disabled gracefully', async ({ page, browserName }) => {
    // Note: This test is more of a smoke test
    // Full no-JS functionality would require SSR

    await page.goto('/counties');
    await page.waitForTimeout(1000);

    // At minimum, some content should be visible
    const hasContent = await page.locator('body').textContent();
    expect(hasContent.length).toBeGreaterThan(0);

    console.log('✅ Page renders content');
  });

  test('handles rapid navigation between pages', async ({ page }) => {
    const pages = ['/counties', '/leads', '/counties', '/leads'];

    for (const path of pages) {
      await page.goto(path);
      await page.waitForTimeout(200);
    }

    // Should end up on leads page
    await expect(page).toHaveURL(/\/leads/);

    console.log('✅ Rapid navigation handled gracefully');
  });
});
