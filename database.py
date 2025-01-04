# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Example: use SQLite in the current directory named 'exchange.db'
DB_URL = os.getenv("DATABASE_URL", "sqlite:///exchange.db")

engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
