# OpenBalancer

OpenBalancer is an open-source LLM routing and load-balancing platform designed to maximize free-tier and low-cost AI inference providers.

This repository now contains a working MVP:

* OpenAI-compatible `POST /v1/chat/completions`
* Provider fallback routing
* Multiple routing policies
* Runtime provider health state
* `GET /health`
* `GET /v1/models`
* Adapters for Groq, OpenRouter, Hugging Face, Cerebras, and Gemini

## Quick Start

Install dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the API:

```bash
python -m openbalancer
```

Send a request:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Say hello from OpenBalancer"}]
  }'
```

Force a provider:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "groq",
    "model": "auto",
    "messages": [{"role": "user", "content": "Use Groq through OpenBalancer"}]
  }'
```

The MVP loads credentials from environment variables first, then falls back to files in `quickstart_curls_and_api_keys`.

Supported environment variables:

* `GROQ_API_KEY`
* `OPENROUTER_API_KEY`
* `CEREBRAS_API_KEY`
* `GEMINI_API_KEY` or `GOOGLE_API_KEY`
* `HF_API_KEY` or `HF_TOKEN`
* `OPENROUTER_ARTIFICIAL_MAX_CONCURRENT` - defaults to `5`; set to `0` to disable the test limiter
* `OPENROUTER_ARTIFICIAL_RPM` - defaults to `0`; set a positive value to simulate an OpenRouter requests-per-minute cap
* `ROUTER_MAX_WAIT_SECONDS` - defaults to `30`; how long one request may wait/retry before failing
* `ROUTER_RETRY_SLEEP_SECONDS` - defaults to `0.15`; minimum sleep between retry rounds
* `PROVIDER_COOLDOWN_SECONDS` - defaults to `2`; cooldown for rate-limit/queue errors
* `PROVIDER_UNAVAILABLE_COOLDOWN_SECONDS` - defaults to `5`; cooldown for temporary provider unavailable errors

## Routing Policies

Use `model: "auto"` to let OpenBalancer choose the provider-specific default model.

Automatic model profiles:

* `auto` - provider default
* `auto:small` - smaller/lighter provider model where configured
* `auto:large` - larger provider model where configured

Routing modes:

* `fallback` - configured order: OpenRouter, Groq, Hugging Face, Cerebras, Gemini
* `fastest` - lowest observed successful latency
* `cheapest` - lowest configured cost rank
* `stable` - lowest observed failure rate and no active cooldown
* `slow_and_stable` - alias for `stable`
* `balanced` - blends cooldown, failure rate, latency, and cost rank

Example:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto:small",
    "routing": "stable",
    "messages": [{"role": "user", "content": "Say hello from a stable small model"}]
  }'
```

## Load Balancing Test

OpenRouter has an artificial limiter enabled by default so concurrent test traffic can spill over to other providers.
The default fallback order is OpenRouter first, then Groq, Hugging Face, Cerebras, and Gemini.
When all providers are saturated, OpenBalancer waits and retries until `ROUTER_MAX_WAIT_SECONDS` is reached.

Run:

```bash
python clients/load_test.py
```

Check limiter state:

```bash
curl http://localhost:8000/health
```

## Vision

Developers should not need to manually switch between Gemini, Groq, OpenRouter, Cerebras, HuggingFace, TogetherAI, Ollama, and other providers.

OpenBalancer automatically routes requests based on:

* Model capabilities
* Available quota
* Rate limits
* Token limits
* Latency
* Cost
* Reliability

## Features

### Unified API

Compatible with OpenAI Chat Completions API.

```http
POST /v1/chat/completions
```

### Intelligent Routing

Route requests according to:

* Fastest provider
* Lowest cost
* Highest remaining quota
* Required capabilities
* Custom user policies

### Provider Support

Cloud Providers:

* Gemini
* Groq
* OpenRouter
* Cerebras
* HuggingFace
* TogetherAI
* Fireworks
* DeepInfra

Self Hosted:

* Ollama
* vLLM
* TGI
* llama.cpp

### Reliability

* Automatic retries
* Circuit breakers
* Provider health checks
* Fallback routing

### Quota Management

Track:

* RPM
* TPM
* Daily quotas
* Concurrent requests

### Observability

Prometheus metrics:

* Request count
* Provider latency
* Success rate
* Token consumption
* Quota utilization

## Architecture

Client -> API Gateway -> Router -> Quota Manager -> Provider Adapter -> Provider

## Technology Stack

Backend:

* Python
* FastAPI
* AsyncIO

Storage:

* Redis
* PostgreSQL

Observability:

* Prometheus
* Grafana

Deployment:

* Docker
* Kubernetes
