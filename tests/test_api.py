from dotenv import load_dotenv
import os
import requests
import pytest
from main import app

# Load environment variables
load_dotenv()


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


@pytest.fixture
def valid_token():
    # Get a valid token from Auth0
    response = requests.post(
        f"https://{os.environ['AUTH0_DOMAIN']}/oauth/token",
        headers={"content-type": "application/json"},
        json={
            "client_id": os.environ["AUTH0_CLIENT_ID"],
            "client_secret": os.environ["AUTH0_CLIENT_SECRET"],
            "audience": os.environ["AUTH0_API_AUDIENCE"],
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    assert response.status_code == 200, "Failed to retrieve Auth0 token"
    return response.json()["access_token"]


def test_index(client):
    """Test public endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data
    assert (
        data["message"] == "MedExchange: Auth0-protected endpoints with rate limiting"
    )


def test_create_order_with_auth(client, valid_token):
    """Test creating an order with valid JWT"""
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.post(
        "/orders",
        json={
            "user_id": "Alice",
            "side": "BUY",
            "price": 100.0,
            "quantity": 10,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "order" in data
    assert data["order"]["user_id"] == "Alice"


def test_create_order_without_auth(client):
    """Test creating an order without JWT"""
    response = client.post(
        "/orders",
        json={
            "user_id": "Alice",
            "side": "BUY",
            "price": 100.0,
            "quantity": 10,
        },
    )
    assert response.status_code == 401
    data = response.get_json()
    assert "code" in data
    assert "description" in data
    assert data["code"] == "authorization_header_missing"


def test_rate_limiting(client, valid_token):
    """Test rate limiting on secured endpoint"""
    headers = {"Authorization": f"Bearer {valid_token}"}

    # Send 9 requests (should succeed)
    for i in range(9):
        response = client.post(
            "/orders",
            json={
                "user_id": "Bob",
                "side": "SELL",
                "price": 95.0,
                "quantity": 5,
            },
            headers=headers,
        )
        assert response.status_code == 200, f"Request {i + 1} failed unexpectedly"

    # The 10th request should fail
    response = client.post(
        "/orders",
        json={"user_id": "Bob", "side": "SELL", "price": 95.0, "quantity": 5},
        headers=headers,
    )
    assert response.status_code == 429, "10th request did not fail as expected"
