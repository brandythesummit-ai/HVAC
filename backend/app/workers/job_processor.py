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
from app.services.accela_client import AccelaClient
from app.services.property_aggregator import PropertyAggregator
from app.services.encryption import encryption_service
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
                # CRITICAL: Reset counters to avoid accumulation across retries
                await self._update_job(
                    job_id,
                    {
                        'status': 'pending',
                        'retry_count': retry_count + 1,
                        'permits_pulled': 0,       # Reset counter
                        'permits_saved': 0,        # Reset counter
                        'per_year_permits': {},    # Reset year tracking
                        'current_year': None,      # Reset current year
                        'progress_percent': 0,     # Reset progress
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
        permit_type = params.get('permit_type', self.PERMIT_TYPE_HVAC)

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

            raise ValueError(f"OAuth token invalid for {county['name']}: {token_result['error']}")

        print(f"✅ Token validated for {county['name']}", flush=True)

        # Initialize property aggregator
        aggregator = PropertyAggregator(self.db)

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

        # Track permits per year for live UI updates
        per_year_permits = {}

        # Track year-level status for accurate progress display
        # Status values: 'not_started', 'in_progress', 'completed'
        years_status = {str(year): 'not_started' for year in range(start_year, end_year + 1)}

        start_time = datetime.utcnow()

        logger.info(f"📅 Pulling {years} years: {start_year} → {end_year}")

        # Initialize job with years_status so UI can show all years immediately
        await self._update_job(job_id, {
            'years_status': years_status,
            'start_year': start_year,
            'end_year': end_year,
            'updated_at': datetime.utcnow().isoformat()
        })

        # Process year by year (oldest first)
        for year in range(start_year, end_year + 1):
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"

            logger.info(f"📆 Processing year {year}...")

            # Mark this year as in_progress
            years_status[str(year)] = 'in_progress'

            # Update job with current year and status
            await self._update_job(job_id, {
                'current_year': year,
                'years_status': years_status,
                'updated_at': datetime.utcnow().isoformat()
            })

            # Pull permits for this year (in batches)
            year_permits_pulled = 0
            batch_num = 0
            batch_size = 1000

            while True:
                batch_num += 1
                logger.info(f"   📦 Batch {batch_num} (up to {batch_size} permits)")

                # Fetch permits
                permit_data = await accela_client.get_permits(
                    date_from=year_start,
                    date_to=year_end,
                    limit=batch_size,
                    permit_type=permit_type
                )

                permits = permit_data.get('permits', [])

                if not permits:
                    logger.info(f"   ✅ No more permits for {year}")
                    break

                year_permits_pulled += len(permits)
                total_permits_pulled += len(permits)

                # Process each permit through property aggregator
                batch_properties_created = 0
                batch_properties_updated = 0
                batch_leads_created = 0
                batch_permits_saved = 0

                for permit in permits:
                    try:
                        # Get additional permit details
                        permit_details = await self._enrich_permit_data(accela_client, permit)

                        # Save permit to database
                        saved_permit = await self._save_permit(county_id, permit_details)
                        if saved_permit:
                            batch_permits_saved += 1

                        # Process through property aggregator
                        property_id, lead_id, was_created = await aggregator.process_permit(
                            saved_permit,
                            county_id
                        )

                        if property_id:
                            if was_created:
                                batch_properties_created += 1
                                if lead_id:
                                    batch_leads_created += 1
                            else:
                                batch_properties_updated += 1

                    except Exception as e:
                        logger.warning(f"Failed to process permit: {str(e)}")
                        continue

                # Update totals
                total_permits_saved += batch_permits_saved
                total_properties_created += batch_properties_created
                total_properties_updated += batch_properties_updated
                total_leads_created += batch_leads_created

                # Calculate elapsed time and rate
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                permits_per_second = total_permits_pulled / elapsed if elapsed > 0 else 0
                estimated_remaining = ((total_years - years_processed) * 1000) / permits_per_second if permits_per_second > 0 else 0
                estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_remaining)

                # Track per-year permits progressively (inside loop so crash-safe)
                per_year_permits[str(year)] = year_permits_pulled

                # Calculate batch-level progress (more granular than year-level)
                # Progress = completed years + partial progress on current year
                # Estimate current year as 50% done after first batch for smoother updates
                year_progress_fraction = min(0.9, batch_num * 0.2)  # Cap at 90% until year complete
                progress_percent = int(((years_processed + year_progress_fraction) / total_years) * 100)

                # Update job progress
                await self._update_job(job_id, {
                    'permits_pulled': total_permits_pulled,
                    'permits_saved': total_permits_saved,
                    'properties_created': total_properties_created,
                    'properties_updated': total_properties_updated,
                    'leads_created': total_leads_created,
                    'current_year': year,
                    'current_batch': batch_num,
                    'progress_percent': progress_percent,
                    'elapsed_seconds': int(elapsed),
                    'permits_per_second': round(permits_per_second, 2),
                    'estimated_completion_at': estimated_completion.isoformat(),
                    'per_year_permits': per_year_permits,
                    'updated_at': datetime.utcnow().isoformat()
                })

                logger.info(f"   ✅ Batch {batch_num}: {batch_permits_saved} saved, {batch_properties_created} properties created, {batch_leads_created} leads created")

                # If we got fewer permits than batch size, we're done with this year
                if len(permits) < batch_size:
                    break

            years_processed += 1

            # Mark this year as completed
            years_status[str(year)] = 'completed'

            # Update progress after year completion (ensures accurate % between years)
            await self._update_job(job_id, {
                'progress_percent': int((years_processed / total_years) * 100),
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

            raise ValueError(f"OAuth token invalid for {county['name']}: {token_result['error']}")

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
                permit_details = await self._enrich_permit_data(accela_client, permit)
                saved_permit = await self._save_permit(county_id, permit_details)

                if saved_permit:
                    total_saved += 1

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

    async def _enrich_permit_data(self, client: AccelaClient, permit: Dict) -> Dict:
        """
        Enrich permit with additional data (addresses, owners, parcels).

        Args:
            client: AccelaClient instance
            permit: Raw permit data

        Returns:
            Enriched permit dictionary
        """
        record_id = permit.get('id')

        # Fetch additional data
        addresses = await client.get_addresses(record_id)
        owners = await client.get_owners(record_id)
        parcels = await client.get_parcels(record_id)

        # Extract primary address
        primary_address = next((addr for addr in addresses if addr.get('isPrimary')), None) if addresses else None

        # Extract primary owner
        primary_owner = next((owner for owner in owners if owner.get('isPrimary')), None) if owners else None

        # Extract primary parcel
        primary_parcel = parcels[0] if parcels else None

        return {
            'id': record_id,
            'type': permit.get('type', {}).get('text'),
            'description': permit.get('description'),
            'opened_date': permit.get('openedDate'),
            'status': permit.get('status', {}).get('text'),
            'job_value': permit.get('estimatedCostOfConstruction'),
            'property_address': primary_address.get('fullAddress') if primary_address else None,
            'year_built': primary_parcel.get('yearBuilt') if primary_parcel else None,
            'square_footage': primary_parcel.get('buildingSquareFeet') if primary_parcel else None,
            'property_value': primary_parcel.get('landValue') if primary_parcel else None,
            'lot_size': primary_parcel.get('lotAreaSquareFeet') if primary_parcel else None,
            'owner_name': primary_owner.get('fullName') if primary_owner else None,
            'owner_phone': primary_owner.get('phone1') if primary_owner else None,
            'owner_email': primary_owner.get('email') if primary_owner else None,
            'raw_data': permit
        }

    async def _save_permit(self, county_id: str, permit_data: Dict) -> Optional[Dict]:
        """
        Save permit to database.

        Args:
            county_id: County UUID
            permit_data: Enriched permit data

        Returns:
            Saved permit record or None if already exists
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
                return existing.data[0]

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
                return result.data[0]

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
