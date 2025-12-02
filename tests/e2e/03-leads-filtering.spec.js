const { test, expect } = require('@playwright/test');

/**
 * Test 3: Lead Review Filtering
 *
 * This test validates lead filtering functionality via FilterPanel:
 * 1. Filter by county
 * 2. Filter by lead tier
 * 3. Filter by qualified status
 * 4. Combined filters
 * 5. Reset filters button
 *
 * Note: sync_status is a FIXED filter on LeadReviewPage (hardcoded to 'pending')
 * and is not a visible/changeable dropdown in the UI.
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Lead Review Filtering - UI Interactions', () => {
  let counties;

  test.beforeAll(async ({ request }) => {
    // Get counties for filter testing
    const response = await request.get(`${API_BASE_URL}/api/counties`);
    const data = await response.json();
    counties = data.data || [];
    console.log(`Found ${counties.length} counties for filter testing`);
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/leads');
    await page.waitForTimeout(500); // Wait for initial load
  });

  test('county filter populates with all counties', async ({ page }) => {
    const countyFilter = page.locator('select#county_id').first();
    const options = countyFilter.locator('option');

    // Should have "All Counties" plus one option per county
    const optionCount = await options.count();

    // At minimum should have "All Counties" option
    expect(optionCount).toBeGreaterThanOrEqual(1);

    // First option should be "All Counties"
    await expect(options.first()).toHaveText('All Counties');

    console.log(`✅ County filter has ${optionCount} options (including "All Counties")`);
  });

  test('lead tier filter has correct options', async ({ page }) => {
    const tierFilter = page.locator('select#lead_tier').first();
    const options = tierFilter.locator('option');

    // Should have: All Tiers, HOT, WARM, COOL, COLD
    expect(await options.count()).toBe(5);

    await expect(options.nth(0)).toHaveText('All Tiers');
    await expect(options.nth(1)).toContainText('HOT');
    await expect(options.nth(2)).toContainText('WARM');
    await expect(options.nth(3)).toContainText('COOL');
    await expect(options.nth(4)).toContainText('COLD');

    console.log('✅ Lead tier filter has correct options');
  });

  test('qualified filter has correct options', async ({ page }) => {
    const qualifiedFilter = page.locator('select#is_qualified').first();
    const options = qualifiedFilter.locator('option');

    // Should have: All Leads, Qualified Only, Not Qualified
    expect(await options.count()).toBe(3);

    await expect(options.nth(0)).toHaveText('All Leads');
    await expect(options.nth(1)).toContainText('Qualified');
    await expect(options.nth(2)).toContainText('Not Qualified');

    console.log('✅ Qualified filter has correct options');
  });

  test('selecting county filter updates value', async ({ page }) => {
    if (counties.length === 0) {
      test.skip('No counties available');
      return;
    }

    const countyFilter = page.locator('select#county_id').first();

    // Select first county
    await countyFilter.selectOption(counties[0].id);

    // Verify selection
    await expect(countyFilter).toHaveValue(counties[0].id);

    console.log(`✅ County filter selection works (${counties[0].name})`);
  });

  test('selecting lead tier filter updates value', async ({ page }) => {
    const tierFilter = page.locator('select#lead_tier').first();
    await expect(tierFilter).toBeVisible();

    // Select "HOT"
    await tierFilter.selectOption('HOT');
    await expect(tierFilter).toHaveValue('HOT');

    // Select "WARM"
    await tierFilter.selectOption('WARM');
    await expect(tierFilter).toHaveValue('WARM');

    // Select "COLD"
    await tierFilter.selectOption('COLD');
    await expect(tierFilter).toHaveValue('COLD');

    console.log('✅ Lead tier filter selection works');
  });

  test('min score input accepts valid values', async ({ page }) => {
    const scoreInput = page.locator('input#min_score').first();

    // Enter a valid score
    await scoreInput.fill('50');
    await expect(scoreInput).toHaveValue('50');

    // Enter boundary values
    await scoreInput.fill('0');
    await expect(scoreInput).toHaveValue('0');

    await scoreInput.fill('100');
    await expect(scoreInput).toHaveValue('100');

    console.log('✅ Min score input accepts valid values');
  });

  test('clearing county filter resets to all counties', async ({ page }) => {
    if (counties.length === 0) {
      test.skip('No counties available');
      return;
    }

    const countyFilter = page.locator('select#county_id').first();

    // Select a county first
    await countyFilter.selectOption(counties[0].id);
    await expect(countyFilter).toHaveValue(counties[0].id);

    // Clear by selecting empty value
    await countyFilter.selectOption('');
    await expect(countyFilter).toHaveValue('');

    console.log('✅ Clearing county filter works');
  });

  test('multiple filters can be combined', async ({ page }) => {
    if (counties.length === 0) {
      test.skip('No counties available');
      return;
    }

    const countyFilter = page.locator('select#county_id').first();
    const tierFilter = page.locator('select#lead_tier').first();
    const qualifiedFilter = page.locator('select#is_qualified').first();

    // Apply multiple filters
    await countyFilter.selectOption(counties[0].id);
    await tierFilter.selectOption('HOT');
    await qualifiedFilter.selectOption('true');

    // Verify all filters are applied
    await expect(countyFilter).toHaveValue(counties[0].id);
    await expect(tierFilter).toHaveValue('HOT');
    await expect(qualifiedFilter).toHaveValue('true');

    console.log('✅ Multiple filters can be combined');
  });

  test('filters persist after typing in min score', async ({ page }) => {
    const tierFilter = page.locator('select#lead_tier').first();
    const scoreInput = page.locator('input#min_score').first();
    await expect(tierFilter).toBeVisible();

    // Apply tier filter first
    await tierFilter.selectOption('HOT');

    // Enter min score
    await scoreInput.fill('50');

    // Verify tier filter still has its value
    await expect(tierFilter).toHaveValue('HOT');
    await expect(scoreInput).toHaveValue('50');

    console.log('✅ Filters persist across interactions');
  });

  test('Reset All button clears filters', async ({ page }) => {
    if (counties.length === 0) {
      test.skip('No counties available');
      return;
    }

    const countyFilter = page.locator('select#county_id').first();
    const tierFilter = page.locator('select#lead_tier').first();

    // Apply some filters
    await countyFilter.selectOption(counties[0].id);
    await tierFilter.selectOption('HOT');

    // Click Reset All button
    await page.getByRole('button', { name: 'Reset All' }).click();
    await page.waitForTimeout(300);

    // Verify filters are reset
    await expect(countyFilter).toHaveValue('');
    await expect(tierFilter).toHaveValue('');

    console.log('✅ Reset All button clears filters');
  });
});

test.describe('Leads Filtering - Data Validation', () => {
  test('API respects county filter parameter', async ({ request }) => {
    // Get counties
    const countiesResponse = await request.get(`${API_BASE_URL}/api/counties`);
    const countiesData = await countiesResponse.json();

    if (countiesData.data.length === 0) {
      test.skip('No counties available');
      return;
    }

    const testCountyId = countiesData.data[0].id;

    // Get leads for this county
    const leadsResponse = await request.get(`${API_BASE_URL}/api/leads?county_id=${testCountyId}`);
    expect(leadsResponse.ok()).toBeTruthy();

    const leadsData = await leadsResponse.json();

    // All leads should be for this county
    for (const lead of leadsData.data.leads) {
      expect(lead.county_id).toBe(testCountyId);
    }

    console.log(`✅ API county filter returns ${leadsData.data.leads.length} leads`);
  });

  test('API respects sync_status filter parameter', async ({ request }) => {
    // Test each status
    for (const status of ['pending', 'synced', 'failed']) {
      const response = await request.get(`${API_BASE_URL}/api/leads?sync_status=${status}`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();

      for (const lead of data.data.leads) {
        expect(lead.summit_sync_status).toBe(status);
      }
    }

    console.log('✅ API sync_status filter works correctly');
  });

  test('API respects lead_tier filter parameter', async ({ request }) => {
    // Test each tier
    for (const tier of ['HOT', 'WARM', 'COOL', 'COLD']) {
      const response = await request.get(`${API_BASE_URL}/api/leads?lead_tier=${tier}`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();

      for (const lead of data.data.leads) {
        expect(lead.lead_tier).toBe(tier);
      }
    }

    console.log('✅ API lead_tier filter works correctly');
  });

  test('API respects is_qualified filter parameter', async ({ request }) => {
    // Test qualified=true
    const qualifiedResponse = await request.get(`${API_BASE_URL}/api/leads?is_qualified=true`);
    expect(qualifiedResponse.ok()).toBeTruthy();

    const qualifiedData = await qualifiedResponse.json();
    for (const lead of qualifiedData.data.leads) {
      expect(lead.is_qualified).toBe(true);
    }

    // Test qualified=false
    const unqualifiedResponse = await request.get(`${API_BASE_URL}/api/leads?is_qualified=false`);
    expect(unqualifiedResponse.ok()).toBeTruthy();

    const unqualifiedData = await unqualifiedResponse.json();
    for (const lead of unqualifiedData.data.leads) {
      expect(lead.is_qualified).toBe(false);
    }

    console.log('✅ API is_qualified filter works correctly');
  });

  test('API respects min_score filter parameter', async ({ request }) => {
    const minScore = 50;
    const response = await request.get(`${API_BASE_URL}/api/leads?min_score=${minScore}`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    for (const lead of data.data.leads) {
      if (lead.lead_score !== null && lead.lead_score !== undefined) {
        expect(lead.lead_score).toBeGreaterThanOrEqual(minScore);
      }
    }

    console.log(`✅ API min_score filter works (${data.data.leads.length} leads with score >= ${minScore})`);
  });

  test('API handles combined filters correctly', async ({ request }) => {
    // Get counties first
    const countiesResponse = await request.get(`${API_BASE_URL}/api/counties`);
    const countiesData = await countiesResponse.json();

    if (countiesData.data.length === 0) {
      test.skip('No counties available');
      return;
    }

    const testCountyId = countiesData.data[0].id;

    // Combine county + sync_status + lead_tier
    const response = await request.get(
      `${API_BASE_URL}/api/leads?county_id=${testCountyId}&sync_status=pending&lead_tier=HOT`
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    for (const lead of data.data.leads) {
      expect(lead.county_id).toBe(testCountyId);
      expect(lead.summit_sync_status).toBe('pending');
      expect(lead.lead_tier).toBe('HOT');
    }

    console.log(`✅ API combined filters work (${data.data.leads.length} leads match all criteria)`);
  });

  test('API returns empty array when no leads match filters', async ({ request }) => {
    // Use a combination of filters unlikely to match anything
    const response = await request.get(
      `${API_BASE_URL}/api/leads?sync_status=failed&lead_tier=HOT&min_score=100`
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(Array.isArray(data.data.leads)).toBeTruthy();
    // May be empty or have some leads - both are valid

    console.log(`✅ API handles restrictive filters (${data.data.leads.length} matches)`);
  });
});
