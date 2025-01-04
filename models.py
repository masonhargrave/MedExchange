import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Order:
    order_id: str
    user_id: str
    side: str  # "BUY" or "SELL"
    price: float
    quantity: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class Trade:
    trade_id: str
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: int
    timestamp: float = field(default_factory=time.time)
