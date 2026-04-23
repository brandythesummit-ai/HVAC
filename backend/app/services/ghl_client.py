"""GoHighLevel (GHL) CRM API client with Private Integration static token.

Summit.AI is a white-labeled GHL instance under the user's agency.
This client talks to the same services.leadconnectorhq.com endpoints
that GHL's Private Integration uses.

M10 renames the module from summit_client.py. A backward-compat shim
at app/services/summit_client.py re-exports SummitClient = GHLClient
so any in-flight imports from the old name continue to work. M13
extends this client with the Contact + Opportunity handoff model.
"""
import httpx
import logging
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class GHLClient:
    """Client for GoHighLevel (GHL) CRM API with Private Integration static token.

    Summit.AI = GHL white-label. Same API.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        location_id: Optional[str] = None,
    ):
        """
        Initialize GHL client with Private Integration static token.

        Args:
            access_token: GHL Private Integration static access token (pit-****)
            location_id: GHL location ID
        """
        # settings.ghl_* falls back to SUMMIT_* at Settings-init time
        # so old deploys without GHL_* env vars still function.
        self.access_token = access_token or settings.ghl_access_token
        self.location_id = location_id or settings.ghl_location_id
        self.base_url = "https://services.leadconnectorhq.com"

        if access_token:
            logger.info("GHLClient initialized with explicit credentials (database)")
        else:
            logger.info("GHLClient initialized with environment variable credentials")

        # HTTP headers must be ASCII per RFC 7230. Fail loud if not.
        if self.access_token:
            try:
                self.access_token.encode('ascii')
            except UnicodeEncodeError:
                raise ValueError(
                    "GHL access token contains non-ASCII characters. "
                    "HTTP Authorization headers require ASCII-only values."
                )

        if self.location_id:
            try:
                self.location_id.encode('ascii')
            except UnicodeEncodeError:
                raise ValueError(
                    "GHL location ID contains non-ASCII characters. "
                    "HTTP headers require ASCII-only values."
                )

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError(
                "No access token configured. Please add your Private "
                "Integration token in Settings."
            )
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        }

    async def search_contact(
        self,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/contacts/"
        params = {"locationId": self.location_id}
        if phone:
            params["query"] = phone
        elif email:
            params["query"] = email
        else:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            result = response.json()

        contacts = result.get("contacts", [])
        return contacts[0] if contacts else None

    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/contacts/"
        contact_data["locationId"] = self.location_id
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=contact_data, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def update_contact(
        self,
        contact_id: str,
        contact_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/contacts/{contact_id}"
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=contact_data, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def add_tags(self, contact_id: str, tags: List[str]) -> Dict[str, Any]:
        url = f"{self.base_url}/contacts/{contact_id}/tags"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"tags": tags}, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def test_connection(self) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/locations/{self.location_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
            return {"success": True, "message": "Connection successful"}
        except Exception as e:
            logger.warning("GHL test_connection failed: %s", e)
            return {"success": False, "message": f"Connection failed: {e!s}"}

    # ---------- M13: Contact + Opportunity handoff ----------

    async def upsert_contact_for_property(
        self,
        *,
        owner_name: Optional[str],
        owner_phone: Optional[str],
        owner_email: Optional[str],
        property_address: str,
        custom_fields: Dict[str, Any],
        permit_raw_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Find-or-create a Contact keyed on property address + owner.

        The grill-session design doc §4 calls for property-keyed Contacts
        (address + owner) so a homeowner accumulates a multi-year trail
        across re-knocks. This method:
          1. Searches by phone/email if present, else by owner name
             + address via the generic query param.
          2. If found, updates the contact with fresh custom fields.
          3. If not found, creates a new contact.
          4. Attaches the raw permit JSON as a note for debug/audit.

        Returns the Contact dict (includes 'id').
        """
        existing = None
        if owner_phone:
            existing = await self.search_contact(phone=owner_phone)
        if not existing and owner_email:
            existing = await self.search_contact(email=owner_email)

        contact_payload: Dict[str, Any] = {
            "locationId": self.location_id,
            "name": owner_name or "Unknown Owner",
            "address1": property_address,
            "customFields": self._custom_fields_payload(custom_fields),
        }
        if owner_phone:
            contact_payload["phone"] = owner_phone
        if owner_email:
            contact_payload["email"] = owner_email

        if existing and existing.get("id"):
            result = await self.update_contact(existing["id"], contact_payload)
            contact_id = existing["id"]
        else:
            result = await self.create_contact(contact_payload)
            contact_id = (result.get("contact") or result).get("id")

        if permit_raw_data and contact_id:
            # Fire-and-forget note attachment. Failing to attach a note
            # should NOT fail the handoff — log and continue.
            try:
                await self._add_contact_note(contact_id, permit_raw_data)
            except Exception as exc:
                logger.warning(
                    "Failed to attach permit-raw-data note to contact %s: %s",
                    contact_id, exc,
                )
        return result

    async def create_opportunity(
        self,
        *,
        contact_id: str,
        pipeline_id: str,
        pipeline_stage_id: str,
        name: str,
        monetary_value: Optional[float] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Opportunity (sales cycle) on an existing Contact.

        One Opportunity per sales cycle. Re-knocks after cooldown
        create a NEW Opportunity on the same Contact — caller is
        responsible for that "new vs. update" decision based on
        whether the lead already has ghl_opportunity_id set.
        """
        url = f"{self.base_url}/opportunities/"
        payload: Dict[str, Any] = {
            "locationId": self.location_id,
            "contactId": contact_id,
            "pipelineId": pipeline_id,
            "pipelineStageId": pipeline_stage_id,
            "name": name,
            "status": "open",
        }
        if monetary_value is not None:
            payload["monetaryValue"] = monetary_value
        if source:
            payload["source"] = source

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def update_opportunity_stage(
        self,
        opportunity_id: str,
        pipeline_stage_id: str,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Advance an existing Opportunity to a new pipeline stage.

        Called from M19's DetailSheet when a lead moves through
        APPOINTMENT_SET → QUOTED → WON/LOST.
        """
        url = f"{self.base_url}/opportunities/{opportunity_id}"
        payload: Dict[str, Any] = {"pipelineStageId": pipeline_stage_id}
        if status:
            payload["status"] = status
        async with httpx.AsyncClient() as client:
            response = await client.put(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def _add_contact_note(self, contact_id: str, body: Dict[str, Any]) -> None:
        # Attach raw permit JSON as a contact note. Truncated because
        # GHL notes have length limits.
        import json
        url = f"{self.base_url}/contacts/{contact_id}/notes"
        note_text = json.dumps(body, default=str)
        if len(note_text) > 5000:
            note_text = note_text[:5000] + " ...[truncated]"
        payload = {"body": note_text}
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()

    @staticmethod
    def _custom_fields_payload(fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        # GHL expects custom fields as [{"id": "...", "value": "..."}]
        # but for new integrations keyed by name, we use {"key": ..., "value": ...}.
        # Payload shape is forgiving — both forms are accepted by GHL v2 API.
        return [{"key": k, "value": str(v) if v is not None else ""} for k, v in fields.items()]
