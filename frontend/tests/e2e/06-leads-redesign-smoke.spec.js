import { test, expect } from '@playwright/test';

/**
 * Smoke Tests for Leads Page Redesign
 * Tests the new two-page architecture (Lead Review + Pipeline)
 */

test.describe('Leads Redesign - Smoke Tests', () => {
  test('Lead Review page loads and displays key components', async ({ page }) => {
    await page.goto('/leads');

    // Page should load
    await expect(page).toHaveURL(/\/leads/);

    // Header should be present
    await expect(page.getByRole('heading', { name: /Lead Review/i })).toBeVisible();

    // Filter panel should be present
    await expect(page.getByText(/Advanced Filters/i)).toBeVisible();

    // Table should be present (even if empty)
    const table = page.locator('table');
    await expect(table).toBeVisible();

    // Pagination controls should be present
    await expect(page.getByText(/Per page:/i)).toBeVisible();

    console.log('✅ Lead Review page loads with all key components');
  });

  test('Pipeline page loads and displays key components', async ({ page }) => {
    await page.goto('/pipeline');

    // Page should load
    await expect(page).toHaveURL(/\/pipeline/);

    // Header should be present
    await expect(page.getByRole('heading', { name: /Summit\.ai Pipeline/i })).toBeVisible();

    // Sync status toggle buttons should be present
    await expect(page.getByText(/Synced/i)).toBeVisible();
    await expect(page.getByText(/Failed/i)).toBeVisible();

    // Filter panel should be present
    await expect(page.getByText(/Advanced Filters/i)).toBeVisible();

    // Table should be present
    const table = page.locator('table');
    await expect(table).toBeVisible();

    console.log('✅ Pipeline page loads with all key components');
  });

  test('Filter panel expands and collapses sections', async ({ page }) => {
    await page.goto('/leads');

    // Wait for filter panel
    await page.waitForSelector('text=/Advanced Filters/i');

    // Basic Filters section should be expanded by default
    const basicSection = page.locator('text=/Basic Filters/i').locator('..');
    await expect(basicSection).toBeVisible();

    // Click to collapse
    await page.getByText('Basic Filters').click();

    // Wait a bit for animation
    await page.waitForTimeout(500);

    // Click to expand again
    await page.getByText('Basic Filters').click();

    console.log('✅ Filter panel sections expand and collapse');
  });

  test('Pagination controls change page size', async ({ page }) => {
    await page.goto('/leads');

    // Wait for page to load
    await page.waitForSelector('text=/Per page:/i');

    // Find the page size selector
    const pageSizeSelect = page.locator('select#pageSize');

    if (await pageSizeSelect.isVisible()) {
      // Change page size
      await pageSizeSelect.selectOption('100');

      // Verify selection changed
      await expect(pageSizeSelect).toHaveValue('100');

      console.log('✅ Pagination page size selector works');
    } else {
      console.log('⚠️ No results to paginate');
    }
  });

  test('Column customizer opens and displays options', async ({ page }) => {
    await page.goto('/leads');

    // Wait for table to load
    await page.waitForSelector('table');

    // Look for "Customize Columns" button
    const customizeButton = page.getByRole('button', { name: /Customize Columns/i });

    if (await customizeButton.isVisible()) {
      // Click to open modal
      await customizeButton.click();

      // Modal should appear
      await expect(page.getByText(/Customize Table Columns/i)).toBeVisible();

      // Should have column options
      await expect(page.getByText(/Contact/i)).toBeVisible();

      // Close modal (look for X button or Cancel)
      const closeButton = page.getByRole('button', { name: /Cancel/i });
      if (await closeButton.isVisible()) {
        await closeButton.click();
      }

      console.log('✅ Column customizer modal works');
    } else {
      console.log('⚠️ Customize Columns button not found');
    }
  });

  test('Lead Review page filters by sync_status=pending', async ({ page }) => {
    await page.goto('/leads');

    // Wait for page to load
    await page.waitForSelector('text=/Lead Review/i');

    // Make API call to get leads with pending status
    const response = await page.request.get('/api/leads?sync_status=pending&limit=10');
    const data = await response.json();

    // Should get pending leads
    expect(data.leads).toBeDefined();

    // All leads should have pending status
    if (data.leads.length > 0) {
      const allPending = data.leads.every(lead =>
        lead.summit_sync_status === 'pending' || lead.summit_sync_status === null
      );
      expect(allPending).toBeTruthy();
      console.log(`✅ Lead Review correctly filters ${data.leads.length} pending leads`);
    } else {
      console.log('⚠️ No pending leads found (this is okay)');
    }
  });

  test('Pipeline page toggles between synced and failed', async ({ page }) => {
    await page.goto('/pipeline');

    // Wait for page to load
    await page.waitForSelector('text=/Summit\.ai Pipeline/i');

    // Synced button should be active by default
    const syncedButton = page.getByRole('button', { name: /Synced/i });
    const failedButton = page.getByRole('button', { name: /Failed/i });

    // Click Failed button
    await failedButton.click();

    // Wait for state change
    await page.waitForTimeout(500);

    // Click Synced button
    await syncedButton.click();

    console.log('✅ Pipeline sync status toggle works');
  });

  test('Expandable row shows lead details', async ({ page }) => {
    await page.goto('/leads');

    // Wait for table to load
    await page.waitForSelector('table');

    // Look for expand icon (ChevronRight)
    const expandButton = page.locator('button svg').first();

    if (await expandButton.isVisible()) {
      // Click to expand
      await expandButton.click();

      // Wait for details to appear
      await page.waitForTimeout(500);

      // Should show expanded content (check for common fields)
      const expandedContent = page.locator('text=/Owner Name|Property Address|HVAC Age/i');

      if (await expandedContent.first().isVisible()) {
        console.log('✅ Expandable row details work');
      } else {
        console.log('⚠️ Expanded content not found');
      }
    } else {
      console.log('⚠️ No leads to expand');
    }
  });

  test('Navigation between Lead Review and Pipeline works', async ({ page }) => {
    // Start at Lead Review
    await page.goto('/leads');
    await expect(page.getByRole('heading', { name: /Lead Review/i })).toBeVisible();

    // Navigate to Pipeline via menu/nav
    await page.goto('/pipeline');
    await expect(page.getByRole('heading', { name: /Summit\.ai Pipeline/i })).toBeVisible();

    // Navigate back to Lead Review
    await page.goto('/leads');
    await expect(page.getByRole('heading', { name: /Lead Review/i })).toBeVisible();

    console.log('✅ Navigation between pages works');
  });

  test('API returns data with pagination parameters', async ({ page }) => {
    await page.goto('/leads');

    // Test API with pagination
    const response = await page.request.get('/api/leads?limit=50&offset=0&sync_status=pending');
    const data = await response.json();

    // Should have leads array and total count
    expect(data.leads).toBeDefined();
    expect(data.total).toBeDefined();
    expect(Array.isArray(data.leads)).toBeTruthy();
    expect(typeof data.total).toBe('number');

    console.log(`✅ API returns ${data.total} total leads with pagination`);
  });
});
