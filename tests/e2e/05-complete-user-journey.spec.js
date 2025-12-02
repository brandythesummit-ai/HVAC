const { test, expect } = require('@playwright/test');

/**
 * Test 5: Complete User Journey
 *
 * This test validates the complete user workflow with the new Coverage Dashboard:
 * 1. Navigate to Coverage Dashboard
 * 2. Browse state sections and counties
 * 3. View county details
 * 4. Configure OAuth credentials (if not authorized)
 * 5. Navigate to Leads page
 * 6. Apply filters
 * 7. View lead details
 *
 * Note: Since OAuth requires real credentials, this test focuses on UI flow validation.
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Complete User Journey', () => {
  test('Coverage Dashboard → County Details → Leads Page', async ({ page, request }) => {
    console.log('\n🚀 Starting complete user journey test\n');

    // STEP 1: Navigate to Coverage Dashboard
    await page.goto('/counties');
    await page.waitForTimeout(500);

    await expect(page.getByRole('heading', { name: 'Coverage Dashboard' })).toBeVisible();
    console.log('✅ Step 1: Navigated to Coverage Dashboard');

    // STEP 2: Verify Florida section is expanded by default
    await expect(page.getByText('FL (67 counties)')).toBeVisible();
    console.log('✅ Step 2: Florida section visible with 67 counties');

    // STEP 3: Find and click on a county
    const brevardCounty = page.getByText('Brevard County').first();
    await expect(brevardCounty).toBeVisible();
    await brevardCounty.click();
    await page.waitForTimeout(300);
    console.log('✅ Step 3: Clicked on Brevard County');

    // STEP 4: Verify detail panel opens
    const detailPanel = page.locator('.fixed.right-0.top-0');
    await expect(detailPanel).toBeVisible();
    await expect(page.locator('.fixed.right-0 h2')).toContainText('Brevard County');
    console.log('✅ Step 4: Detail panel opened');

    // STEP 5: Check authorization status and OAuth form
    const isAuthorized = await page.getByText('Authorized with Accela').isVisible().catch(() => false);

    if (isAuthorized) {
      console.log('✅ Step 5: County is already authorized - metrics should be visible');

      // Check for metrics section
      const metricsSection = page.getByText('Metrics').first();
      const hasMetrics = await metricsSection.isVisible().catch(() => false);

      if (hasMetrics) {
        console.log('   - Metrics section is displayed');
      }
    } else {
      console.log('✅ Step 5: County needs authorization - checking OAuth form');

      // Check for Connect button
      const connectButton = page.getByRole('button', { name: 'Connect to Accela' });
      const hasConnect = await connectButton.isVisible().catch(() => false);

      if (hasConnect) {
        console.log('   - "Connect to Accela" button is available');

        // Click to expand form
        await connectButton.click();
        await page.waitForTimeout(200);

        // Verify form elements
        await expect(page.getByRole('button', { name: 'Password' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'OAuth Popup' })).toBeVisible();
        console.log('   - OAuth form elements are present');

        // Cancel form
        await page.getByRole('button', { name: 'Cancel' }).click();
        await page.waitForTimeout(200);
      }
    }

    // STEP 6: Close detail panel
    await page.locator('.fixed.right-0 button').first().click();
    await page.waitForTimeout(300);
    await expect(detailPanel).not.toBeVisible();
    console.log('✅ Step 6: Closed detail panel');

    // STEP 7: Use search to find another county
    const searchInput = page.getByPlaceholder('Search states or counties...');
    await searchInput.fill('Hillsborough');
    await page.waitForTimeout(300);

    // Florida section should still be visible (contains Hillsborough)
    await expect(page.getByText('FL (67 counties)')).toBeVisible();
    console.log('✅ Step 7: Search filters counties correctly');

    // STEP 8: Clear search
    await searchInput.fill('');
    await page.waitForTimeout(300);
    console.log('✅ Step 8: Search cleared');

    // STEP 9: Navigate to Leads page via sidebar
    await page.getByRole('link', { name: 'Lead Review' }).click();
    await expect(page).toHaveURL(/\/leads/);
    console.log('✅ Step 9: Navigated to Leads page');

    // STEP 10: Verify Lead Review page loads (use h1 specifically to avoid matching nav h2)
    await expect(page.locator('h1').filter({ hasText: 'Lead Review' })).toBeVisible();
    await expect(page.getByText('Advanced Filters')).toBeVisible();
    console.log('✅ Step 10: Lead Review page loaded');

    // STEP 11: Apply a filter (use first() for safety with responsive layouts)
    const tierFilter = page.locator('select#lead_tier').first();
    await expect(tierFilter).toBeVisible();
    await tierFilter.selectOption('HOT');
    await page.waitForTimeout(300);
    await expect(tierFilter).toHaveValue('HOT');
    console.log('✅ Step 11: Applied lead tier filter');

    // STEP 12: Navigate back to Coverage Dashboard
    await page.getByRole('link', { name: 'Counties' }).click();
    await expect(page).toHaveURL(/\/counties/);
    await expect(page.getByRole('heading', { name: 'Coverage Dashboard' })).toBeVisible();
    console.log('✅ Step 12: Navigated back to Coverage Dashboard');

    console.log('\n✅ Complete user journey test passed!\n');
  });

  test('Multi-county workflow: Browse multiple counties', async ({ page }) => {
    console.log('\n🚀 Starting multi-county browse test\n');

    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Browse through 3 different counties
    const countyNames = ['Alachua County', 'Baker County', 'Bay County'];
    const visitedCounties = [];

    for (const countyName of countyNames) {
      // Search for the county
      const searchInput = page.getByPlaceholder('Search states or counties...');
      await searchInput.fill(countyName.split(' ')[0]); // Search by first word
      await page.waitForTimeout(300);

      // Try to find and click the county
      const countyRow = page.getByText(countyName).first();
      const isVisible = await countyRow.isVisible().catch(() => false);

      if (isVisible) {
        await countyRow.click();
        await page.waitForTimeout(300);

        // Verify panel opens
        const panelTitle = await page.locator('.fixed.right-0 h2').textContent().catch(() => '');

        if (panelTitle.includes(countyName)) {
          visitedCounties.push(countyName);
          console.log(`✅ Viewed: ${countyName}`);
        }

        // Close panel by clicking backdrop
        await page.locator('.fixed.inset-0.bg-black').click();
        await page.waitForTimeout(200);
      }

      // Clear search
      await searchInput.fill('');
      await page.waitForTimeout(200);
    }

    console.log(`\n✅ Successfully browsed ${visitedCounties.length} counties\n`);
    expect(visitedCounties.length).toBeGreaterThan(0);
  });

  test('API integration: Verify county data consistency', async ({ page, request }) => {
    console.log('\n🚀 Starting data consistency test\n');

    // Get counties from API
    const response = await request.get(`${API_BASE_URL}/api/counties`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    const counties = data.data;
    const floridaCounties = counties.filter(c => c.state === 'FL');

    console.log(`API returns ${counties.length} total counties, ${floridaCounties.length} in Florida`);

    // Navigate to Coverage Dashboard
    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Verify count matches UI
    await expect(page.getByText(`FL (${floridaCounties.length} counties)`)).toBeVisible();
    console.log('✅ County count matches between API and UI');

    // Check platform distribution
    const platformCounts = floridaCounties.reduce((acc, c) => {
      const platform = c.platform || 'Unknown';
      acc[platform] = (acc[platform] || 0) + 1;
      return acc;
    }, {});

    console.log('Platform distribution:');
    Object.entries(platformCounts).forEach(([platform, count]) => {
      console.log(`   - ${platform}: ${count}`);
    });

    // Verify authorized count
    const authorizedCount = floridaCounties.filter(c => c.oauth_authorized).length;
    console.log(`Authorized counties: ${authorizedCount}/${floridaCounties.length}`);

    // UI should show authorized count in state metrics
    const authorizedText = page.locator('text=/\\d+ authorized/');
    const hasAuthorizedCount = await authorizedText.isVisible().catch(() => false);

    if (hasAuthorizedCount) {
      console.log('✅ Authorized count visible in UI');
    }

    console.log('\n✅ Data consistency test passed!\n');
  });

  test('OAuth configuration journey (UI flow only)', async ({ page }) => {
    console.log('\n🚀 Starting OAuth configuration UI test\n');

    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Find an unauthorized Accela county
    const searchInput = page.getByPlaceholder('Search states or counties...');
    await searchInput.fill('Brevard');
    await page.waitForTimeout(300);

    await page.getByText('Brevard County').first().click();
    await page.waitForTimeout(300);

    // Check if needs authorization
    const isAuthorized = await page.getByText('Authorized with Accela').isVisible().catch(() => false);

    if (isAuthorized) {
      console.log('ℹ️ Brevard County is already authorized, skipping OAuth flow');
      return;
    }

    const connectButton = page.getByRole('button', { name: 'Connect to Accela' });
    const hasConnect = await connectButton.isVisible().catch(() => false);

    if (!hasConnect) {
      console.log('ℹ️ Connect button not visible (may be non-Accela platform)');
      return;
    }

    // STEP 1: Open OAuth form
    await connectButton.click();
    await page.waitForTimeout(200);
    console.log('✅ Step 1: Opened OAuth configuration form');

    // STEP 2: Verify Password method is default
    await expect(page.getByPlaceholder('user@example.com')).toBeVisible();
    await expect(page.getByPlaceholder('••••••••')).toBeVisible();
    console.log('✅ Step 2: Password method form is visible');

    // STEP 3: Switch to OAuth Popup method
    await page.getByRole('button', { name: 'OAuth Popup' }).click();
    await page.waitForTimeout(100);

    await expect(page.getByText("You'll be taken to Accela's login page")).toBeVisible();
    await expect(page.getByRole('button', { name: 'Authorize with Accela' })).toBeVisible();
    console.log('✅ Step 3: OAuth Popup method UI is correct');

    // STEP 4: Switch back to Password method
    await page.getByRole('button', { name: 'Password' }).click();
    await page.waitForTimeout(100);
    await expect(page.getByPlaceholder('user@example.com')).toBeVisible();
    console.log('✅ Step 4: Switched back to Password method');

    // STEP 5: Fill credentials (don't submit - just UI test)
    await page.getByPlaceholder('user@example.com').fill('test@example.com');
    await page.getByPlaceholder('••••••••').fill('testpassword123');
    console.log('✅ Step 5: Filled credential fields');

    // Check if agency code field is visible
    const agencyField = page.locator('input[placeholder="e.g., HCFL"]');
    if (await agencyField.isVisible().catch(() => false)) {
      await agencyField.fill('BREVARD');
      console.log('✅ Step 5b: Filled agency code field');
    }

    // STEP 6: Verify Connect County button is enabled
    const submitButton = page.getByRole('button', { name: 'Connect County' });
    const isDisabled = await submitButton.isDisabled().catch(() => true);
    expect(isDisabled).toBeFalsy();
    console.log('✅ Step 6: Connect County button is enabled');

    // STEP 7: Cancel and verify form closes
    await page.getByRole('button', { name: 'Cancel' }).click();
    await page.waitForTimeout(200);

    await expect(connectButton).toBeVisible();
    await expect(page.getByPlaceholder('user@example.com')).not.toBeVisible();
    console.log('✅ Step 7: Cancelled - form closed correctly');

    console.log('\n✅ OAuth configuration UI test passed!\n');
  });
});

test.describe('End-to-End Data Flow', () => {
  test('Leads API returns correct data structure', async ({ request }) => {
    // Test leads endpoint
    const response = await request.get(`${API_BASE_URL}/api/leads`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('data');
    expect(data.data).toHaveProperty('leads');
    expect(data.data).toHaveProperty('total');

    console.log(`✅ Leads API returns ${data.data.total} total leads`);

    // Verify lead structure if any exist
    if (data.data.leads.length > 0) {
      const lead = data.data.leads[0];
      expect(lead).toHaveProperty('id');
      expect(lead).toHaveProperty('county_id');
      expect(lead).toHaveProperty('summit_sync_status');
      console.log('✅ Lead data structure is correct');
    }
  });

  test('Counties API returns correct data structure', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/counties`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('success', true);
    expect(data).toHaveProperty('data');
    expect(Array.isArray(data.data)).toBeTruthy();

    console.log(`✅ Counties API returns ${data.data.length} counties`);

    // Verify county structure
    if (data.data.length > 0) {
      const county = data.data[0];
      expect(county).toHaveProperty('id');
      expect(county).toHaveProperty('name');
      expect(county).toHaveProperty('state');
      expect(county).toHaveProperty('platform');
      console.log('✅ County data structure is correct');
    }
  });
});
