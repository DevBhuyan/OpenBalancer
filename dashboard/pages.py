"""Page components for the OpenBalancer Dashboard."""

from __future__ import annotations

import reflex as rx
from dashboard.state import AuthState, DashboardState


def login_page() -> rx.Component:
    """Login page component."""
    return rx.box(
        rx.vstack(
            rx.heading("OpenBalancer Dashboard", size="xl"),
            rx.text("Log in to manage your API keys"),
            
            rx.cond(
                AuthState.login_error != "",
                rx.box(
                    rx.text(
                        AuthState.login_error,
                        color="red"
                    ),
                    padding="1rem",
                    border_radius="0.5rem",
                    background_color="#fee"
                )
            ),
            
            rx.input(
                placeholder="Email",
                value=AuthState.email,
                on_change=AuthState.set_email,
                width="100%",
                is_disabled=AuthState.is_loading
            ),
            
            rx.input(
                placeholder="Password",
                type_="password",
                value=AuthState.password,
                on_change=AuthState.set_password,
                width="100%",
                is_disabled=AuthState.is_loading
            ),
            
            rx.button(
                "Login",
                on_click=AuthState.login,
                width="100%",
                is_loading=AuthState.is_loading
            ),
            
            rx.text(
                "Don't have an account? ",
                rx.button(
                    "Sign up",
                    on_click=AuthState.register,
                    variant="link",
                    color_scheme="blue",
                    is_loading=AuthState.is_loading
                ),
                display="flex",
                align_items="center",
                gap="0.5rem"
            ),
            
            width="400px",
            spacing="1rem",
            border_radius="0.5rem",
            border="1px solid #ddd",
            padding="2rem",
        ),
        display="flex",
        justify_content="center",
        align_items="center",
        min_height="100vh",
        background_color="#f5f5f5"
    )


def navbar() -> rx.Component:
    """Navigation bar component."""
    return rx.box(
        rx.hstack(
            rx.heading("OpenBalancer", size="lg"),
            rx.spacer(),
            rx.button(
                "Logout",
                on_click=DashboardState.logout,
                color_scheme="red",
                variant="ghost"
            ),
            width="100%",
            padding="1rem 2rem",
            border_bottom="1px solid #ddd",
        ),
        background_color="white"
    )


def provider_keys_section() -> rx.Component:
    """Provider API keys management section."""
    return rx.box(
        rx.vstack(
            rx.heading("Connect Providers", size="md"),
            rx.text("Add your provider API keys below. Your keys are stored securely."),
            
            rx.cond(
                DashboardState.provider_keys_error != "",
                rx.box(
                    rx.text(DashboardState.provider_keys_error, color="red"),
                    padding="1rem",
                    border_radius="0.5rem",
                    background_color="#fee"
                )
            ),
            
            rx.cond(
                DashboardState.provider_keys_success != "",
                rx.box(
                    rx.text(DashboardState.provider_keys_success, color="green"),
                    padding="1rem",
                    border_radius="0.5rem",
                    background_color="#efe"
                )
            ),
            
            rx.vstack(
                rx.heading("Groq", size="sm"),
                rx.input(
                    placeholder="Groq API Key (gsk_...)",
                    value=DashboardState.groq_api_key,
                    on_change=DashboardState.set_groq_api_key,
                    width="100%",
                    type_="password"
                ),
                spacing="0.5rem"
            ),
            
            rx.vstack(
                rx.heading("OpenRouter", size="sm"),
                rx.input(
                    placeholder="OpenRouter API Key (sk_...)",
                    value=DashboardState.openrouter_api_key,
                    on_change=DashboardState.set_openrouter_api_key,
                    width="100%",
                    type_="password"
                ),
                spacing="0.5rem"
            ),
            
            rx.vstack(
                rx.heading("Cerebras", size="sm"),
                rx.input(
                    placeholder="Cerebras API Key (csk_...)",
                    value=DashboardState.cerebras_api_key,
                    on_change=DashboardState.set_cerebras_api_key,
                    width="100%",
                    type_="password"
                ),
                spacing="0.5rem"
            ),
            
            rx.vstack(
                rx.heading("Google Gemini", size="sm"),
                rx.input(
                    placeholder="Gemini API Key (AIzaSy...)",
                    value=DashboardState.gemini_api_key,
                    on_change=DashboardState.set_gemini_api_key,
                    width="100%",
                    type_="password"
                ),
                spacing="0.5rem"
            ),
            
            rx.vstack(
                rx.heading("Hugging Face", size="sm"),
                rx.input(
                    placeholder="Hugging Face API Key (hf_...)",
                    value=DashboardState.huggingface_api_key,
                    on_change=DashboardState.set_huggingface_api_key,
                    width="100%",
                    type_="password"
                ),
                spacing="0.5rem"
            ),
            
            rx.button(
                "Save Provider Credentials",
                on_click=DashboardState.save_provider_keys,
                width="100%",
                is_loading=DashboardState.provider_keys_loading,
                color_scheme="blue"
            ),
            
            width="100%",
            spacing="1rem",
            border_radius="0.5rem",
            border="1px solid #ddd",
            padding="2rem"
        )
    )


def openbalancer_key_section() -> rx.Component:
    """OpenBalancer API key display section."""
    return rx.box(
        rx.vstack(
            rx.heading("Your OpenBalancer API Key", size="md"),
            
            rx.cond(
                DashboardState.openbalancer_key_loading,
                rx.text("Loading...")
            ),
            
            rx.cond(
                DashboardState.openbalancer_key != None,
                rx.vstack(
                    rx.box(
                        rx.text(
                            DashboardState.openbalancer_key,
                            font_family="monospace",
                            font_size="0.9rem",
                            word_break="break-all"
                        ),
                        padding="1rem",
                        border_radius="0.5rem",
                        background_color="#f5f5f5",
                        border="1px solid #ddd",
                        width="100%"
                    ),
                    rx.button(
                        "Copy to Clipboard",
                        on_click=lambda: rx.window_alert("Copy functionality not yet implemented"),
                        size="sm"
                    ),
                    spacing="0.5rem"
                ),
                rx.box(
                    rx.text(
                        "Add provider credentials to generate your OpenBalancer API key",
                        color="gray"
                    ),
                    padding="1rem",
                    border_radius="0.5rem",
                    background_color="#f9f9f9"
                )
            ),
            
            width="100%",
            spacing="1rem",
            border_radius="0.5rem",
            border="1px solid #ddd",
            padding="2rem"
        )
    )


def quickstart_section() -> rx.Component:
    """Quickstart code snippets section."""
    return rx.box(
        rx.vstack(
            rx.heading("Quickstart Code", size="md"),
            rx.text("Choose your preferred language to see usage examples"),
            
            rx.hstack(
                rx.button(
                    "cURL",
                    on_click=lambda: DashboardState.set_selected_language("curl"),
                    color_scheme=rx.cond(DashboardState.selected_language == "curl", "blue", "gray"),
                    variant=rx.cond(DashboardState.selected_language == "curl", "solid", "outline")
                ),
                rx.button(
                    "Python",
                    on_click=lambda: DashboardState.set_selected_language("python"),
                    color_scheme=rx.cond(DashboardState.selected_language == "python", "blue", "gray"),
                    variant=rx.cond(DashboardState.selected_language == "python", "solid", "outline")
                ),
                rx.button(
                    "Python (OpenAI)",
                    on_click=lambda: DashboardState.set_selected_language("python-openai"),
                    color_scheme=rx.cond(DashboardState.selected_language == "python-openai", "blue", "gray"),
                    variant=rx.cond(DashboardState.selected_language == "python-openai", "solid", "outline")
                ),
                rx.button(
                    "TypeScript",
                    on_click=lambda: DashboardState.set_selected_language("typescript"),
                    color_scheme=rx.cond(DashboardState.selected_language == "typescript", "blue", "gray"),
                    variant=rx.cond(DashboardState.selected_language == "typescript", "solid", "outline")
                ),
                spacing="0.5rem",
                flex_wrap="wrap"
            ),
            
            rx.cond(
                DashboardState.quickstart_loading,
                rx.text("Loading..."),
                rx.box(
                    rx.code(
                        DashboardState.quickstart_code,
                        display="block",
                        font_size="0.85rem",
                        overflow_x="auto",
                        width="100%"
                    ),
                    padding="1rem",
                    border_radius="0.5rem",
                    background_color="#f5f5f5",
                    border="1px solid #ddd",
                    width="100%"
                )
            ),
            
            width="100%",
            spacing="1rem",
            border_radius="0.5rem",
            border="1px solid #ddd",
            padding="2rem"
        )
    )


def provider_health_section() -> rx.Component:
    """Provider health status section."""
    return rx.box(
        rx.vstack(
            rx.heading("Provider Status", size="md"),
            
            rx.cond(
                DashboardState.health_loading,
                rx.text("Loading..."),
                rx.cond(
                    DashboardState.provider_health != {},
                    rx.vstack(
                        rx.foreach(
                            rx.cond(
                                "providers" in DashboardState.provider_health,
                                DashboardState.provider_health["providers"],
                                []
                            ),
                            lambda provider: rx.hstack(
                                rx.text(provider["name"], weight="bold"),
                                rx.badge(
                                    provider["status"],
                                    color_scheme=rx.cond(
                                        provider["status"] == "healthy",
                                        "green",
                                        rx.cond(provider["status"] == "degraded", "orange", "red")
                                    )
                                ),
                                width="100%",
                                justify_content="space-between"
                            )
                        ),
                        width="100%"
                    ),
                    rx.text("No provider data available")
                )
            ),
            
            width="100%",
            spacing="1rem",
            border_radius="0.5rem",
            border="1px solid #ddd",
            padding="2rem"
        )
    )


def dashboard_page() -> rx.Component:
    """Main dashboard page."""
    return rx.box(
        rx.vstack(
            navbar(),
            
            rx.box(
                rx.vstack(
                    rx.heading("Welcome!", size="lg"),
                    rx.text(f"Connected as: {AuthState.email}"),
                    
                    provider_keys_section(),
                    
                    rx.hstack(
                        openbalancer_key_section(),
                        provider_health_section(),
                        spacing="2rem",
                        width="100%"
                    ),
                    
                    quickstart_section(),
                    
                    spacing="2rem",
                    padding="2rem",
                    max_width="1200px",
                    margin="0 auto",
                    width="100%"
                ),
                width="100%"
            ),
            
            width="100%",
            spacing="0",
            min_height="100vh"
        ),
        width="100%"
    )
