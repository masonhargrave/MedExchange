import pytest
from order_book import OrderBook
from models import Order


def test_add_buy_order_no_match():
    """
    Test adding a BUY order when there are no SELL orders.
    Expect no trades to be executed and the buy order
    to remain in the order book.
    """
    ob = OrderBook()
    buy_order = Order(
        order_id="test_buy_1", user_id="UserA", side="BUY", price=100.0, quantity=10
    )

    trades = ob.add_order(buy_order)

    # Assert no trades
    assert len(trades) == 0
    # Assert the order book has one BUY order
    assert len(ob.buy_orders) == 1
    assert ob.buy_orders[0].order_id == "test_buy_1"


def test_add_sell_order_no_match():
    """
    Test adding a SELL order when there are no BUY orders.
    Expect no trades to be executed and the sell order
    to remain in the order book.
    """
    ob = OrderBook()
    sell_order = Order(
        order_id="test_sell_1", user_id="UserB", side="SELL", price=105.0, quantity=5
    )

    trades = ob.add_order(sell_order)

    # Assert no trades
    assert len(trades) == 0
    # Assert the order book has one SELL order
    assert len(ob.sell_orders) == 1
    assert ob.sell_orders[0].order_id == "test_sell_1"


def test_buy_and_sell_match_exact():
    """
    Test matching a BUY and a SELL with equal quantity
    and a matching price scenario.
    """
    ob = OrderBook()

    # Add BUY
    buy_order = Order(
        order_id="test_buy_2", user_id="UserA", side="BUY", price=100.0, quantity=5
    )
    ob.add_order(buy_order)

    # Add SELL that matches (SELL price <= BUY price)
    sell_order = Order(
        order_id="test_sell_2", user_id="UserB", side="SELL", price=100.0, quantity=5
    )
    trades = ob.add_order(sell_order)

    # Expect a single trade
    assert len(trades) == 1
    trade = trades[0]
    assert trade.price == 100.0
    assert trade.quantity == 5
    assert trade.buy_order_id == "test_buy_2"
    assert trade.sell_order_id == "test_sell_2"

    # Both orders fully matched; no orders remain
    assert len(ob.buy_orders) == 0
    assert len(ob.sell_orders) == 0


def test_partial_fill():
    """
    Test a scenario where a BUY order is larger than the SELL order.
    Expect partial fill.
    """
    ob = OrderBook()

    # BUY 10 @ 100
    buy_order = Order(
        order_id="buy_partial", user_id="UserA", side="BUY", price=100.0, quantity=10
    )
    ob.add_order(buy_order)

    # SELL 6 @ 95
    sell_order = Order(
        order_id="sell_partial", user_id="UserB", side="SELL", price=95.0, quantity=6
    )
    trades = ob.add_order(sell_order)

    # We expect one trade for 6
    assert len(trades) == 1
    assert trades[0].quantity == 6
    assert (
        trades[0].price == 100.0
    )  # Usually matched at SELL's price or BUY's price; depends on logic
    # The SELL is fully filled; the BUY has 4 left
    assert len(ob.sell_orders) == 0
    assert len(ob.buy_orders) == 1
    assert ob.buy_orders[0].quantity == 4
