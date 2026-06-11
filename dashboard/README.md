# OpenBalancer Dashboard

A minimalistic Reflex-based web dashboard for managing OpenBalancer API keys and provider credentials.

## Quick Start

### Prerequisites
- Python 3.9+
- Dependencies installed: `pip install -e .`

### Run Dashboard

**Terminal 1 - Backend API:**
```bash
python -m uvicorn openbalancer.app:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend Dashboard:**
```bash
cd dashboard
reflex run
```

Then visit: **http://localhost:3000**

## Features

✅ **User Authentication**
- Email/password registration and login
- JWT-based session management
- Secure logout

✅ **Provider Management**
- Add API keys for multiple LLM providers
- Secure credential storage
- Provider health status monitoring

✅ **API Key Management**
- Auto-generated OpenBalancer API keys
- Masked credential display for security
- Easy-to-copy key format

✅ **Quickstart Code**
- Copy-paste ready code snippets
- Multiple languages: Python, cURL, TypeScript, etc.
- Uses your OpenBalancer API key automatically

✅ **Provider Health**
- Real-time status of connected providers
- Health indicators (healthy/degraded/offline)

## Project Structure

```
dashboard/
├── __init__.py       # Package initialization
├── app.py           # Reflex app configuration
├── state.py         # State management (AuthState, DashboardState)
├── pages.py         # UI components (login, dashboard, sections)
├── README.md        # This file
```

## State Management

### AuthState
Handles user authentication:
- Email/password inputs
- Login/logout operations
- Token storage
- Authentication status

### DashboardState
Extends AuthState, handles dashboard data:
- Provider API key management
- OpenBalancer key retrieval
- Health status fetching
- Quickstart code retrieval

## API Endpoints

All endpoints require `Authorization: Bearer <token>` header except `/auth/*` endpoints.

### Authentication
- `POST /auth/register` - Create account
- `POST /auth/login` - Get JWT token
- `POST /auth/logout` - Invalidate token
- `GET /auth/me` - Get user info

### Dashboard
- `GET /api/providers` - Available providers
- `POST /api/user/provider-keys` - Save credentials
- `GET /api/user/provider-keys` - Get saved keys (masked)
- `GET /api/user/openbalancer-key` - Get API key
- `GET /api/providers/health` - Provider status
- `GET /api/quickstart-code?language=python` - Code snippets

## Configuration

Environment variables (in `.env`):
```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///./.data/openbalancer.db
```

## Components

### Pages
- `login_page()` - User registration and login
- `dashboard_page()` - Main dashboard after login
- `navbar()` - Navigation bar with logout

### Sections
- `provider_keys_section()` - Add/manage provider API keys
- `openbalancer_key_section()` - Display OpenBalancer API key
- `quickstart_section()` - Code snippets in multiple languages
- `provider_health_section()` - Provider status display

## Development

### Hot Reload
Changes to `state.py` and `pages.py` are automatically reloaded while running `reflex run`.

### Debugging
- Browser console (F12) for frontend errors
- Terminal output shows backend API calls
- FastAPI docs at http://localhost:8000/docs

### Adding New Features
1. Add state variables to `DashboardState` in `state.py`
2. Add async methods for API calls
3. Create UI components in `pages.py` using those state variables
4. Use `rx.cond()` for conditional rendering

## Styling

Uses Reflex's built-in Chakra UI theme. Customize by:
- Modifying component properties (spacing, colors, sizes)
- Creating custom CSS-in-JS
- Using Chakra UI design tokens

Example:
```python
rx.box(
    rx.text("Hello"),
    background_color="blue.100",
    padding="1rem",
    border_radius="0.5rem"
)
```

## Performance Optimizations

- Async API calls to prevent UI blocking
- Debounced form submissions
- Selective component re-renders using `rx.cond()`
- In-memory caching of provider lists

## Security Best Practices

1. ✅ Never log API keys
2. ✅ Always use HTTPS in production
3. ✅ Mask sensitive data in UI
4. ✅ Use secure password requirements
5. ✅ Implement rate limiting on backend
6. ✅ Rotate JWT secrets regularly
7. ✅ Store tokens in httpOnly cookies

## Troubleshooting

### "Connection refused" error
- Ensure backend is running: `python -m uvicorn openbalancer.app:app`
- Check port 8000 is not in use

### Reflex compilation fails
- Clear cache: `rm -rf dashboard/.web`
- Install Node.js: required by Reflex
- Reinstall Reflex: `pip install --upgrade reflex`

### Blank dashboard page
- Check browser console for errors (F12)
- Verify token is valid: check `/auth/me` endpoint
- Check backend API is accessible

## Next Steps

1. See [DASHBOARD_SETUP.md](../DASHBOARD_SETUP.md) for detailed setup
2. Check [API_KEY_AUTHENTICATION.md](../API_KEY_AUTHENTICATION.md) for auth system details
3. Visit FastAPI docs at http://localhost:8000/docs for API testing

## Contributing

Pull requests welcome! Please:
1. Test changes locally
2. Follow existing code style
3. Update documentation
4. Add UI tests if modifying components

## License

Same as OpenBalancer - See LICENSE file

