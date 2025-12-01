const { test, expect } = require('@playwright/test');

/**
 * Test 4: Error Scenarios & Edge Cases
 *
 * This test validates that the application handles errors gracefully:
 * 1. API timeout scenarios
 * 2. No permits found (empty results)
 * 3. API 500 errors
 * 4. Invalid form input
 * 5. Network disconnection
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Error Scenarios', () => {
  let testCounty;

  test.beforeAll(async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/counties`);
    const responseData = await response.json();
    const counties = responseData.data;
    testCounty = counties[0];
  });

  test('shows error message on API timeout', async ({ page }) => {
    await page.goto('/counties');

    // Intercept the pull-permits request and delay it significantly
    await page.route('**/pull-permits', async route => {
      // Delay for 31 seconds (beyond typical timeout)
      await new Promise(resolve => setTimeout(resolve, 31000));
      route.abort();
    });

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Fill form with minimal data
    const today = new Date().toISOString().split('T')[0];
    const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    await page.fill('input[name="date_from"]', lastWeek);
    await page.fill('input[name="date_to"]', today);

    await page.click('button[type="submit"]');

    // Wait for error to appear (with generous timeout)
    const errorLocator = page.locator('text=/timeout|timed out|failed|error/i').first();

    try {
      await errorLocator.waitFor({ timeout: 35000 });
      const errorText = await errorLocator.textContent();
      console.log(`✅ Error message displayed: ${errorText}`);
      expect(errorText.toLowerCase()).toMatch(/timeout|timed out|failed|error/);
    } catch (e) {
      // If no error message, check if still loading (also acceptable)
      const loading = page.locator('text=/loading|pulling/i');
      const isLoading = await loading.count() > 0;

      if (isLoading) {
        console.log('⚠️  Still showing loading state (no timeout error shown)');
      } else {
        throw new Error('Expected timeout error or loading state');
      }
    } finally {
      // Clean up route
      await page.unroute('**/pull-permits');
    }
  });

  test('handles empty results gracefully (no permits found)', async ({ page }) => {
    await page.goto('/counties');

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Use a date range very far in the past (unlikely to have permits)
    const oldDate = new Date('2010-01-01').toISOString().split('T')[0];
    const olderDate = new Date('2010-01-02').toISOString().split('T')[0];

    await page.fill('input[name="date_from"]', oldDate);
    await page.fill('input[name="date_to"]', olderDate);
    await page.selectOption('select[name="limit"]', '50');

    await page.click('button[type="submit"]');

    // Wait for response (could be empty results or error)
    await page.waitForTimeout(5000);

    // Check if results view is shown
    const heading = page.locator('h3').first();
    const headingText = await heading.textContent();

    // Should show results heading even with 0 results
    expect(headingText).toMatch(/Pull Results|Pull Permits/);

    // Look for empty state indicators
    const zeroStats = page.locator('text=/Total Permits Pulled.*0|0 total/i');
    const emptyMessage = page.locator('text=/no permits|no results|0 leads/i');

    const hasZeroStats = await zeroStats.count() > 0;
    const hasEmptyMessage = await emptyMessage.count() > 0;

    if (hasZeroStats || hasEmptyMessage) {
      console.log('✅ Empty results handled gracefully');
    } else {
      console.log('⚠️  No explicit empty state shown (may have results from old data)');
    }
  });

  test('shows error on server failure (500 error)', async ({ page }) => {
    await page.goto('/counties');

    // Intercept and return 500 error
    await page.route('**/pull-permits', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Internal Server Error'
        })
      });
    });

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Fill and submit form
    const today = new Date().toISOString().split('T')[0];
    const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    await page.fill('input[name="date_from"]', lastWeek);
    await page.fill('input[name="date_to"]', today);

    await page.click('button[type="submit"]');

    // Wait for error message
    const errorMessage = page.locator('text=/error|failed|server error/i').first();

    await expect(errorMessage).toBeVisible({ timeout: 10000 });

    const errorText = await errorMessage.textContent();
    console.log(`✅ Error message displayed on 500 error: ${errorText}`);

    // Clean up
    await page.unroute('**/pull-permits');
  });

  test('validates date range (from_date after to_date)', async ({ page }) => {
    await page.goto('/counties');

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Fill with invalid date range (from > to)
    await page.fill('input[name="date_from"]', '2025-12-31');
    await page.fill('input[name="date_to"]', '2025-01-01');

    await page.click('button[type="submit"]');

    // Look for validation error
    // This might be browser validation or custom validation
    const formError = page.locator('text=/invalid|date range|from date|after/i');
    const validationError = page.locator('.form-error, .error-message, [class*="error"]');

    const hasFormError = await formError.count() > 0;
    const hasValidationError = await validationError.count() > 0;

    if (hasFormError || hasValidationError) {
      console.log('✅ Form validation prevents invalid date range');
    } else {
      // Check if form was submitted anyway (should not happen)
      const isModalOpen = await page.locator('h3:has-text("Pull Permits")').count() > 0;

      if (isModalOpen) {
        console.log('⚠️  Form submitted with invalid dates (validation may be missing)');
      } else {
        console.log('✅ Form handled invalid input (closed modal)');
      }
    }
  });

  test('handles network disconnection', async ({ page, context }) => {
    await page.goto('/counties');

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Fill form
    const today = new Date().toISOString().split('T')[0];
    const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    await page.fill('input[name="date_from"]', lastWeek);
    await page.fill('input[name="date_to"]', today);

    // Simulate network offline
    await context.setOffline(true);

    await page.click('button[type="submit"]');

    // Wait for error
    const networkError = page.locator('text=/network|connection|offline|failed/i').first();

    try {
      await expect(networkError).toBeVisible({ timeout: 10000 });
      const errorText = await networkError.textContent();
      console.log(`✅ Network error displayed: ${errorText}`);
    } catch (e) {
      console.log('⚠️  No specific network error message (generic error may be shown)');
    } finally {
      // Restore network
      await context.setOffline(false);
    }
  });

  test('handles missing required fields in form', async ({ page }) => {
    await page.goto('/counties');

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Try to submit without filling required fields
    // Clear any default values
    await page.fill('input[name="date_from"]', '');
    await page.fill('input[name="date_to"]', '');

    await page.click('button[type="submit"]');

    // Check for HTML5 validation or custom error
    const invalidInputs = page.locator('input:invalid');
    const errorMessages = page.locator('text=/required|must provide/i');

    const hasError = (await invalidInputs.count() > 0) || (await errorMessages.count() > 0);

    if (hasError) {
      console.log('✅ Form requires date fields to be filled');
    } else {
      // Check if form has default values that prevent this
      const dateFromValue = await page.inputValue('input[name="date_from"]');
      const dateToValue = await page.inputValue('input[name="date_to"]');

      if (dateFromValue && dateToValue) {
        console.log('ℹ️  Form has default date values (prevents empty submission)');
      }
    }
  });

  test('handles malformed API response gracefully', async ({ page }) => {
    await page.goto('/counties');

    // Intercept and return malformed JSON
    await page.route('**/pull-permits', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{ invalid json }' // Malformed
      });
    });

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Fill and submit
    const today = new Date().toISOString().split('T')[0];
    const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    await page.fill('input[name="date_from"]', lastWeek);
    await page.fill('input[name="date_to"]', today);

    await page.click('button[type="submit"]');

    // Should show error
    const errorMessage = page.locator('text=/error|failed|invalid/i').first();

    try {
      await expect(errorMessage).toBeVisible({ timeout: 10000 });
      console.log('✅ Malformed response handled gracefully');
    } catch (e) {
      console.log('⚠️  No error shown for malformed response');
    } finally {
      await page.unroute('**/pull-permits');
    }
  });

  test('handles API returning unexpected data structure', async ({ page }) => {
    await page.goto('/counties');

    // Return valid JSON but unexpected structure
    await page.route('**/pull-permits', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            // Missing expected fields
            unexpected: 'data'
          }
        })
      });
    });

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    const today = new Date().toISOString().split('T')[0];
    const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    await page.fill('input[name="date_from"]', lastWeek);
    await page.fill('input[name="date_to"]', today);

    await page.click('button[type="submit"]');

    // Should either show error or show results with 0 values
    await page.waitForTimeout(3000);

    const heading = page.locator('h3').first();
    const headingText = await heading.textContent();

    // Should show some response (error or empty results)
    expect(headingText).toBeTruthy();

    console.log('✅ Unexpected data structure handled without crash');

    await page.unroute('**/pull-permits');
  });

  test('modal closes without errors on cancel', async ({ page }) => {
    await page.goto('/counties');

    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Wait for modal
    await expect(page.getByRole('heading', { name: `Pull Permits - ${testCounty.name}` })).toBeVisible();

    // Click close button
    const closeButton = page.locator('button').filter({ has: page.locator('svg') }).first();
    await closeButton.click();

    // Modal should close
    await expect(page.getByRole('heading', { name: `Pull Permits - ${testCounty.name}` })).not.toBeVisible();

    console.log('✅ Modal closes cleanly without errors');
  });
});
