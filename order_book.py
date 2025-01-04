# order_book.py

from typing import List
import uuid
from sqlalchemy.orm import Session

from models import Order, Trade
from db_models import DbOrder, DbTrade
from database import SessionLocal
from logger import logger


class OrderBook:
    """
    Manages in-memory orders and performs matching between BUY and SELL orders.
    Provides methods for persisting order and trade data to the database.
    """

    def __init__(self):
        """
        Initialize the OrderBook with empty in-memory lists for buy orders,
        sell orders, and a trade history.
        """
        self.buy_orders: List[Order] = []
        self.sell_orders: List[Order] = []
        self.trade_history: List[Trade] = []

    def add_order(self, order: Order) -> List[Trade]:
        """
        Add an order to the order book. If it matches any existing orders
        (depending on side and price), create trade records.

        :param order: An Order object to be added or matched.
        :return: A list of Trade objects executed by this operation.
        """
        logger.info(f"New order received: {order}")
        if order.side.upper() == "BUY":
            trades = self._match_buy(order)
        else:
            trades = self._match_sell(order)

        # If there's still quantity left on the order,
        # that means partial or no fill. Persist it.
        self._save_or_update_order(order)
        # Also, save any new trades.
        for t in trades:
            self._save_trade(t)

        logger.info(f"Executed trades: {trades}")
        return trades

    def _match_buy(self, buy_order: Order) -> List[Trade]:
        """
        Match a BUY order against the best available SELL orders in ascending price order.

        :param buy_order: The BUY Order object to be matched.
        :return: A list of executed Trade objects from this matching session.
        """
        trades_executed = []
        while (
            buy_order.quantity > 0
            and len(self.sell_orders) > 0
            and buy_order.price >= self.sell_orders[0].price
        ):
            best_sell = self.sell_orders[0]
            trade_qty = min(buy_order.quantity, best_sell.quantity)
            trade_price = best_sell.price

            trade = Trade(
                trade_id=str(uuid.uuid4()),
                buy_order_id=buy_order.order_id,
                sell_order_id=best_sell.order_id,
                price=trade_price,
                quantity=trade_qty,
            )
            trades_executed.append(trade)
            self.trade_history.append(trade)

            # Update in-memory quantities
            buy_order.quantity -= trade_qty
            best_sell.quantity -= trade_qty

            logger.debug(
                f"Matching BUY: {buy_order.order_id} fills {trade_qty} "
                f"against SELL: {best_sell.order_id} at price {trade_price}"
            )

            # Update DB for partial fill right away
            self._save_trade(trade)
            self._save_or_update_order(buy_order)
            self._save_or_update_order(best_sell)

            # If the sell order is fully filled, remove it
            if best_sell.quantity == 0:
                self.sell_orders.pop(0)
            else:
                # Otherwise, update the in-memory sell order
                self.sell_orders[0] = best_sell

        # If there's any remainder of the buy order, keep it in the in-memory book
        if buy_order.quantity > 0:
            self.buy_orders.append(buy_order)
            self.buy_orders.sort(key=lambda o: o.price, reverse=True)

        return trades_executed

    def _match_sell(self, sell_order: Order) -> List[Trade]:
        """
        Match a SELL order against the best available BUY orders in descending price order.

        :param sell_order: The SELL Order object to be matched.
        :return: A list of executed Trade objects from this matching session.
        """
        trades_executed = []
        while (
            sell_order.quantity > 0
            and len(self.buy_orders) > 0
            and sell_order.price <= self.buy_orders[0].price
        ):
            best_buy = self.buy_orders[0]
            trade_qty = min(sell_order.quantity, best_buy.quantity)
            trade_price = best_buy.price

            trade = Trade(
                trade_id=str(uuid.uuid4()),
                buy_order_id=best_buy.order_id,
                sell_order_id=sell_order.order_id,
                price=trade_price,
                quantity=trade_qty,
            )
            trades_executed.append(trade)
            self.trade_history.append(trade)

            # Update in-memory quantities
            sell_order.quantity -= trade_qty
            best_buy.quantity -= trade_qty

            logger.debug(
                f"Matching SELL: {sell_order.order_id} fills {trade_qty} "
                f"against BUY: {best_buy.order_id} at price {trade_price}"
            )

            # Update DB for partial fill right away
            self._save_trade(trade)
            self._save_or_update_order(sell_order)
            self._save_or_update_order(best_buy)

            # If the buy order is fully filled, remove it
            if best_buy.quantity == 0:
                self.buy_orders.pop(0)
            else:
                self.buy_orders[0] = best_buy

        # If there's any remainder of the sell order, keep it in the in-memory book
        if sell_order.quantity > 0:
            self.sell_orders.append(sell_order)
            self.sell_orders.sort(key=lambda o: o.price)

        return trades_executed

    def _save_or_update_order(self, order: Order) -> None:
        """
        Perform an upsert (merge) for the given Order object in the database.
        """
        if not order.order_id:
            return

        with SessionLocal() as db:
            try:
                db_order = DbOrder(
                    id=order.order_id,
                    user_id=order.user_id,
                    side=order.side,
                    price=order.price,
                    quantity=order.quantity,
                    timestamp=order.timestamp,
                )
                db.merge(db_order)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error updating order {order.order_id} in DB: {e}")

    def _save_trade(self, trade: Trade) -> None:
        """
        Insert or merge the given Trade object in the database.
        """
        with SessionLocal() as db:
            try:
                logger.debug(f"Saving trade {trade.trade_id} to DB.")
                db_trade = DbTrade(
                    id=trade.trade_id,
                    buy_order_id=trade.buy_order_id,
                    sell_order_id=trade.sell_order_id,
                    price=trade.price,
                    quantity=trade.quantity,
                    timestamp=trade.timestamp,
                )
                db.merge(db_trade)  # Avoid duplicate insertion errors
                db.commit()
            except Exception as e:
                db.rollback()
            logger.error(f"Error inserting trade {trade.trade_id} in DB: {e}")

    def get_order_book(self):
        """
        Retrieve the current state of the in-memory order book.

        :return: A dictionary with "buy_orders" and "sell_orders" keys,
                 each containing a list of order dictionaries.
        """

        return {
            "buy_orders": [o.__dict__ for o in self.buy_orders],
            "sell_orders": [o.__dict__ for o in self.sell_orders],
        }

    def get_trade_history(self):
        """
        Retrieve the in-memory trade history.

        :return: A list of trade dictionaries representing all trades executed so far.
        """
        return [t.__dict__ for t in self.trade_history]
