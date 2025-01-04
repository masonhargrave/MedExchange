# db_models.py

from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base
import uuid
import time


class DbOrder(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    side = Column(String)
    price = Column(Float)
    quantity = Column(Integer)
    timestamp = Column(Float, default=time.time)


class DbTrade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, index=True)
    buy_order_id = Column(String)
    sell_order_id = Column(String)
    price = Column(Float)
    quantity = Column(Integer)
    timestamp = Column(Float, default=time.time)
