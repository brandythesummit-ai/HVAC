"""Deprecated: use app.services.ghl_client.GHLClient.

Summit.AI is a white-labeled GoHighLevel instance. M10 renamed the
canonical module from summit_client to ghl_client. This shim
re-exports the old name so existing imports (routers/summit.py,
routers/counties.py, routers/leads.py, property_aggregator.py) keep
working during the rename transition.

Remove this shim once all imports point at ghl_client directly.
"""
from app.services.ghl_client import GHLClient  # noqa: F401

# Backward-compat alias
SummitClient = GHLClient

__all__ = ["SummitClient", "GHLClient"]
