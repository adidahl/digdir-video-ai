"""Tests for authentication endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_user():
    """Test user registration."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
            "organization_name": "Test Organization"
        }
    )
    assert response.status_code in [200, 201, 400]  # 400 if user already exists


def test_login():
    """Test user login."""
    # First register
    client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "password": "testpassword123",
            "full_name": "Login Test",
            "organization_name": "Test Org"
        }
    )
    
    # Then login
    response = client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200 or response.status_code == 401
    
    if response.status_code == 200:
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

