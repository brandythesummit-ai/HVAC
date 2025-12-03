"""
Property Aggregation Service

Aggregates permits by property address and manages property-level lead generation.

Key responsibilities:
- Normalize addresses and group permits by property
- Track most recent HVAC permit per property
- Calculate HVAC age, lead scores, and lead tiers
- Create/update property records
- Create/update lead records (one per property)
"""

from datetime import date, datetime
from typing import Dict, Optional, List, Tuple
from uuid import UUID
import logging

from supabase import Client
from app.services.address_normalizer import AddressNormalizer

logger = logging.getLogger(__name__)


class PropertyAggregator:
    """
    Service for aggregating permits into property-level records.

    Lead Scoring Algorithm:
    - HOT (15-20+ years):    Score 80-100  (Replacement urgent/soon)
    - WARM (10-15 years):    Score 60-79   (Maintenance + potential replacement)
    - COOL (5-10 years):     Score 40-59   (Maintenance only)
    - COLD (<5 years):       Score 0-39    (Not qualified)
    - Qualification threshold: 5+ years
    """

    # Lead tier thresholds (in years)
    TIER_THRESHOLDS = {
        'HOT': 15,      # 15+ years = HOT
        'WARM': 10,     # 10-15 years = WARM
        'COOL': 5,      # 5-10 years = COOL
        'COLD': 0,      # <5 years = COLD
    }

    QUALIFICATION_THRESHOLD = 5  # 5+ years = qualified lead

    def __init__(self, db: Client):
        """
        Initialize PropertyAggregator with database client.

        Args:
            db: Supabase client instance
        """
        self.db = db

    def calculate_hvac_age(self, hvac_date: date) -> int:
        """
        Calculate HVAC age in years from installation date.

        Args:
            hvac_date: Date of HVAC installation

        Returns:
            Age in years (rounded down)
        """
        if not hvac_date:
            return 0

        today = date.today()
        age_years = today.year - hvac_date.year

        # Adjust if birthday hasn't occurred yet this year
        if (today.month, today.day) < (hvac_date.month, hvac_date.day):
            age_years -= 1

        return max(0, age_years)

    def calculate_lead_score(self, hvac_age_years: int) -> int:
        """
        Calculate lead score (0-100) based on HVAC age.

        Scoring:
        - 20+ years:  100 (HOT - replacement urgent)
        - 15-20 years: 80-95 (HOT - replacement soon)
        - 10-15 years: 60-75 (WARM - maintenance + potential replacement)
        - 5-10 years:  40-55 (COOL - maintenance only)
        - <5 years:    0-35 (COLD - not qualified)

        Args:
            hvac_age_years: Age of HVAC system in years

        Returns:
            Lead score (0-100)
        """
        if hvac_age_years >= 20:
            return 100
        elif hvac_age_years >= 15:
            # Linear scale from 80 to 95 over 5 years
            return 80 + int((hvac_age_years - 15) * 3)
        elif hvac_age_years >= 10:
            # Linear scale from 60 to 75 over 5 years
            return 60 + int((hvac_age_years - 10) * 3)
        elif hvac_age_years >= 5:
            # Linear scale from 40 to 55 over 5 years
            return 40 + int((hvac_age_years - 5) * 3)
        else:
            # Linear scale from 0 to 35 over 5 years
            return int(hvac_age_years * 7)

    def determine_lead_tier(self, hvac_age_years: int) -> str:
        """
        Determine lead tier based on HVAC age.

        Args:
            hvac_age_years: Age of HVAC system in years

        Returns:
            Lead tier: 'HOT', 'WARM', 'COOL', or 'COLD'
        """
        if hvac_age_years >= self.TIER_THRESHOLDS['HOT']:
            return 'HOT'
        elif hvac_age_years >= self.TIER_THRESHOLDS['WARM']:
            return 'WARM'
        elif hvac_age_years >= self.TIER_THRESHOLDS['COOL']:
            return 'COOL'
        else:
            return 'COLD'

    def is_qualified_lead(self, hvac_age_years: int) -> bool:
        """
        Determine if property qualifies as a lead.

        Args:
            hvac_age_years: Age of HVAC system in years

        Returns:
            True if HVAC is 5+ years old
        """
        return hvac_age_years >= self.QUALIFICATION_THRESHOLD

    def calculate_contact_completeness(
        self,
        owner_phone: Optional[str],
        owner_email: Optional[str]
    ) -> str:
        """
        Calculate contact information completeness.

        Args:
            owner_phone: Owner phone number
            owner_email: Owner email address

        Returns:
            'complete', 'partial', or 'minimal'
        """
        if owner_phone and owner_email:
            return 'complete'
        elif owner_phone or owner_email:
            return 'partial'
        else:
            return 'minimal'

    def calculate_affluence_tier(self, property_value: Optional[float]) -> str:
        """
        Calculate affluence tier based on property value.

        Args:
            property_value: Total property value

        Returns:
            'ultra_high', 'high', 'medium', or 'standard'
        """
        if not property_value:
            return 'standard'

        if property_value >= 500000:
            return 'ultra_high'
        elif property_value >= 350000:
            return 'high'
        elif property_value >= 200000:
            return 'medium'
        else:
            return 'standard'

    def calculate_pipeline_assignment(
        self,
        lead_tier: str,
        hvac_age_years: int,
        contact_completeness: str,
        affluence_tier: str,
        property_value: Optional[float] = None
    ) -> Tuple[str, int]:
        """
        Calculate recommended Summit.ai pipeline and confidence score.

        Pipeline Assignment Logic:
        1. hot_call: HOT leads with complete contact (phone + email)
        2. premium_mailer: HOT leads with partial contact OR high-value WARM leads
        3. nurture_drip: WARM leads OR high-value COOL leads
        4. retargeting_ads: COOL leads (standard value)
        5. cold_storage: COLD leads (not qualified)

        Args:
            lead_tier: Lead tier (HOT, WARM, COOL, COLD)
            hvac_age_years: Age of HVAC system
            contact_completeness: Contact quality (complete, partial, minimal)
            affluence_tier: Property value tier
            property_value: Total property value (optional, for logging)

        Returns:
            Tuple of (pipeline_name, confidence_score)
        """
        # HOT leads (15+ years)
        if lead_tier == 'HOT':
            if contact_completeness == 'complete':
                # Best leads: old HVAC + full contact info = immediate call opportunity
                return 'hot_call', 95
            elif contact_completeness == 'partial':
                # Good leads but missing some contact info = premium mail campaign
                return 'premium_mailer', 85
            else:
                # HOT but no contact info = still worth premium effort
                return 'premium_mailer', 75

        # WARM leads (10-15 years)
        elif lead_tier == 'WARM':
            if affluence_tier in ('ultra_high', 'high'):
                # High-value properties worth premium mailer even if not urgent yet
                return 'premium_mailer', 80
            elif contact_completeness == 'complete':
                # Good contact info = nurture until ready
                return 'nurture_drip', 75
            else:
                # Standard WARM lead = nurture campaign
                return 'nurture_drip', 70

        # COOL leads (5-10 years)
        elif lead_tier == 'COOL':
            if affluence_tier in ('ultra_high', 'high'):
                # High-value properties worth nurturing long-term
                return 'nurture_drip', 65
            else:
                # Standard COOL = retargeting ads for brand awareness
                return 'retargeting_ads', 60

        # COLD leads (<5 years) - not qualified but keep in system
        else:
            return 'cold_storage', 50

    def create_qualification_reason(
        self,
        hvac_age_years: int,
        property_value: Optional[float] = None
    ) -> str:
        """
        Generate human-readable qualification reason.

        Args:
            hvac_age_years: Age of HVAC system
            property_value: Total property value (optional)

        Returns:
            Qualification reason string
        """
        reason_parts = [f"HVAC {hvac_age_years} years old"]

        if property_value:
            reason_parts.append(f"property value ${int(property_value):,}")

        return ", ".join(reason_parts)

    async def process_permit(
        self,
        permit_data: Dict,
        county_id: str
    ) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Process a permit and create/update property and lead records.

        Args:
            permit_data: Permit data dictionary
            county_id: County UUID

        Returns:
            Tuple of (property_id, lead_id, was_created)
        """
        try:
            # Extract and normalize address
            raw_address = permit_data.get('property_address')

            # Parse address components (use permit ID as fallback for no-address permits)
            if raw_address:
                parsed_address = AddressNormalizer.parse_address(raw_address)
                normalized_address = parsed_address.normalized_address
            else:
                # No address available - use permit ID as unique identifier
                # This allows historical permits (which often lack address data) to still become leads
                permit_id = permit_data.get('id', 'unknown')
                logger.info(f"Permit {permit_id} has no address - using permit ID as identifier")
                parsed_address = AddressNormalizer.parse_address(f"PERMIT-{permit_id}")
                normalized_address = f"PERMIT-{permit_id}"

            # Extract HVAC permit date
            opened_date = permit_data.get('opened_date')
            if isinstance(opened_date, str):
                opened_date = datetime.fromisoformat(opened_date).date()
            elif isinstance(opened_date, datetime):
                opened_date = opened_date.date()

            if not opened_date:
                logger.warning(f"Permit {permit_data.get('id')} has no date, skipping")
                return None, None, False

            # Check if property already exists
            existing_property = self.db.table('properties') \
                .select('*') \
                .eq('county_id', county_id) \
                .eq('normalized_address', normalized_address) \
                .execute()

            property_id = None
            lead_id = None
            was_created = False

            if existing_property.data:
                # Property exists - check if this permit is more recent
                property_record = existing_property.data[0]
                property_id = property_record['id']

                current_hvac_date = property_record.get('most_recent_hvac_date')
                if current_hvac_date:
                    if isinstance(current_hvac_date, str):
                        current_hvac_date = datetime.fromisoformat(current_hvac_date).date()

                # Update if this permit is more recent OR if no current HVAC date
                if not current_hvac_date or opened_date > current_hvac_date:
                    property_id = await self._update_property(
                        property_id,
                        permit_data,
                        opened_date,
                        parsed_address
                    )
                    lead_id = await self._update_lead(property_id, county_id)
                else:
                    # Permit is older - just increment total_hvac_permits counter
                    await self._increment_permit_counter(property_id)

            else:
                # New property - create it
                property_id = await self._create_property(
                    county_id,
                    permit_data,
                    opened_date,
                    parsed_address
                )
                lead_id = await self._create_lead(property_id, county_id)
                was_created = True

            return property_id, lead_id, was_created

        except Exception as e:
            logger.error(f"Error processing permit {permit_data.get('id')}: {str(e)}")
            raise

    async def _create_property(
        self,
        county_id: str,
        permit_data: Dict,
        hvac_date: date,
        parsed_address
    ) -> str:
        """Create a new property record."""
        # Calculate lead metrics
        hvac_age = self.calculate_hvac_age(hvac_date)
        lead_score = self.calculate_lead_score(hvac_age)
        lead_tier = self.determine_lead_tier(hvac_age)
        is_qualified = self.is_qualified_lead(hvac_age)

        # Calculate pipeline intelligence
        owner_phone = permit_data.get('owner_phone')
        owner_email = permit_data.get('owner_email')
        property_value = permit_data.get('property_value')

        contact_completeness = self.calculate_contact_completeness(owner_phone, owner_email)
        affluence_tier = self.calculate_affluence_tier(property_value)
        recommended_pipeline, pipeline_confidence = self.calculate_pipeline_assignment(
            lead_tier, hvac_age, contact_completeness, affluence_tier, property_value
        )

        property_data = {
            'county_id': county_id,
            'normalized_address': parsed_address.normalized_address,
            'street_number': parsed_address.street_number,
            'street_name': parsed_address.street_name,
            'street_suffix': parsed_address.street_suffix,
            'unit_number': parsed_address.unit_number,
            'city': parsed_address.city,
            'state': parsed_address.state,
            'zip_code': parsed_address.zip_code,
            'most_recent_hvac_permit_id': permit_data.get('id'),
            'most_recent_hvac_date': hvac_date.isoformat(),
            'hvac_age_years': hvac_age,
            'lead_score': lead_score,
            'lead_tier': lead_tier,
            'is_qualified': is_qualified,
            'owner_name': permit_data.get('owner_name'),
            'owner_phone': owner_phone,
            'owner_email': owner_email,
            'parcel_number': permit_data.get('raw_data', {}).get('parcelNumber'),
            'year_built': permit_data.get('year_built'),
            'lot_size_sqft': int(permit_data.get('lot_size')) if permit_data.get('lot_size') else None,
            'total_property_value': property_value,
            'total_hvac_permits': 1,
            'contact_completeness': contact_completeness,
            'affluence_tier': affluence_tier,
            'recommended_pipeline': recommended_pipeline,
            'pipeline_confidence': pipeline_confidence,
        }

        # Use upsert to handle re-pulls gracefully (avoids duplicate key errors)
        # If a property with this county_id + normalized_address already exists, update it
        result = self.db.table('properties').upsert(
            property_data,
            on_conflict='county_id,normalized_address'
        ).execute()

        if result.data:
            logger.info(f"Upserted property {result.data[0]['id']} at {parsed_address.normalized_address} (Pipeline: {recommended_pipeline})")
            return result.data[0]['id']
        else:
            raise Exception("Failed to upsert property record")

    async def _update_property(
        self,
        property_id: str,
        permit_data: Dict,
        hvac_date: date,
        parsed_address
    ) -> str:
        """Update an existing property with more recent HVAC permit."""
        # Calculate lead metrics
        hvac_age = self.calculate_hvac_age(hvac_date)
        lead_score = self.calculate_lead_score(hvac_age)
        lead_tier = self.determine_lead_tier(hvac_age)
        is_qualified = self.is_qualified_lead(hvac_age)

        # Calculate pipeline intelligence
        owner_phone = permit_data.get('owner_phone')
        owner_email = permit_data.get('owner_email')
        property_value = permit_data.get('property_value')

        contact_completeness = self.calculate_contact_completeness(owner_phone, owner_email)
        affluence_tier = self.calculate_affluence_tier(property_value)
        recommended_pipeline, pipeline_confidence = self.calculate_pipeline_assignment(
            lead_tier, hvac_age, contact_completeness, affluence_tier, property_value
        )

        # Get current total_hvac_permits count
        current = self.db.table('properties').select('total_hvac_permits').eq('id', property_id).execute()
        current_count = current.data[0]['total_hvac_permits'] if current.data else 1

        update_data = {
            'most_recent_hvac_permit_id': permit_data.get('id'),
            'most_recent_hvac_date': hvac_date.isoformat(),
            'hvac_age_years': hvac_age,
            'lead_score': lead_score,
            'lead_tier': lead_tier,
            'is_qualified': is_qualified,
            'owner_name': permit_data.get('owner_name'),
            'owner_phone': owner_phone,
            'owner_email': owner_email,
            'year_built': permit_data.get('year_built'),
            'lot_size_sqft': int(permit_data.get('lot_size')) if permit_data.get('lot_size') else None,
            'total_property_value': property_value,
            'total_hvac_permits': current_count + 1,
            'contact_completeness': contact_completeness,
            'affluence_tier': affluence_tier,
            'recommended_pipeline': recommended_pipeline,
            'pipeline_confidence': pipeline_confidence,
            'updated_at': datetime.utcnow().isoformat(),
        }

        result = self.db.table('properties').update(update_data).eq('id', property_id).execute()

        if result.data:
            logger.info(f"Updated property {property_id} with more recent HVAC from {hvac_date} (Pipeline: {recommended_pipeline})")
            return property_id
        else:
            raise Exception(f"Failed to update property {property_id}")

    async def _increment_permit_counter(self, property_id: str):
        """Increment the total_hvac_permits counter for a property."""
        # Get current count
        current = self.db.table('properties').select('total_hvac_permits').eq('id', property_id).execute()
        current_count = current.data[0]['total_hvac_permits'] if current.data else 0

        # Update count
        self.db.table('properties').update({
            'total_hvac_permits': current_count + 1,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', property_id).execute()

    async def _create_lead(self, property_id: str, county_id: str) -> Optional[str]:
        """Create a new lead for a property."""
        # Get property data
        property_result = self.db.table('properties').select('*').eq('id', property_id).execute()

        if not property_result.data:
            logger.warning(f"Property {property_id} not found, skipping lead creation")
            return None

        property_record = property_result.data[0]

        # Create lead for ALL properties regardless of qualification
        # This allows users to see all permit data in the Leads tab
        # The is_qualified and lead_tier fields still indicate actual qualification status

        # Get the associated permit for additional details
        permit_id = property_record.get('most_recent_hvac_permit_id')
        permit_result = self.db.table('permits').select('*').eq('id', permit_id).execute()
        permit_record = permit_result.data[0] if permit_result.data else {}

        qualification_reason = self.create_qualification_reason(
            property_record['hvac_age_years'],
            property_record.get('total_property_value')
        )

        lead_data = {
            'county_id': county_id,
            'property_id': property_id,
            'permit_id': permit_id,  # Keep for backward compatibility
            'lead_score': property_record['lead_score'],
            'lead_tier': property_record['lead_tier'],
            'qualification_reason': qualification_reason,
            'notes': f"HVAC system {property_record['hvac_age_years']} years old ({property_record['lead_tier']} tier)"
        }

        # Use upsert to prevent duplicate leads per property
        # If a lead already exists for this property_id, update it instead of inserting
        result = self.db.table('leads').upsert(
            lead_data,
            on_conflict='property_id'
        ).execute()

        if result.data:
            logger.info(f"Upserted lead {result.data[0]['id']} for property {property_id}")
            return result.data[0]['id']
        else:
            raise Exception(f"Failed to upsert lead for property {property_id}")

    async def _update_lead(self, property_id: str, county_id: str) -> Optional[str]:
        """Update existing lead or create new one if needed."""
        # Get property data
        property_result = self.db.table('properties').select('*').eq('id', property_id).execute()

        if not property_result.data:
            logger.warning(f"Property {property_id} not found, skipping lead update")
            return None

        property_record = property_result.data[0]

        # Check if lead exists
        lead_result = self.db.table('leads').select('*').eq('property_id', property_id).execute()

        if lead_result.data:
            # Update existing lead
            lead_id = lead_result.data[0]['id']

            # If property no longer qualified, disqualify the lead
            if not property_record.get('is_qualified'):
                disqualification_reason = f"New HVAC installed {property_record['most_recent_hvac_date']} (now {property_record['hvac_age_years']} years old)"

                self.db.table('leads').update({
                    'lead_score': property_record['lead_score'],
                    'lead_tier': property_record['lead_tier'],
                    'disqualified_at': datetime.utcnow().isoformat(),
                    'disqualification_reason': disqualification_reason,
                    'updated_at': datetime.utcnow().isoformat(),
                }).eq('id', lead_id).execute()

                logger.info(f"Disqualified lead {lead_id} - newer HVAC detected")
                return lead_id

            # Update qualified lead with new scores
            qualification_reason = self.create_qualification_reason(
                property_record['hvac_age_years'],
                property_record.get('total_property_value')
            )

            self.db.table('leads').update({
                'lead_score': property_record['lead_score'],
                'lead_tier': property_record['lead_tier'],
                'qualification_reason': qualification_reason,
                'notes': f"HVAC system {property_record['hvac_age_years']} years old ({property_record['lead_tier']} tier)",
                'disqualified_at': None,  # Clear any previous disqualification
                'disqualification_reason': None,
                'updated_at': datetime.utcnow().isoformat(),
            }).eq('id', lead_id).execute()

            logger.info(f"Updated lead {lead_id} for property {property_id}")
            return lead_id

        else:
            # No lead exists - create one if qualified
            return await self._create_lead(property_id, county_id)
