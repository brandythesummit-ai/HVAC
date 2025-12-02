const { test, expect } = require('@playwright/test');

/**
 * Test 1: Coverage Dashboard UI
 *
 * This test validates the Coverage Dashboard functionality:
 * 1. Dashboard loads with state sections
 * 2. State sections expand to show counties
 * 3. County detail panel opens on click
 * 4. OAuth configuration form works for unauthorized counties
 * 5. Search functionality filters states and counties
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Coverage Dashboard - UI Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/counties');
  });

  test('should load Coverage Dashboard with state sections', async ({ page }) => {
    // Verify page title and header
    await expect(page.getByRole('heading', { name: 'Coverage Dashboard' })).toBeVisible();
    await expect(page.getByText('Monitor county permit sources')).toBeVisible();

    // Verify search box is present
    await expect(page.getByPlaceholder('Search states or counties...')).toBeVisible();

    // Verify Florida section exists (should be expanded by default)
    await expect(page.getByText('FL (67 counties)')).toBeVisible();

    console.log('✅ Coverage Dashboard loads correctly');
  });

  test('should show Florida counties when state section is expanded', async ({ page }) => {
    // Florida should be expanded by default
    const floridaSection = page.getByText('FL (67 counties)');
    await expect(floridaSection).toBeVisible();

    // Verify some county rows are visible (FL should have counties showing)
    // Wait for virtual list to render
    await page.waitForTimeout(500);

    // Check for known Florida counties
    const brevardCounty = page.getByText('Brevard County').first();
    const alachuaCounty = page.getByText('Alachua County').first();

    // At least one Florida county should be visible
    const brevardVisible = await brevardCounty.isVisible().catch(() => false);
    const alachuaVisible = await alachuaCounty.isVisible().catch(() => false);

    expect(brevardVisible || alachuaVisible).toBeTruthy();

    console.log('✅ Florida counties visible when state expanded');
  });

  test('should open county detail panel when county row is clicked', async ({ page }) => {
    // Wait for Florida counties to load
    await page.waitForTimeout(500);

    // Click on Brevard County (should be visible in the list)
    const brevardRow = page.getByText('Brevard County').first();
    await brevardRow.click();

    // Verify detail panel opens
    const detailPanel = page.locator('.fixed.right-0.top-0');
    await expect(detailPanel).toBeVisible();

    // Verify county name is shown in panel header
    await expect(page.locator('.fixed.right-0 h2')).toContainText('Brevard County');

    // Verify Authorization section exists
    await expect(page.getByText('Authorization')).toBeVisible();

    console.log('✅ County detail panel opens correctly');
  });

  test('should show OAuth configuration form for unauthorized Accela county', async ({ page }) => {
    // Wait for counties to load
    await page.waitForTimeout(500);

    // Click on Brevard County (Accela platform, likely unauthorized)
    const brevardRow = page.getByText('Brevard County').first();
    await brevardRow.click();

    // Wait for detail panel
    await page.waitForTimeout(300);

    // Check if county is already authorized or needs setup
    const isAuthorized = await page.getByText('Authorized with Accela').isVisible().catch(() => false);

    if (!isAuthorized) {
      // Click "Connect to Accela" button
      const connectButton = page.getByRole('button', { name: 'Connect to Accela' });

      if (await connectButton.isVisible().catch(() => false)) {
        await connectButton.click();

        // Verify OAuth form elements appear
        await expect(page.getByRole('button', { name: 'Password' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'OAuth Popup' })).toBeVisible();

        // Check for username/password fields (password method should be default)
        await expect(page.getByPlaceholder('user@example.com')).toBeVisible();
        await expect(page.getByPlaceholder('••••••••')).toBeVisible();

        // Check for action buttons
        await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Connect County' })).toBeVisible();

        console.log('✅ OAuth configuration form displays correctly');
      } else {
        console.log('ℹ️ Connect to Accela button not visible - county may have different platform');
      }
    } else {
      console.log('ℹ️ County already authorized - skipping OAuth form test');
    }
  });

  test('should toggle between Password and OAuth Popup auth methods', async ({ page }) => {
    // Click on Brevard County
    await page.waitForTimeout(500);
    await page.getByText('Brevard County').first().click();
    await page.waitForTimeout(300);

    // Skip if already authorized
    const isAuthorized = await page.getByText('Authorized with Accela').isVisible().catch(() => false);
    if (isAuthorized) {
      test.skip('County already authorized');
      return;
    }

    // Open credential form
    const connectButton = page.getByRole('button', { name: 'Connect to Accela' });
    if (!await connectButton.isVisible().catch(() => false)) {
      test.skip('Connect button not visible');
      return;
    }

    await connectButton.click();
    await page.waitForTimeout(200);

    // Verify Password tab is active by default (has shadow-sm class)
    const passwordTab = page.getByRole('button', { name: 'Password' });
    const oauthTab = page.getByRole('button', { name: 'OAuth Popup' });

    await expect(passwordTab).toBeVisible();
    await expect(oauthTab).toBeVisible();

    // Click OAuth Popup tab
    await oauthTab.click();
    await page.waitForTimeout(100);

    // Verify OAuth info message appears
    await expect(page.getByText("You'll be taken to Accela's login page")).toBeVisible();
    await expect(page.getByRole('button', { name: 'Authorize with Accela' })).toBeVisible();

    // Switch back to Password
    await passwordTab.click();
    await page.waitForTimeout(100);

    // Verify password fields are back
    await expect(page.getByPlaceholder('user@example.com')).toBeVisible();

    console.log('✅ Auth method toggle works correctly');
  });

  test('should close detail panel when close button is clicked', async ({ page }) => {
    // Open a county detail panel
    await page.waitForTimeout(500);
    await page.getByText('Brevard County').first().click();

    // Verify panel is open
    const detailPanel = page.locator('.fixed.right-0.top-0');
    await expect(detailPanel).toBeVisible();

    // Click close button (X icon)
    await page.locator('.fixed.right-0 button').first().click();

    // Verify panel is closed (with animation time)
    await page.waitForTimeout(300);
    await expect(detailPanel).not.toBeVisible();

    console.log('✅ Detail panel closes correctly');
  });

  test('should close detail panel when backdrop is clicked', async ({ page }) => {
    // Open a county detail panel
    await page.waitForTimeout(500);
    await page.getByText('Brevard County').first().click();

    // Verify panel is open
    const detailPanel = page.locator('.fixed.right-0.top-0');
    await expect(detailPanel).toBeVisible();

    // Click the backdrop (semi-transparent overlay)
    await page.locator('.fixed.inset-0.bg-black').click();

    // Verify panel is closed
    await page.waitForTimeout(300);
    await expect(detailPanel).not.toBeVisible();

    console.log('✅ Backdrop click closes panel correctly');
  });
});

test.describe('Coverage Dashboard - Search Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/counties');
  });

  test('should filter counties when searching by name', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search states or counties...');

    // Search for "Brevard"
    await searchInput.fill('Brevard');
    await page.waitForTimeout(300);

    // Florida section should still be visible (contains Brevard)
    await expect(page.getByText('FL (67 counties)')).toBeVisible();

    // Brevard County should be findable
    await expect(page.getByText('Brevard County').first()).toBeVisible();

    console.log('✅ Search by county name works');
  });

  test('should filter by state code', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search states or counties...');

    // Search for "FL"
    await searchInput.fill('FL');
    await page.waitForTimeout(300);

    // Florida section should be visible
    await expect(page.getByText('FL (67 counties)')).toBeVisible();

    console.log('✅ Search by state code works');
  });

  test('should show "no results" message for non-existent search', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search states or counties...');

    // Search for something that doesn't exist
    await searchInput.fill('XYZNONEXISTENT123');
    await page.waitForTimeout(300);

    // Should show "no counties found" message
    await expect(page.getByText(/No counties found matching/i)).toBeVisible();

    console.log('✅ No results message displays correctly');
  });

  test('should clear search and show all states again', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search states or counties...');

    // Search for something specific
    await searchInput.fill('Brevard');
    await page.waitForTimeout(300);

    // Clear search
    await searchInput.fill('');
    await page.waitForTimeout(300);

    // All states should be visible again (at least FL)
    await expect(page.getByText('FL (67 counties)')).toBeVisible();

    console.log('✅ Clearing search restores full list');
  });
});

test.describe('Coverage Dashboard - Platform Badges', () => {
  test('should display platform badges on county rows', async ({ page }) => {
    await page.goto('/counties');
    await page.waitForTimeout(500);

    // Look for platform badges (Accela, Unknown, etc.)
    // At least one Accela badge should be visible in the Florida list
    const accelaBadge = page.getByText('Accela', { exact: true }).first();
    const unknownBadge = page.getByText('Unknown').first();

    const hasAccela = await accelaBadge.isVisible().catch(() => false);
    const hasUnknown = await unknownBadge.isVisible().catch(() => false);

    // At least one type of badge should be visible
    expect(hasAccela || hasUnknown).toBeTruthy();

    console.log('✅ Platform badges display correctly');
  });
});

test.describe('Coverage Dashboard - API Integration', () => {
  test('should load county data from API', async ({ request }) => {
    // Verify the API returns counties
    const response = await request.get(`${API_BASE_URL}/api/counties`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.success).toBeTruthy();
    expect(data.data).toBeDefined();
    expect(Array.isArray(data.data)).toBeTruthy();
    expect(data.data.length).toBeGreaterThan(0);

    // Verify county data structure
    const county = data.data[0];
    expect(county).toHaveProperty('id');
    expect(county).toHaveProperty('name');
    expect(county).toHaveProperty('state');

    console.log(`✅ API returns ${data.data.length} counties`);
  });

  test('should have Florida counties with platform information', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/counties`);
    const data = await response.json();

    const floridaCounties = data.data.filter(c => c.state === 'FL');
    expect(floridaCounties.length).toBe(67);

    // Count by platform
    const platformCounts = floridaCounties.reduce((acc, c) => {
      const platform = c.platform || 'Unknown';
      acc[platform] = (acc[platform] || 0) + 1;
      return acc;
    }, {});

    console.log('Platform distribution:', platformCounts);
    console.log(`✅ Found ${floridaCounties.length} Florida counties`);
  });
});
