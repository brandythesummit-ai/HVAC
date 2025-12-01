# Zombie Process Prevention Strategy

This document describes the multi-layered defense strategy implemented to prevent orphaned test processes from accumulating on the system.

## The Problem

Playwright tests and Node.js test scripts can become "zombie processes" when:
- Tests hang or timeout without proper cleanup
- Processes receive kill signals but don't exit gracefully
- Unhandled exceptions occur during test execution
- Parent processes terminate without killing child processes

**Impact:**
- Consumes system resources (memory, CPU)
- Can interfere with new test runs
- Difficult to debug when processes accumulate
- Requires manual `kill` commands to clean up

## The Solution: Four-Layer Defense

### Layer 1: Pre-Test Cleanup (Proactive)

**File:** `scripts/cleanup-test-processes.sh`

Automatically kills orphaned processes before each test run.

```bash
npm run cleanup          # Manual cleanup
npm test                 # Automatic cleanup via pretest hook
```

**How it works:**
- Scans for orphaned Playwright and test script processes
- Kills them with SIGKILL (-9) to ensure termination
- Runs automatically before every `npm test` command

**Files modified:**
- `scripts/cleanup-test-processes.sh` - Cleanup script
- `package.json` - Added `cleanup` and `pretest` scripts

### Layer 2: Strict Timeout Enforcement (Prevention)

**File:** `playwright.config.ts`

Enforces hard limits on test execution time.

```typescript
timeout: 15000,           // 15s per test (CLAUDE.md requirement)
globalTimeout: 600000,    // 10 minute absolute maximum
actionTimeout: 15000,     // 15s for clicks/navigation
navigationTimeout: 15000, // 15s for page loads
```

**How it works:**
- Tests that exceed 15 seconds are forcibly terminated
- Entire test suite has 10 minute maximum runtime
- Prevents infinite loops and hanging tests

**Benefits:**
- Tests fail fast instead of hanging indefinitely
- Consistent test execution time
- Prevents resource exhaustion

### Layer 3: Graceful Shutdown Handler (Cleanup)

**File:** `tests/utils/graceful-shutdown.js`

Catches exit signals and ensures clean process termination.

**Handles:**
- `SIGTERM` - Standard termination signal
- `SIGINT` - Ctrl+C / keyboard interrupt
- `uncaughtException` - Unexpected errors
- `unhandledRejection` - Async errors
- Normal `exit` - Standard process exit

**How it works:**
1. Signal received → cleanup() called
2. 5-second timeout starts (force exit if cleanup hangs)
3. Cleanup logic executes (close browsers, cleanup temp files, etc.)
4. Process exits cleanly with proper exit code

**Files:**
- `tests/utils/graceful-shutdown.js` - Shutdown handler
- `tests/global-setup.ts` - Imports handler for all tests
- `playwright.config.ts` - Configures global setup

### Layer 4: Global Setup Integration (Automatic)

**File:** `tests/global-setup.ts`

Automatically initializes graceful shutdown for all Playwright tests.

```typescript
import './utils/graceful-shutdown.js';
```

**How it works:**
- Runs once before all tests start
- Registers shutdown handlers globally
- No per-test configuration needed
- Works for all test files automatically

## Usage Guide

### Running Tests (Automatic Protection)

```bash
npm test                 # Full test suite with cleanup
npm run test:ui          # Interactive mode with cleanup
npm run test:headed      # Headed mode with cleanup
```

**What happens:**
1. Pre-test cleanup kills any orphaned processes
2. Global setup initializes shutdown handlers
3. Tests run with strict 15-second timeouts
4. Any failures trigger graceful cleanup
5. Process exits cleanly (no zombies)

### Manual Cleanup

```bash
npm run cleanup          # Kill orphaned processes now
```

**When to use:**
- After forcibly killing tests with Ctrl+C
- When system feels sluggish (check for zombies)
- Before important test runs
- After unexpected crashes

### Verifying No Zombies

```bash
# Check for orphaned test processes
ps aux | grep -E "(playwright|test-.*\.js)" | grep -v grep

# Should return empty (no results)
```

### Custom Test Scripts

For standalone test scripts outside Playwright:

```javascript
// Import at the top of your test script
require('./tests/utils/graceful-shutdown.js');

// Your test code here
// Automatic cleanup on exit/error
```

## Architecture Decisions

### Why bash script for cleanup?

- Fast execution (<100ms)
- Works across all npm scripts
- No additional dependencies
- Easy to audit and modify

### Why 15-second timeout?

- Per CLAUDE.md project requirements
- Long enough for realistic test scenarios
- Short enough to fail fast on hangs
- Prevents resource exhaustion

### Why global setup vs per-test import?

- **Global:** Automatic protection, no boilerplate
- **Per-test:** Would require imports in every test file
- **Decision:** Global setup for zero-friction adoption

### Why SIGKILL (-9) in cleanup script?

- Orphaned processes are already unresponsive
- Need guaranteed termination
- SIGTERM would be polite but ineffective
- Cleanup script is last resort, not first line of defense

## Testing the Strategy

### Verify Pre-Test Cleanup

```bash
# Create a fake zombie process
node -e "setTimeout(() => {}, 999999)" &
ZOMBIE_PID=$!

# Run cleanup
npm run cleanup

# Verify process is killed
ps -p $ZOMBIE_PID   # Should return "no such process"
```

### Verify Timeout Enforcement

```bash
# Run a test that intentionally hangs
# Should timeout after 15 seconds
npm test
```

### Verify Graceful Shutdown

```bash
# Start a test and press Ctrl+C
npm test
# Should see: "🛑 Received SIGINT - cleaning up..."
# Should see: "✅ Cleanup complete"
```

## Monitoring & Maintenance

### Check for Zombie Accumulation

```bash
# Weekly check (add to crontab if desired)
ps aux | grep -E "(playwright|test-.*\.js)" | grep -v grep | wc -l
```

**Expected:** 0 orphaned processes

**If >0:** Run `npm run cleanup` and investigate root cause

### Log Analysis

Look for these patterns in test output:

```
✅ No orphaned test processes found        # Healthy
⚠️  Found orphaned processes: 1234 5678    # Cleanup triggered
🛑 Received SIGTERM - cleaning up...       # Graceful shutdown working
⚠️  Cleanup timeout exceeded              # Issue: cleanup hung (investigate)
```

## Troubleshooting

### Issue: Tests still hanging after 15 seconds

**Diagnosis:** Playwright may not be respecting timeout config

**Fix:**
1. Check `playwright.config.ts` - verify timeout: 15000
2. Check individual test files for `test.setTimeout()` overrides
3. Run: `npx playwright test --timeout=15000` to force timeout

### Issue: Cleanup script doesn't kill processes

**Diagnosis:** Process pattern matching failing

**Fix:**
1. Check `ps aux` manually to see actual process names
2. Update `scripts/cleanup-test-processes.sh` grep patterns
3. Test with: `bash -x scripts/cleanup-test-processes.sh` (debug mode)

### Issue: Graceful shutdown not triggering

**Diagnosis:** Global setup not loading

**Fix:**
1. Verify `playwright.config.ts` has `globalSetup` configured
2. Check for errors during test startup
3. Add console.log to `tests/global-setup.ts` to verify execution

## Future Enhancements

### Potential Improvements:

1. **Process Monitoring Dashboard**
   - Real-time display of running test processes
   - Automatic alerts when zombies detected
   - Integration with CI/CD pipelines

2. **Adaptive Timeout Management**
   - Different timeouts for different test types
   - Dynamic adjustment based on test complexity
   - Timeout history tracking

3. **Zombie Prevention Metrics**
   - Track zombie occurrences over time
   - Identify problematic tests
   - Performance impact analysis

4. **CI/CD Integration**
   - Pre-deployment zombie check
   - Automatic cleanup in CI pipelines
   - Zombie detection in pull request checks

## Related Documentation

- [CLAUDE.md](/CLAUDE.md) - Project memory (includes testing requirements)
- [playwright.config.ts](/playwright.config.ts) - Playwright configuration
- [package.json](/package.json) - npm scripts and hooks

## Changelog

**2025-12-01:** Initial implementation
- Created cleanup script
- Added pre-test hooks
- Implemented graceful shutdown handler
- Updated Playwright config with strict timeouts
- Configured global setup for automatic protection

---

**Last Updated:** 2025-12-01
**Maintainer:** Brandy (with Claude Code assistance)
