import json
import pytest
from main import app  # The Flask app in main.py


@pytest.fixture
def client():
    """
    This fixture provides a test client for our Flask app.
    """
    with app.test_client() as client:
        yield client


def test_create_buy_order_api(client):
    response = client.post(
        "/orders",
        data=json.dumps(
            {"user_id": "TraderA", "side": "BUY", "price": 100.0, "quantity": 10}
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()

    assert data["order"]["side"] == "BUY"
    assert data["order"]["quantity"] == 10
    assert len(data["trades_executed"]) == 0


def test_create_sell_order_api(client):
    # Place a BUY first so the SELL will match
    client.post(
        "/orders",
        data=json.dumps(
            {"user_id": "TraderA", "side": "BUY", "price": 100.0, "quantity": 5}
        ),
        content_type="application/json",
    )
    # Now place SELL that should match the BUY above
    response = client.post(
        "/orders",
        data=json.dumps(
            {"user_id": "TraderB", "side": "SELL", "price": 90.0, "quantity": 5}
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()

    # Expect trades_executed to have 1 item
    trades = data["trades_executed"]
    assert len(trades) == 1
    assert (
        trades[0]["price"] == 100.0
    )  # or 90.0 if your logic matches at the SELL price
    assert trades[0]["quantity"] == 5
