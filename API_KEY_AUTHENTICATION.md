# OpenBalancer API Key Authentication System

## Overview

A complete API key authentication system has been successfully implemented for OpenBalancer. This system provides:

- **Secure API Key Generation**: Cryptographically secure OpenBalancer API keys (`obk_` prefix)
- **Persistent Storage**: SQLite database (upgradeable to PostgreSQL) for API key management
- **Request Validation**: FastAPI dependency injection for endpoint protection
- **Auto-Bootstrap**: Automatic key generation on first startup
- **In-Memory Caching**: 5-minute TTL cache to reduce database load
- **Provider Credential Mapping**: API keys map to actual provider credentials from environment variables

## What Was Implemented

### 1. **Core Authentication Modules** (`openbalancer/auth/`)

#### `keygen.py` - API Key Generation & Hashing
- `generate_api_key()`: Generates new keys with format `obk_<32-random-hex>`
- `hash_api_key()`: SHA-256 hashing for secure storage
- `verify_api_key()`: Verify plaintext key against stored hash
- `extract_api_key_from_header()`: Parse Authorization header

#### `db.py` - Database Management
- `APIKeyRecord`: SQLAlchemy model for persistent storage
- `DatabaseManager`: Handles database operations
  - `initialize()`: Creates SQLite DB and tables (creates `.data` directory if needed)
  - `get_key_by_hash()`: Retrieve enabled API keys
  - `create_key()`: Store new API key records
  - `update_last_used()`: Track usage for future auditing
  - `disable_key()`: Revoke compromised keys
  - `get_all_keys()`: Admin access to all keys

#### `middleware.py` - Request Validation
- `APIKeyValidator`: In-memory cache + database validation
  - `validate()`: Authenticate requests and cache results (5min TTL)
  - `clear_cache()`: Manual cache invalidation
  - `get_cache_size()`: Monitor cache usage
- `verify_api_key_dependency()`: FastAPI dependency for endpoint protection

#### `bootstrap.py` - Auto-Key Generation
- `bootstrap_api_key()`: Auto-generate key on startup if missing
- `get_provider_credentials_from_env()`: Capture current env variables
- Key saved to `.env` file automatically (shown once to user)

#### `exceptions.py` - Custom Exceptions
- `InvalidAPIKeyError`: Base authentication error
- `APIKeyNotFoundError`: Key not in database
- `MissingAPIKeyError`: No Authorization header
- `DatabaseError`: DB operation failures

### 2. **Integration into FastAPI App** (`app.py`)

```python
# Database and validator initialized at startup
db_manager = DatabaseManager(settings.auth_db_path)
db_manager.initialize()
api_key_validator = APIKeyValidator(db_manager, cache_ttl_seconds=settings.auth_cache_ttl_seconds)

# Dependency functions for endpoints
async def verify_api_key(request: Request) -> dict
async def optional_verify_api_key(request: Request) -> dict  # For optional auth

# Startup event bootstraps the API key
@app.on_event("startup")
async def startup_event():
    if settings.require_api_key:
        bootstrap_api_key(db_manager)
```

**Protected Endpoints:**
- ✅ `POST /v1/chat/completions` - Requires API key
- ✅ `GET /v1/models` - Requires API key (optional by settings)

**Public Endpoints:**
- ✅ `GET /health` - No authentication needed
- ✅ `GET /docs` - Documentation endpoint

### 3. **Configuration** (`settings.py`)

New settings added:
```python
require_api_key: bool = True                              # Enable/disable auth
openbalancer_api_key: Optional[str] = None               # Loaded from .env
auth_db_path: str = "sqlite:///./.data/openbalancer.db"  # SQLite path (changeable for PostgreSQL)
auth_cache_ttl_seconds: int = 300                        # 5-minute cache TTL
```

### 4. **Dependencies**

Added to `pyproject.toml`:
```toml
sqlalchemy>=2.0.0  # ORM for database management
```

## How It Works

### First Startup Flow

1. App starts and initializes `DatabaseManager`
2. Creates `.data/` directory and SQLite database
3. Bootstrap event fires:
   - Generates new API key: `obk_1a2a1d9d34b5400c5042943a05bf6930`
   - Captures all environment provider credentials
   - Stores key hash in database (plaintext key never stored)
   - Writes plaintext key to `.env` file
   - **Prints key to console once** (user must save it)

### Request Authentication Flow

1. Client sends request with `Authorization: Bearer obk_...` header
2. `verify_api_key_dependency()` extracts key from header
3. Validator checks in-memory cache first (5min TTL)
4. Cache miss → query database for key hash
5. If found and enabled → cache result and allow request
6. If not found → return 401 Unauthorized
7. Update `last_used` timestamp in database (non-blocking)

### Database Schema

```sql
CREATE TABLE api_keys (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    key_hash VARCHAR(64) UNIQUE NOT NULL,    -- SHA-256 hash
    provider_credentials TEXT NOT NULL,      -- JSON with provider keys
    created_at DATETIME NOT NULL,            -- When key was created
    last_used DATETIME,                      -- Last time used
    enabled VARCHAR(1) NOT NULL,             -- Y or N
    description VARCHAR(255)                 -- For future dashboard
);
```

## Usage

### Making API Requests

**Without API Key (Will be rejected):**
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "hello"}]}'
# Returns 401: Missing or invalid Authorization header
```

**With Valid API Key:**
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer obk_1a2a1d9d34b5400c5042943a05bf6930" \
  -H "Content-Type: application/json" \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "hello"}]}'
# Returns 200 with chat response
```

**Get Available Models:**
```bash
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer obk_1a2a1d9d34b5400c5042943a05bf6930"
```

**Check Health (No Auth Required):**
```bash
curl http://localhost:8000/health
# Returns provider health status
```

## Testing Results ✅

All tests passed:

| Test | Result |
|------|--------|
| Missing API key → 401 | ✅ PASS |
| Invalid API key → 401 | ✅ PASS |
| Valid API key → 200 | ✅ PASS |
| /health without auth → 200 | ✅ PASS |
| /v1/chat/completions with key → 200 | ✅ PASS |
| Database creation | ✅ PASS |
| .env file update | ✅ PASS |
| Auto key generation | ✅ PASS |

## Configuration Options

### Enable/Disable Authentication
```python
# In .env or environment
REQUIRE_API_KEY=true   # Set to false to disable auth (not recommended)
```

### Switch to PostgreSQL
```python
# In .env
AUTH_DB_PATH=postgresql://user:password@localhost/openbalancer
```

### Adjust Cache TTL
```python
# In .env
AUTH_CACHE_TTL_SECONDS=600  # Default is 300 (5 minutes)
```

## Future Enhancements

The system is designed to support:

1. **Dashboard Integration**: Manage multiple API keys per user
2. **Key Rotation**: Disable old keys, generate new ones
3. **Usage Quotas**: Track requests per key
4. **Expiration**: Auto-expire keys after X days
5. **Per-Key Rate Limiting**: Limit requests per API key
6. **Audit Trail**: Log authentication attempts and usage
7. **Custom Scopes**: Restrict keys to specific models/endpoints

## Files Added

```
openbalancer/
├── auth/
│   ├── __init__.py          # Module exports
│   ├── bootstrap.py         # Auto-key generation
│   ├── db.py               # Database models & management
│   ├── exceptions.py       # Custom exceptions
│   ├── keygen.py          # Key generation & hashing
│   └── middleware.py      # FastAPI dependencies
├── app.py                 # Updated with auth integration
└── settings.py           # Updated with auth config

.data/
└── openbalancer.db       # SQLite database (auto-created)

pyproject.toml            # Updated with SQLAlchemy dependency
```

## Security Notes

⚠️ **Important Considerations:**

1. **Key Protection**: API keys are SHA-256 hashed before storage (plaintext never stored)
2. **First Display Only**: Plaintext key shown once on generation, saved to .env
3. **In-Memory Cache**: 5-minute TTL reduces DB queries but maintains reasonable security
4. **Environment Variables**: Provider credentials captured from environment at key creation time
5. **Production Deployment**: 
   - Use HTTPS/TLS for all API requests
   - Store `.env` securely (not in git)
   - Use PostgreSQL for multi-instance deployments
   - Implement key rotation policy
   - Consider adding rate limiting per key

## Support

For future enhancements or questions about the API key system, refer to the auth module documentation or create an issue in the repository.
