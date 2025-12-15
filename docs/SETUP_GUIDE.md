# Setup Guide

This guide walks you through setting up the Chase the Source development environment.

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | LangGraph requires 3.11+ |
| Docker | 20.10+ | Container deployment |
| Docker Compose | 2.0+ | Local orchestration |
| Git | Any | Version control |

### API Keys Required

You will need accounts and API keys from:

1. **OpenAI** - [platform.openai.com](https://platform.openai.com)
   - Used for: GPT-5-mini LLM calls
   - Billing: Pay-per-use

2. **Tavily** - [tavily.com](https://tavily.com)
   - Used for: Web search and source retrieval
   - Free tier: 1,000 searches/month

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd chase_source
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# .env
OPENAI_API_KEY=sk-your-openai-key-here
TAVILY_API_KEY=tvly-your-tavily-key-here

# Optional: Override defaults
OPENAI_MODEL=gpt-5-mini
LOG_LEVEL=INFO
```

### 5. Run the Application

```bash
python app.py
```

The Gradio interface will be available at `http://localhost:7860`

---

## Docker Setup

### Build the Image

```bash
docker build -t chase-the-source .
```

### Run with Docker

```bash
docker run -p 7860:7860 \
  -e OPENAI_API_KEY=sk-your-key \
  -e TAVILY_API_KEY=tvly-your-key \
  chase-the-source
```

### Run with Docker Compose (Recommended)

Create a `.env` file with your keys, then:

```bash
docker compose up
```

For development with hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## File: `requirements.txt`

```
# Core framework
langgraph>=0.2.0
langchain>=0.3.0
langchain-openai>=0.2.0

# Web search
tavily-python>=0.5.0

# UI
gradio>=5.0.0

# Data validation
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Environment management
python-dotenv>=1.0.0

# HTTP client
httpx>=0.27.0

# Development
pytest>=8.0.0
pytest-asyncio>=0.24.0
pytest-cov>=5.0.0

# Type checking (optional)
mypy>=1.11.0
```

---

## File: `.env.example`

```bash
# Required API Keys
OPENAI_API_KEY=sk-your-openai-api-key-here
TAVILY_API_KEY=tvly-your-tavily-api-key-here

# LLM Configuration
OPENAI_MODEL=gpt-5-mini
OPENAI_TEMPERATURE=0.0
OPENAI_MAX_TOKENS=2000

# Tavily Configuration
TAVILY_MAX_RESULTS=10
TAVILY_SEARCH_DEPTH=advanced

# Application Settings
LOG_LEVEL=INFO
GRADIO_SERVER_PORT=7860
GRADIO_SERVER_NAME=0.0.0.0
```

---

## File: `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Gradio port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:7860/')" || exit 1

# Run the application
CMD ["python", "app.py"]
```

---

## File: `docker-compose.yml`

```yaml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "7860:7860"
    env_file:
      - .env
    environment:
      - GRADIO_SERVER_NAME=0.0.0.0
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:7860/')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

---

## File: `docker-compose.dev.yml`

```yaml
# Use with: docker compose -f docker-compose.yml -f docker-compose.dev.yml up
version: "3.8"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - .:/app
      - /app/venv  # Exclude venv from mount
    environment:
      - LOG_LEVEL=DEBUG
      - GRADIO_WATCH=true
    command: ["python", "-u", "app.py"]
```

---

## Verification

After setup, verify your installation:

```bash
# Check Python version
python --version  # Should be 3.11+

# Verify dependencies
pip list | grep -E "langgraph|gradio|tavily"

# Test API connectivity
python -c "
from openai import OpenAI
from tavily import TavilyClient
import os

# Test OpenAI
client = OpenAI()
print('OpenAI: Connected')

# Test Tavily
tavily = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))
print('Tavily: Connected')
"
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: langgraph` | Ensure Python 3.11+ and reinstall requirements |
| `Invalid API key` | Check `.env` file has correct keys without quotes around values |
| `Connection refused on 7860` | Check if another service is using the port |
| `Docker build fails` | Ensure Docker daemon is running |

### Getting Help

1. Check the error message against the troubleshooting table
2. Verify API keys are valid by testing in the provider's playground
3. Ensure all environment variables are set correctly
