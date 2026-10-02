from __future__ import annotations

from collections.abc import Iterable

from openbalancer.providers.definition import ProviderDefinition


class ProviderRegistry:
    """Small in-process registry of provider definitions."""

    def __init__(self, definitions: Iterable[ProviderDefinition] = ()) -> None:
        self._definitions: dict[str, ProviderDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: ProviderDefinition) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"Provider {definition.name!r} is already registered")
        self._definitions[definition.name] = definition

    def get(self, provider_name: str) -> ProviderDefinition:
        try:
            return self._definitions[provider_name]
        except KeyError:
            raise KeyError(f"Unknown provider {provider_name!r}") from None

    def all(self) -> tuple[ProviderDefinition, ...]:
        return tuple(self._definitions.values())

    def contains(self, provider_name: str) -> bool:
        return provider_name in self._definitions

    def is_registered(self, provider_name: str) -> bool:
        return self.contains(provider_name)
