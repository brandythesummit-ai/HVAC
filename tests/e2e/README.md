# End-to-End Testing Guide

This directory contains comprehensive E2E tests for the HVAC permit management system using Playwright.

## Test Files

### 01-pull-permits.spec.js
**Purpose**: Validates the complete pull permits workflow

**What it tests**:
- Form submission and API request validation
- Results display and statistics accuracy
- Data persistence in database
- Permit and lead creation
- Navigation to Leads page with filters

**Key validations**:
- API requests include correct parameters
- Stats cards show accurate numbers
- Permits table displays correct data
- Database contains created leads with all required fields

### 02-leads-data-validation.spec.js
**Purpose**: Ensures leads appear correctly and data integrity is maintained

**What it tests**:
- Leads appear on Leads page after pulling permits
- Lead data matches source permit data
- All leads have required fields
- Sync status indicators display correctly
- Timestamps are accurate and recent
- API-level filtering for Mechanical permits

**Key validations**:
- At least 80% of leads have all required fields
- Lead data in UI matches database data
- Permit types are correctly filtered (Mechanical only)

### 03-leads-filtering.spec.js
**Purpose**: Validates all filtering and querying functionality

**What it tests**:
- County filter shows only selected county
- Sync status filter works correctly
- Multiple filters combine properly
- Filter clearing/reset functionality
- Filter persistence across navigation
- Empty result set handling

**Key validations**:
- Filtered results match API responses
- UI counts match database counts
- All displayed leads match filter criteria

### 04-error-scenarios.spec.js
**Purpose**: Tests error handling and edge cases

**What it tests**:
- API timeout scenarios
- Empty results (no permits found)
- Server errors (500 responses)
- Invalid form input validation
- Network disconnection handling
- Malformed API responses
- Modal close without errors

**Key validations**:
- Error messages display appropriately
- Application doesn't crash on errors
- Empty states handled gracefully

### 05-complete-user-journey.spec.js
**Purpose**: Tests the entire workflow from start to finish

**What it tests**:
- Pull permits → Verify results → Navigate to Leads
- Filter leads → Select leads → Sync to Summit.AI
- Verify sync status updates in UI and database
- Multi-county workflow
- Data integrity throughout the process

**Key validations**:
- Complete workflow executes without errors
- Data persists correctly through all steps
- Sync status updates in real-time
- Database integrity maintained at 80%+ level

## Prerequisites

### 1. Start Backend Server
```bash
cd backend
# Activate your Python virtual environment
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Start FastAPI server
uvicorn app.main:app --reload
```

The backend should be running at `http://localhost:8000`

### 2. Start Frontend Server
```bash
cd frontend
npm run dev
```

The frontend should be running at `http://localhost:5173`

### 3. Configure Test Database
Ensure you have:
- At least one county configured with valid Accela credentials
- Database properly initialized
- Accela API credentials are valid and not expired

## Running the Tests

### Run all tests
```bash
npm test
```

### Run tests in UI mode (interactive)
```bash
npm run test:ui
```

### Run tests in headed mode (see browser)
```bash
npm run test:headed
```

### Run specific test file
```bash
npm run test:pull-permits
npm run test:leads-validation
npm run test:filtering
npm run test:errors
npm run test:journey
```

### Run tests in debug mode
```bash
npm run test:debug
```

### View test report
```bash
npm run test:report
```

## Test Configuration

Tests are configured to:
- Run sequentially (not in parallel) to avoid database conflicts
- Use a single worker to prevent race conditions
- Take screenshots on failure
- Record video on failure
- Target the frontend at `http://localhost:5173`
- Call the API at `http://localhost:8000`

Configuration can be modified in `/playwright.config.ts`

## Important Notes

### Real API Testing
These tests use **real Accela API** and **real Summit.AI** integration:
- Tests will pull actual permits from Accela
- Tests will create real leads in your database
- Sync tests will send data to Summit.AI (if sync is implemented)

### Data Cleanup
Consider implementing cleanup after tests:
```javascript
// Example cleanup in test.afterAll
test.afterAll(async ({ request }) => {
  // Delete test leads created during this run
  // This requires implementing a cleanup endpoint
});
```

### Test Data
Tests expect:
- At least one county with valid Accela credentials
- Accela API returning permits within the date ranges used
- Database allowing lead creation

### Timeouts
Some tests have extended timeouts (60s) for:
- Real Accela API calls which can be slow
- Large permit pulls that require enrichment
- Network operations

## Troubleshooting

### Tests failing with "No leads created"
- Check that your Accela credentials are valid
- Verify the date range has permits available
- Check that the permit type filter is working ("Mechanical")

### Connection errors
- Ensure both frontend and backend servers are running
- Check that ports 5173 (frontend) and 8000 (backend) are available
- Verify your database is accessible

### Timeout errors
- Increase timeout in `playwright.config.ts`
- Check Accela API performance
- Verify network connectivity

### Database conflicts
- Tests run sequentially to avoid this
- If issues persist, ensure workers=1 in config
- Clear test data between runs

## CI/CD Integration

Tests are configured for GitHub Actions (see `.github/workflows/playwright.yml`).

To run in CI:
- Set environment variables for database connection
- Ensure Accela credentials are available as secrets
- Run backend and frontend as background processes
- Execute tests with `npx playwright test`

## Success Criteria

Tests pass when:
- ✅ All leads appear on Leads page after pulling permits
- ✅ Lead data matches source permit data (100% accuracy)
- ✅ All filters work correctly and change displayed results
- ✅ Error scenarios handled gracefully
- ✅ Complete user journey passes end-to-end
- ✅ Data integrity maintained at 80%+ level
- ✅ API-level filtering reduces unnecessary API calls

## Next Steps

After tests pass:
1. Review test coverage and add additional edge cases
2. Implement cleanup scripts for test data
3. Add performance benchmarks
4. Monitor Accela API usage to verify optimization
5. Set up continuous testing in CI/CD pipeline
