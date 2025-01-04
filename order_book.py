# order_book.py

from typing import List
import uuid
from sqlalchemy.orm import Session

from models import Order, Trade
from db_models import DbOrder, DbTrade
from database import SessionLocal


class OrderBook:
    def __init__(self):
        self.buy_orders: List[Order] = []
        self.sell_orders: List[Order] = []
        self.trade_history: List[Trade] = []

    def add_order(self, order: Order) -> List[Trade]:
        trades = []
        if order.side.upper() == "BUY":
            trades = self._match_buy(order)
        else:
            trades = self._match_sell(order)

        # Persist the new order (if any quantity remains) and trades
        self._persist_to_db(order, trades)
        return trades

    def _match_buy(self, buy_order: Order) -> List[Trade]:
        trades_executed = []
        while (
            buy_order.quantity > 0
            and len(self.sell_orders) > 0
            and buy_order.price >= self.sell_orders[0].price
        ):
            best_sell = self.sell_orders[0]

            # Determine how much can be traded
            trade_qty = min(buy_order.quantity, best_sell.quantity)
            trade_price = best_sell.price

            # Create the trade
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                buy_order_id=buy_order.order_id,
                sell_order_id=best_sell.order_id,
                price=trade_price,
                quantity=trade_qty,
            )
            trades_executed.append(trade)
            self.trade_history.append(trade)

            # Decrement
            buy_order.quantity -= trade_qty
            best_sell.quantity -= trade_qty

            # Remove or update the matched sell order
            if best_sell.quantity == 0:
                self.sell_orders.pop(0)
            else:
                self.sell_orders[0] = best_sell

        if buy_order.quantity > 0:
            self.buy_orders.append(buy_order)
            self.buy_orders.sort(key=lambda o: o.price, reverse=True)

        return trades_executed

    def _match_sell(self, sell_order: Order) -> List[Trade]:
        trades_executed = []
        while (
            sell_order.quantity > 0
            and len(self.buy_orders) > 0
            and sell_order.price <= self.buy_orders[0].price
        ):
            best_buy = self.buy_orders[0]

            # Determine how much can be traded
            trade_qty = min(sell_order.quantity, best_buy.quantity)
            trade_price = best_buy.price

            # Create the trade
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                buy_order_id=best_buy.order_id,
                sell_order_id=sell_order.order_id,
                price=trade_price,
                quantity=trade_qty,
            )
            trades_executed.append(trade)
            self.trade_history.append(trade)

            # Decrement
            sell_order.quantity -= trade_qty
            best_buy.quantity -= trade_qty

            # Remove or update the matched buy order
            if best_buy.quantity == 0:
                self.buy_orders.pop(0)
            else:
                self.buy_orders[0] = best_buy

        if sell_order.quantity > 0:
            self.sell_orders.append(sell_order)
            self.sell_orders.sort(key=lambda o: o.price)

        return trades_executed

    def _persist_to_db(self, order: Order, trades: List[Trade]) -> None:
        """
        Persists the (potentially updated) order and generated trades to the DB.
        """
        db: Session = SessionLocal()
        try:
            # If order still has quantity > 0, that means it's partially or not filled.
            if order.quantity > 0:
                db_order = DbOrder(
                    id=order.order_id,
                    user_id=order.user_id,
                    side=order.side,
                    price=order.price,
                    quantity=order.quantity,
                    timestamp=order.timestamp,
                )
                # Merge or add new record
                db.merge(db_order)

            # For each executed trade, save to DB
            for t in trades:
                db_trade = DbTrade(
                    id=t.trade_id,
                    buy_order_id=t.buy_order_id,
                    sell_order_id=t.sell_order_id,
                    price=t.price,
                    quantity=t.quantity,
                    timestamp=t.timestamp,
                )
                db.add(db_trade)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"DB Error: {e}")
        finally:
            db.close()

    def get_order_book(self):
        return {
            "buy_orders": [o.__dict__ for o in self.buy_orders],
            "sell_orders": [o.__dict__ for o in self.sell_orders],
        }

    def get_trade_history(self):
        return [t.__dict__ for t in self.trade_history]
