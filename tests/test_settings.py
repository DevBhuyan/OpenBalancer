from openbalancer.settings import Settings


def test_quickstart_defaults_load_available_keys():
    settings = Settings.with_quickstart_defaults()

    assert settings.groq_api_key
    assert settings.openrouter_api_key
    assert settings.cerebras_api_key
    assert settings.gemini_api_key
