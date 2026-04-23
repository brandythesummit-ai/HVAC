"""Unit tests for GHLClient — Contact + Opportunity handoff."""
import pytest

from app.services.ghl_client import GHLClient


BASE = "https://services.leadconnectorhq.com"


@pytest.fixture
def client():
    return GHLClient(access_token="test-pit-token", location_id="test-loc-id")


class TestUpsertContactForProperty:
    async def test_creates_new_contact_when_not_found(self, client, httpx_mock):
        # Search returns 200 with zero contacts → client creates.
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE}/contacts/?locationId=test-loc-id&query=555-0100",
            json={"contacts": []},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE}/contacts/",
            json={"contact": {"id": "new-contact-123", "name": "Jane Doe"}},
            status_code=201,
        )
        # Contact note POST — fire-and-forget; mock a 200
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE}/contacts/new-contact-123/notes",
            json={"note": {"id": "note-1"}},
            status_code=201,
        )

        result = await client.upsert_contact_for_property(
            owner_name="Jane Doe",
            owner_phone="555-0100",
            owner_email=None,
            property_address="1519 DALE MABRY HWY",
            custom_fields={
                "HVAC Permit Age": 3,
                "Permit Type": "Mechanical",
                "Property Value": 350000,
            },
            permit_raw_data={"permit_id": "NME36051"},
        )
        assert (result.get("contact") or {}).get("id") == "new-contact-123"

    async def test_updates_existing_contact_when_found(self, client, httpx_mock):
        # Search returns an existing contact
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE}/contacts/?locationId=test-loc-id&query=555-0100",
            json={"contacts": [{"id": "existing-456", "name": "Jane Old"}]},
            status_code=200,
        )
        httpx_mock.add_response(
            method="PUT",
            url=f"{BASE}/contacts/existing-456",
            json={"contact": {"id": "existing-456", "name": "Jane Doe"}},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE}/contacts/existing-456/notes",
            json={"note": {"id": "note-2"}},
            status_code=201,
        )

        result = await client.upsert_contact_for_property(
            owner_name="Jane Doe",
            owner_phone="555-0100",
            owner_email=None,
            property_address="1519 DALE MABRY HWY",
            custom_fields={"HVAC Permit Age": 3},
            permit_raw_data={"permit_id": "NME36051"},
        )
        # PUT response from update_contact returned
        assert (result.get("contact") or {}).get("id") == "existing-456"

    async def test_note_failure_does_not_fail_handoff(self, client, httpx_mock, caplog):
        # Contact creation succeeds but note attachment fails —
        # we want the handoff to return the contact regardless.
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE}/contacts/?locationId=test-loc-id&query=555-0100",
            json={"contacts": []},
            status_code=200,
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE}/contacts/",
            json={"contact": {"id": "new-999"}},
            status_code=201,
        )
        # Note POST returns 500
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE}/contacts/new-999/notes",
            status_code=500,
        )

        result = await client.upsert_contact_for_property(
            owner_name="Test",
            owner_phone="555-0100",
            owner_email=None,
            property_address="1 Test St",
            custom_fields={},
            permit_raw_data={"permit_id": "X"},
        )
        # Handoff still succeeded
        assert (result.get("contact") or {}).get("id") == "new-999"
        # ... but the warning was logged
        assert any("Failed to attach" in r.message for r in caplog.records)


class TestCreateOpportunity:
    async def test_create_basic_opportunity(self, client, httpx_mock):
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE}/opportunities/",
            json={"opportunity": {"id": "opp-abc", "status": "open"}},
            status_code=201,
            match_json={
                "locationId": "test-loc-id",
                "contactId": "contact-1",
                "pipelineId": "pipe-1",
                "pipelineStageId": "stage-interested",
                "name": "HVAC Lead - 1 Main St",
                "status": "open",
            },
        )
        result = await client.create_opportunity(
            contact_id="contact-1",
            pipeline_id="pipe-1",
            pipeline_stage_id="stage-interested",
            name="HVAC Lead - 1 Main St",
        )
        assert result["opportunity"]["id"] == "opp-abc"

    async def test_create_opportunity_with_value_and_source(self, client, httpx_mock):
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE}/opportunities/",
            json={"opportunity": {"id": "opp-xyz"}},
            status_code=201,
            match_json={
                "locationId": "test-loc-id",
                "contactId": "contact-2",
                "pipelineId": "pipe-1",
                "pipelineStageId": "stage-interested",
                "name": "HVAC Lead",
                "status": "open",
                "monetaryValue": 12000.0,
                "source": "door-knock",
            },
        )
        result = await client.create_opportunity(
            contact_id="contact-2",
            pipeline_id="pipe-1",
            pipeline_stage_id="stage-interested",
            name="HVAC Lead",
            monetary_value=12000.0,
            source="door-knock",
        )
        assert result["opportunity"]["id"] == "opp-xyz"


class TestUpdateOpportunityStage:
    async def test_update_stage(self, client, httpx_mock):
        httpx_mock.add_response(
            method="PUT",
            url=f"{BASE}/opportunities/opp-abc",
            json={"opportunity": {"id": "opp-abc", "pipelineStageId": "stage-quoted"}},
            status_code=200,
            match_json={"pipelineStageId": "stage-quoted"},
        )
        result = await client.update_opportunity_stage(
            "opp-abc", "stage-quoted",
        )
        assert result["opportunity"]["pipelineStageId"] == "stage-quoted"

    async def test_update_stage_with_status(self, client, httpx_mock):
        httpx_mock.add_response(
            method="PUT",
            url=f"{BASE}/opportunities/opp-abc",
            json={"opportunity": {"id": "opp-abc", "status": "won"}},
            status_code=200,
            match_json={"pipelineStageId": "stage-won", "status": "won"},
        )
        result = await client.update_opportunity_stage(
            "opp-abc", "stage-won", status="won",
        )
        assert result["opportunity"]["status"] == "won"


class TestCustomFieldsPayload:
    def test_fields_shaped_for_ghl(self, client):
        payload = GHLClient._custom_fields_payload({
            "HVAC Permit Age": 10,
            "Permit Type": "Mechanical",
            "Owner Occupied flag": True,
        })
        assert isinstance(payload, list)
        assert {"key": "HVAC Permit Age", "value": "10"} in payload
        # Bools serialize too
        assert {"key": "Owner Occupied flag", "value": "True"} in payload

    def test_none_values_become_empty_string(self, client):
        payload = GHLClient._custom_fields_payload({"Year Built": None})
        assert payload == [{"key": "Year Built", "value": ""}]


class TestAsciiValidation:
    def test_non_ascii_token_rejected(self):
        with pytest.raises(ValueError, match="non-ASCII"):
            GHLClient(access_token="pit-token-with-ñ", location_id="loc-1")

    def test_non_ascii_location_id_rejected(self):
        with pytest.raises(ValueError, match="non-ASCII"):
            GHLClient(access_token="ascii-token", location_id="loc-ñ")
