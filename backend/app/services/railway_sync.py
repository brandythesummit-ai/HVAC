"""Service to sync configuration to Railway environment variables."""
import os
import httpx
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RailwaySync:
    """Sync configuration to Railway environment variables."""

    def __init__(self):
        """Initialize Railway sync service."""
        self.api_token = os.getenv("RAILWAY_TOKEN")
        self.project_id = os.getenv("RAILWAY_PROJECT_ID")
        self.environment_id = os.getenv("RAILWAY_ENVIRONMENT_ID")
        self.service_id = os.getenv("RAILWAY_SERVICE_ID")
        self.base_url = "https://backboard.railway.app/graphql"

    def is_configured(self) -> bool:
        """Check if Railway API is configured."""
        return bool(
            self.api_token
            and self.project_id
            and self.environment_id
            and self.service_id
        )

    async def update_variables(self, variables: Dict[str, str]) -> Dict[str, any]:
        """
        Update Railway environment variables.

        Args:
            variables: Dictionary of environment variable names and values

        Returns:
            Result dictionary with success status and message
        """
        if not self.is_configured():
            logger.warning(
                "Railway API not configured - skipping environment variable sync"
            )
            return {
                "success": False,
                "message": "Railway API not configured",
                "synced": False,
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Railway GraphQL mutation to upsert variables
                for var_name, var_value in variables.items():
                    mutation = """
                    mutation VariableUpsert($input: VariableUpsertInput!) {
                        variableUpsert(input: $input)
                    }
                    """

                    # Build the input for the mutation
                    variables_input = {
                        "input": {
                            "projectId": self.project_id,
                            "environmentId": self.environment_id,
                            "serviceId": self.service_id,
                            "name": var_name,
                            "value": var_value,
                        }
                    }

                    headers = {
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json",
                    }

                    response = await client.post(
                        self.base_url, json={"query": mutation, "variables": variables_input}, headers=headers
                    )

                    if response.status_code != 200:
                        logger.error(
                            f"Failed to update Railway variable {var_name}: {response.status_code} - {response.text}"
                        )
                        return {
                            "success": False,
                            "message": f"Railway API error: {response.status_code}",
                            "synced": False,
                        }

                    result = response.json()
                    if "errors" in result:
                        logger.error(
                            f"GraphQL errors updating {var_name}: {result['errors']}"
                        )
                        return {
                            "success": False,
                            "message": f"GraphQL error: {result['errors'][0]['message']}",
                            "synced": False,
                        }

                logger.info(
                    f"Successfully synced {len(variables)} variables to Railway"
                )
                return {
                    "success": True,
                    "message": f"Synced {len(variables)} variables to Railway",
                    "synced": True,
                }

        except Exception as e:
            logger.error(f"Error syncing to Railway: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "synced": False,
            }


async def sync_summit_credentials(
    access_token: str, location_id: str
) -> Dict[str, any]:
    """
    Sync Summit.AI credentials to Railway environment variables.

    Args:
        access_token: Summit.AI access token
        location_id: Summit.AI location ID

    Returns:
        Result dictionary
    """
    sync_service = RailwaySync()

    if not sync_service.is_configured():
        logger.info(
            "Railway sync not configured - credentials saved to database only"
        )
        return {"success": True, "message": "Saved to database", "synced": False}

    variables = {
        "SUMMIT_ACCESS_TOKEN": access_token,
        "SUMMIT_LOCATION_ID": location_id,
    }

    return await sync_service.update_variables(variables)
