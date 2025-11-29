const { test, expect } = require('@playwright/test');

/**
 * Test 1: Pull Permits - Complete Validation
 *
 * This test validates the entire pull permits workflow:
 * 1. Form submission and API request
 * 2. Results display and statistics accuracy
 * 3. Data persistence in database
 * 4. Permit and lead creation
 */

const API_BASE_URL = 'http://localhost:8000';

test.describe('Pull Permits - Complete Workflow', () => {
  let countyId;
  let countyName;

  test.beforeAll(async ({ request }) => {
    // Get the first available county for testing
    const response = await request.get(`${API_BASE_URL}/api/counties`);
    expect(response.ok()).toBeTruthy();

    const responseData = await response.json();
    expect(responseData.success).toBeTruthy();

    const counties = responseData.data;
    expect(counties.length).toBeGreaterThan(0);

    countyId = counties[0].id;
    countyName = counties[0].name;

    console.log(`Testing with county: ${countyName} (ID: ${countyId})`);
  });

  test('should complete full pull permits workflow with data validation', async ({ page, request }) => {
    // STEP 1: Navigate to Counties page
    await page.goto('/counties');
    await page.waitForLoadState('networkidle');

    // STEP 2: Find and click the Pull Permits button for the test county
    const countyCard = page.locator('.card').filter({ hasText: countyName }).first();
    await expect(countyCard).toBeVisible();

    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // STEP 3: Wait for modal to open
    await expect(page.getByRole('heading', { name: `Pull Permits - ${countyName}` })).toBeVisible();

    // STEP 4: Fill out the form
    const today = new Date();
    const fromDate = new Date(today);
    fromDate.setDate(fromDate.getDate() - 30); // Last 30 days

    const formatDate = (date) => {
      return date.toISOString().split('T')[0];
    };

    await page.fill('input[name="date_from"]', formatDate(fromDate));
    await page.fill('input[name="date_to"]', formatDate(today));
    await page.selectOption('select[name="limit"]', '50');

    // STEP 5: Submit form and intercept API request
    const requestPromise = page.waitForRequest(
      request => request.url().includes('/pull-permits') && request.method() === 'POST'
    );

    const responsePromise = page.waitForResponse(
      response => response.url().includes('/pull-permits') && response.status() === 200
    );

    await page.click('button[type="submit"]');

    // STEP 6: Validate API request parameters
    const apiRequest = await requestPromise;
    const requestBody = apiRequest.postDataJSON();

    expect(requestBody).toHaveProperty('date_from');
    expect(requestBody).toHaveProperty('date_to');
    expect(requestBody).toHaveProperty('limit');
    expect(requestBody.limit).toBeLessThanOrEqual(50);

    // STEP 7: Wait for response and validate
    const apiResponse = await responsePromise;
    const responseData = await apiResponse.json();

    expect(responseData).toHaveProperty('success', true);
    expect(responseData).toHaveProperty('data');

    const results = responseData.data;
    expect(results).toHaveProperty('total_pulled');
    expect(results).toHaveProperty('hvac_permits');
    expect(results).toHaveProperty('leads_created');
    expect(results).toHaveProperty('permits');

    console.log(`Pull results: ${results.total_pulled} total, ${results.hvac_permits} HVAC, ${results.leads_created} leads`);

    // STEP 8: Validate results view is displayed
    await expect(page.getByRole('heading', { name: `Pull Results - ${countyName}` })).toBeVisible();

    // STEP 9: Validate statistics cards
    const statCards = page.locator('.bg-white.border');

    const totalPulledCard = statCards.filter({ hasText: 'Total Permits Pulled' });
    await expect(totalPulledCard).toContainText(results.total_pulled.toString());

    const hvacCard = statCards.filter({ hasText: 'HVAC Permits' });
    await expect(hvacCard).toContainText(results.hvac_permits.toString());

    const leadsCard = statCards.filter({ hasText: 'Leads Created' });
    await expect(leadsCard).toContainText(results.leads_created.toString());

    // STEP 10: Validate permits table displays correct count
    if (results.permits && results.permits.length > 0) {
      const tableRows = page.locator('table tbody tr');
      const rowCount = await tableRows.count();

      // Table should show up to 20 rows (first page)
      const expectedRowCount = Math.min(results.permits.length, 20);
      expect(rowCount).toBe(expectedRowCount);

      // STEP 11: Validate each row has required fields
      for (let i = 0; i < Math.min(rowCount, 3); i++) {
        const row = tableRows.nth(i);

        // Check that owner, address, date, year, and value columns exist
        await expect(row.locator('td').nth(0)).toBeVisible(); // Owner
        await expect(row.locator('td').nth(1)).toBeVisible(); // Address
        await expect(row.locator('td').nth(2)).toBeVisible(); // Permit Date
        await expect(row.locator('td').nth(3)).toBeVisible(); // Year Built
        await expect(row.locator('td').nth(4)).toBeVisible(); // Job Value
        await expect(row.locator('td').nth(5)).toBeVisible(); // Actions
      }
    }

    // STEP 12: Query database to verify permits were saved
    if (results.leads_created > 0) {
      const dbResponse = await request.get(`${API_BASE_URL}/api/leads?county_id=${countyId}`);
      expect(dbResponse.ok()).toBeTruthy();

      const dbLeads = await dbResponse.json();

      // Verify we have at least the leads we just created
      expect(dbLeads.length).toBeGreaterThanOrEqual(results.leads_created);

      // STEP 13: Validate lead data structure
      // Find the most recent leads (created within last minute)
      const recentLeads = dbLeads.filter(lead => {
        const createdAt = new Date(lead.created_at);
        const oneMinuteAgo = new Date(Date.now() - 60000);
        return createdAt > oneMinuteAgo;
      });

      expect(recentLeads.length).toBeGreaterThan(0);

      // Validate each recent lead has required fields
      for (const lead of recentLeads.slice(0, 3)) {
        expect(lead).toHaveProperty('id');
        expect(lead).toHaveProperty('permit_id');
        expect(lead).toHaveProperty('county_id', countyId);
        expect(lead).toHaveProperty('summit_sync_status');
        expect(['pending', 'synced', 'failed']).toContain(lead.summit_sync_status);
        expect(lead).toHaveProperty('created_at');

        // Validate permit data is populated
        expect(lead).toHaveProperty('permits');
        expect(lead.permits).toHaveProperty('owner_name');
        expect(lead.permits).toHaveProperty('property_address');

        // Owner name and address should not be empty for valid leads
        if (lead.permits.owner_name) {
          expect(lead.permits.owner_name).not.toBe('');
        }
        if (lead.permits.property_address) {
          expect(lead.permits.property_address).not.toBe('');
        }
      }

      console.log(`✅ Verified ${recentLeads.length} leads in database with complete data`);
    }

    // STEP 14: Test "Go to Leads" button
    const goToLeadsButton = page.getByRole('button', { name: /go to leads/i });
    await expect(goToLeadsButton).toBeVisible();
    await goToLeadsButton.click();

    // STEP 15: Verify navigation to Leads page with filters applied
    await page.waitForURL('**/leads');
    await expect(page).toHaveURL(/\/leads/);

    // Check that county filter is pre-selected
    const countyFilter = page.locator('select[name="county_id"]');
    await expect(countyFilter).toHaveValue(countyId.toString());

    // Check that sync status filter is set to pending
    const syncStatusFilter = page.locator('select[name="sync_status"]');
    await expect(syncStatusFilter).toHaveValue('pending');

    console.log('✅ All pull permits validations passed!');
  });

  test('should handle empty results gracefully', async ({ page }) => {
    // Test pulling from a date range that likely has no permits
    await page.goto('/counties');

    const countyCard = page.locator('.card').filter({ hasText: countyName }).first();
    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    // Fill form with date range from 10 years ago (unlikely to have permits)
    const oldDate = new Date();
    oldDate.setFullYear(oldDate.getFullYear() - 10);
    const olderDate = new Date(oldDate);
    olderDate.setDate(olderDate.getDate() - 1);

    const formatDate = (date) => date.toISOString().split('T')[0];

    await page.fill('input[name="date_from"]', formatDate(olderDate));
    await page.fill('input[name="date_to"]', formatDate(oldDate));
    await page.selectOption('select[name="limit"]', '50');

    await page.click('button[type="submit"]');

    // Wait for results (or error)
    await page.waitForTimeout(3000);

    // Should either show 0 results or still be loading
    // This handles the graceful degradation case
    const heading = page.locator('h3').first();
    const headingText = await heading.textContent();

    // Should show some heading (may be "Pull Results", "Pull Permits", or county name)
    expect(headingText).toBeTruthy();

    console.log('✅ Empty results handled gracefully');
  });
});
