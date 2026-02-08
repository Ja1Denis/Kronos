import pytest
from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_stats_endpoint():
    # Testiramo da endpoint vraća 200, čak i ako je baza prazna
    response = client.get("/stats")
    assert response.status_code == 200
    assert "total_chunks" in response.json()
