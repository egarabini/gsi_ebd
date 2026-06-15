import reflex as rx

config = rx.Config(
    app_name="gsi_ebd",
    db_url="sqlite:///gsi_ebd.db",
    state_auto_setters=True,
)
