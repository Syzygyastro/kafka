# Web Scraper Bot - AI Development Prompt

Use this prompt to continue development or enhance this web scraper.

---

## System Context

You are developing a production-grade web scraping service built with Python FastAPI. The project has these core components:

### Architecture
```
app/
├── main.py              # FastAPI application entry point
├── core/                # Configuration, logging, exceptions
├── api/                 # REST API routes and middleware
├── models/              # Pydantic request/response models
├── strategies/          # Scraping strategies (simple, headless, stealth)
├── services/            # Business logic (scraper, proxy, captcha)
└── utils/               # Helper utilities
```

### Three Scraping Strategies

1. **Simple Strategy** (`strategies/simple.py`)
   - Basic HTTP requests with httpx
   - Randomized user agents via fake-useragent
   - Fastest, lowest resource usage
   - Best for: APIs, simple HTML pages

2. **Headless Strategy** (`strategies/headless.py`)
   - Playwright browser automation
   - Full JavaScript rendering
   - Screenshot capability
   - Best for: JavaScript-heavy sites, SPAs

3. **Stealth Strategy** (`strategies/stealth.py`)
   - Advanced anti-detection measures
   - Browser fingerprint spoofing
   - Human-like behavior simulation (mouse movement, scrolling)
   - Canvas/WebGL fingerprint protection
   - Best for: Sites with bot detection

### Key Services

1. **Proxy Manager** (`services/proxy_manager.py`)
   - Multiple rotation strategies: round-robin, random, weighted, LRU
   - Automatic health checking
   - Success rate tracking
   - Unhealthy proxy removal

2. **Captcha Solver** (`services/captcha_solver.py`)
   - 2Captcha integration
   - Anti-Captcha integration
   - Supports: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile

3. **Scraper Service** (`services/scraper_service.py`)
   - Orchestrates all scraping operations
   - Rate limiting
   - Batch processing with concurrency control
   - Retry logic with exponential backoff

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/stats` | Scraper statistics |
| POST | `/api/v1/scrape` | Scrape single URL |
| POST | `/api/v1/scrape/batch` | Scrape multiple URLs |
| GET | `/api/v1/proxy/stats` | Proxy pool stats |
| GET | `/api/v1/captcha/stats` | Captcha solver stats |

---

## Example API Requests

### Simple Scrape
```json
POST /api/v1/scrape
{
    "url": "https://example.com",
    "strategy": "simple",
    "output_format": "json"
}
```

### Headless with Selectors
```json
POST /api/v1/scrape
{
    "url": "https://example.com",
    "strategy": "headless",
    "selectors": {
        "title": "h1",
        "links": "a[href]"
    },
    "wait_for_selector": ".content",
    "screenshot": true
}
```

### Stealth Mode
```json
POST /api/v1/scrape
{
    "url": "https://example.com",
    "strategy": "stealth",
    "scroll_to_bottom": true,
    "use_proxy": true,
    "solve_captcha": true
}
```

### Batch Scrape
```json
POST /api/v1/scrape/batch
{
    "urls": [
        "https://example1.com",
        "https://example2.com"
    ],
    "strategy": "simple",
    "concurrency": 5
}
```

---

## Configuration (.env)

```env
# Enable/disable features
PROXY_ENABLED=true
CAPTCHA_SOLVER_ENABLED=true

# Proxy list (comma-separated)
PROXY_LIST=http://user:pass@proxy1:8080,http://user:pass@proxy2:8080

# Captcha API keys
CAPTCHA_SOLVER_PROVIDER=2captcha
TWOCAPTCHA_API_KEY=your_key
ANTICAPTCHA_API_KEY=your_key

# Rate limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_PERIOD=60
```

---

## Enhancement Ideas

1. **Add More Captcha Types**
   - FunCaptcha support
   - GeeTest support
   - AWS WAF captcha

2. **Database Integration**
   - Store scrape results in PostgreSQL/MongoDB
   - Job queue with Celery/Redis
   - Scheduled scraping tasks

3. **Additional Strategies**
   - Selenium strategy for legacy browser support
   - API-based scraping for known sites
   - RSS feed scraping

4. **Monitoring & Observability**
   - Prometheus metrics
   - Grafana dashboards
   - Distributed tracing with OpenTelemetry

5. **Advanced Features**
   - Sitemap parsing and crawling
   - Recursive link following
   - Content deduplication
   - Data extraction pipelines

6. **Security Hardening**
   - API key authentication
   - Request signing
   - IP whitelisting
   - Usage quotas

---

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run tests
python -m pytest tests/ -v

# Start server
python run.py serve
# or
uvicorn app.main:app --reload

# Test scraper
python run.py test
```

---

## Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f scraper

# Scale workers
docker-compose up -d --scale scraper=3
```
