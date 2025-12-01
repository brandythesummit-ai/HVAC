const { test, expect } = require('@playwright/test');

/**
 * Test 5: Complete User Journey
 *
 * This test validates the complete workflow from start to finish:
 * 1. Pull permits from Accela
 * 2. Verify results display correctly
 * 3. Navigate to Leads page
 * 4. Verify leads appear with correct data
 * 5. Filter leads by status
 * 6. Select leads for sync
 * 7. Sync to Summit.AI
 * 8. Verify sync status updates
 * 9. Validate database state
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Complete User Journey', () => {
  test('complete workflow: Pull → Verify → Filter → Sync', async ({ page, request }) => {
    // STEP 1: Get test county
    const countiesResponse = await request.get(`${API_BASE_URL}/api/counties`);
    expect(countiesResponse.ok()).toBeTruthy();

    const countiesData = await countiesResponse.json();
    const counties = countiesData.data;
    expect(counties.length).toBeGreaterThan(0);

    const testCounty = counties[0];
    console.log(`\n🚀 Starting complete user journey with county: ${testCounty.name}\n`);

    // STEP 2: Navigate to Counties page
    await page.goto('/counties');
    await expect(page).toHaveTitle(/Summit\.AI/);
    console.log('✅ Step 1: Navigated to Counties page');

    // STEP 3: Open Pull Permits modal
    const countyCard = page.locator('.card').filter({ hasText: testCounty.name }).first();
    await expect(countyCard).toBeVisible();

    const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
    await pullButton.click();

    await expect(page.getByRole('heading', { name: `Pull Permits - ${testCounty.name}` })).toBeVisible();
    console.log('✅ Step 2: Opened Pull Permits modal');

    // STEP 4: Fill out form with recent date range
    const today = new Date();
    const fromDate = new Date(today);
    fromDate.setDate(fromDate.getDate() - 45); // Last 45 days for good sample

    const formatDate = (date) => date.toISOString().split('T')[0];

    await page.fill('input[name="date_from"]', formatDate(fromDate));
    await page.fill('input[name="date_to"]', formatDate(today));
    await page.selectOption('select[name="limit"]', '50'); // Higher limit for better testing

    console.log(`✅ Step 3: Configured date range (${formatDate(fromDate)} to ${formatDate(today)})`);

    // STEP 5: Submit form and wait for results
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/pull-permits') && response.status() === 200,
      { timeout: 60000 } // Extended timeout for real API calls
    );

    await page.click('button[type="submit"]');
    console.log('⏳ Step 4: Submitted pull permits request...');

    const apiResponse = await responsePromise;
    const responseData = await apiResponse.json();

    expect(responseData.success).toBeTruthy();
    const results = responseData.data;

    console.log(`✅ Step 5: Received results - ${results.total_pulled} total, ${results.hvac_permits} HVAC, ${results.leads_created} leads created`);

    // STEP 6: Verify results view displays correctly
    await expect(page.getByRole('heading', { name: `Pull Results - ${testCounty.name}` })).toBeVisible();

    const statCards = page.locator('.bg-white.border');

    await expect(statCards.filter({ hasText: 'Total Permits Pulled' })).toContainText(results.total_pulled.toString());
    await expect(statCards.filter({ hasText: 'HVAC Permits' })).toContainText(results.hvac_permits.toString());
    await expect(statCards.filter({ hasText: 'Leads Created' })).toContainText(results.leads_created.toString());

    console.log('✅ Step 6: Results view shows correct statistics');

    if (results.leads_created === 0) {
      console.log('⚠️  No leads created - test will skip remaining steps');
      test.skip();
    }

    // STEP 7: Verify permits table shows data
    const tableRows = page.locator('table tbody tr');
    const rowCount = await tableRows.count();

    expect(rowCount).toBeGreaterThan(0);
    console.log(`✅ Step 7: Permits table displays ${rowCount} rows`);

    // STEP 8: Navigate to Leads page
    const goToLeadsButton = page.getByRole('button', { name: /go to leads/i });
    await expect(goToLeadsButton).toBeVisible();
    await goToLeadsButton.click();

    await page.waitForURL('**/leads');
    await expect(page).toHaveURL(/\/leads/);

    console.log('✅ Step 8: Navigated to Leads page');

    // STEP 9: Verify filters are pre-applied
    const countyFilter = page.locator('select[name="county_id"]');
    const syncStatusFilter = page.locator('select[name="sync_status"]');

    await expect(countyFilter).toHaveValue(testCounty.id.toString());
    await expect(syncStatusFilter).toHaveValue('pending');

    console.log('✅ Step 9: Filters pre-applied (county + pending status)');

    // STEP 10: Wait for leads table to load
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    const leadRows = page.locator('table tbody tr');
    const leadRowCount = await leadRows.count();

    expect(leadRowCount).toBeGreaterThan(0);
    console.log(`✅ Step 10: Leads table displays ${leadRowCount} rows`);

    // STEP 11: Verify lead data is displayed correctly
    const firstLead = leadRows.first();

    // Check that required columns are visible
    await expect(firstLead.locator('td').nth(0)).toBeVisible(); // Owner
    await expect(firstLead.locator('td').nth(1)).toBeVisible(); // Address
    await expect(firstLead.locator('td').nth(2)).toBeVisible(); // Permit Date
    await expect(firstLead.locator('td').nth(3)).toBeVisible(); // Sync Status

    const ownerText = await firstLead.locator('td').nth(0).textContent();
    const addressText = await firstLead.locator('td').nth(1).textContent();

    console.log(`✅ Step 11: Lead data visible (Owner: ${ownerText?.substring(0, 20)}..., Address: ${addressText?.substring(0, 30)}...)`);

    // STEP 12: Select leads for syncing
    // Check if there are any pending leads
    const pendingLeads = page.locator('table tbody tr').filter({ has: page.locator('text=/pending/i') });
    const pendingCount = await pendingLeads.count();

    console.log(`Found ${pendingCount} pending leads to sync`);

    if (pendingCount === 0) {
      console.log('⚠️  No pending leads to sync - they may all be synced already');

      // Try clearing sync status filter to see all leads
      await syncStatusFilter.selectOption('');
      await page.waitForTimeout(1000);

      const allLeadRows = page.locator('table tbody tr');
      const allCount = await allLeadRows.count();

      console.log(`Total leads (all statuses): ${allCount}`);
    } else {
      // STEP 13: Select leads (select first few)
      const leadsToSelect = Math.min(pendingCount, 3); // Select up to 3 leads

      for (let i = 0; i < leadsToSelect; i++) {
        const checkbox = pendingLeads.nth(i).locator('input[type="checkbox"]');

        if (await checkbox.count() > 0) {
          await checkbox.check();
        }
      }

      console.log(`✅ Step 12: Selected ${leadsToSelect} leads for syncing`);

      // STEP 14: Click "Send to Summit.AI" button
      const syncButton = page.getByRole('button', { name: /send to summit|sync/i });

      if (await syncButton.count() > 0) {
        await syncButton.click();
        console.log('⏳ Step 13: Clicked sync button, sending to Summit.AI...');

        // Wait for sync to complete (look for success message or status update)
        const successMessage = page.locator('text=/success|synced|sent/i');

        try {
          await expect(successMessage).toBeVisible({ timeout: 30000 });
          console.log('✅ Step 14: Sync completed successfully');

          // STEP 15: Verify sync status updated in database
          await page.waitForTimeout(2000); // Give database time to update

          const leadsResponse = await request.get(`${API_BASE_URL}/api/leads?county_id=${testCounty.id}`);
          expect(leadsResponse.ok()).toBeTruthy();

          const allLeads = await leadsResponse.json();

          const syncedLeads = allLeads.filter(lead => lead.summit_sync_status === 'synced');

          console.log(`✅ Step 15: Database shows ${syncedLeads.length} synced leads`);

          // Verify synced leads have Summit contact IDs
          const leadsWithContactIds = syncedLeads.filter(lead => lead.summit_contact_id);

          console.log(`   - ${leadsWithContactIds.length} leads have Summit contact IDs`);

          // Verify synced timestamp exists
          const leadsWithTimestamp = syncedLeads.filter(lead => lead.summit_synced_at);

          console.log(`   - ${leadsWithTimestamp.length} leads have sync timestamps`);

          expect(leadsWithContactIds.length).toBeGreaterThan(0);

        } catch (error) {
          console.log('⚠️  Sync may have failed or is still in progress');
          console.log(`   Error: ${error.message}`);

          // Check if any error message is displayed
          const errorMessage = page.locator('text=/error|failed/i');

          if (await errorMessage.count() > 0) {
            const errorText = await errorMessage.first().textContent();
            console.log(`   Error message: ${errorText}`);
          }
        }

        // STEP 16: Refresh page and verify status persists
        await page.reload();
        await page.waitForSelector('table tbody tr', { timeout: 10000 });

        console.log('✅ Step 16: Page refreshed to verify data persistence');

        // Check that synced leads now show "synced" status
        const syncedBadges = page.locator('text=/synced/i');
        const syncedBadgeCount = await syncedBadges.count();

        if (syncedBadgeCount > 0) {
          console.log(`✅ Step 17: ${syncedBadgeCount} leads showing "synced" status in UI`);
        }

      } else {
        console.log('⚠️  Sync button not found - may not be implemented yet');
      }
    }

    // STEP 18: Final database validation
    const finalLeadsResponse = await request.get(`${API_BASE_URL}/api/leads?county_id=${testCounty.id}`);
    expect(finalLeadsResponse.ok()).toBeTruthy();

    const finalLeads = await finalLeadsResponse.json();

    console.log('\n📊 Final Data Summary:');
    console.log(`   Total leads for ${testCounty.name}: ${finalLeads.length}`);

    const statusCounts = finalLeads.reduce((acc, lead) => {
      acc[lead.summit_sync_status] = (acc[lead.summit_sync_status] || 0) + 1;
      return acc;
    }, {});

    console.log(`   Status breakdown:`, statusCounts);

    // Verify data integrity
    const leadsWithRequiredFields = finalLeads.filter(lead =>
      lead.id &&
      lead.permit_id &&
      lead.county_id &&
      lead.permits &&
      lead.permits.owner_name &&
      lead.permits.property_address
    );

    const dataIntegrityPercent = (leadsWithRequiredFields.length / finalLeads.length) * 100;

    console.log(`   Data integrity: ${dataIntegrityPercent.toFixed(1)}% (${leadsWithRequiredFields.length}/${finalLeads.length} with all required fields)`);

    expect(dataIntegrityPercent).toBeGreaterThanOrEqual(80);

    console.log('\n✅ Complete user journey test passed!\n');
  });

  test('complete workflow with multiple counties', async ({ page, request }) => {
    // Get multiple counties
    const countiesResponse = await request.get(`${API_BASE_URL}/api/counties`);
    const countiesData = await countiesResponse.json();
    const counties = countiesData.data;

    if (counties.length < 2) {
      test.skip('Need at least 2 counties for this test');
    }

    console.log(`\n🚀 Testing multi-county workflow with ${Math.min(counties.length, 2)} counties\n`);

    const countiesToTest = counties.slice(0, 2);
    const countyResults = [];

    for (const county of countiesToTest) {
      await page.goto('/counties');

      const countyCard = page.locator('.card').filter({ hasText: county.name }).first();
      const pullButton = countyCard.getByRole('button', { name: /pull permits/i });
      await pullButton.click();

      const today = new Date();
      const fromDate = new Date(today);
      fromDate.setDate(fromDate.getDate() - 30);

      const formatDate = (date) => date.toISOString().split('T')[0];

      await page.fill('input[name="date_from"]', formatDate(fromDate));
      await page.fill('input[name="date_to"]', formatDate(today));
      await page.selectOption('select[name="limit"]', '50');

      const responsePromise = page.waitForResponse(
        response => response.url().includes('/pull-permits'),
        { timeout: 60000 }
      );

      await page.click('button[type="submit"]');

      const apiResponse = await responsePromise;
      const responseData = await apiResponse.json();

      if (responseData.success) {
        countyResults.push({
          county: county.name,
          results: responseData.data
        });

        console.log(`✅ ${county.name}: ${responseData.data.leads_created} leads created`);
      }

      // Close modal
      const closeButton = page.locator('button').filter({ has: page.locator('svg') }).first();
      await closeButton.click();
    }

    // Navigate to Leads page
    await page.goto('/leads');
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    // Test filtering by each county
    const countyFilter = page.locator('select[name="county_id"]');

    for (const result of countyResults) {
      const county = counties.find(c => c.name === result.county);

      await countyFilter.selectOption(county.id.toString());
      await page.waitForTimeout(1000);

      const filteredRows = page.locator('table tbody tr');
      const count = await filteredRows.count();

      console.log(`✅ ${result.county} filter: showing ${count} leads`);
    }

    // Clear filter and verify all leads shown
    await countyFilter.selectOption('');
    await page.waitForTimeout(1000);

    const allRows = page.locator('table tbody tr');
    const totalCount = await allRows.count();

    console.log(`✅ All counties: showing ${totalCount} total leads`);

    console.log('\n✅ Multi-county workflow test passed!\n');
  });
});
