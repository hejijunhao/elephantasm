# Elephantasm Backend API

FastAPI backend for the Elephantasm project.

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**

   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

   On Windows:
   ```bash
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Running the Server

**Development mode with auto-reload:**
```bash
python main.py
```

**Or using uvicorn directly:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Root:** http://localhost:8000
- **Interactive Docs (Swagger UI):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/api/v1/health

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py              # Main API router
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── health.py       # Health check endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # App configuration
│   ├── models/                     # SQLModel database models
│   │   └── __init__.py
│   ├── domain/                     # Domain operations & business logic
│   │   ├── __init__.py
│   │   └── example_operations.py  # Example operations pattern
│   └── services/                   # Additional services (external APIs, etc.)
│       └── __init__.py
├── tests/                          # Test files
│   └── __init__.py
├── main.py                         # Application entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment variables
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

## 🛠️ Development

### Adding New Endpoints

1. Create a new file in `app/api/v1/endpoints/` (e.g., `users.py`)
2. Define your router and endpoints:
   ```python
   from fastapi import APIRouter

   router = APIRouter()

   @router.get("/users")
   async def get_users():
       return {"users": []}
   ```

3. Register the router in `app/api/v1/api.py`:
   ```python
   from app.api.v1.endpoints import health, users

   api_router.include_router(users.router, prefix="/users", tags=["users"])
   ```

### Running Tests

```bash
pytest
```

### Code Style

This project follows PEP 8 style guidelines. Consider using:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

## 📝 Configuration

Configuration is managed through environment variables. See `.env.example` for available options.

Key configuration areas:
- **API Settings:** Project name, version, API prefix
- **CORS:** Allowed origins for cross-origin requests
- **Security:** Secret key, token expiration
- **Database:** Database connection settings (when needed)

## 🔐 Security

- Change the `SECRET_KEY` in production
- Use strong passwords for database connections
- Configure CORS origins appropriately for your frontend
- Keep dependencies up to date

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These provide interactive API documentation where you can test endpoints directly.

## 🤝 Contributing

When adding new features:
1. Define SQLModel models in `app/models/` (combines validation + ORM)
2. Implement domain operations in `app/domain/` (CRUD + business logic)
3. Create API endpoints in `app/api/v1/endpoints/` that use domain operations
4. Add external service integrations in `app/services/` if needed
5. Write tests in `tests/`

### Architecture Pattern

This project uses a **domain-driven** architecture:
- **models/**: SQLModel definitions (database + validation in one)
- **domain/**: Business logic and domain operations (the "how")
- **api/endpoints/**: HTTP layer that calls domain operations (the "what")
- **services/**: External integrations (email, S3, third-party APIs, etc.)

## 📦 Dependencies

Main dependencies:
- **FastAPI:** Modern web framework for building APIs
- **Uvicorn:** ASGI server
- **Pydantic:** Data validation using Python type hints
- **python-jose:** JWT token handling
- **passlib:** Password hashing

See `requirements.txt` for the complete list.
