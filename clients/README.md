# OpenBalancer Integration Tests

This directory contains integration tests for OpenBalancer that demonstrate how to use the API with various client libraries.

## Prerequisites

- OpenBalancer server running on `http://127.0.0.1:8000`
- API key generated and saved in `.env` file in the project root
- Required Python packages: `requests`, `openai`, `litellm`

## API Key Authentication

All tests now require an OpenBalancer API key for authentication. The API key is automatically loaded from:

1. `OPENBALANCER_API_KEY` environment variable (if set)
2. `.env` file in the project root (format: `OPENBALANCER_API_KEY=obk_...`)

The API key is passed as an `Authorization: Bearer <key>` header in all requests.

### Getting Your API Key

If you haven't already generated an API key:

```bash
# Start the server
python -m uvicorn openbalancer.app:app --reload

# The API key is automatically generated and printed on startup:
# 🔑 NEW OpenBalancer API Key Generated
# API Key: obk_1a2a1d9d34b5400c5042943a05bf6930
# ✓ Key automatically saved to: .env
```

## Test Files

### `config.py` - Configuration & API Key Loading

Helper module that loads the OpenBalancer API key from environment or `.env` file.

```python
from config import get_api_key, get_api_headers

# Get just the API key
key = get_api_key()  # Returns: "obk_1a2a1d9d34b5400c5042943a05bf6930"

# Get headers dict with Authorization header
headers = get_api_headers()  # Returns: {"Authorization": "Bearer obk_...", "Content-Type": "application/json"}
```

### `requests_test.py` - Requests Library Tests

Tests using the standard `requests` library with manual header configuration.

```bash
python -c "from requests_test import test_requests_completions; test_requests_completions()"
```

**Features:**
- ✅ Non-streaming completion requests
- ✅ Streaming responses with SSE parsing
- ✅ Raw stream line inspection

### `openai_test.py` - OpenAI Client Tests

Tests using the official OpenAI Python client library configured to work with OpenBalancer.

```bash
python -c "from openai_test import test_openai_response; test_openai_response()"
```

**Features:**
- ✅ OpenAI-compatible chat completions
- ✅ Streaming responses with automatic parsing
- ✅ Full response object introspection

### `litellm_test.py` - LiteLLM Tests

Tests using LiteLLM's unified LLM interface.

```bash
python -c "from litellm_test import test_litellm_completion; test_litellm_completion()"
```

**Features:**
- ✅ Basic completions
- ✅ Streaming responses
- ✅ Server-sent events (SSE) parsing

### `load_test.py` - Load Testing & Stress Testing

Concurrent load testing tool to measure throughput, latency, and provider distribution.

```bash
# Run 200 concurrent requests with 50 workers
python load_test.py 200 50

# Run 1000 requests with 100 workers
python load_test.py 1000 100

# Default: 200 requests, 500 max workers
python load_test.py
```

**Output:**
- Success/failure counts
- Requests per second (RPS)
- Provider distribution across multiple providers
- Failure examples with error details

### `main.py` - Full Test Suite

Runs all integration tests sequentially and concurrently.

```bash
# Run all tests (output suppressed for cleanliness)
python main.py

# Expected output:
# ✓ test_litellm_completion
# ✓ test_litellm_stream
# ✓ test_litellm_stream_sse
# ✓ test_openai_response
# ✓ test_openai_stream
# ✓ test_requests_completions
# ✓ test_requests_stream
# ✓ test_requests_stream_raw
```

## Usage Examples

### 1. Basic Request with Requests Library

```python
from requests_test import test_requests_completions

# Make a chat completion request with API key authentication
test_requests_completions()
```

### 2. Using OpenAI Client

```python
from openai_test import test_openai_response

# Use OpenAI-compatible endpoint
test_openai_response()
```

### 3. LiteLLM Integration

```python
from litellm_test import test_litellm_completion

# Use LiteLLM with OpenBalancer
test_litellm_completion()
```

### 4. Load Testing

```bash
# Stress test with 100 concurrent requests
python load_test.py 100

# Output:
# Success: 100
# Failed: 0
# Time: 12.34s
# RPS: 8.10
# 
# Provider Distribution
# SiliconFlow: 50
# Groq: 30
# OpenRouter: 20
```

### 5. Streaming Responses

```python
from requests_test import test_requests_stream

# Stream a response token by token
test_requests_stream()
```

## Manual Testing

### Test without API key (should fail):

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "hello"}]}'

# Returns 401 Unauthorized
```

### Test with valid API key:

```bash
# Get your API key from .env
API_KEY=$(grep OPENBALANCER_API_KEY .env | cut -d= -f2)

# Make request with API key
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "hello"}]}'

# Returns 200 with chat response
```

## Troubleshooting

### "API key not found" Error

**Solution:** Ensure OpenBalancer is running and `.env` file exists in the project root with `OPENBALANCER_API_KEY=obk_...`

```bash
# Check if .env exists
cat ../.env | grep OPENBALANCER_API_KEY

# Or set environment variable
export OPENBALANCER_API_KEY=obk_1a2a1d9d34b5400c5042943a05bf6930
```

### Tests failing with 401 Unauthorized

**Solution:** Verify your API key is correct and the server is running:

```bash
# Check server status
curl http://localhost:8000/health

# Verify API key
python config.py
```

### Connection Refused

**Solution:** Start the OpenBalancer server:

```bash
cd /path/to/project
python -m uvicorn openbalancer.app:app --host 0.0.0.0 --port 8000
```

## API Key Security Notes

⚠️ **Important:**

1. **Keep your API key confidential** - Treat it like a password
2. **Don't commit `.env` to git** - Add `.env` to `.gitignore`
3. **Use HTTPS in production** - Always use TLS/SSL for API requests
4. **Rotate keys regularly** - Consider regenerating keys periodically
5. **Monitor usage** - Check for unauthorized access patterns

## Examples with Different Client Libraries

### Using OpenAI Client

```python
from openai import OpenAI
from config import get_api_key

client = OpenAI(
    api_key=get_api_key(),
    base_url="http://127.0.0.1:8000/v1"
)

response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### Using LiteLLM

```python
from litellm import completion
from config import get_api_key

response = completion(
    model="openai/auto",
    api_base="http://127.0.0.1:8000/v1",
    api_key=get_api_key(),
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### Using Requests Library

```python
import requests
from config import get_api_headers

response = requests.post(
    "http://127.0.0.1:8000/v1/chat/completions",
    json={
        "model": "auto",
        "messages": [{"role": "user", "content": "Hello!"}]
    },
    headers=get_api_headers()
)
print(response.json()["choices"][0]["message"]["content"])
```

## Testing Results

After updating all test files to use API key authentication, the following tests pass:

| Test | Status |
|------|--------|
| requests completions | ✅ PASS |
| requests streaming | ✅ PASS |
| requests raw stream | ✅ PASS |
| OpenAI response | ✅ PASS |
| OpenAI streaming | ✅ PASS |
| LiteLLM completion | ✅ PASS |
| LiteLLM streaming | ✅ PASS |
| LiteLLM SSE | ✅ PASS |
| Load test (concurrent) | ✅ PASS |

## Support

For issues or questions:

1. Check that OpenBalancer is running (`curl http://localhost:8000/health`)
2. Verify your API key is set (`python config.py`)
3. Review the API key authentication docs: `../API_KEY_AUTHENTICATION.md`
4. Check OpenBalancer logs for error details

## Next Steps

- Configure rate limiting per API key
- Set up usage tracking and quotas
- Implement API key rotation
- Add monitoring and alerting
