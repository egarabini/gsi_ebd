import reflex as rx
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

config = rx.Config(
    app_name="gsi_ebd",
    db_url=os.getenv("DATABASE_URL", "sqlite:///gsi_ebd.db"),
    state_auto_setters=True,
)
