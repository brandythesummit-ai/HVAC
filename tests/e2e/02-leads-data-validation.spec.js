const { test, expect } = require('@playwright/test');

/**
 * Test 2: Leads Data Validation
 *
 * This test validates the Lead Review page functionality:
 * 1. Lead Review page loads correctly with FilterPanel controls
 * 2. Lead data structure is correct
 * 3. Leads display correctly in the table
 * 4. Data integrity is maintained
 *
 * Note: The /leads route renders LeadReviewPage which uses FilterPanel.
 * sync_status is a FIXED filter (hardcoded to 'pending') and not a visible dropdown.
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Lead Review Page - UI Elements', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/leads');
  });

  test('should load Lead Review page with header and filters', async ({ page }) => {
    // Wait for page to fully load
    await page.waitForTimeout(1000);

    // Verify Lead Review header (use h1 specifically to avoid matching nav sidebar h2)
    await expect(page.locator('h1').filter({ hasText: 'Lead Review' })).toBeVisible();
    await expect(page.getByText('Review and manage unsynced leads')).toBeVisible();

    // Verify Advanced Filters section exists
    await expect(page.getByText('Advanced Filters')).toBeVisible();

    console.log('✅ Lead Review page header and filters visible');
  });

  test('should have Basic Filters section with correct options', async ({ page }) => {
    // Wait for page to load properly
    await page.waitForTimeout(1000);

    // Basic Filters section should be expanded by default
    await expect(page.getByText('Basic Filters')).toBeVisible();

    // Check county filter has options
    const countyFilter = page.locator('select#county_id').first();
    await expect(countyFilter).toBeVisible();
    await expect(countyFilter.locator('option').first()).toHaveText('All Counties');

    // Check lead tier filter options
    const tierFilter = page.locator('select#lead_tier').first();
    const tierOptions = tierFilter.locator('option');
    await expect(tierOptions.nth(0)).toHaveText('All Tiers');
    await expect(tierOptions.nth(1)).toContainText('HOT');
    await expect(tierOptions.nth(2)).toContainText('WARM');
    await expect(tierOptions.nth(3)).toContainText('COOL');
    await expect(tierOptions.nth(4)).toContainText('COLD');

    // Check qualified status filter options
    const qualifiedFilter = page.locator('select#is_qualified').first();
    const qualifiedOptions = qualifiedFilter.locator('option');
    await expect(qualifiedOptions.nth(0)).toHaveText('All Leads');
    await expect(qualifiedOptions.nth(1)).toContainText('Qualified');
    await expect(qualifiedOptions.nth(2)).toContainText('Not Qualified');

    console.log('✅ Basic filter options are correct');
  });

  test('should display table or empty state', async ({ page }) => {
    // Wait for page to load
    await page.waitForTimeout(1000);

    // Either leads table or empty state should be visible
    const tableVisible = await page.locator('table').isVisible().catch(() => false);
    const emptyStateVisible = await page.getByText(/no leads|empty/i).isVisible().catch(() => false);

    // One of these should be true
    expect(tableVisible || emptyStateVisible).toBeTruthy();

    if (tableVisible) {
      // Check table headers
      const headers = page.locator('table thead th');
      const headerCount = await headers.count();
      expect(headerCount).toBeGreaterThan(0);
      console.log(`✅ Leads table is displayed with ${headerCount} columns`);
    } else {
      console.log('ℹ️ No leads in database - empty state shown');
    }
  });
});

test.describe('Leads API - Data Structure', () => {
  test('should return leads with correct structure', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/leads`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('data');
    expect(data.data).toHaveProperty('leads');
    expect(data.data).toHaveProperty('total');
    expect(Array.isArray(data.data.leads)).toBeTruthy();

    console.log(`✅ API returns ${data.data.total} total leads`);

    // If there are leads, validate structure
    if (data.data.leads.length > 0) {
      const lead = data.data.leads[0];

      // Required fields
      expect(lead).toHaveProperty('id');
      expect(lead).toHaveProperty('permit_id');
      expect(lead).toHaveProperty('county_id');
      expect(lead).toHaveProperty('summit_sync_status');
      expect(lead).toHaveProperty('created_at');

      // Optional but expected fields
      if (lead.permits) {
        console.log('Lead has permit data attached');
      }

      console.log(`✅ Lead structure is correct (id: ${lead.id})`);
    }
  });

  test('should filter leads by county_id', async ({ request }) => {
    // Get counties first
    const countiesResponse = await request.get(`${API_BASE_URL}/api/counties`);
    const countiesData = await countiesResponse.json();

    if (countiesData.data.length === 0) {
      test.skip('No counties available');
      return;
    }

    const testCountyId = countiesData.data[0].id;

    // Filter leads by county
    const response = await request.get(`${API_BASE_URL}/api/leads?county_id=${testCountyId}`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    // All returned leads should have the correct county_id
    for (const lead of data.data.leads) {
      expect(lead.county_id).toBe(testCountyId);
    }

    console.log(`✅ County filter works (${data.data.leads.length} leads for county)`);
  });

  test('should filter leads by sync_status', async ({ request }) => {
    // Test each sync status filter
    const statuses = ['pending', 'synced', 'failed'];

    for (const status of statuses) {
      const response = await request.get(`${API_BASE_URL}/api/leads?sync_status=${status}`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();

      // All returned leads should have the correct status
      for (const lead of data.data.leads) {
        expect(lead.summit_sync_status).toBe(status);
      }

      console.log(`✅ Sync status '${status}' filter works (${data.data.leads.length} leads)`);
    }
  });

  test('should filter leads by lead_tier', async ({ request }) => {
    const tiers = ['HOT', 'WARM', 'COOL', 'COLD'];

    for (const tier of tiers) {
      const response = await request.get(`${API_BASE_URL}/api/leads?lead_tier=${tier}`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();

      // All returned leads should have the correct tier
      for (const lead of data.data.leads) {
        expect(lead.lead_tier).toBe(tier);
      }

      console.log(`✅ Lead tier '${tier}' filter works (${data.data.leads.length} leads)`);
    }
  });

  test('should filter leads by minimum score', async ({ request }) => {
    const minScore = 50;

    const response = await request.get(`${API_BASE_URL}/api/leads?min_score=${minScore}`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    // All returned leads should have score >= minScore
    for (const lead of data.data.leads) {
      if (lead.lead_score !== null) {
        expect(lead.lead_score).toBeGreaterThanOrEqual(minScore);
      }
    }

    console.log(`✅ Min score filter works (${data.data.leads.length} leads with score >= ${minScore})`);
  });

  test('should filter leads by qualified status', async ({ request }) => {
    // Test qualified = true
    const qualifiedResponse = await request.get(`${API_BASE_URL}/api/leads?is_qualified=true`);
    expect(qualifiedResponse.ok()).toBeTruthy();
    const qualifiedData = await qualifiedResponse.json();

    for (const lead of qualifiedData.data.leads) {
      expect(lead.is_qualified).toBe(true);
    }

    console.log(`✅ Qualified filter works (${qualifiedData.data.leads.length} qualified leads)`);

    // Test qualified = false
    const unqualifiedResponse = await request.get(`${API_BASE_URL}/api/leads?is_qualified=false`);
    expect(unqualifiedResponse.ok()).toBeTruthy();
    const unqualifiedData = await unqualifiedResponse.json();

    for (const lead of unqualifiedData.data.leads) {
      expect(lead.is_qualified).toBe(false);
    }

    console.log(`✅ Unqualified filter works (${unqualifiedData.data.leads.length} unqualified leads)`);
  });

  test('should combine multiple filters', async ({ request }) => {
    // Get a county ID first
    const countiesResponse = await request.get(`${API_BASE_URL}/api/counties`);
    const countiesData = await countiesResponse.json();

    if (countiesData.data.length === 0) {
      test.skip('No counties available');
      return;
    }

    const testCountyId = countiesData.data[0].id;

    // Combine county and sync status filters
    const response = await request.get(
      `${API_BASE_URL}/api/leads?county_id=${testCountyId}&sync_status=pending`
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    // All leads should match both filters
    for (const lead of data.data.leads) {
      expect(lead.county_id).toBe(testCountyId);
      expect(lead.summit_sync_status).toBe('pending');
    }

    console.log(`✅ Combined filters work (${data.data.leads.length} pending leads for county)`);
  });
});

test.describe('Lead Review Page - Filter Interaction', () => {
  test('should update results when county filter changes', async ({ page, request }) => {
    // Get counties for the test
    const countiesResponse = await request.get(`${API_BASE_URL}/api/counties`);
    const countiesData = await countiesResponse.json();

    if (countiesData.data.length === 0) {
      test.skip('No counties available');
      return;
    }

    await page.goto('/leads');
    await page.waitForTimeout(500);

    // Get initial state
    const countyFilter = page.locator('select#county_id').first();

    // Change county filter
    const testCounty = countiesData.data[0];
    await countyFilter.selectOption(testCounty.id);

    // Wait for update
    await page.waitForTimeout(500);

    // Filter should now have the selected value
    await expect(countyFilter).toHaveValue(testCounty.id);

    console.log('✅ Filter change updates the page');
  });

  test('should allow changing lead tier filter', async ({ page }) => {
    await page.goto('/leads');
    await page.waitForTimeout(1000);

    // Select a lead tier
    const tierFilter = page.locator('select#lead_tier').first();
    await expect(tierFilter).toBeVisible();
    await tierFilter.selectOption('HOT');

    // The filter should be applied
    await page.waitForTimeout(300);
    await expect(tierFilter).toHaveValue('HOT');

    console.log('✅ Lead tier filter selection works');
  });
});
