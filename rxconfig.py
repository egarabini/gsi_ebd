import reflex as rx
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

config = rx.Config(
    app_name="gsi_ebd",
    db_url=os.getenv("DATABASE_URL", "sqlite:///gsi_ebd.db"),
    # DESLIGADO na DEM-202610-002: com setters automaticos, o cliente dispara
    # set_current_user_role(1) por evento direto e vira ADMIN para o servidor -
    # toda a guarda de papel (utils/rbac.py) passaria a proteger um estado que o
    # atacante controla. Os setters explicitos existem so para campo de
    # formulario, e o Reflex 1.0 remove esta flag de qualquer forma.
    state_auto_setters=False,
)
