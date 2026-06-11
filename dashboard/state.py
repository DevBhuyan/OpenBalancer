"""State management for the OpenBalancer Dashboard using Reflex."""

from __future__ import annotations

import os
import httpx
from typing import Optional

import reflex as rx


# Get API URL from environment or derive from browser location
def get_api_url() -> str:
    """Get the API URL, preferring environment variable or current host."""
    # Check environment variable first
    if env_api_url := os.getenv("OPENBALANCER_API_URL"):
        return env_api_url
    
    # Fallback to localhost
    return "http://localhost:8000"


API_BASE_URL = get_api_url()


class AuthState(rx.State):
    """Authentication state."""
    
    email: str = ""
    password: str = ""
    login_error: str = ""
    is_loading: bool = False
    access_token: Optional[str] = None
    user_id: Optional[str] = None
    is_authenticated: bool = False
    
    async def login(self):
        """Handle user login."""
        self.is_loading = True
        self.login_error = ""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/auth/login",
                    json={
                        "email": self.email,
                        "password": self.password
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data["access_token"]
                    self.user_id = data["user_id"]
                    self.is_authenticated = True
                    self.email = data["email"]
                    self.password = ""
                    return rx.redirect("/dashboard")
                else:
                    error_data = response.json()
                    self.login_error = error_data.get("detail", "Login failed")
        except Exception as e:
            self.login_error = f"Connection error: {str(e)}"
        finally:
            self.is_loading = False
    
    async def register(self):
        """Handle user registration."""
        self.is_loading = True
        self.login_error = ""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/auth/register",
                    json={
                        "email": self.email,
                        "password": self.password
                    }
                )
                
                if response.status_code == 201:
                    data = response.json()
                    self.access_token = data["access_token"]
                    self.user_id = data["user_id"]
                    self.is_authenticated = True
                    self.email = data["email"]
                    self.password = ""
                    return rx.redirect("/dashboard")
                else:
                    error_data = response.json()
                    self.login_error = error_data.get("detail", "Registration failed")
        except Exception as e:
            self.login_error = f"Connection error: {str(e)}"
        finally:
            self.is_loading = False
    
    async def logout(self):
        """Handle user logout."""
        if self.access_token:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{API_BASE_URL}/auth/logout",
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
            except Exception:
                pass  # Ignore errors during logout
        
        self.access_token = None
        self.user_id = None
        self.is_authenticated = False
        self.email = ""
        self.password = ""
        return rx.redirect("/")


class DashboardState(AuthState):
    """Dashboard state, inherits from AuthState."""
    
    # Provider credentials
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    cerebras_api_key: str = ""
    gemini_api_key: str = ""
    huggingface_api_key: str = ""
    
    # UI state
    provider_keys_loading: bool = False
    provider_keys_error: str = ""
    provider_keys_success: str = ""
    openbalancer_key: Optional[str] = None
    openbalancer_key_loading: bool = False
    
    # Quickstart state
    selected_language: str = "python"
    quickstart_code: str = ""
    quickstart_loading: bool = False
    
    # Provider health
    provider_health: dict = {}
    health_loading: bool = False
    
    async def load_provider_keys(self):
        """Load user's provider keys."""
        if not self.access_token:
            return
        
        self.provider_keys_loading = True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/api/user/provider-keys",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    providers = data.get("providers", {})
                    # Map the masked values back to the form fields
                    # Note: We can't get the actual values back, so we keep existing values
                    self.provider_keys_success = "Provider keys loaded"
        except Exception as e:
            self.provider_keys_error = f"Failed to load provider keys: {str(e)}"
        finally:
            self.provider_keys_loading = False
    
    async def save_provider_keys(self):
        """Save provider keys to the dashboard."""
        if not self.access_token:
            self.provider_keys_error = "Not authenticated"
            return
        
        self.provider_keys_loading = True
        self.provider_keys_error = ""
        self.provider_keys_success = ""
        
        try:
            payload = {}
            if self.groq_api_key:
                payload["groq_api_key"] = self.groq_api_key
            if self.openrouter_api_key:
                payload["openrouter_api_key"] = self.openrouter_api_key
            if self.cerebras_api_key:
                payload["cerebras_api_key"] = self.cerebras_api_key
            if self.gemini_api_key:
                payload["gemini_api_key"] = self.gemini_api_key
            if self.huggingface_api_key:
                payload["huggingface_api_key"] = self.huggingface_api_key
            
            if not payload:
                self.provider_keys_error = "Please enter at least one provider API key"
                return
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}/api/user/provider-keys",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                
                if response.status_code == 200:
                    self.provider_keys_success = "Provider credentials saved successfully!"
                    # Clear the input fields
                    self.groq_api_key = ""
                    self.openrouter_api_key = ""
                    self.cerebras_api_key = ""
                    self.gemini_api_key = ""
                    self.huggingface_api_key = ""
                    # Try to load the OpenBalancer key
                    await self.load_openbalancer_key()
                else:
                    error_data = response.json()
                    self.provider_keys_error = error_data.get("detail", "Failed to save provider credentials")
        except Exception as e:
            self.provider_keys_error = f"Connection error: {str(e)}"
        finally:
            self.provider_keys_loading = False
    
    async def load_openbalancer_key(self):
        """Load user's OpenBalancer API key."""
        if not self.access_token:
            return
        
        self.openbalancer_key_loading = True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/api/user/openbalancer-key",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.openbalancer_key = data["api_key"]
        except Exception as e:
            # Silently fail if key not found
            self.openbalancer_key = None
        finally:
            self.openbalancer_key_loading = False
    
    async def get_quickstart_code(self):
        """Get quickstart code for the selected language."""
        if not self.access_token:
            return
        
        self.quickstart_loading = True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/api/quickstart-code?language={self.selected_language}",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.quickstart_code = data["code"]
        except Exception as e:
            self.quickstart_code = f"Error loading quickstart code: {str(e)}"
        finally:
            self.quickstart_loading = False
    
    async def load_provider_health(self):
        """Load provider health status."""
        if not self.access_token:
            return
        
        self.health_loading = True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/api/providers/health",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.provider_health = data
        except Exception as e:
            self.provider_health = {"error": str(e)}
        finally:
            self.health_loading = False
