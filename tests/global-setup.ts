/**
 * Playwright Global Setup
 *
 * Runs once before all tests.
 * Initializes graceful shutdown handling to prevent zombie processes.
 */

import './utils/graceful-shutdown.js';

async function globalSetup() {
  console.log('🚀 Global test setup complete');
}

export default globalSetup;
