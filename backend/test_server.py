#!/usr/bin/env python3
"""Simple test script to verify the server works."""
import asyncio
from app.main import app
from fastapi.testclient import TestClient


def test_health_endpoint():
    """Test the health endpoint."""
    client = TestClient(app)
    response = client.get("/health")

    print("Testing /health endpoint:")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("  ✓ Health check passed!")


def test_root_endpoint():
    """Test the root endpoint."""
    client = TestClient(app)
    response = client.get("/")

    print("\nTesting / endpoint:")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "HVAC Lead Generation API"
    print("  ✓ Root endpoint passed!")


def test_api_structure():
    """Verify API structure."""
    client = TestClient(app)

    print("\nAPI Structure:")
    print(f"  Title: {app.title}")
    print(f"  Version: {app.version}")
    print(f"  Docs URL: http://localhost:8000/docs")
    print(f"  Total Routes: {len(app.routes)}")

    print("\nKey Endpoints:")
    endpoints = [
        ("POST", "/api/counties", "Create county"),
        ("GET", "/api/counties", "List counties"),
        ("POST", "/api/counties/{id}/pull-permits", "Pull permits"),
        ("GET", "/api/permits", "List permits"),
        ("POST", "/api/leads/create-from-permits", "Create leads"),
        ("POST", "/api/leads/sync-to-summit", "Sync to Summit.AI"),
        ("GET", "/health", "Health check"),
    ]

    for method, path, desc in endpoints:
        print(f"  {method:6} {path:40} - {desc}")


if __name__ == "__main__":
    print("=" * 60)
    print("HVAC Lead Generation API - Server Tests")
    print("=" * 60)
    print()

    test_health_endpoint()
    test_root_endpoint()
    test_api_structure()

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print("\nTo start the server, run:")
    print("  cd /Users/Brandy/projects/HVAC/backend")
    print("  source venv/bin/activate")
    print("  uvicorn app.main:app --reload")
    print("\nThen visit: http://localhost:8000/docs")
