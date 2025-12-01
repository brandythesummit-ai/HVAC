/**
 * Graceful Shutdown Handler
 *
 * Ensures test processes clean up properly and don't become zombies.
 * Import this module in test scripts to enable automatic cleanup on exit signals.
 *
 * Usage:
 *   import './utils/graceful-shutdown.js';
 *   // Or in CommonJS:
 *   require('./utils/graceful-shutdown.js');
 */

const SHUTDOWN_TIMEOUT = 5000; // 5 seconds to clean up before force exit
let isShuttingDown = false;

/**
 * Cleanup handler that runs on process exit
 */
async function cleanup(signal) {
  if (isShuttingDown) {
    console.log('⚠️  Force exit - cleanup already in progress');
    process.exit(1);
  }

  isShuttingDown = true;
  console.log(`\n🛑 Received ${signal} - cleaning up...`);

  // Set a timeout to force exit if cleanup hangs
  const forceExitTimer = setTimeout(() => {
    console.error('⚠️  Cleanup timeout exceeded - forcing exit');
    process.exit(1);
  }, SHUTDOWN_TIMEOUT);

  try {
    // Cleanup logic here
    // For Playwright tests, the framework handles browser cleanup
    // For custom test scripts, add cleanup logic here

    console.log('✅ Cleanup complete');
    clearTimeout(forceExitTimer);
    process.exit(0);
  } catch (error) {
    console.error('❌ Cleanup error:', error);
    clearTimeout(forceExitTimer);
    process.exit(1);
  }
}

/**
 * Handle uncaught exceptions to prevent zombie processes
 */
process.on('uncaughtException', (error) => {
  console.error('❌ Uncaught Exception:', error);
  cleanup('uncaughtException').finally(() => process.exit(1));
});

/**
 * Handle unhandled promise rejections
 */
process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
  cleanup('unhandledRejection').finally(() => process.exit(1));
});

/**
 * Handle SIGTERM (kill signal)
 */
process.on('SIGTERM', () => {
  cleanup('SIGTERM');
});

/**
 * Handle SIGINT (Ctrl+C)
 */
process.on('SIGINT', () => {
  cleanup('SIGINT');
});

/**
 * Handle normal process exit
 */
process.on('exit', (code) => {
  if (!isShuttingDown) {
    console.log(`\n✅ Process exiting with code ${code}`);
  }
});

console.log('🛡️  Graceful shutdown handler initialized');

module.exports = { cleanup };
