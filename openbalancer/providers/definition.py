from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TypeVar

from openbalancer.providers.base import ProviderAdapter

ProviderAdapterT = TypeVar("ProviderAdapterT", bound=ProviderAdapter)
ProviderFactory = Callable[..., ProviderAdapter]


@dataclass(frozen=True)
class ProviderDefinition:
    """Provider identity and configuration metadata, alongside its adapter factory."""

    name: str
    display_name: str
    adapter_factory: ProviderFactory
    credential_id: str
    default_model: str
    api_key_setting: str
    default_model_setting: str
    small_model_setting: str
    large_model_setting: str
    base_url: str | None = None
    small_model: str | None = None
    large_model: str | None = None
    cost_rank_setting: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)

    def create_adapter(self, **kwargs: object) -> ProviderAdapter:
        """Construct this provider's existing adapter with caller-supplied runtime values."""
        return self.adapter_factory(**kwargs)
