# OpenBalancer Dashboard Setup Guide

## Overview

The OpenBalancer Dashboard is a Reflex-based web interface that allows users to:
- **Authenticate**: Sign up and log in with email/password
- **Manage Provider API Keys**: Store API keys for multiple LLM providers (Groq, OpenRouter, Cerebras, Gemini, Hugging Face)
- **Get OpenBalancer API Key**: Generate and view their personal OpenBalancer API key for accessing the load balancer
- **View Provider Status**: See the health status of connected providers
- **Get Quickstart Code**: View code snippets in multiple languages (Python, cURL, TypeScript, etc.)

## Architecture

### Backend (FastAPI)
- **Authentication Endpoints** (`/auth/*`):
  - `POST /auth/register` - Create new user account
  - `POST /auth/login` - Authenticate and get JWT token
  - `POST /auth/logout` - Invalidate session
  - `GET /auth/me` - Get current user info

- **Dashboard API** (`/api/*`):
  - `GET /api/providers` - List available providers
  - `GET /api/user/provider-keys` - Get user's provider keys (masked)
  - `POST /api/user/provider-keys` - Update provider credentials
  - `GET /api/user/openbalancer-key` - Get user's OpenBalancer API key
  - `GET /api/providers/health` - Get provider health status
  - `GET /api/quickstart-code` - Get code snippets in various languages

### Frontend (Reflex)
- **State Management**: Handles authentication, form inputs, and API communication
- **Pages**:
  - Login page with registration option
  - Dashboard with provider management, API key display, and quickstart code

### Database
- **Users Table**: User accounts with email and password hash
- **UserSessions Table**: Valid JWT tokens with expiration
- **UserAPIKeys Table**: OpenBalancer API keys linked to users with provider credentials

## Setup Instructions

### 1. Install Dependencies

Dependencies are already listed in `pyproject.toml`. Reinstall if needed:

```bash
cd "LLM Load Balancer"
pip install -e . --upgrade
```

Key dependencies:
- `reflex>=0.4.0` - Frontend framework
- `python-jose[cryptography]>=3.3.0` - JWT token handling
- `passlib[bcrypt]>=1.7.4` - Password hashing
- `email-validator>=2.0.0` - Email validation

### 2. Configure Environment Variables (Optional)

Edit `.env` file to customize settings:

```bash
# Authentication settings
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Database (if using PostgreSQL instead of SQLite)
DATABASE_URL=sqlite:///./.data/openbalancer.db
```

### 3. Initialize Database

The database is automatically initialized on first app startup. Tables created:
- `users` - User accounts
- `user_sessions` - Active JWT sessions
- `user_api_keys` - OpenBalancer keys per user
- `api_keys` - Legacy API key support (optional)

## Running the Application

### Option 1: Run Both API and Dashboard (Recommended)

#### Terminal 1 - Start FastAPI Backend
```bash
cd "LLM Load Balancer"
python -m uvicorn openbalancer.app:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
...
```

#### Terminal 2 - Start Reflex Frontend
```bash
cd "LLM Load Balancer/dashboard"
reflex run
```

Expected output:
```
Compiled successfully!
Frontend: http://localhost:3000
Backend: http://localhost:8000
```

Access the dashboard at: **http://localhost:3000**

### Option 2: Run API Only

If you want to use the API programmatically without the UI:

```bash
python -m uvicorn openbalancer.app:app --host 0.0.0.0 --port 8000
```

Then interact with:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Auth: POST http://localhost:8000/auth/register

## Usage Workflow

### 1. Register/Login
- Visit http://localhost:3000
- Click "Sign up" for new users or enter credentials for existing users
- Enter email and password
- Click "Login" or "Sign up"

### 2. Add Provider API Keys
- On the dashboard, fill in provider API keys:
  - **Groq**: `gsk_...`
  - **OpenRouter**: `sk_...`
  - **Cerebras**: `csk_...`
  - **Gemini**: `AIzaSy...`
  - **Hugging Face**: `hf_...`
- Click "Save Provider Credentials"
- Your OpenBalancer API key will be generated

### 3. Get Your OpenBalancer API Key
- After saving provider credentials, the API key appears in the "Your OpenBalancer API Key" section
- The key format is `obk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Use this key in the `Authorization: Bearer <key>` header

### 4. View Quickstart Code
- Select your preferred language (Python, cURL, TypeScript, etc.)
- Copy the code snippet
- Replace `obk_...` with your actual OpenBalancer API key

### 5. Check Provider Status
- View the "Provider Status" section to see which providers are online
- Status indicators: `healthy`, `degraded`, or `offline`

## API Usage Examples

### Using cURL
```bash
API_KEY="obk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto:small",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Using Python
```python
import requests

api_key = "obk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers=headers,
    json={
        "model": "auto:small",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)

print(response.json())
```

### Using OpenAI SDK
```python
from openai import OpenAI

client = OpenAI(
    api_key="obk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="auto:small",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

## File Structure

```
LLM Load Balancer/
├── openbalancer/
│   ├── app.py                    # Main FastAPI app with CORS and routers
│   ├── auth/
│   │   ├── db.py                 # Database models (User, UserSession, UserAPIKey)
│   │   ├── user_auth.py          # Password hashing and JWT utilities
│   │   ├── keygen.py             # API key generation
│   │   ├── middleware.py         # FastAPI dependencies
│   │   ├── bootstrap.py          # Auto-key generation
│   │   └── exceptions.py         # Custom exceptions
│   ├── routers/
│   │   ├── user_auth.py          # Authentication endpoints
│   │   └── dashboard.py          # Dashboard API endpoints
│   └── ...
├── dashboard/
│   ├── state.py                  # Reflex state management
│   ├── pages.py                  # UI components
│   ├── app.py                    # Reflex app configuration
│   └── __init__.py
└── ...
```

## Security Considerations

### Password Security
- Passwords are hashed using bcrypt (not stored in plaintext)
- Minimum password strength recommendations:
  - At least 12 characters
  - Mix of uppercase, lowercase, numbers, special characters
  - Avoid dictionary words and personal information

### API Key Security
- API keys are hashed before storage
- Provider credentials are stored as JSON in encrypted format
- Never expose plaintext keys in logs or frontend code
- Keys are included in Authorization header only during API calls

### JWT Tokens
- Tokens expire after 30 minutes (configurable)
- Store tokens securely (httpOnly cookies recommended for production)
- Always use HTTPS in production

### CORS
- Currently allows all origins for development (`allow_origins=["*"]`)
- **For production**: Restrict to specific domains:
  ```python
  allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"]
  ```

## Troubleshooting

### Dashboard Shows "Connection Error"
- Check if FastAPI backend is running on `http://localhost:8000`
- Verify CORS is enabled in `openbalancer/app.py`
- Check browser console for specific error messages

### "Invalid or expired token"
- Token may have expired (default: 30 minutes)
- Log in again to get a new token
- Check browser's local storage for token

### Provider Keys Not Saving
- Verify all required fields are filled
- Check browser console for API error details
- Ensure backend is running and accessible

### Reflex Compilation Errors
- Clear Reflex cache: `rm -rf dashboard/.web`
- Restart Reflex: `reflex run`
- Check Node.js installation: `node --version`

## Advanced Configuration

### Change JWT Expiration
Edit `openbalancer/auth/user_auth.py`:
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Change from 30 to 60
```

### Use PostgreSQL Instead of SQLite
Edit `.env`:
```bash
DATABASE_URL=postgresql://user:password@localhost/openbalancer
```

### Customize CORS Origins
Edit `openbalancer/app.py`:
```python
allow_origins=["https://yourdomain.com"]
```

### Enable HTTPS
Use a reverse proxy (nginx) or modify Uvicorn:
```bash
python -m uvicorn openbalancer.app:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

## Future Enhancements

- [ ] OAuth2 authentication (Google, GitHub)
- [ ] API key expiration and rotation
- [ ] Usage analytics and quota management
- [ ] Multi-user team support
- [ ] API key scoping (read-only, write-only)
- [ ] Rate limiting per API key
- [ ] Webhook notifications
- [ ] Mobile app support

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs: `http://localhost:8000/docs`
3. Check frontend console: F12 → Console tab
4. Open an issue on GitHub with:
   - Error messages
   - Steps to reproduce
   - System information
   - Terminal output

## API Documentation

After starting the backend, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide interactive API documentation and testing capabilities.
