# config.py
import os

from dotenv import load_dotenv

# Load environment variables from .env file in the project root
dotenv_path = os.path.join(
    os.path.dirname(__file__), ".env"
)  # Construct path relative to config.py
load_dotenv(dotenv_path=dotenv_path)
print(f"Loading .env from: {dotenv_path}")  # Debug print


class Settings:
    PROJECT_NAME: str = "Modular Trading Backend"
    API_V1_STR: str = "/api/v1"

    # --- Load Angel One Credentials Safely ---
    ANGELONE_API_KEY: str | None = os.getenv("ANGELONE_API_KEY")
    ANGELONE_CLIENT_ID: str | None = os.getenv("ANGELONE_CLIENT_ID")
    ANGELONE_PASSWORD: str | None = os.getenv("ANGELONE_PASSWORD")
    ANGELONE_TOTP_SECRET: str | None = os.getenv("ANGELONE_TOTP_SECRET")

    # --- Broker Configurations Dictionary ---
    # This structure allows easily adding more brokers later
    BROKER_CONFIG = {
        "mock_broker": {
            # Configuration for the paper trading mock broker (if any)
            "initial_balance": 100000.0,
        },
        "angelone": {
            # Configuration specific to Angel One, loaded from environment
            "api_key": ANGELONE_API_KEY,
            "client_id": ANGELONE_CLIENT_ID,
            "password": ANGELONE_PASSWORD,
            "totp_secret": ANGELONE_TOTP_SECRET,
        },
        # Example for another broker (credentials would also come from .env)
        # "other_broker": {
        #     "api_key": os.getenv("OTHER_BROKER_API_KEY"),
        #     "secret": os.getenv("OTHER_BROKER_SECRET"),
        #     "base_url": "https://api.otherbroker.com"
        # }
    }


settings = Settings()

# --- Basic Logging Setup ---
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Validate Essential Config ---
# Ensure critical Angel One config is present if intended to be used
if not all(
    [
        settings.ANGELONE_API_KEY,
        settings.ANGELONE_CLIENT_ID,
        settings.ANGELONE_PASSWORD,
        settings.ANGELONE_TOTP_SECRET,
    ]
):
    logger.warning(
        "One or more Angel One credentials (API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET) are missing in the environment variables (.env file). Angel One integration will likely fail."
    )
else:
    logger.info("Angel One credentials appear to be loaded from environment.")
