# logger.py
import logging

# Configure root logger (all modules can use this)
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more verbosity
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger("MedExchangeLogger")
