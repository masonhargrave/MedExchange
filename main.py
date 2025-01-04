# main.py

from flask import Flask, request, jsonify
import uuid
from database import engine, SessionLocal, Base
from db_models import DbOrder, DbTrade  # new import
from models import Order
from order_book import OrderBook

app = Flask(__name__)

# Create the DB tables if they do not exist
Base.metadata.create_all(bind=engine)

# In-memory OrderBook (unchanged for now)
order_book = OrderBook()


@app.route("/")
def index():
    return jsonify({"message": "Welcome to the MedExchange API!"})


@app.route("/orders", methods=["POST"])
def create_order():
    """
    Create a new buy or sell order.
    Example JSON:
    {
      "user_id": "TraderA",
      "side": "BUY",
      "price": 100.0,
      "quantity": 10
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    # Extract fields from JSON
    user_id = data.get("user_id")
    side = data.get("side")
    price = data.get("price")
    quantity = data.get("quantity")

    if not all([user_id, side, price, quantity]):
        return jsonify({"error": "Missing required fields"}), 400

    # Create the Order object
    new_order = Order(
        order_id=str(uuid.uuid4()),
        user_id=user_id,
        side=side,
        price=float(price),
        quantity=int(quantity),
    )

    # Add the order to the OrderBook
    trades = order_book.add_order(new_order)

    return jsonify(
        {
            "message": "Order created",
            "order": new_order.__dict__,
            "trades_executed": [t.__dict__ for t in trades],
        }
    )


@app.route("/order_book", methods=["GET"])
def get_order_book():
    """
    Get the current order book (active buy and sell orders).
    """
    return jsonify(order_book.get_order_book())


@app.route("/trades", methods=["GET"])
def get_trades():
    """
    Get trade history for the session.
    """
    return jsonify(order_book.get_trade_history())


if __name__ == "__main__":
    # Run the Flask app
    # Access it at http://127.0.0.1:5000/
    app.run(debug=True)
