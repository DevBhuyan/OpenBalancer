from openbalancer.models import ChatCompletionRequest
from openbalancer.providers.gemini import GeminiProvider


def test_gemini_request_translation():
    provider = GeminiProvider(api_key="test", default_model="gemini-flash-latest", timeout_seconds=1)
    request = ChatCompletionRequest(
        messages=[
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hello"},
        ],
        temperature=0.2,
        max_tokens=64,
    )

    body = provider._to_gemini_body(request)

    assert body["system_instruction"]["parts"][0]["text"] == "Be concise."
    assert body["contents"][0]["role"] == "user"
    assert body["contents"][0]["parts"][0]["text"] == "Hello"
    assert body["generationConfig"]["maxOutputTokens"] == 64
