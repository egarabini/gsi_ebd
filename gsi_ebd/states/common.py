from typing import List, Optional

import reflex as rx

from ..models.user import User, Role
from ..models.progress import Progress


class CommonState(rx.State):
    sidebar_open: bool = True

    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    @rx.var
    def sidebar_width(self) -> str:
        return "250px" if self.sidebar_open else "60px"
