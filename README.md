# OpenBalancer

> **Aggregate multiple AI providers into a single OpenAI-compatible endpoint.**

OpenBalancer is an **open-source AI inference orchestration platform** that unifies cloud and self-hosted LLM providers behind a single API. It provides intelligent routing, automatic failover, provider health monitoring, multi-user credential management, and an OpenAI-compatible interface while allowing users to securely bring their own provider API keys.

**🌐 [Live Demo](https://openbalancer.up.railway.app/dashboard)**
**📄 [Whitepaper](https://www.overleaf.com/read/kfwpbhjjyjrc#1c8936)**

---

# Dashboard

> <img width="1124" height="929" alt="613293772-59c96729-1d1f-473f-88d4-e8546df21f4b" src="https://github.com/user-attachments/assets/dc139b1a-9a34-45c6-9274-b06918781998" />
> Dashboard Overview


OpenBalancer includes a built-in web dashboard for managing providers, credentials, API keys, and available models.

Features include:

* User authentication
* Secure provider credential management
* OpenBalancer API key generation
* Provider health monitoring
* Available model browser
* Language-specific SDK quickstarts
* Multi-user isolation

---

# Why OpenBalancer?

Modern AI applications rarely rely on a single provider.

Developers often juggle:

* Groq
* OpenRouter
* Gemini
* Hugging Face
* Cerebras
* TogetherAI
* Ollama
* vLLM

Each provider has different:

* Rate limits
* Pricing
* Latency
* Available models
* Reliability

OpenBalancer abstracts these differences away, allowing applications to interact with a single OpenAI-compatible endpoint while intelligently routing requests across multiple providers.

---

# Architecture

> **[Screenshot Placeholder – Architecture Diagram]**

```
                 Browser
                     │
             Dashboard (Jinja2)
                     │
              Authentication
                     │
           OpenBalancer API
                     │
              Routing Engine
                     │
      +--------------+--------------+
      │              │              │
    Groq       OpenRouter      Gemini
      │              │              │
      └──────────────┴──────────────┘
          Additional Providers
```

---

# Key Features

## OpenAI Compatible

Drop-in replacement for OpenAI APIs.

Simply change your base URL.

Compatible with:

* OpenAI SDK
* LiteLLM
* LangChain
* Direct HTTP clients

---

## Multi-User Platform

Each user receives:

* Secure authentication
* Isolated provider credentials
* Personal OpenBalancer API key
* Independent routing decisions

Users never share provider credentials.

---

## Intelligent Routing

Built-in routing policies:

* `balanced`
* `fastest`
* `stable`
* `fallback`
* `cheapest`

Routing decisions consider:

* Provider health
* Latency
* Quotas
* Failures
* Cost
* Cooldown state

---

## Automatic Failover

If a provider becomes unavailable or reaches quota limits, OpenBalancer automatically retries using alternative providers whenever possible.

---

## Supported Providers

### Cloud

* Groq
* OpenRouter
* Gemini
* Cerebras
* Hugging Face
* TogetherAI *(planned)*
* Fireworks *(planned)*
* DeepInfra *(planned)*

### Self Hosted

* Ollama *(planned)*
* vLLM *(planned)*
* Text Generation Inference *(planned)*
* llama.cpp *(planned)*

---

# Dashboard Preview

> <img width="1124" height="929" alt="image" src="https://github.com/user-attachments/assets/864464d7-2edc-4be8-839b-3c1267afb0c0" />
> Provider Management

Manage provider API keys directly from the dashboard.

* Groq
* OpenRouter
* Gemini
* Cerebras
* Hugging Face

---

> <img width="1124" height="929" alt="image" src="https://github.com/user-attachments/assets/83d8f8f8-b389-4db3-8f64-6e4ed6924a9d" />
> Available Models

Browse models aggregated from connected providers.

---

> <img width="1122" height="645" alt="613295525-98b128ba-ba7c-45e3-9322-d5815a1efbec" src="https://github.com/user-attachments/assets/b43c512f-d03b-4a3c-951b-0944ce87ff72" />
> SDK Quickstarts

Generate ready-to-use examples for:

* cURL
* Python Requests
* OpenAI SDK
* TypeScript

---

# Quick Start

Clone the repository

```bash
git clone https://github.com/DevBhuyan/OpenBalancer.git

cd OpenBalancer
```

Install dependencies

```bash
python -m pip install -e ".[dev]"
```

Run the server

```bash
python -m openbalancer
```

---

## Configure Provider Keys

OpenBalancer supports environment variables:

```text
GROQ_API_KEY
OPENROUTER_API_KEY
CEREBRAS_API_KEY
GEMINI_API_KEY
HF_API_KEY
```

or provider credentials through the hosted dashboard.

---

## Send a Request

```bash
curl http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-d '{
  "model":"auto",
  "messages":[
    {
      "role":"user",
      "content":"Hello!"
    }
  ]
}'
```

---

# Routing Policies

Automatic model selection:

* `auto`
* `auto:small`
* `auto:large`

Available routing modes:

| Policy   | Description               |
| -------- | ------------------------- |
| fallback | Provider priority order   |
| fastest  | Lowest observed latency   |
| stable   | Lowest failure rate       |
| balanced | Latency + failures + cost |
| cheapest | Lowest configured cost    |

---

# Benchmarks

> **[Screenshot Placeholder – Benchmark Graph]**

Example benchmark scenarios:

* Capacity aggregation
* Provider failover
* Routing policy comparison
* Concurrent load testing
* Multi-user isolation

Run the benchmark suite:

```bash
python clients/load_test.py
```

---

# API

### Chat Completions

```
POST /v1/chat/completions
```

### Models

```
GET /v1/models
```

### Health

```
GET /health
```

---

# Technology Stack

### Backend

* Python
* FastAPI
* AsyncIO

### Frontend

* HTML
* CSS
* JavaScript
* Jinja2 Templates

### Storage

* SQLite
* PostgreSQL *(planned)*

### Deployment

* Uvicorn
* Docker *(planned)*
* Kubernetes *(planned)*

---

# Roadmap

* [x] OpenAI-compatible API
* [x] Intelligent routing
* [x] Automatic failover
* [x] Multi-user authentication
* [x] Provider credential management
* [x] Web dashboard
* [x] Hosted deployment
* [ ] PostgreSQL migration
* [ ] Usage analytics
* [ ] Dynamic provider scoring
* [ ] Team workspaces
* [ ] Cost optimization
* [ ] Ollama / vLLM integration
* [ ] Prometheus metrics
* [ ] Kubernetes deployment

---

# Contributing

Contributions, feature requests, and bug reports are welcome.

Feel free to open an issue or submit a pull request.

---

# License

Apache 2.0 License.
