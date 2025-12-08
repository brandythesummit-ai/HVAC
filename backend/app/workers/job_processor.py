"""
Background Job Processor

Polls the background_jobs table for pending jobs and processes them.
Supports:
- initial_pull: Pull 30 years of historical HVAC permits
- incremental_pull: Pull recent permits (e.g., last 24 hours)
- property_aggregation: Rebuild property records from existing permits

No external dependencies (no Celery/Redis/ARQ) - just PostgreSQL polling.
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Optional, Any
import traceback

from supabase import Client
from app.database import get_db
from app.services.accela_client import AccelaClient, TokenExpiredError
from app.services.property_aggregator import PropertyAggregator
from app.services.encryption import encryption_service
from app.services.agency_discovery import AgencyDiscoveryService
from app.config import settings

logger = logging.getLogger(__name__)


class JobProcessor:
    """
    Background job processor that polls for and executes jobs.

    Poll Interval: 5 seconds
    Job Types:
    - initial_pull: 30-year historical pull (pull oldest first for best leads)
    - incremental_pull: Daily new permits
    - property_aggregation: Rebuild property records
    """

    POLL_INTERVAL = 5  # seconds
    PERMIT_TYPE_HVAC = "Building/Residential/Trade/Mechanical"

    def __init__(self, db: Client):
        """
        Initialize job processor.

        Args:
            db: Supabase client
        """
        self.db = db
        self.is_running = False
        self.current_job_id = None

    async def start(self):
        """Start the job processor polling loop."""
        self.is_running = True

        # Force stdout for Railway visibility
        print("🚀 JOB PROCESSOR STARTED", flush=True)
        logger.info("🚀 Job processor started - polling every %d seconds", self.POLL_INTERVAL)

        # Recover any stale jobs from previous crash/restart
        await self._recover_stale_jobs()

        while self.is_running:
            try:
                await self._poll_and_process()
            except Exception as e:
                logger.error(f"❌ Error in job processor: {str(e)}")
                logger.error(traceback.format_exc())

            # Wait before next poll
            await asyncio.sleep(self.POLL_INTERVAL)

        logger.info("⏹️  Job processor stopped")

    async def stop(self):
        """Stop the job processor."""
        self.is_running = False

    async def _recover_stale_jobs(self):
        """
        Reset jobs stuck in 'running' state from server crash/restart.

        Jobs that have been 'running' for > 10 minutes without progress
        are assumed to be orphaned and reset to 'pending' for retry.
        """
        stale_threshold = datetime.utcnow() - timedelta(minutes=10)

        try:
            # Find and reset stale jobs
            result = self.db.table('background_jobs') \
                .select('id, county_id, job_type, updated_at') \
                .eq('status', 'running') \
                .lt('updated_at', stale_threshold.isoformat()) \
                .execute()

            if not result.data:
                print("♻️ No stale jobs to recover", flush=True)
                return

            for job in result.data:
                job_id = job['id']
                self.db.table('background_jobs').update({
                    'status': 'pending',
                    'error_message': 'Recovered: Job was interrupted by server restart',
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', job_id).execute()

                print(f"♻️ Recovered stale job {job_id} ({job['job_type']})", flush=True)
                logger.warning(f"♻️ Recovered stale job {job_id}")

            logger.warning(f"♻️ Recovered {len(result.data)} stale jobs")

        except Exception as e:
            logger.error(f"❌ Error recovering stale jobs: {str(e)}")
            print(f"❌ Error recovering stale jobs: {str(e)}", flush=True)

    async def _poll_and_process(self):
        """Poll for pending jobs and process the oldest one."""
        # Get oldest pending job
        result = self.db.table('background_jobs') \
            .select('*') \
            .eq('status', 'pending') \
            .order('created_at', desc=False) \
            .limit(1) \
            .execute()

        if not result.data:
            # No pending jobs
            return

        job = result.data[0]
        job_id = job['id']

        print(f"📋 PICKED UP JOB {job_id} ({job['job_type']})", flush=True)
        logger.info(f"📋 Picked up job {job_id} ({job['job_type']})")

        # Mark job as running
        self.current_job_id = job_id
        await self._update_job_status(job_id, 'running', started_at=datetime.utcnow())

        try:
            # Process job based on type
            if job['job_type'] == 'initial_pull':
                await self._process_initial_pull(job)
            elif job['job_type'] == 'incremental_pull':
                await self._process_incremental_pull(job)
            elif job['job_type'] == 'property_aggregation':
                await self._process_property_aggregation(job)
            else:
                raise ValueError(f"Unknown job type: {job['job_type']}")

            # Mark as completed
            await self._update_job_status(
                job_id,
                'completed',
                completed_at=datetime.utcnow(),
                progress_percent=100
            )

            print(f"✅ JOB {job_id} COMPLETED SUCCESSFULLY", flush=True)
            logger.info(f"✅ Job {job_id} completed successfully")

        except TokenExpiredError as e:
            # LAYER 6: Token expiration - fail immediately (no retries)
            # Re-authentication is required, retrying won't help
            error_message = str(e)
            error_details = {
                'error': error_message,
                'traceback': traceback.format_exc(),
                'requires_reauth': True
            }

            await self._update_job(
                job_id,
                {
                    'status': 'failed',
                    'error_message': f"🔐 RE-AUTHENTICATION REQUIRED: {error_message}",
                    'error_details': error_details,
                    'completed_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
            )
            print(f"🔐 JOB {job_id} FAILED - TOKEN EXPIRED (no retry): {error_message}", flush=True)
            logger.error(f"🔐 Job {job_id} failed due to token expiration - requires re-authentication")

        except Exception as e:
            # Mark as failed and check for retry
            error_message = str(e)
            error_details = {
                'error': error_message,
                'traceback': traceback.format_exc()
            }

            retry_count = job.get('retry_count', 0)
            max_retries = job.get('max_retries', 3)

            if retry_count < max_retries:
                # Retry - set back to pending
                # IMPORTANT: Keep years_status to allow resuming from where we left off
                # Only reset permits_pulled/saved as they'll be recalculated
                await self._update_job(
                    job_id,
                    {
                        'status': 'pending',
                        'retry_count': retry_count + 1,
                        # DO NOT reset years_status or per_year_permits - these enable resume!
                        'current_year': None,      # Reset current year
                        'error_message': error_message,
                        'error_details': error_details,
                        'updated_at': datetime.utcnow().isoformat()
                    }
                )
                print(f"⚠️ JOB {job_id} FAILED, RETRY {retry_count + 1}/{max_retries}: {error_message}", flush=True)
                logger.warning(f"⚠️  Job {job_id} failed, retry {retry_count + 1}/{max_retries}")
            else:
                # Max retries exceeded - mark as failed
                await self._update_job(
                    job_id,
                    {
                        'status': 'failed',
                        'error_message': error_message,
                        'error_details': error_details,
                        'completed_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                )
                print(f"❌ JOB {job_id} FAILED PERMANENTLY after {max_retries} retries: {error_message}", flush=True)
                logger.error(f"❌ Job {job_id} failed permanently after {max_retries} retries")

        finally:
            self.current_job_id = None

    async def _process_initial_pull(self, job: Dict):
        """
        Process 30-year historical permit pull.

        Strategy:
        - Pull oldest permits first (best leads appear first)
        - Process year by year: 1995 → 2025
        - Each year in batches of 1000 permits
        - Update progress in real-time
        """
        job_id = job['id']
        county_id = job['county_id']
        params = job.get('parameters', {})

        # Get parameters
        years = params.get('years', 30)

        # Get county info
        county_result = self.db.table('counties').select('*').eq('id', county_id).execute()
        if not county_result.data:
            raise ValueError(f"County {county_id} not found")

        county = county_result.data[0]

        # Use county's permit_type if configured, otherwise job params, otherwise None (no filter)
        # If permit_type is None, Accela API returns ALL Building permits (no type filtering)
        permit_type = (
            params.get('permit_type') or
            county.get('permit_type')  # May be None for counties without configured type
        )

        if permit_type:
            print(f"📋 Using permit type filter: {permit_type}", flush=True)
        else:
            print(f"📋 No permit type filter - fetching all Building permits", flush=True)

        # Get Accela app credentials from database (needed for both discovery and API calls)
        app_settings = self.db.table("app_settings").select("*").eq("key", "accela").execute()
        if not app_settings.data or not app_settings.data[0].get("app_id"):
            raise ValueError("Accela app credentials not configured. Please configure in Settings.")

        app_id = app_settings.data[0]["app_id"]
        app_secret_encrypted = app_settings.data[0]["app_secret"]
        app_secret = encryption_service.decrypt(app_secret_encrypted)

        # ============================================================
        # SELF-HEALING: Auto-discover county_code if missing
        # ============================================================
        if not county.get('county_code'):
            print(f"⚠️ County code missing for {county['name']}, attempting auto-discovery...", flush=True)
            logger.warning(f"County code missing for {county['name']}, attempting auto-discovery")

            discovery = AgencyDiscoveryService()
            match = await discovery.discover_county_code(
                county_name=county['name'],
                state=county.get('state', 'FL'),
                app_id=app_id  # Required for Agencies API
            )

            if match:
                await self._update_county_code(
                    county_id=county['id'],
                    county_code=match['county_code'],
                    confidence=match['confidence'],
                    match_score=match['match_score']
                )
                county['county_code'] = match['county_code']
                print(f"✅ Auto-discovered county code: {match['county_code']}", flush=True)
            else:
                raise ValueError(
                    f"Could not auto-discover Accela agency code for '{county['name']}'. "
                    f"This county may not use Accela or uses a different platform."
                )

        # Initialize Accela client
        accela_client = AccelaClient(
            app_id=app_id,
            app_secret=app_secret,
            county_code=county['county_code'],
            refresh_token=county['refresh_token'],
            access_token=county.get('access_token', ''),
            token_expires_at=county.get('token_expires_at', '')
        )

        # CRITICAL: Validate token before processing to fail fast
        print(f"🔐 Validating OAuth token for {county['name']}...", flush=True)
        token_result = await accela_client.ensure_valid_token()

        if not token_result['success']:
            print(f"❌ Token validation failed: {token_result['error']}", flush=True)
            logger.error(f"❌ Token validation failed for {county['name']}: {token_result['error']}")

            if token_result.get('needs_reauth'):
                # Mark county as needing re-authorization
                self.db.table('counties').update({
                    'status': 'disconnected',
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', county_id).execute()
                print(f"⚠️ County {county['name']} marked as disconnected - needs re-authorization", flush=True)
                # LAYER 6: Raise TokenExpiredError for immediate failure (no retries)
                raise TokenExpiredError(f"OAuth token expired for {county['name']}: {token_result['error']}")

            # Non-auth error - allow retries
            raise ValueError(f"OAuth token error for {county['name']}: {token_result['error']}")

        print(f"✅ Token validated for {county['name']}", flush=True)

        # LAYER 4: Token Age Warning
        # Warn if token is >5 days old (may fail mid-job due to refresh token expiration)
        token_obtained_at = county.get('token_obtained_at')
        if token_obtained_at:
            try:
                from dateutil.parser import parse as parse_datetime
                token_obtained = parse_datetime(token_obtained_at)
                token_age_days = (datetime.utcnow() - token_obtained.replace(tzinfo=None)).days
                if token_age_days >= 5:
                    print(f"⚠️ WARNING: Token is {token_age_days} days old. "
                          f"Consider re-authenticating before starting long jobs.", flush=True)
                    logger.warning(f"Token age warning for {county['name']}: {token_age_days} days old")
                else:
                    print(f"🔒 Token age: {token_age_days} days (fresh)", flush=True)
            except Exception as e:
                logger.warning(f"Could not parse token_obtained_at: {e}")
        else:
            print(f"⚠️ Token age unknown (token_obtained_at not set)", flush=True)

        # DIAGNOSTIC: Print after each step to find hang location
        print(f"🔍 [DEBUG] Step 1: Initializing aggregator...", flush=True)

        # Initialize property aggregator
        aggregator = PropertyAggregator(self.db)
        print(f"🔍 [DEBUG] Step 2: Aggregator initialized", flush=True)

        # Calculate year range (pull oldest first)
        current_year = datetime.now().year
        start_year = current_year - years  # e.g., 2025 - 30 = 1995
        end_year = current_year

        total_years = years
        years_processed = 0

        total_permits_pulled = 0
        total_permits_saved = 0
        total_properties_created = 0
        total_properties_updated = 0
        total_leads_created = 0

        # LAYER 1: RESUMABLE JOBS
        # Check if we have existing progress from a previous run/retry
        existing_years_status = job.get('years_status', {})
        existing_per_year_permits = job.get('per_year_permits', {})
        is_resuming = bool(existing_years_status)

        if is_resuming:
            # Count completed years and their permits for accurate totals
            completed_years = [y for y, status in existing_years_status.items() if status == 'completed']
            print(f"♻️ RESUMING JOB - {len(completed_years)} years already completed", flush=True)
            logger.info(f"♻️ Resuming job with {len(completed_years)} completed years")

            # Restore previous progress for accurate totals
            for year_str in completed_years:
                if year_str in existing_per_year_permits:
                    total_permits_pulled += existing_per_year_permits[year_str]

        # Track permits per year for live UI updates (preserve existing)
        per_year_permits = existing_per_year_permits.copy() if is_resuming else {}

        # Track year-level status for accurate progress display
        # Status values: 'not_started', 'in_progress', 'completed'
        print(f"🔍 [DEBUG] Step 3: Creating years_status dict for {start_year}-{end_year}...", flush=True)
        if is_resuming:
            # Use existing status but ensure all years are present
            years_status = {str(year): 'not_started' for year in range(start_year, end_year + 1)}
            years_status.update(existing_years_status)  # Preserve completed status
        else:
            years_status = {str(year): 'not_started' for year in range(start_year, end_year + 1)}
        print(f"🔍 [DEBUG] Step 4: years_status created with {len(years_status)} years", flush=True)

        start_time = datetime.utcnow()

        print(f"📅 Pulling {years} years: {start_year} → {end_year}", flush=True)
        logger.info(f"📅 Pulling {years} years: {start_year} → {end_year}")

        # Initialize job with years_status so UI can show all years immediately
        print(f"🔍 [DEBUG] Step 5: About to update job with years_status...", flush=True)
        await self._update_job(job_id, {
            'years_status': years_status,
            'start_year': start_year,
            'end_year': end_year,
            'updated_at': datetime.utcnow().isoformat()
        })
        print(f"🔍 [DEBUG] Step 6: Job updated, starting year loop...", flush=True)

        # Process year by year (oldest first)
        for year in range(start_year, end_year + 1):
            year_str = str(year)

            # LAYER 1: Skip completed years when resuming
            if years_status.get(year_str) == 'completed':
                print(f"⏭️ Skipping {year} (already completed)", flush=True)
                logger.info(f"⏭️ Skipping {year} (already completed)")
                years_processed += 1
                continue

            print(f"📆 Processing year {year}...", flush=True)
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"

            logger.info(f"📆 Processing year {year}...")

            # LAYER 2: Validate token at each year boundary
            # This catches token expiration early instead of failing mid-year
            token_result = await accela_client.ensure_valid_token()
            if not token_result['success']:
                print(f"❌ Token validation failed at year {year}: {token_result['error']}", flush=True)
                if token_result.get('needs_reauth'):
                    # Mark county as disconnected
                    self.db.table('counties').update({
                        'status': 'disconnected',
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('id', county_id).execute()
                    raise TokenExpiredError(f"Re-authentication required: {token_result['error']}")
                raise Exception(f"Token validation failed: {token_result['error']}")

            # Mark this year as in_progress
            years_status[str(year)] = 'in_progress'

            # Update job with current year and status
            await self._update_job(job_id, {
                'current_year': year,
                'years_status': years_status,
                'updated_at': datetime.utcnow().isoformat()
            })

            # STREAMING: Process permits in batches to avoid memory issues
            # Instead of loading 10,000+ permits into memory, we process 100 at a time
            # Memory savings: 99% reduction (1MB vs 100MB for 10,000 permits)
            year_permits_pulled = 0
            year_properties_created = 0
            year_properties_updated = 0
            year_leads_created = 0
            year_permits_saved = 0
            batch_count = 0
            permit_count = 0
            last_progress_update = datetime.utcnow()

            print(f"   📡 Streaming permits for {year}...", flush=True)
            logger.info(f"   📡 Streaming permits for {year} (batch_size=100)")

            # Stream permits in batches - never holds more than 100 in memory
            async for batch in accela_client.get_permits_stream(
                date_from=year_start,
                date_to=year_end,
                batch_size=100,
                permit_type=permit_type
            ):
                batch_count += 1
                batch_size = len(batch)
                year_permits_pulled += batch_size
                total_permits_pulled += batch_size

                print(f"   📦 Batch {batch_count}: processing {batch_size} permits (total: {year_permits_pulled})", flush=True)

                # Filter permits with incorrect dates (if any)
                filtered_batch = [
                    p for p in batch
                    if p.get('openedDate', '')[:10] >= year_start
                    and p.get('openedDate', '')[:10] <= year_end
                ]
                if len(filtered_batch) < batch_size:
                    filtered_count = batch_size - len(filtered_batch)
                    print(f"      🔧 Filtered {filtered_count} permits with incorrect dates", flush=True)

                # Process each permit in this batch
                for permit in filtered_batch:
                    permit_count += 1

                    # Yield to event loop every 10 permits
                    if permit_count % 10 == 0:
                        await asyncio.sleep(0)

                    # Update progress every 50 permits or every 30 seconds
                    now = datetime.utcnow()
                    should_update = (permit_count % 50 == 0) or ((now - last_progress_update).total_seconds() >= 30)

                    if should_update:
                        # Check if job was cancelled or deleted
                        if await self._is_job_cancelled_or_deleted(job_id):
                            raise Exception("Job was cancelled or deleted by user")

                        print(f"      ⏳ Saved {year_permits_saved} permits for {year}", flush=True)

                        await self._update_job(job_id, {
                            'permits_pulled': total_permits_pulled,
                            'permits_saved': total_permits_saved + year_permits_saved,
                            'current_year': year,
                            'updated_at': now.isoformat()
                        })
                        last_progress_update = now

                    try:
                        # Get additional permit details (extracted from expanded data, no API calls)
                        permit_details = self._enrich_permit_data(permit)

                        # Save permit to database - returns (permit, is_new_insert)
                        saved_permit, was_inserted = await self._save_permit(county_id, permit_details)
                        if saved_permit and was_inserted:
                            year_permits_saved += 1

                        # Process through property aggregator
                        property_id, lead_id, was_created = await aggregator.process_permit(
                            saved_permit,
                            county_id
                        )

                        if property_id:
                            if was_created:
                                year_properties_created += 1
                                if lead_id:
                                    year_leads_created += 1
                            else:
                                year_properties_updated += 1

                    except Exception as e:
                        logger.warning(f"Failed to process permit: {str(e)}")
                        continue

            # Handle case where no permits were found for the year
            if year_permits_pulled == 0:
                logger.info(f"   ✅ No permits found for {year}")
                per_year_permits[str(year)] = 0
                years_processed += 1
                years_status[str(year)] = 'completed'
                await self._update_job(job_id, {
                    'progress_percent': min(100, int((years_processed / total_years) * 100)),
                    'years_status': years_status,
                    'per_year_permits': per_year_permits,
                    'updated_at': datetime.utcnow().isoformat()
                })
                continue

            print(f"   ✅ Year {year}: {batch_count} batches, {year_permits_pulled} pulled, {year_permits_saved} saved", flush=True)

            # Update totals after processing all permits for the year
            total_permits_saved += year_permits_saved
            total_properties_created += year_properties_created
            total_properties_updated += year_properties_updated
            total_leads_created += year_leads_created

            # Calculate elapsed time and rate
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            permits_per_second = total_permits_pulled / elapsed if elapsed > 0 else 0
            estimated_remaining = ((total_years - years_processed - 1) * 1000) / permits_per_second if permits_per_second > 0 else 0
            estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_remaining)

            # Track per-year permits
            per_year_permits[str(year)] = year_permits_pulled

            # Update job progress after completing year
            await self._update_job(job_id, {
                'permits_pulled': total_permits_pulled,
                'permits_saved': total_permits_saved,
                'properties_created': total_properties_created,
                'properties_updated': total_properties_updated,
                'leads_created': total_leads_created,
                'current_year': year,
                'elapsed_seconds': int(elapsed),
                'permits_per_second': round(permits_per_second, 2),
                'estimated_completion_at': estimated_completion.isoformat(),
                'per_year_permits': per_year_permits,
                'updated_at': datetime.utcnow().isoformat()
            })

            logger.info(f"   ✅ Year {year}: {year_permits_saved} NEW saved (of {year_permits_pulled} pulled), {year_properties_created} properties created, {year_leads_created} leads created")

            years_processed += 1

            # Mark this year as completed
            years_status[str(year)] = 'completed'

            # Update progress after year completion (ensures accurate % between years)
            await self._update_job(job_id, {
                'progress_percent': min(100, int((years_processed / total_years) * 100)),
                'years_status': years_status,
                'updated_at': datetime.utcnow().isoformat()
            })

            logger.info(f"✅ Year {year} complete: {year_permits_pulled} permits pulled")

        # Final update
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        permits_per_second = total_permits_pulled / elapsed if elapsed > 0 else 0

        await self._update_job(job_id, {
            'permits_pulled': total_permits_pulled,
            'permits_saved': total_permits_saved,
            'properties_created': total_properties_created,
            'properties_updated': total_properties_updated,
            'leads_created': total_leads_created,
            'elapsed_seconds': int(elapsed),
            'permits_per_second': round(permits_per_second, 2),
            'progress_percent': 100,
            'per_year_permits': per_year_permits,
            'years_status': years_status,
            'start_year': start_year,
            'end_year': end_year,
            'updated_at': datetime.utcnow().isoformat()
        })

        logger.info(f"🎉 Initial pull complete: {total_permits_pulled} permits, {total_properties_created} properties, {total_leads_created} leads")

    async def _process_incremental_pull(self, job: Dict):
        """
        Process incremental permit pull (e.g., daily new permits).

        Pulls permits from the last 24-48 hours to catch new installations.
        """
        job_id = job['id']
        county_id = job['county_id']
        params = job.get('parameters', {})

        # Get parameters
        permit_type = params.get('permit_type', self.PERMIT_TYPE_HVAC)
        days_back = params.get('days_back', 2)  # Default 2 days to ensure overlap

        # Calculate date range
        date_to = date.today()
        date_from = date_to - timedelta(days=days_back)

        logger.info(f"📅 Incremental pull: {date_from} to {date_to}")

        # Get county info
        county_result = self.db.table('counties').select('*').eq('id', county_id).execute()
        if not county_result.data:
            raise ValueError(f"County {county_id} not found")

        county = county_result.data[0]

        # Get Accela app credentials from database
        app_settings = self.db.table("app_settings").select("*").eq("key", "accela").execute()
        if not app_settings.data or not app_settings.data[0].get("app_id"):
            raise ValueError("Accela app credentials not configured. Please configure in Settings.")

        app_id = app_settings.data[0]["app_id"]
        app_secret_encrypted = app_settings.data[0]["app_secret"]
        app_secret = encryption_service.decrypt(app_secret_encrypted)

        # Initialize clients
        accela_client = AccelaClient(
            app_id=app_id,
            app_secret=app_secret,
            county_code=county['county_code'],
            refresh_token=county['refresh_token'],
            access_token=county.get('access_token', ''),
            token_expires_at=county.get('token_expires_at', '')
        )

        # CRITICAL: Validate token before processing to fail fast
        print(f"🔐 Validating OAuth token for {county['name']}...", flush=True)
        token_result = await accela_client.ensure_valid_token()

        if not token_result['success']:
            print(f"❌ Token validation failed: {token_result['error']}", flush=True)
            logger.error(f"❌ Token validation failed for {county['name']}: {token_result['error']}")

            if token_result.get('needs_reauth'):
                # Mark county as needing re-authorization
                self.db.table('counties').update({
                    'status': 'disconnected',
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', county_id).execute()
                print(f"⚠️ County {county['name']} marked as disconnected - needs re-authorization", flush=True)
                # LAYER 6: Raise TokenExpiredError for immediate failure (no retries)
                raise TokenExpiredError(f"OAuth token expired for {county['name']}: {token_result['error']}")

            # Non-auth error - allow retries
            raise ValueError(f"OAuth token error for {county['name']}: {token_result['error']}")

        print(f"✅ Token validated for {county['name']}", flush=True)

        aggregator = PropertyAggregator(self.db)

        # Pull permits
        permit_data = await accela_client.get_permits(
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
            limit=1000,
            permit_type=permit_type
        )

        permits = permit_data.get('permits', [])
        logger.info(f"📋 Found {len(permits)} permits")

        # Process permits
        total_saved = 0
        total_properties_created = 0
        total_properties_updated = 0
        total_leads_created = 0

        for permit in permits:
            try:
                permit_details = self._enrich_permit_data(permit)  # No API calls needed
                saved_permit, was_inserted = await self._save_permit(county_id, permit_details)

                if saved_permit and was_inserted:
                    total_saved += 1

                if saved_permit:
                    property_id, lead_id, was_created = await aggregator.process_permit(
                        saved_permit,
                        county_id
                    )

                    if property_id:
                        if was_created:
                            total_properties_created += 1
                            if lead_id:
                                total_leads_created += 1
                        else:
                            total_properties_updated += 1

            except Exception as e:
                logger.warning(f"Failed to process permit: {str(e)}")
                continue

        # Update job
        await self._update_job(job_id, {
            'permits_pulled': len(permits),
            'permits_saved': total_saved,
            'properties_created': total_properties_created,
            'properties_updated': total_properties_updated,
            'leads_created': total_leads_created,
            'progress_percent': 100,
            'updated_at': datetime.utcnow().isoformat()
        })

        logger.info(f"✅ Incremental pull complete: {total_saved} permits, {total_properties_created} properties, {total_leads_created} leads")

    async def _process_property_aggregation(self, job: Dict):
        """
        Process property aggregation job.

        Rebuilds property records from existing permits.
        """
        # TODO: Implement property aggregation
        # This would be used for data migration or rebuilding corrupted data
        logger.info("Property aggregation not yet implemented")
        pass

    def _enrich_permit_data(self, permit: Dict) -> Dict:
        """
        Extract enrichment data from permit with expanded data.

        Note: Permit already contains addresses, owners, parcels from the
        'expand' parameter used in get_permits(). No additional API calls needed.

        Args:
            permit: Permit data with expanded addresses/owners/parcels

        Returns:
            Enriched permit dictionary
        """
        record_id = permit.get('id')

        # Extract from expanded data - NO API CALLS NEEDED
        # The 'expand' parameter in get_permits() already fetched this data
        addresses = permit.get('addresses', [])
        owners = permit.get('owners', [])
        parcels = permit.get('parcels', [])

        # Extract primary address
        primary_address = next((addr for addr in addresses if addr.get('isPrimary')), None) if addresses else None

        # Extract primary owner
        primary_owner = next((owner for owner in owners if owner.get('isPrimary')), None) if owners else None

        # Extract primary parcel
        primary_parcel = parcels[0] if parcels else None

        # Build property address from components (API returns separate fields, not fullAddress)
        property_address = None
        if primary_address:
            addr_parts = [
                primary_address.get('addressLine1', ''),
                primary_address.get('city', ''),
            ]
            # Handle state (can be string or dict)
            state = primary_address.get('state', '')
            if isinstance(state, dict):
                state = state.get('value') or state.get('text', '')
            addr_parts.append(state)
            addr_parts.append(primary_address.get('postalCode', ''))
            property_address = ', '.join(filter(None, addr_parts))

        # Extract owner contact info - check multiple possible field names
        owner_phone = None
        owner_email = None
        if primary_owner:
            # Try various phone field names
            owner_phone = (
                primary_owner.get('phone1') or
                primary_owner.get('phone') or
                primary_owner.get('phoneNumber') or
                primary_owner.get('homePhone') or
                primary_owner.get('workPhone')
            )
            # Try various email field names
            owner_email = (
                primary_owner.get('email') or
                primary_owner.get('emailAddress') or
                primary_owner.get('email1')
            )

        # Extract parcel data - check various field name patterns
        year_built = None
        square_footage = None
        property_value = None
        lot_size = None
        if primary_parcel:
            year_built = (
                primary_parcel.get('yearBuilt') or
                primary_parcel.get('actualYearBuilt')
            )
            square_footage = (
                primary_parcel.get('buildingSquareFeet') or
                primary_parcel.get('squareFeet') or
                primary_parcel.get('livingArea')
            )
            property_value = (
                primary_parcel.get('landValue') or
                primary_parcel.get('totalValue') or
                primary_parcel.get('assessedValue') or
                primary_parcel.get('marketValue')
            )
            lot_size = (
                primary_parcel.get('lotAreaSquareFeet') or
                primary_parcel.get('lotSize') or
                primary_parcel.get('acreage')
            )

        return {
            'id': record_id,
            'type': permit.get('type', {}).get('text'),
            'description': permit.get('description'),
            'opened_date': permit.get('openedDate'),
            'status': permit.get('status', {}).get('text'),
            'job_value': permit.get('estimatedCostOfConstruction') or permit.get('jobValue'),
            'property_address': property_address,
            'year_built': year_built,
            'square_footage': square_footage,
            'property_value': property_value,
            'lot_size': lot_size,
            'owner_name': primary_owner.get('fullName') if primary_owner else None,
            'owner_phone': owner_phone,
            'owner_email': owner_email,
            # Store COMPLETE raw data including enrichment (not just base permit)
            'raw_data': {
                'permit': permit,
                'addresses': addresses,
                'owners': owners,
                'parcels': parcels
            }
        }

    async def _save_permit(self, county_id: str, permit_data: Dict) -> tuple[Optional[Dict], bool]:
        """
        Save permit to database.

        Args:
            county_id: County UUID
            permit_data: Enriched permit data

        Returns:
            Tuple of (saved permit record, was_inserted boolean)
            - If permit already existed: (existing_record, False)
            - If new permit inserted: (new_record, True)
            - If error: (None, False)
        """
        try:
            # Check if permit already exists
            existing = self.db.table('permits') \
                .select('*') \
                .eq('county_id', county_id) \
                .eq('accela_record_id', permit_data['id']) \
                .execute()

            if existing.data:
                # Permit already exists - return full record for property aggregator
                # but indicate this was NOT a new insert
                return existing.data[0], False

            # Insert new permit
            insert_data = {
                'county_id': county_id,
                'accela_record_id': permit_data['id'],
                'permit_type': permit_data.get('type'),
                'description': permit_data.get('description'),
                'opened_date': permit_data.get('opened_date'),
                'status': permit_data.get('status'),
                'job_value': permit_data.get('job_value'),
                'property_address': permit_data.get('property_address'),
                'year_built': permit_data.get('year_built'),
                'square_footage': permit_data.get('square_footage'),
                'property_value': permit_data.get('property_value'),
                'lot_size': permit_data.get('lot_size'),
                'owner_name': permit_data.get('owner_name'),
                'owner_phone': permit_data.get('owner_phone'),
                'owner_email': permit_data.get('owner_email'),
                'raw_data': permit_data.get('raw_data')
            }

            # Use upsert to handle re-runs gracefully (avoids duplicate key errors)
            # If permit with this county_id + accela_record_id exists, update it
            result = self.db.table('permits').upsert(
                insert_data,
                on_conflict='county_id,accela_record_id'
            ).execute()

            if result.data:
                return result.data[0], True

            return None, False

        except Exception as e:
            logger.error(f"Error saving permit: {str(e)}")
            raise

    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs
    ):
        """Update job status and optional fields."""
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }

        # Add optional fields
        for key, value in kwargs.items():
            if isinstance(value, datetime):
                update_data[key] = value.isoformat()
            else:
                update_data[key] = value

        self.db.table('background_jobs').update(update_data).eq('id', job_id).execute()

    async def _update_job(self, job_id: str, updates: Dict):
        """Update job with arbitrary fields."""
        self.db.table('background_jobs').update(updates).eq('id', job_id).execute()

    async def _update_county_code(
        self,
        county_id: str,
        county_code: str,
        confidence: str,
        match_score: int
    ) -> None:
        """
        Update county with discovered Accela agency code.

        This is called when auto-discovery finds a county's serviceProviderCode.
        Sets the platform to 'Accela' and records discovery confidence.

        Args:
            county_id: UUID of the county record
            county_code: The discovered serviceProviderCode
            confidence: Match confidence level ('exact', 'code_match', 'fuzzy')
            match_score: Numeric match score (0-100)
        """
        self.db.table('counties').update({
            'county_code': county_code,
            'platform': 'Accela',
            'platform_confidence': f"Auto-discovered ({confidence}, score={match_score})",
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', county_id).execute()

        logger.info(f"✅ Updated county {county_id} with discovered code: {county_code}")
        print(f"   📝 Saved county_code='{county_code}' to database", flush=True)

    async def _is_job_cancelled_or_deleted(self, job_id: str) -> bool:
        """
        Check if the job has been cancelled or deleted from the database.

        This is called periodically during permit processing to allow
        users to stop a running job by either:
        1. Setting status = 'cancelled' in the database
        2. Deleting the job row entirely

        Returns True if the job should stop processing.
        """
        try:
            result = self.db.table('background_jobs') \
                .select('status') \
                .eq('id', job_id) \
                .execute()

            # Job was deleted
            if not result.data:
                print(f"🛑 Job {job_id} was deleted - stopping processing", flush=True)
                return True

            # Job was cancelled
            status = result.data[0].get('status')
            if status in ('cancelled', 'failed', 'completed'):
                print(f"🛑 Job {job_id} status is '{status}' - stopping processing", flush=True)
                return True

            return False
        except Exception as e:
            logger.warning(f"Error checking job status: {e}")
            # On error, continue processing (fail-safe)
            return False


# Singleton instance
_processor_instance: Optional[JobProcessor] = None


async def start_job_processor():
    """Start the background job processor."""
    global _processor_instance

    if _processor_instance is not None:
        logger.warning("Job processor already running")
        return

    db = get_db()
    _processor_instance = JobProcessor(db)

    # Start processor in background
    asyncio.create_task(_processor_instance.start())

    logger.info("✅ Job processor startup complete")


async def stop_job_processor():
    """Stop the background job processor."""
    global _processor_instance

    if _processor_instance is not None:
        await _processor_instance.stop()
        _processor_instance = None
        logger.info("✅ Job processor stopped")
