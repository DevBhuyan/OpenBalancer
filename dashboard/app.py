"""Main OpenBalancer Dashboard Reflex application."""

from __future__ import annotations

import reflex as rx
from dashboard.state import AuthState, DashboardState
from dashboard.pages import login_page, dashboard_page


# Configure Reflex app
config = rx.Config(
    app_name="openbalancer_dashboard",
    env=rx.Env.DEV,
)


def index() -> rx.Component:
    """Root page - redirect to login or dashboard."""
    return rx.cond(
        AuthState.is_authenticated,
        dashboard_page(),
        login_page()
    )


# Create app
app = rx.App()

# Add pages
app.add_page(index, route="/")
app.add_page(
    dashboard_page,
    route="/dashboard",
    on_load=DashboardState.load_openbalancer_key
)

# Compile app
if __name__ == "__main__":
    config.compile()
