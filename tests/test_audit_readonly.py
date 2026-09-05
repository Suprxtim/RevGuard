import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_audit_is_readonly():
    """
    Proves that calling GET /audit twice returns the exact same HTML content (and thus identical metrics),
    proving that it does not mutate database state or re-calculate non-deterministic values.
    """
    with TestClient(app) as client:
        response1 = client.get("/audit")
        assert response1.status_code == 200
        
        response2 = client.get("/audit")
        assert response2.status_code == 200
        
        # The content of the HTML should be completely identical if no mutation occurred
        assert response1.text == response2.text, "GET /audit mutated state or returned non-deterministic metrics!"
