# OpenBalancer

OpenBalancer is an open-source LLM routing and load-balancing platform designed to maximize free-tier and low-cost AI inference providers.

This repository now contains a working MVP:

* OpenAI-compatible `POST /v1/chat/completions`
* Provider fallback routing
* Optional fastest-known routing
* Runtime provider health state
* `GET /health`
* `GET /v1/models`
* Adapters for Groq, OpenRouter, Cerebras, and Gemini

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