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
def token():
    # Obtain a token dynamically
    response = requests.post(
        f"https://{os.environ['AUTH0_DOMAIN']}/oauth/token",
        headers={"content-type": "application/json"},
        json={
            "client_id": os.environ["AUTH0_CLIENT_ID"],
            "client_secret": os.environ["AUTH0_CLIENT_SECRET"],
            "audience": os.environ["AUTH0_API_AUDIENCE"],
            "grant_type": "client_credentials",
        },
    )
    return response.json()["access_token"]
