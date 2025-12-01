"""
Scheduler service for automated incremental permit pulls.
Runs as a background thread, checking every hour for counties due for refresh.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging
from app.database import get_db

logger = logging.getLogger(__name__)


class PullScheduler:
    """Manages automated incremental pulls for all counties."""

    def __init__(self):
        self.running = False
        self.check_interval = 3600  # Check every hour (in seconds)

    def start(self):
        """Start the scheduler in background thread."""
        self.running = True
        logger.info("Pull scheduler started (checking every hour)")
        asyncio.create_task(self._run_loop())

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Pull scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop - checks every hour for due pulls."""
        while self.running:
            try:
                await self._check_and_schedule_pulls()
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)

            # Wait 1 hour before next check
            await asyncio.sleep(self.check_interval)

    async def _check_and_schedule_pulls(self):
        """Check for counties due for incremental pull and create jobs."""
        db = get_db()
        now = datetime.utcnow()

        # Find counties due for pull (next_pull_at <= now)
        due_counties = db.table("county_pull_schedules")\
            .select("*, counties!inner(id, name, agency_id)")\
            .lte("next_pull_at", now.isoformat())\
            .eq("auto_pull_enabled", True)\
            .eq("incremental_pull_enabled", True)\
            .execute()

        if not due_counties.data:
            logger.info("No counties due for incremental pull")
            return

        logger.info(f"Found {len(due_counties.data)} counties due for pull")

        for schedule in due_counties.data:
            county_id = schedule["county_id"]
            county_name = schedule["counties"]["name"]

            try:
                # Check if initial pull is complete
                county = db.table("counties")\
                    .select("initial_pull_completed")\
                    .eq("id", county_id)\
                    .single()\
                    .execute()

                if not county.data["initial_pull_completed"]:
                    logger.info(f"Skipping {county_name} - initial pull not complete")
                    # Reschedule for tomorrow
                    self._reschedule_county(db, county_id, schedule, days=1)
                    continue

                # Check for already-running job
                active_jobs = db.table("background_jobs")\
                    .select("id")\
                    .eq("county_id", county_id)\
                    .in_("status", ["pending", "running"])\
                    .execute()

                if active_jobs.data:
                    logger.info(f"Skipping {county_name} - job already running")
                    continue

                # Calculate date range (last 8 days to ensure no gaps)
                date_to = now.date()
                date_from = date_to - timedelta(days=8)

                # Check if this range was already pulled
                if self._range_already_pulled(db, county_id, date_from, date_to):
                    logger.info(f"Skipping {county_name} - range already pulled")
                    self._reschedule_county(db, county_id, schedule, days=7)
                    continue

                # Create incremental pull job
                job_data = {
                    "county_id": county_id,
                    "job_type": "incremental_pull",
                    "status": "pending",
                    "parameters": {
                        "date_from": date_from.isoformat(),
                        "date_to": date_to.isoformat(),
                        "limit": 10000  # Pull all in range
                    },
                    "created_at": now.isoformat()
                }

                job_result = db.table("background_jobs").insert(job_data).execute()
                job_id = job_result.data[0]["id"]

                # Update schedule status
                db.table("county_pull_schedules").update({
                    "last_pull_at": now.isoformat(),
                    "last_pull_status": "pending"
                }).eq("county_id", county_id).execute()

                logger.info(f"Created incremental pull job {job_id} for {county_name} ({date_from} to {date_to})")

                # Schedule next pull (7 days from now)
                self._reschedule_county(db, county_id, schedule, days=7)

            except Exception as e:
                logger.error(f"Failed to schedule pull for county {county_id}: {e}", exc_info=True)

    def _range_already_pulled(self, db, county_id: str, date_from, date_to) -> bool:
        """Check if date range has already been pulled."""
        # Query pull_history for overlapping ranges
        overlaps = db.table("pull_history")\
            .select("id")\
            .eq("county_id", county_id)\
            .lte("date_from", date_to.isoformat())\
            .gte("date_to", date_from.isoformat())\
            .execute()

        return len(overlaps.data) > 0

    def _reschedule_county(self, db, county_id: str, current_schedule: dict, days: int):
        """Reschedule county pull for N days in the future."""
        next_pull = datetime.fromisoformat(current_schedule["next_pull_at"].replace('Z', '+00:00'))
        next_pull += timedelta(days=days)

        db.table("county_pull_schedules").update({
            "next_pull_at": next_pull.isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("county_id", county_id).execute()


# Global scheduler instance
_scheduler = None

def get_scheduler() -> PullScheduler:
    """Get or create global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PullScheduler()
    return _scheduler
