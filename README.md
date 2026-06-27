# <img width="32" height="32" alt="favicon-32x32" src="https://github.com/user-attachments/assets/513a637b-3d02-4949-ba35-00e7c62196c4" /> OpenBalancer

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

_Why shouldn't I just use Groq directly?_
<img width="768" height="432" alt="Successful requests under concurrent load" src="https://github.com/user-attachments/assets/24147867-1b7a-4111-8474-293dde26565f" />
| Configuration    | Successful |  Failed | Success Rate |
| ---------------- | ---------: | ------: | -----------: |
| Groq             |        140 |     360 |        28.0% |
| OpenRouter       |        254 |     246 |        50.8% |
| **OpenBalancer** |    **291** | **209** |    **58.2%** |


<img width="768" height="432" alt="Provider utilization" src="https://github.com/user-attachments/assets/e492367a-293b-4b67-bd2f-420ec864b865" />

| Provider     | Requests |
| ------------ | -------: |
| OpenRouter   |      139 |
| Groq         |      110 |
| Hugging Face |       30 |
| Cerebras     |       12 |


## What differentiates OpenBalancer from other providers?
| Feature                        | Direct Provider | OpenBalancer |
| ------------------------------ | :-------------: | :----------: |
| OpenAI-compatible API          |        ✅        |       ✅      |
| Automatic failover             |        ❌        |       ✅      |
| Multi-provider routing         |        ❌        |       ✅      |
| Provider health monitoring     |        ❌        |       ✅      |
| Routing policies               |        ❌        |       ✅      |
| Multi-user support             |        ❌        |       ✅      |
| Provider credential management |        ❌        |       ✅      |
| Dashboard                      |        ❌        |       ✅      |
| Vendor lock-in                 |       High      |     None     |

---

# Architecture

> <img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/09edd26d-d48e-4462-985c-cdad541ea975" />
> Architecture Diagram

```
Incoming Request
        │
        ▼
Authenticate User
        │
        ▼
Load User Provider Keys
        │
        ▼
Discover Healthy Providers
        │
        ▼
Apply Routing Policy
        │
        ▼
Try Selected Provider
        │
        │ Success?
   ┌────┴─────┐
   │          │
 Yes         No
   │          │
   ▼          ▼
 Return   Cooldown Provider
 Response       │
                ▼
        Select Next Provider
                │
                ▼
         Retry Request
```
> Routing lifecycle

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

> <img width="768" height="432" alt="Successful requests under concurrent load" src="https://github.com/user-attachments/assets/7dd934c5-0097-4d62-8f35-8e509a26a313" />

> Benchmark Graph

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
