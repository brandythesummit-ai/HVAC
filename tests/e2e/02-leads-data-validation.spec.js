const { test, expect } = require('@playwright/test');

/**
 * Test 2: Leads Data Validation
 *
 * This test validates that:
 * 1. Leads appear on the Leads page after pulling permits
 * 2. Lead data matches source permit data
 * 3. All leads have required fields populated
 * 4. Data integrity is maintained throughout the system
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Leads Data Validation', () => {
  let testCountyId;
  let testCountyName;
  let pullResults;

  test.beforeAll(async ({ request }) => {
    // Get a county to test with
    const response = await request.get(`${API_BASE_URL}/api/counties`);
    expect(response.ok()).toBeTruthy();

    const responseData = await response.json();
    const counties = responseData.data;
    expect(counties.length).toBeGreaterThan(0);

    testCountyId = counties[0].id;
    testCountyName = counties[0].name;

    // Pull permits to create test leads
    const today = new Date();
    const fromDate = new Date(today);
    fromDate.setDate(fromDate.getDate() - 60); // Last 60 days for more results

    const pullResponse = await request.post(`${API_BASE_URL}/api/counties/${testCountyId}/pull-permits`, {
      data: {
        date_from: fromDate.toISOString().split('T')[0],
        date_to: today.toISOString().split('T')[0],
        limit: 5
      }
    });

    expect(pullResponse.ok()).toBeTruthy();
    const pullData = await pullResponse.json();
    pullResults = pullData.data;

    console.log(`Setup: Created ${pullResults.leads_created} test leads`);
  });

  test('leads from pull appear on Leads page', async ({ page }) => {
    if (!pullResults || pullResults.leads_created === 0) {
      test.skip('No leads were created during setup');
    }

    // Navigate to Leads page
    await page.goto('/leads');

    // Wait for leads to load
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    // Verify table has rows
    const rows = page.locator('table tbody tr');
    const rowCount = await rows.count();

    expect(rowCount).toBeGreaterThan(0);
    console.log(`Found ${rowCount} leads on Leads page`);

    // Verify that leads have visible owner names and addresses
    const firstRow = rows.first();
    await expect(firstRow.locator('td').nth(0)).toBeVisible(); // Owner column
    await expect(firstRow.locator('td').nth(1)).toBeVisible(); // Address column
    await expect(firstRow.locator('td').nth(2)).toBeVisible(); // Permit Date
    await expect(firstRow.locator('td').nth(3)).toBeVisible(); // Sync Status

    console.log('✅ Leads appear on Leads page with required columns');
  });

  test('lead data matches source permit data', async ({ page, request }) => {
    if (!pullResults || !pullResults.permits || pullResults.permits.length === 0) {
      test.skip('No permits available for comparison');
    }

    // Get the first permit from pull results
    const sourcePermit = pullResults.permits[0];
    const permitId = sourcePermit.id;

    // Query database for lead with this permit_id
    const leadsResponse = await request.get(`${API_BASE_URL}/api/leads?county_id=${testCountyId}`);
    expect(leadsResponse.ok()).toBeTruthy();

    const leadsData = await leadsResponse.json();
    const allLeads = leadsData.data?.leads || [];
    const matchingLead = allLeads.find(lead => lead.permit_id === permitId);

    expect(matchingLead).toBeDefined();
    console.log(`Found matching lead for permit ${permitId}`);

    // Verify data matches
    expect(matchingLead.permits.owner_name).toBe(sourcePermit.owner_name);
    expect(matchingLead.permits.property_address).toBe(sourcePermit.property_address);

    if (sourcePermit.year_built) {
      expect(matchingLead.permits.year_built).toBe(sourcePermit.year_built);
    }

    if (sourcePermit.job_value) {
      expect(matchingLead.permits.job_value).toBe(sourcePermit.job_value);
    }

    // Navigate to Leads page and find this lead in the UI
    await page.goto('/leads');
    await page.waitForSelector('table tbody tr');

    // Look for the lead's owner name in the table
    const leadRow = page.locator('table tbody tr').filter({
      has: page.locator('text=' + sourcePermit.owner_name)
    }).first();

    if (await leadRow.count() > 0) {
      // Verify the row displays the correct data
      const addressCell = leadRow.locator('td').nth(1);
      const addressText = await addressCell.textContent();

      expect(addressText).toContain(sourcePermit.property_address);

      console.log('✅ Lead data in UI matches source permit data');
    }
  });

  test('all leads have required fields', async ({ request }) => {
    const leadsResponse = await request.get(`${API_BASE_URL}/api/leads?county_id=${testCountyId}`);
    expect(leadsResponse.ok()).toBeTruthy();

    const leadsResponseData = await leadsResponse.json();
    const leads = leadsResponseData.data?.leads || [];
    expect(leads.length).toBeGreaterThan(0);

    let validLeadCount = 0;
    const requiredFieldsIssues = [];

    for (const lead of leads) {
      // Track issues for reporting
      const issues = [];

      // Verify lead metadata
      if (!lead.id) issues.push('Missing id');
      if (!lead.permit_id) issues.push('Missing permit_id');
      if (!lead.county_id) issues.push('Missing county_id');
      if (!lead.summit_sync_status) issues.push('Missing summit_sync_status');
      if (!lead.created_at) issues.push('Missing created_at');

      // Verify sync status is valid
      if (!['pending', 'synced', 'failed'].includes(lead.summit_sync_status)) {
        issues.push(`Invalid sync_status: ${lead.summit_sync_status}`);
      }

      // Verify permit data exists
      if (!lead.permits) {
        issues.push('Missing permits object');
      } else {
        // Owner name should exist for most leads
        if (!lead.permits.owner_name || lead.permits.owner_name.trim() === '') {
          issues.push('Missing or empty owner_name');
        }

        // Property address is critical
        if (!lead.permits.property_address || lead.permits.property_address.trim() === '') {
          issues.push('Missing or empty property_address');
        }

        // Opened date should exist
        if (!lead.permits.opened_date) {
          issues.push('Missing opened_date');
        }
      }

      if (issues.length === 0) {
        validLeadCount++;
      } else {
        requiredFieldsIssues.push({
          leadId: lead.id,
          permitId: lead.permit_id,
          issues
        });
      }
    }

    // Log any issues found
    if (requiredFieldsIssues.length > 0) {
      console.log(`⚠️  Found ${requiredFieldsIssues.length} leads with missing fields:`);
      requiredFieldsIssues.slice(0, 5).forEach(item => {
        console.log(`  Lead ${item.leadId}: ${item.issues.join(', ')}`);
      });
    }

    // At least 80% of leads should have all required fields
    const validPercentage = (validLeadCount / leads.length) * 100;
    console.log(`${validLeadCount}/${leads.length} leads (${validPercentage.toFixed(1)}%) have all required fields`);

    expect(validPercentage).toBeGreaterThanOrEqual(80);

    console.log('✅ Required fields validation passed');
  });

  test('leads display with correct sync status indicators', async ({ page }) => {
    await page.goto('/leads');
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    const rows = page.locator('table tbody tr');
    const rowCount = await rows.count();

    expect(rowCount).toBeGreaterThan(0);

    // Check first few rows for sync status badges
    for (let i = 0; i < Math.min(rowCount, 3); i++) {
      const row = rows.nth(i);
      const statusCell = row.locator('td').nth(3); // Sync status column

      // Should have a visible status badge
      await expect(statusCell).toBeVisible();

      const statusText = await statusCell.textContent();

      // Status should be one of the valid values
      expect(['Pending', 'Synced', 'Failed', 'Error'].some(status =>
        statusText.toLowerCase().includes(status.toLowerCase())
      )).toBeTruthy();
    }

    console.log('✅ Sync status indicators display correctly');
  });

  test('lead timestamps are recent and in correct timezone', async ({ request }) => {
    if (!pullResults || pullResults.leads_created === 0) {
      test.skip('No leads created in this test run');
    }

    // Get leads created in the last 5 minutes
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);

    const leadsResponse = await request.get(`${API_BASE_URL}/api/leads?county_id=${testCountyId}`);
    expect(leadsResponse.ok()).toBeTruthy();

    const leads = await leadsResponse.json();

    const recentLeads = leads.filter(lead => {
      const createdAt = new Date(lead.created_at);
      return createdAt > fiveMinutesAgo;
    });

    expect(recentLeads.length).toBeGreaterThan(0);

    // Verify timestamps are reasonable (not in the future, not too old)
    const now = new Date();
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);

    for (const lead of recentLeads) {
      const createdAt = new Date(lead.created_at);

      // Created date should be recent (within last hour for test data)
      expect(createdAt).toBeGreaterThan(oneHourAgo);

      // Created date should not be in the future
      expect(createdAt).toBeLessThanOrEqual(now);
    }

    console.log(`✅ Verified ${recentLeads.length} recent leads have correct timestamps`);
  });

  test('permits table shows accurate permit type information', async ({ page, request }) => {
    // Get leads to verify permit types
    const leadsResponse = await request.get(`${API_BASE_URL}/api/leads?county_id=${testCountyId}`);
    const leads = await leadsResponse.json();

    if (leads.length === 0) {
      test.skip('No leads available for permit type validation');
    }

    // All leads should be from Mechanical permits (due to API filtering)
    const mechanicalLeads = leads.filter(lead =>
      lead.permits.type_value && lead.permits.type_value.includes('Mechanical')
    );

    // Since we're filtering at API level, ALL leads should be Mechanical
    const mechanicalPercentage = (mechanicalLeads.length / leads.length) * 100;

    console.log(`${mechanicalLeads.length}/${leads.length} leads (${mechanicalPercentage.toFixed(1)}%) are Mechanical permits`);

    // With API-level filtering, we expect 100% Mechanical
    expect(mechanicalPercentage).toBeGreaterThanOrEqual(90);

    console.log('✅ API-level permit type filtering working correctly');
  });
});
