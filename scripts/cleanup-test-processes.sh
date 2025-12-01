#!/bin/bash
# cleanup-test-processes.sh
# Kills orphaned Playwright and test processes to prevent zombie accumulation

set -e

echo "🧹 Checking for orphaned test processes..."

# Find orphaned Playwright processes
PLAYWRIGHT_PIDS=$(ps aux | grep -E "playwright.*test.*\.js" | grep -v grep | awk '{print $2}' || true)

# Find orphaned test script processes
TEST_PIDS=$(ps aux | grep -E "node /tmp/test-.*\.js" | grep -v grep | awk '{print $2}' || true)

# Combine and deduplicate PIDs
ALL_PIDS=$(echo "$PLAYWRIGHT_PIDS $TEST_PIDS" | tr ' ' '\n' | sort -u | grep -v '^$' || true)

if [ -z "$ALL_PIDS" ]; then
    echo "✅ No orphaned test processes found"
    exit 0
fi

echo "⚠️  Found orphaned processes: $ALL_PIDS"
echo "🔪 Killing processes..."

for PID in $ALL_PIDS; do
    if ps -p $PID > /dev/null 2>&1; then
        echo "   Killing PID $PID"
        kill -9 $PID 2>/dev/null || true
    fi
done

echo "✅ Cleanup complete"
